import contextlib,io,sys,types,unittest
from unittest.mock import patch,Mock
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
import bridge

class LauncherTests(unittest.TestCase):
    def run_waiting(self,hwnd=None,transport_error=None):
        vr=types.ModuleType('openvr');vr.init=Mock(side_effect=AssertionError('SteamVR started without a supported game'))
        output=io.StringIO()
        with patch.object(sys,'argv',['HexagonVR.exe','--seconds','.05']),patch.dict(sys.modules,{'openvr':vr}),patch.object(bridge,'find_player_window',return_value=hwnd),patch.object(bridge,'window_pid',return_value=42),patch.object(bridge,'configure_console'),patch('client_transport.LocalTransport',side_effect=transport_error),contextlib.redirect_stdout(output):
            bridge.main()
        vr.init.assert_not_called()
        self.assertEqual(output.getvalue(),'Launch SteamVR and connect your headset.\nenter a game with support for hexagonVR\n')
    def test_no_game_does_not_start_steamvr(self):self.run_waiting()
    def test_unsupported_game_does_not_start_steamvr(self):self.run_waiting(123,RuntimeError('No mailbox'))
    def test_closed_game_while_waiting_for_headset_returns_to_game_wait(self):
        class Error(Exception):pass
        vr=types.ModuleType('openvr');vr.OpenVRError=Error;vr.VRApplication_Scene=1;vr.VRApplication_Background=2
        vr.init=Mock(side_effect=Error('No headset'))
        transport=Mock();transport.push.side_effect=OSError('Client closed')
        output=io.StringIO()
        with patch.object(sys,'argv',['HexagonVR.exe','--seconds','.4']),patch.dict(sys.modules,{'openvr':vr}),patch.object(bridge,'find_player_window',return_value=123),patch.object(bridge,'window_pid',return_value=42),patch.object(bridge,'configure_console'),patch('client_transport.LocalTransport',return_value=transport),contextlib.redirect_stdout(output):bridge.main()
        self.assertEqual(vr.init.call_count,1);transport.close.assert_called_once()
        self.assertEqual(output.getvalue().splitlines(),['Launch SteamVR and connect your headset.','enter a game with support for hexagonVR','Launch SteamVR and connect your headset to continue.','enter a game with support for hexagonVR'])

if __name__=='__main__':unittest.main()
