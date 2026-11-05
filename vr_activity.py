"""Report active VR use to the legacy client's ordinary input path."""
import ctypes as C
from ctypes import wintypes as W
import math,time

class WindowActivityInput:
    def __init__(self):
        self.u=C.WinDLL('user32',use_last_error=True)
        self.u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
        self.u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
        self.u.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)]
        self.u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];self.u.PostMessageW.restype=W.BOOL
        self.callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
        self.u.EnumWindows.argtypes=[self.callback,W.LPARAM]
        self.u.EnumChildWindows.argtypes=[W.HWND,self.callback,W.LPARAM]
    def notify(self,pid):
        windows=[];seen=set()
        def visit(hwnd,_):
            owner=W.DWORD();self.u.GetWindowThreadProcessId(hwnd,C.byref(owner))
            if owner.value==pid and hwnd not in seen:
                seen.add(hwnd);rect=W.RECT()
                if self.u.GetClientRect(hwnd,C.byref(rect))and rect.right>200 and rect.bottom>150:windows.append((hwnd,rect.right,rect.bottom))
                self.u.EnumChildWindows(hwnd,visitor,0)
            return True
        visitor=self.callback(visit);self.u.EnumWindows(visitor,0)
        sent=False
        for hwnd,width,height in windows:
            # Balanced fractional-wheel events reach the legacy input handler.
            # Target only this process, preserving Windows focus/cursor position.
            owner=W.DWORD();self.u.GetWindowThreadProcessId(hwnd,C.byref(owner))
            if owner.value!=pid:continue
            screen=W.POINT(width//2,height//2)
            if not self.u.ClientToScreen(hwnd,C.byref(screen)):continue
            point=(screen.y&0xffff)<<16|(screen.x&0xffff)
            down=self.u.PostMessageW(hwnd,0x020a,1<<16,point)
            up=self.u.PostMessageW(hwnd,0x020a,0xffff<<16,point)
            sent=bool(down and up)or sent
        return sent

class VRActivity:
    def __init__(self,backend=None,clock=time.monotonic,interval=30):
        self.backend=backend or WindowActivityInput();self.clock=clock;self.interval=interval
        self.target=None;self.sample=None;self.last_activity=-math.inf;self.last_report=-math.inf
    def update(self,pid,pose,camera_active):
        now=self.clock()
        if pid!=self.target:
            self.target=pid;self.sample=None;self.last_activity=-math.inf;self.last_report=-math.inf
        if not camera_active or not pose.get('tracked'):
            self.sample=None;self.last_activity=-math.inf;return False
        current={key:pose.get(key)for key in ('head','left','right','buttons','move','turn')}
        changed=self.sample is None
        if self.sample:
            changed=current['buttons']!=self.sample['buttons']
            for hand in ('head','left','right'):
                a,b=current[hand],self.sample[hand]
                if bool(a)!=bool(b):changed=True
                elif a and b and(sum((a[n]-b[n])**2 for n in range(3))>.01**2 or sum(a[n]*b[n]for n in range(3,12))<1+2*math.cos(math.radians(.75))):changed=True
        moving=abs(pose.get('turn')or 0)>.01 or any(abs(v)>.05 for v in(pose.get('move')or[]))or (int(pose.get('buttons')or 0)&129)!=0
        if changed or moving:self.last_activity=now;self.sample=current
        if now-self.last_activity>self.interval or now-self.last_report<self.interval:return False
        if self.backend.notify(pid):self.last_report=now;return True
        return False
