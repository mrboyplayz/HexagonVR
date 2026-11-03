"""User-selected menu actions. Chat uses the normal, foreground game chat box."""
import ctypes as C
from ctypes import wintypes as W
import queue,threading,time

class NativeChat:
    def __init__(self):
        self.u=C.WinDLL('user32',use_last_error=True)
        self.u.GetForegroundWindow.restype=W.HWND
        self.u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
        self.u.SetForegroundWindow.argtypes=[W.HWND]
        class KEYBDINPUT(C.Structure):
            _fields_=[('vk',W.WORD),('scan',W.WORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
        class MOUSEINPUT(C.Structure):
            _fields_=[('x',W.LONG),('y',W.LONG),('data',W.DWORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
        class DATA(C.Union):_fields_=[('keyboard',KEYBDINPUT),('mouse',MOUSEINPUT)]
        class INPUT(C.Structure):_fields_=[('type',W.DWORD),('data',DATA)]
        self.K=KEYBDINPUT;self.I=INPUT
        self.u.SendInput.argtypes=[W.UINT,C.POINTER(INPUT),C.c_int]
        self.u.SendInput.restype=W.UINT
    def is_target(self,hwnd,pid):
        foreground=self.u.GetForegroundWindow();owner=W.DWORD()
        self.u.GetWindowThreadProcessId(foreground,C.byref(owner))
        return foreground==hwnd and owner.value==pid
    def key(self,vk=0,scan=0,unicode=False,up=False):
        event=self.I();event.type=1;event.data.keyboard=self.K(vk,scan,(4 if unicode else 0)|(2 if up else 0),0,0)
        if self.u.SendInput(1,C.byref(event),C.sizeof(event))!=1:raise OSError('Game input was not accepted')
    def tap(self,vk):self.key(vk);self.key(vk,up=True)
    def send(self,hwnd,pid,text):
        if not text or len(text)>140 or any(ord(x)<32 for x in text):raise ValueError('Invalid chat text')
        # Never type into another application if the client has closed or focus changes.
        self.u.SetForegroundWindow(hwnd);time.sleep(.08)
        if not self.is_target(hwnd,pid):raise RuntimeError('Focus the Hexagon game window before sending chat')
        self.tap(0xBF);time.sleep(.15) # Roblox's normal slash-to-chat binding.
        if not self.is_target(hwnd,pid):raise RuntimeError('Game focus changed before chat entry')
        self.key(0x11)
        try:self.tap(0x41)
        finally:self.key(0x11,up=True)
        for offset in range(0,len(text.encode('utf-16-le')),2):
            if not self.is_target(hwnd,pid):raise RuntimeError('Game focus changed during chat entry')
            unit=int.from_bytes(text.encode('utf-16-le')[offset:offset+2],'little')
            self.key(scan=unit,unicode=True);self.key(scan=unit,unicode=True,up=True)
        if not self.is_target(hwnd,pid):raise RuntimeError('Game focus changed before chat send')
        self.tap(0x0D)
    def leave(self,hwnd,pid):
        owner=W.DWORD();self.u.GetWindowThreadProcessId(W.HWND(hwnd),C.byref(owner))
        if owner.value!=pid:raise RuntimeError('The game window changed')
        self.u.PostMessageW(W.HWND(hwnd),0x10,0,0)

class Actions:
    def __init__(self,backend=None):
        self.backend=backend or NativeChat();self.buffer=None;self.started=0
        self.jobs=queue.Queue(maxsize=4);self.thread=threading.Thread(target=self._worker,daemon=True);self.thread.start()
    def _worker(self):
        while True:
            item=self.jobs.get()
            if item is None:self.jobs.task_done();return
            try:self.backend.send(*item)
            except Exception as error:print('VR chat:',error,flush=True)
            finally:self.jobs.task_done()
    def receive(self,kind,a,b,hwnd,pid):
        if kind==5:self.buffer=bytearray();self.started=time.monotonic()
        elif kind==6 and self.buffer is not None:
            if time.monotonic()-self.started>10:self.buffer=None;return
            for packed in (a,b):self.buffer.extend(int(packed).to_bytes(3,'little'))
            if len(self.buffer)>144:self.buffer=None
        elif kind==7 and self.buffer is not None:
            data=self.buffer;self.buffer=None
            if time.monotonic()-self.started>10:return
            try:
                message=data.rstrip(b'\0').decode('utf8')
                if not message or len(message)>140 or any(ord(x)<32 for x in message):return
                self.jobs.put_nowait((hwnd,pid,message))
            except (UnicodeError,queue.Full):print('VR chat was not queued',flush=True)
        elif kind==4:self.backend.leave(hwnd,pid);return 'leave'
