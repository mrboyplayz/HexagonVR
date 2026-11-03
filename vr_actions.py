"""User-selected menu actions. Chat uses the normal, foreground game chat box."""
import ctypes as C
from ctypes import wintypes as W
import queue,threading,time

class ChatFocusError(RuntimeError):pass

class NativeChat:
    def __init__(self):
        self.u=C.WinDLL('user32',use_last_error=True)
        self.u.GetForegroundWindow.restype=W.HWND
        self.u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
        self.u.SetForegroundWindow.argtypes=[W.HWND]
        self.u.IsWindowVisible.argtypes=[W.HWND]
        self.u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
        self.u.ShowWindow.argtypes=[W.HWND,C.c_int]
        self.u.IsIconic.argtypes=[W.HWND]
        self.u.MapVirtualKeyW.argtypes=[W.UINT,W.UINT]
        self.u.MapVirtualKeyW.restype=W.UINT
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
        flags=4 if unicode else 8
        if not unicode:
            scan=scan or self.u.MapVirtualKeyW(vk,4)
            if scan&0xff00:flags|=1
            scan&=0xff
        event=self.I();event.type=1;event.data.keyboard=self.K(0,scan,flags|(2 if up else 0),0,0)
        if self.u.SendInput(1,C.byref(event),C.sizeof(event))!=1:raise OSError('Game input was not accepted')
    def tap(self,vk):
        self.key(vk)
        try:time.sleep(.1)
        finally:self.key(vk,up=True)
        time.sleep(.02)
    def window_for(self,pid):
        rows=[]
        callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
        def visit(hwnd,_):
            owner=W.DWORD();self.u.GetWindowThreadProcessId(hwnd,C.byref(owner))
            if owner.value==pid and self.u.IsWindowVisible(hwnd):
                rect=W.RECT();self.u.GetClientRect(hwnd,C.byref(rect))
                if rect.right>400 and rect.bottom>250:rows.append((rect.right*rect.bottom,hwnd))
            return True
        self.u.EnumWindows(callback(visit),0)
        if not rows:raise RuntimeError('The Hexagon game window is not available')
        return max(rows)[1]
    def send(self,hwnd,pid,text,focus_check=None):
        if not text or len(text)>140 or any(ord(x)<32 for x in text):raise ValueError('Invalid chat text')
        hwnd=self.window_for(pid)
        # Never type into another application if the client has closed or focus changes.
        if self.u.IsIconic(hwnd):self.u.ShowWindow(hwnd,9)
        self.u.SetForegroundWindow(hwnd)
        deadline=time.monotonic()+.75
        while not self.is_target(hwnd,pid)and time.monotonic()<deadline:time.sleep(.01)
        if not self.is_target(hwnd,pid):raise RuntimeError('Focus the Hexagon game window before sending chat')
        self.tap(0xBF) # Roblox's normal slash-to-chat binding.
        if focus_check:
            deadline=time.monotonic()+.6
            focused=focus_check(pid)
            while focused is False and time.monotonic()<deadline:
                time.sleep(.02);focused=focus_check(pid)
            # CoreScript-owned text boxes may be hidden from LocalScripts.
            # Only a positive observation shortens the settling time; a
            # negative observation cannot prove the default chat bar is closed.
            if focused is not True:time.sleep(.5)
        else:time.sleep(.5)
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
        hwnd=self.window_for(pid)
        owner=W.DWORD();self.u.GetWindowThreadProcessId(W.HWND(hwnd),C.byref(owner))
        if owner.value!=pid:raise RuntimeError('The game window changed')
        self.u.PostMessageW(W.HWND(hwnd),0x10,0,0)

class Actions:
    def __init__(self,backend=None,focus_probe=None,legacy_chat=True):
        self.backend=backend or NativeChat();self.buffer=None;self.started=0;self.transaction=0;self.results=queue.Queue(maxsize=8)
        self.jobs=queue.Queue(maxsize=4);self.thread=threading.Thread(target=self._worker,daemon=True);self.thread.start()
        self.focus_probe=focus_probe;self.last_send_token=0;self.last_confirmed_token=0;self.legacy_chat=legacy_chat
    def _worker(self):
        while True:
            item=self.jobs.get()
            if item is None:self.jobs.task_done();return
            result=1
            try:
                if isinstance(self.backend,NativeChat):self.backend.send(*item[:3],focus_check=self.focus_probe)
                else:self.backend.send(*item[:3])
            except Exception as error:
                result=4 if isinstance(error,ChatFocusError)else 2 if isinstance(error,RuntimeError)else 3
                print('VR chat:',error,flush=True)
            if item[3]:
                try:self.results.put_nowait((item[1],item[3],result))
                except queue.Full:pass
            self.jobs.task_done()
    def poll_result(self,pid):
        result=None
        while True:
            try:game,token,code=self.results.get_nowait()
            except queue.Empty:return result
            if game==pid:result=(token,code)
    def receive(self,kind,a,b,hwnd,pid,token=0):
        if kind in(5,6,7)and not self.legacy_chat:
            if kind==5:print('Update the game support scripts to use internal VR chat.',flush=True)
            return
        if kind==5:self.buffer=bytearray();self.started=time.monotonic();self.transaction=token
        elif kind==6 and self.buffer is not None:
            if time.monotonic()-self.started>30:self.buffer=None;return
            for packed in (a,b):self.buffer.extend(int(packed).to_bytes(3,'little'))
            if len(self.buffer)>144:self.buffer=None
        elif kind==7 and self.buffer is not None:
            data=self.buffer;self.buffer=None
            if time.monotonic()-self.started>30:return
            try:
                message=data.rstrip(b'\0').decode('utf8')
                if not message or len(message)>140 or any(ord(x)<32 for x in message):return
                self.jobs.put_nowait((hwnd,pid,message,self.transaction))
                self.last_send_token=self.transaction
            except (UnicodeError,queue.Full):print('VR chat was not queued',flush=True)
        elif kind==4:self.backend.leave(hwnd,pid);return 'leave'
