import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.parse
import uuid
import winreg
from multiprocessing.connection import Client
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import launch_integration as launch


def request(ticket='opaque+ticket:part',version='2015',url='https://www.hexagon.pw/game/Join.ashx?place=1'):
    return 'hexagon-player:1+launchmode:play+gameinfo:'+ticket+'+placelauncherurl:'+urllib.parse.quote(url,safe='')+'+version:'+version


class ProtocolTests(unittest.TestCase):
    def test_launch_fields_preserve_opaque_ticket_and_encoded_url(self):
        self.assertEqual(launch.parse_protocol(request()),('2015','opaque+ticket:part','https://www.hexagon.pw/game/Join.ashx?place=1'))

    def test_non_vr_launch_modes_are_left_to_the_official_launcher(self):
        self.assertEqual(launch.parse_protocol('hexagon-player:1+launchmode:edit+gameinfo:test'),(None,None,None))

    def test_legacy_same_origin_http_join_is_upgraded_to_https(self):
        self.assertEqual(launch.parse_protocol(request(url='http://www.hexagon.pw/game/Join.ashx?place=1'))[2],'https://www.hexagon.pw/game/Join.ashx?place=1')

    def test_foreign_join_origins_and_injected_fields_are_rejected(self):
        for uri in (request(url='https://other.example/game/Join.ashx'),request(url='https://user@www.hexagon.pw/game/Join.ashx'),request()+'+version:2015',request()+'"'):
            with self.subTest(uri=uri),self.assertRaises(ValueError):launch.parse_protocol(uri)

    def test_launch_ticket_goes_to_stdin_not_to_a_file_or_loader_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);client=root/'Hexagon/Versions/version-test/RobloxPlayerBeta.exe';client.parent.mkdir(parents=True);client.write_bytes(b'test client')
            native=root/'native';native.mkdir()
            class Input(io.BytesIO):
                def close(self):self.saved=self.getvalue();super().close()
            class Process:
                stdin=Input()
                def poll(self):pidfile.write_text('12345');return None
            process=Process()
            def start(args,**kwargs):
                nonlocal pidfile
                pidfile=Path(args[-1]);self.assertNotIn('opaque+ticket:part',' '.join(args));return process
            pidfile=None
            with patch.dict(os.environ,{'LOCALAPPDATA':str(root)}),patch.object(launch,'PLAYER_HASH',hashlib.sha256(b'test client').hexdigest()),patch.object(launch.subprocess,'Popen',side_effect=start):
                game=launch.launch_player(request(),native)
            self.assertEqual(game.pid,12345)
            self.assertIn(b'opaque+ticket:part',process.stdin.saved)
            self.assertEqual(list(native.iterdir()),[])


class WindowsRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.scheme='hexagonvr-test-'+uuid.uuid4().hex
        self.key='Software\\Classes\\'+self.scheme+'\\shell\\open\\command'
        self.original='"C:\\test\\original.exe" "%1"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,self.key) as key:
            winreg.SetValueEx(key,'',0,winreg.REG_SZ,self.original)
        self.redirect=launch.RegistryRedirect('"C:\\test\\replacement.exe" "%1"',Path(self.temp.name)/'state.json',self.scheme)

    def tearDown(self):
        parts=self.key.split('\\')
        # Only this test's randomly named protocol is removed.
        while len(parts)>=3:
            try:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,'\\'.join(parts))
            except FileNotFoundError:pass
            parts.pop()
        self.temp.cleanup()

    def test_original_association_is_restored_exactly(self):
        state=self.redirect.install('unused',b'key')
        self.assertEqual(self.redirect.user_value()[0],self.redirect.replacement)
        self.redirect.restore(state)
        self.assertEqual(self.redirect.user_value(),(self.original,winreg.REG_SZ))
        self.assertFalse(self.redirect.path.exists())

    def test_an_external_association_change_is_preserved(self):
        state=self.redirect.install('unused',b'key')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,self.key) as key:winreg.SetValueEx(key,'',0,winreg.REG_SZ,'other launcher')
        self.redirect.restore(state)
        self.assertEqual(self.redirect.user_value()[0],'other launcher')

    def test_real_authenticated_pipe_delivers_uri_and_restores_registration(self):
        host=launch.ProtocolHost(Path(self.temp.name))
        host.suffix=self.scheme
        host.endpoint='\\\\.\\pipe\\'+self.scheme
        host.redirect=self.redirect
        host.start()
        try:
            with Client(host.endpoint,family='AF_PIPE',authkey=host.authkey) as connection:
                connection.send_bytes(request().encode())
                self.assertTrue(connection.poll(3))
                self.assertEqual(connection.recv_bytes(16),b'ok')
            self.assertEqual(host.requests.get(timeout=3),request())
        finally:host.close()
        self.assertEqual(self.redirect.user_value()[0],self.original)


if __name__=='__main__':unittest.main()
