"""Temporary per-user Hexagon launch routing for early native initialization.

Authentication tickets travel through an authenticated local pipe and stdin.
They are never written to a configuration file or printed.
"""
from pathlib import Path
import ctypes as C
import hashlib
import json
import os
import queue
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.parse
import winreg
from multiprocessing import AuthenticationError
from multiprocessing.connection import Client, Listener

SCHEME = 'hexagon-player'
PLAYER_HASH = '432aa5e86c66275d1a27c4e5c6833c8a23ccc0d8e9114eef7c134ba2d6953b9d'


def state_path():
    return Path(os.environ['LOCALAPPDATA']) / 'HexagonVR' / 'launch-state.json'


def parse_protocol(uri):
    if len(uri) > 65536 or any(c in uri for c in '\r\n\x00"') or not uri.startswith(SCHEME + ':1+'):
        raise ValueError('Invalid Hexagon launch request')
    parts = re.split(r'\+(?=(?:launchmode|gameinfo|placelauncherurl|version):)', uri.split(':1+', 1)[1])
    fields = {}
    for part in parts:
        name, sep, value = part.partition(':')
        if not sep or name in fields:
            raise ValueError('Invalid Hexagon launch fields')
        fields[name] = value
    if fields.get('launchmode') != 'play':
        return None, None, None
    if not fields.get('gameinfo') or not fields.get('version'):
        raise ValueError('Incomplete Hexagon launch request')
    url = urllib.parse.unquote(fields.get('placelauncherurl', ''))
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http','https') or parsed.hostname not in ('hexagon.pw', 'www.hexagon.pw') or parsed.username or parsed.password:
        raise ValueError('Unsupported Hexagon join origin')
    if not parsed.path.lower().endswith('/join.ashx'):
        raise ValueError('Unsupported Hexagon join endpoint')
    return fields['version'], fields['gameinfo'], urllib.parse.urlunsplit(parsed._replace(scheme='https'))


class RegistryRedirect:
    def __init__(self, replacement, path=None, scheme=SCHEME):
        self.replacement = replacement
        self.path = path or state_path()
        self.key = 'Software\\Classes\\' + scheme + '\\shell\\open\\command'

    def user_value(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.key) as key:
                return winreg.QueryValueEx(key, '')
        except FileNotFoundError:
            return None

    def restore(self, state):
        if self.user_value() == (state['replacement'], winreg.REG_SZ):
            old = state['user_original']
            if old is not None:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.key) as key:
                    winreg.SetValueEx(key, '', 0, old[1], old[0])
            else:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.key, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, '')
                # Remove only empty keys created for this one protocol override.
                parts = self.key.split('\\')
                while len(parts) >= 3:
                    name = '\\'.join(parts)
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, name) as key:
                            children, values, _ = winreg.QueryInfoKey(key)
                        if children or values:
                            break
                        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, name)
                    except FileNotFoundError:
                        pass
                    parts.pop()
            self.notify_shell()
        self.path.unlink(missing_ok=True)

    @staticmethod
    def notify_shell():
        shell=C.WinDLL('shell32')
        shell.SHChangeNotify.argtypes=[C.c_long,C.c_uint,C.c_void_p,C.c_void_p]
        shell.SHChangeNotify(0x08000000,0,None,None)

    def install(self, endpoint, key):
        if self.path.exists():
            self.restore(json.loads(self.path.read_text()))
        old = self.user_value()
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, self.key.removeprefix('Software\\Classes\\')) as handle:
            original, kind = winreg.QueryValueEx(handle, '')
        if not isinstance(original, str) or kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            raise RuntimeError('Unsupported Hexagon launch registration')
        state = dict(replacement=self.replacement, user_original=old, original=original,
                     endpoint=endpoint, key=key.hex(), pid=os.getpid())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2))
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.key) as handle:
                winreg.SetValueEx(handle, '', 0, winreg.REG_SZ, self.replacement)
            self.notify_shell()
        except Exception:
            self.path.unlink(missing_ok=True)
            raise
        return state


def forward_original(command, uri):
    shell = C.WinDLL('shell32', use_last_error=True)
    kernel = C.WinDLL('kernel32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [C.c_wchar_p, C.POINTER(C.c_int)]
    shell.CommandLineToArgvW.restype = C.POINTER(C.c_wchar_p)
    kernel.LocalFree.argtypes = [C.c_void_p]
    count = C.c_int()
    values = shell.CommandLineToArgvW(os.path.expandvars(command), C.byref(count))
    if not values:
        raise RuntimeError('Could not read the original Hexagon launch command')
    try:
        args = [values[i] for i in range(count.value)]
    finally:
        kernel.LocalFree(C.cast(values, C.c_void_p))
    found = any('%1' in arg or '%L' in arg for arg in args)
    args = [arg.replace('%1', uri).replace('%L', uri) for arg in args]
    if not found:
        args.append(uri)
    return subprocess.Popen(args)


def handle_protocol(uri):
    parse_protocol(uri)
    path = state_path()
    if not path.exists():
        raise RuntimeError('HexagonVR launch state is missing; reopen the regular Hexagon launcher')
    state = json.loads(path.read_text())
    try:
        C.WinDLL('user32').AllowSetForegroundWindow(C.c_uint32(state['pid']))
        with Client(state['endpoint'], family='AF_PIPE', authkey=bytes.fromhex(state['key'])) as connection:
            connection.send_bytes(uri.encode('utf8'))
            if not connection.poll(5) or connection.recv_bytes(16) != b'ok':
                raise RuntimeError('The running HexagonVR helper could not accept the launch')
        return
    except (FileNotFoundError, ConnectionError, OSError):
        RegistryRedirect(state['replacement'], path).restore(state)
        forward_original(state['original'], uri)


def launch_player(uri, directory):
    version, ticket, url = parse_protocol(uri)
    if version != '2015':
        raise ValueError('This renderer supports the 2015 client')
    base = Path(os.environ['LOCALAPPDATA']) / 'Hexagon' / 'Versions'
    candidates = list(base.glob('*/RobloxPlayerBeta.exe'))
    exe = next((p for p in candidates if hashlib.sha256(p.read_bytes()).hexdigest() == PLAYER_HASH), None)
    if exe is None:
        raise RuntimeError('Install the supported Hexagon 2015 client with the regular launcher first')
    directory = Path(directory).resolve()
    pidfile = directory / ('player-' + secrets.token_hex(8) + '.pid')
    args = subprocess.list2cmdline(['-a', 'https://www.hexagon.pw/Login/Negotiate.ashx', '-t', ticket, '-j', url])
    process = subprocess.Popen([str(directory / 'HexagonVRStudioLoader.exe'), '--player', str(exe),
                                str(directory / 'HexagonVRNative.dll'), str(pidfile)],
                               stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        process.stdin.write(args.encode('utf8'))
        process.stdin.close()
        deadline = time.monotonic() + 25
        while not pidfile.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        if not pidfile.exists():
            raise RuntimeError('The early graphics launcher did not start; check Windows Security for a blocked component')
        pid = int(pidfile.read_text())
    finally:
        pidfile.unlink(missing_ok=True)
    from native_renderer import NativeGame
    return NativeGame(process, pid)


class ProtocolHost:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.requests = queue.Queue(maxsize=4)
        self.stopping = threading.Event()
        self.games = []
        user = os.environ.get('USERDOMAIN', '') + '\\' + os.environ.get('USERNAME', '')
        self.suffix = hashlib.sha256(user.encode()).hexdigest()[:20]
        self.endpoint = '\\\\.\\pipe\\HexagonVR.Launch.' + self.suffix
        self.authkey = secrets.token_bytes(32)
        command = [sys.executable]
        if not getattr(sys, 'frozen', False):
            command.append(str(Path(__file__).resolve().parent / 'bridge.py'))
        self.redirect = RegistryRedirect(subprocess.list2cmdline(command) + ' --protocol "%1"')
        self.listener = None
        self.thread = None
        self.state = None
        self.mutex = None

    def start(self):
        kernel = C.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [C.c_void_p, C.c_int, C.c_wchar_p]
        kernel.CreateMutexW.restype = C.c_void_p
        self.mutex = kernel.CreateMutexW(None, False, 'Local\\HexagonVR.Launch.' + self.suffix)
        if not self.mutex or C.get_last_error() == 183:
            if self.mutex:
                kernel.CloseHandle(C.c_void_p(self.mutex))
                self.mutex = None
            raise RuntimeError('HexagonVR is already running')
        try:
            self.listener = Listener(self.endpoint, family='AF_PIPE', authkey=self.authkey)
            self.state = self.redirect.install(self.endpoint, self.authkey)
            self.thread = threading.Thread(target=self._serve, daemon=True)
            self.thread.start()
        except Exception:
            self.close()
            raise

    def _serve(self):
        # close() sends an authenticated stop packet; keep accepting until it
        # arrives so shutdown cannot race the end of the previous connection.
        while True:
            try:
                with self.listener.accept() as connection:
                    if not connection.poll(3):
                        continue
                    message = connection.recv_bytes(131072)
                    if not message and self.stopping.is_set():
                        connection.send_bytes(b'ok')
                        break
                    uri = message.decode('utf8')
                    parse_protocol(uri)
                    self.requests.put_nowait(uri)
                    connection.send_bytes(b'ok')
            except (OSError, EOFError, ValueError, queue.Full, AuthenticationError):
                if self.stopping.is_set():
                    break

    def poll(self):
        try:
            uri = self.requests.get_nowait()
        except queue.Empty:
            return
        if parse_protocol(uri)[0] != '2015':
            forward_original(self.state['original'], uri)
        else:
            self.games.append(launch_player(uri, self.directory))
        self.games = [game for game in self.games if game.poll() is None]

    def close(self):
        self.stopping.set()
        if self.listener:
            if self.thread and self.thread.is_alive():
                try:
                    with Client(self.endpoint, family='AF_PIPE', authkey=self.authkey) as connection:
                        connection.send_bytes(b'')
                except (OSError, EOFError):
                    pass
            self.listener.close()
            self.listener = None
        if self.state:
            self.redirect.restore(self.state)
            self.state = None
        if self.mutex:
            C.WinDLL('kernel32').CloseHandle(C.c_void_p(self.mutex))
            self.mutex = None
