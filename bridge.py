"""SteamVR tracking, native stereo rendering, and local R6 controls for Hexagon."""
import argparse, ctypes, http.server, json, math, os, secrets, sys, threading, time, urllib.parse, urllib.request
from pathlib import Path
import numpy as np
from vr_settings import turn_speed,load_settings,save_setting

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
USER_ROOT=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
VERBOSE=False

def debug(*args,**kwargs):
    if VERBOSE:print(*args,**kwargs)

def configure_console():
    """Keep a status-only console; disable selection freezes and input echo."""
    from ctypes import wintypes as W
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetStdHandle.argtypes=[W.DWORD];k.GetStdHandle.restype=W.HANDLE
    k.GetConsoleMode.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD)]
    k.SetConsoleMode.argtypes=[W.HANDLE,W.DWORD]
    handle=k.GetStdHandle(-10);mode=W.DWORD()
    if k.GetConsoleMode(handle,ctypes.byref(mode)):
        k.SetConsoleMode(handle,(mode.value|0x80)&~(0x40|0x4|0x2))
    k.SetConsoleTitleW('HexagonVR')
    k.GetConsoleWindow.restype=W.HWND
    window=k.GetConsoleWindow()
    if window:ctypes.WinDLL('user32').ShowWindow(window,5)

def matrix34(values):
    a=np.array(values,dtype=float).reshape(3,4)
    m=np.eye(4);m[:3,:]=a
    return m

def cframe(m): return [float(x) for x in (*m[:3,3],*m[:3,:3].reshape(-1))]

def offset_hands(pose,outset,forward):
    for name,side in (('left',-1),('right',1)):
        hand=pose.get(name)
        if hand:
            hand[0]+=side*outset
            for coordinate,basis in enumerate((5,8,11)):hand[coordinate]-=hand[basis]*forward

def eye_resolution(recommended,scale=1):
    if not math.isfinite(scale)or not .5<=scale<=1.5:raise ValueError('Eye scale must be between 0.5 and 1.5')
    if len(recommended)!=2 or any(not math.isfinite(x)or x<64 for x in recommended):raise ValueError('SteamVR returned an invalid eye resolution')
    return tuple(max(64,int(round(x*scale/8))*8)for x in recommended)

def projection_plan(frusta, aspect, minimum_fov=0):
    """Map a symmetric source camera to the headset's asymmetric eye frusta.

    Full desktop UVs must never be used as full-eye UVs: their angular extents
    and aspect ratios differ. Bounds below preserve rays rather than pixels.
    This fixes geometric stretching but does not add stereo depth or reduce lag.
    """
    if not math.isfinite(aspect) or aspect<=0:raise ValueError('Invalid viewport aspect ratio')
    ty=max(max(max(abs(t),abs(b),abs(l)/aspect,abs(r)/aspect) for l,r,t,b in frusta)*1.01,math.tan(math.radians(minimum_fov/2)))
    fov=math.degrees(2*math.atan(ty))
    if fov>120:raise ValueError('Headset projection exceeds the 2015 camera FOV limit')
    tx=ty*aspect
    bounds=[((l/tx+1)/2,(t/ty+1)/2,(r/tx+1)/2,(b/ty+1)/2) for l,r,t,b in frusta]
    return fov,bounds

class Tracker:
    def __init__(self,scale=3):self.scale=scale;self.origin=None;self.turn=0;self.turn_held=False;self.grip_held=False
    def convert(self,head,left=None,right=None,move=(0,0),jump=False,turn_axis=0,recenter=False):
        if self.origin is None or recenter:
            forward=-head[:3,2];yaw=math.atan2(-forward[0],-forward[2])
            co,si=math.cos(yaw),math.sin(yaw)
            origin=np.eye(4);origin[:3,:3]=((co,0,si),(0,1,0),(-si,0,co))
            origin[:3,3]=(head[0,3],head[1,3]-.5,head[2,3])
            self.origin=np.linalg.inv(origin)
        self.turn=turn_command(turn_axis)
        def local(m):
            if m is None:return None
            result=self.origin@m;result[:3,3]*=self.scale
            return cframe(result)
        return {'tracked':True,'head':local(head),'left':local(left),'right':local(right),'move':list(move),'jump':bool(jump),'turn':self.turn,'fov':100}

def turn_command(axis):
    if not isinstance(axis,(int,float))or not math.isfinite(axis):return 0.
    value=max(-1.,min(1.,float(axis)))
    return math.copysign((abs(value)-.2)/.8,value)if abs(value)>.2 else 0.

class State:
    def __init__(self,key):self.key=key;self.lock=threading.Lock();self.pose={'tracked':False,'seq':0};self.updated=0;self.seq=0;self.requests=0;self.viewport=None
    def publish(self,pose):
        with self.lock:self.seq+=1;self.pose={**pose,'seq':self.seq};self.updated=time.monotonic()
    def read(self):
        with self.lock:
            self.requests+=1
            return {**self.pose,'tracked':bool(self.pose.get('tracked')) and time.monotonic()-self.updated<.5}

def serve(state,host,port):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def response(self,code,data):
            data=json.dumps(data,allow_nan=False,separators=(',',':')).encode()
            self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def authorized(self):
            supplied=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('key',[''])[0]
            return secrets.compare_digest(supplied,state.key)
        def do_GET(self):
            if not self.authorized():self.response(403,{'error':'Invalid bridge key'});return
            if urllib.parse.urlsplit(self.path).path!='/pose':self.response(404,{'error':'Not found'});return
            self.response(200,state.read())
        def do_POST(self):
            if not self.authorized():self.response(403,{'error':'Invalid bridge key'});return
            if urllib.parse.urlsplit(self.path).path=='/viewport':
                try:
                    size=int(self.headers.get('Content-Length',0))
                    if not 0<size<1024:raise ValueError()
                    viewport=json.loads(self.rfile.read(size))
                    if not all(isinstance(viewport[k],(int,float)) and math.isfinite(viewport[k]) and 0<viewport[k]<20000 for k in ('width','height','fov')):raise ValueError()
                    state.viewport=viewport;self.response(200,{'ok':True})
                except (ValueError,KeyError,TypeError):self.response(400,{'error':'Invalid viewport'})
                return
            if urllib.parse.urlsplit(self.path).path!='/pose':self.response(404,{'error':'Not found'});return
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<8192:raise ValueError('Invalid body size')
                pose=json.loads(self.rfile.read(size))
                for name in ('head','left','right'):
                    a=pose.get(name)
                    if a is not None and (not isinstance(a,list) or len(a)!=12 or not all(isinstance(x,(float,int)) and math.isfinite(x) and abs(x)<10000 for x in a)):raise ValueError('Invalid pose')
                if not isinstance(pose.get('head'),list):raise ValueError('Missing head pose')
                if not isinstance(pose.get('move'),list) or len(pose['move'])!=2 or not all(isinstance(x,(float,int)) and math.isfinite(x) and abs(x)<=1 for x in pose['move']):raise ValueError('Invalid movement')
                if not isinstance(pose.get('turn'),(int,float))or not math.isfinite(pose['turn'])or abs(pose['turn'])>1:raise ValueError('Invalid turn axis')
                pose={k:pose.get(k) for k in ('tracked','head','left','right','move','jump','turn','fov','cameraForward')}
                state.publish(pose);self.response(200,{'ok':True})
            except (ValueError,TypeError,KeyError):self.response(400,{'error':'Invalid tracking packet'})
    server=http.server.ThreadingHTTPServer((host,port),Handler);server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server

_AIM_OFFSETS={}
def controller_aim_pose(vr,system,index,role,device_pose):
    try:
        model=system.getStringTrackedDeviceProperty(index,vr.Prop_RenderModelName_String)
        key=(model,role)
        if key not in _AIM_OFFSETS:
            models=vr.VRRenderModels();source=vr.VRInput().getInputSourceHandle('/user/hand/left' if role==vr.TrackedControllerRole_LeftHand else '/user/hand/right')
            offset=np.eye(4);selected='device pose'
            for component in ('openxr_aim','tip'):
                ok,state=models.getComponentStateForDevicePath(model,component,source,vr.RenderModel_ControllerMode_State_t())
                if ok:offset=matrix34(state.mTrackingToComponentLocal.m);selected=component;break
            _AIM_OFFSETS[key]=offset
            debug('Controller pointing pose:',model,selected,flush=True)
        aimed=device_pose@_AIM_OFFSETS[key]
        # Keep the controller's grip position; use the runtime's aim orientation.
        aimed[:3,3]=device_pose[:3,3]
        return aimed
    except vr.OpenVRError:return device_pose

_GRIP_STATES={}
_HAND_POSES={}
def tracked_hand(role,pose,now=None):
    now=time.monotonic()if now is None else now
    if pose is not None:
        _HAND_POSES[role]=(now,pose.copy());return pose
    previous=_HAND_POSES.get(role)
    if previous and now-previous[0]<=.075:return previous[1].copy()
    _HAND_POSES.pop(role,None);return None

def stable_grip(role,pressed,now=None):
    now=time.monotonic()if now is None else now
    held,released=_GRIP_STATES.get(role,(False,None))
    if pressed:held,released=True,None
    elif held:
        if released is None:released=now
        elif now-released>=.05:held=False
    _GRIP_STATES[role]=(held,released)
    return held

def openvr_inputs(vr,system,poses,role):
    index=system.getTrackedDeviceIndexForControllerRole(role)
    if index==vr.k_unTrackedDeviceIndexInvalid or not poses[index].bPoseIsValid:
        previous=tracked_hand(role,None)
        if previous is not None:
            held=_GRIP_STATES.get(role,(False,None))[0]
            return previous,(0,0),False,(1<<vr.k_EButton_Grip)if held else 0
        _GRIP_STATES.pop(role,None);return None,(0,0),False,0
    matrix=matrix34(poses[index].mDeviceToAbsoluteTracking.m)
    matrix=controller_aim_pose(vr,system,index,role,matrix)
    tracked_hand(role,matrix)
    ok,state=system.getControllerState(index)
    if not ok:return matrix,(0,0),False,(1<<vr.k_EButton_Grip)if stable_grip(role,False)else 0
    axis=(0,0)
    for i in range(5):
        try:
            if system.getInt32TrackedDeviceProperty(index,vr.Prop_Axis0Type_Int32+i)==vr.k_eControllerAxis_Joystick:
                axis=(float(state.rAxis[i].x),-float(state.rAxis[i].y));break
        except vr.OpenVRError:pass
    axis=tuple(0 if abs(x)<.15 else max(-1,min(1,x)) for x in axis)
    trigger=bool(state.ulButtonPressed & (1<<vr.k_EButton_SteamVR_Trigger)) or state.rAxis[1].x>.7
    buttons=int(state.ulButtonPressed);grip=1<<vr.k_EButton_Grip
    buttons=(buttons|grip)if stable_grip(role,bool(buttons&grip))else(buttons&~grip)
    return matrix,axis,trigger,buttons


def controller_buttons(vr,left_trigger,right_trigger,left_buttons,right_buttons):
    """Y is the only menu shortcut. A jumps; B and X are unassigned."""
    a=1<<vr.k_EButton_A;menu=1<<vr.k_EButton_ApplicationMenu;grip=1<<vr.k_EButton_Grip
    return (int(right_trigger)+(2 if left_buttons&menu else 0)
            +(8 if right_buttons&a else 0)
            +(32 if left_buttons&grip else 0)+(64 if right_buttons&grip else 0)+(128 if left_trigger else 0))

def pulse_controller(vr,system,hand,strength):
    role=vr.TrackedControllerRole_LeftHand if hand==0 else vr.TrackedControllerRole_RightHand
    index=system.getTrackedDeviceIndexForControllerRole(role)
    if index!=vr.k_unTrackedDeviceIndexInvalid:system.triggerHapticPulse(index,0,max(100,min(3999,int(strength))))

def find_window(pid):
    from ctypes import wintypes
    user=ctypes.windll.user32;rows=[]
    enum=ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
    def callback(hwnd,_):
        process=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(process))
        if process.value==pid and user.IsWindowVisible(hwnd):
            title=ctypes.create_unicode_buffer(512);user.GetWindowTextW(hwnd,title,512)
            if 'studio -' not in title.value.lower():return True
            rect=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(rect));size=(rect.right-rect.left)*(rect.bottom-rect.top)
            if size>10000:rows.append((size,hwnd))
        return True
    user.EnumWindows(enum(callback),0)
    return max(rows)[1] if rows else None

def find_player_window():
    from ctypes import wintypes
    user=ctypes.windll.user32;kernel=ctypes.windll.kernel32;rows=[]
    kernel.OpenProcess.restype=wintypes.HANDLE
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def callback(hwnd,_):
        if not user.IsWindowVisible(hwnd):return True
        pid=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        process=kernel.OpenProcess(0x1000,False,pid.value)
        if not process:return True
        try:
            size=wintypes.DWORD(32768);path=ctypes.create_unicode_buffer(size.value)
            if not kernel.QueryFullProcessImageNameW(wintypes.HANDLE(process),0,path,ctypes.byref(size)):return True
            executable=Path(path.value)
            allowed=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions'
            if executable.name.lower()!='robloxplayerbeta.exe' or not executable.is_relative_to(allowed):return True
            rect=wintypes.RECT();user.GetClientRect(hwnd,ctypes.byref(rect))
            if rect.right>400 and rect.bottom>300:rows.append(hwnd)
        finally:kernel.CloseHandle(wintypes.HANDLE(process))
        return True
    user.EnumWindows(callback_type(callback),0)
    return rows[0] if len(rows)==1 else None

def window_pid(hwnd):
    from ctypes import wintypes
    value=wintypes.DWORD();ctypes.windll.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(value))
    return value.value

def viewport_crop(hwnd,frame_width,frame_height,viewport):
    """Locate the renderer's actual child widget, in physical capture pixels."""
    from ctypes import wintypes
    u=ctypes.windll.user32;dwm=ctypes.windll.dwmapi
    rect=wintypes.RECT()
    if dwm.DwmGetWindowAttribute(wintypes.HWND(hwnd),9,ctypes.byref(rect),ctypes.sizeof(rect))!=0:u.GetWindowRect(wintypes.HWND(hwnd),ctypes.byref(rect))
    bounds=(rect.left,rect.top,rect.right,rect.bottom);candidates=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def callback(child,_):
        if not u.IsWindowVisible(child):return True
        r=wintypes.RECT();u.GetClientRect(child,ctypes.byref(r));point=wintypes.POINT(0,0);u.ClientToScreen(child,ctypes.byref(point))
        width,height=r.right-r.left,r.bottom-r.top
        error=abs(width-viewport['width'])+abs(height-viewport['height'])
        candidates.append((error,point.x,point.y,width,height));return True
    callback(wintypes.HWND(hwnd),0)
    u.EnumChildWindows(wintypes.HWND(hwnd),callback_type(callback),0)
    if not candidates:return None
    error,x,y,w,h=min(candidates)
    if error>6:return None
    sx=frame_width/(bounds[2]-bounds[0]);sy=frame_height/(bounds[3]-bounds[1])
    l=round((x-bounds[0])*sx);t=round((y-bounds[1])*sy)
    r=frame_width-l-round(w*sx);b=frame_height-t-round(h*sy)
    if min(l,t,r,b)<0:return None
    return (l,t,r,b)

class Preview:
    def __init__(self,hwnd,crop,frusta,state,minimum_fov=110,projections=None,eye_size=None):
        import glfw
        from OpenGL import GL
        from windows_capture import WindowsCapture,Frame,InternalCaptureControl
        self.glfw=glfw;self.GL=GL;self.lock=threading.Lock();self.frame=None;self.crop=crop;self.frames=0;self.submitted=0;self.frusta=frusta;self.fov=minimum_fov;self.state=state;self.hwnd=hwnd;self.minimum_fov=minimum_fov;self.last_geometry=None
        native_tan=max(max(abs(t),abs(b)) for _,_,t,b in frusta)
        self.native_tan=native_tan
        self.view_mode='wide';self.set_fov(minimum_fov)
        if not glfw.init():raise RuntimeError('Could not initialize OpenGL')
        glfw.window_hint(glfw.VISIBLE,glfw.FALSE)
        self.window=glfw.create_window(64,64,'HexagonVR compositor',None,None)
        if not self.window:raise RuntimeError('Could not create an OpenGL context')
        glfw.make_context_current(self.window)
        from eye_renderer import EyeRenderer
        if eye_size is None:raise ValueError('Use the SteamVR recommended render resolution')
        self.eye_renderer=EyeRenderer(projections,eye_size)
        self.last_resolution_check=0;self.last_metrics=0;self.metrics_start=time.monotonic();self.metrics_frames=0;self.metrics_submits=0
        print('Headset resolution:',str(eye_size[0])+'x'+str(eye_size[1]),'per eye',flush=True)
        self.texture=int(GL.glGenTextures(1));GL.glBindTexture(GL.GL_TEXTURE_2D,self.texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MIN_FILTER,GL.GL_LINEAR);GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_LINEAR)
        self.capture_generation=0
        self.start_capture(hwnd)
    def set_fov(self,fov):
        self.minimum_fov=max(60,min(120,float(fov)))
        self.view_scale=math.tan(math.radians(self.minimum_fov/2))/self.native_tan
    def set_view_mode(self,mode):
        if mode not in ('native','wide'):raise ValueError('Invalid view mode')
        self.view_mode=mode
    def start_capture(self,hwnd):
        from windows_capture import WindowsCapture,Frame,InternalCaptureControl
        if hasattr(self,'control'):
            try:self.control.stop()
            except Exception:pass
        self.capture_generation+=1;generation=self.capture_generation
        self.hwnd=hwnd
        with self.lock:self.frame=None
        self.capture=WindowsCapture(cursor_capture=False,draw_border=None,window_hwnd=hwnd)
        @self.capture.event
        def on_frame_arrived(frame:Frame,control:InternalCaptureControl):
            if generation==self.capture_generation:
                with self.lock:self.frame=frame.frame_buffer.copy();self.frames+=1
        @self.capture.event
        def on_closed():
            if generation==self.capture_generation:
                with self.lock:self.frame=None
        self.control=self.capture.start_free_threaded()
    def submit(self,vr,compositor):
        from OpenGL import GL
        with self.lock:frame=self.frame
        if frame is None:return
        h,w=frame.shape[:2]
        viewport=self.state.viewport
        if viewport:
            measured=viewport_crop(self.hwnd,w,h,viewport)
            if measured is not None:self.crop=measured
        l,t,r,b=self.crop
        if l+r>=w or t+b>=h:return
        frame=np.ascontiguousarray(frame[t:h-b if b else h,l:w-r if r else w][::-1])
        aspect=frame.shape[1]/frame.shape[0]
        native_fit=max(max(abs(t),abs(b),abs(l)/aspect,abs(r)/aspect) for l,r,t,b in self.frusta)
        desired=1 if self.view_mode=='native' else math.tan(math.radians(self.minimum_fov/2))/self.native_tan
        self.view_scale=min(desired,math.tan(math.radians(60))/native_fit/1.01)
        render_tan=min(math.tan(math.radians(60)),native_fit*self.view_scale*1.01)
        self.fov=math.degrees(2*math.atan(render_tan))
        if not viewport or abs(viewport['fov']-self.fov)>.25:return
        geometry=(w,h,self.crop,frame.shape[1],frame.shape[0],round(self.fov,2))
        if geometry!=self.last_geometry:
            print('Game image resolution:',str(frame.shape[1])+'x'+str(frame.shape[0]),flush=True)
            debug('Capture geometry:',geometry,'camera:',viewport,flush=True);self.last_geometry=geometry
        textures=self.eye_renderer.render(frame,viewport['fov'],self.view_scale)
        # Per-eye projection is now baked into full eye textures. Source is still monocular.
        for eye,tex in zip((vr.Eye_Left,vr.Eye_Right),textures):
            texture=vr.Texture_t(ctypes.c_void_p(tex),vr.TextureType_OpenGL,vr.ColorSpace_Gamma)
            compositor.submit(eye,texture,vr.VRTextureBounds_t(0,0,1,1))
        self.submitted+=1
        if time.monotonic()-self.last_metrics>5:
            now=time.monotonic();elapsed=now-self.metrics_start
            metrics={'eye_resolution':list(self.eye_renderer.size),'source_resolution':[frame.shape[1],frame.shape[0]],'capture_resolution':[w,h],'capture_fps':round((self.frames-self.metrics_frames)/max(.01,elapsed),1),'submit_fps':round((self.submitted-self.metrics_submits)/max(.01,elapsed),1)}
            try:(USER_ROOT/'render-status.json').write_text(json.dumps(metrics,indent=2)+'\n')
            except OSError:pass
            self.last_metrics=now;self.metrics_start=now;self.metrics_frames=self.frames;self.metrics_submits=self.submitted
        self.glfw.poll_events()
    def close(self):
        self.control.stop();self.glfw.destroy_window(self.window);self.glfw.terminate()

def launch_place(path,key,port,hidden=False,user_id=0,auto_vr=False,local_client=False,menu_test=False,native_directory=None,native_scale=3,native_eye_scale=1):
    import subprocess,uuid,shutil
    from game_tools import install
    base=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions'
    choices=[p for p in base.glob('*/RobloxStudioBeta.exe') if p.parent.name=='version-18d4f802f49c6c9d']
    if not choices:raise RuntimeError('Hexagon 2015 Studio version-18d4f802f49c6c9d was not found')
    exe=choices[0]
    if local_client and native_directory:
        import openvr
        from native_renderer import write_config
        try:vr_system=openvr.init(openvr.VRApplication_Background)
        except openvr.OpenVRError:
            # The native renderer supports deferred configuration. Open Studio
            # now; the tracking loop configures the eyes when the headset wakes.
            debug('Studio will wait for the headset before enabling stereo.',flush=True)
        else:
            try:write_config(vr_system,openvr,native_directory,native_scale,native_eye_scale)
            finally:openvr.shutdown()
    session=uuid.uuid4().hex[:12];folder=exe.parent/'content/HexagonVR'/session;folder.mkdir(parents=True)
    install(path,folder/'VRPlace.rbxlx','http://127.0.0.1:'+str(port),key,user_id,local_fast_poll=True)
    if menu_test:
        import xml.etree.ElementTree as ET
        from game_tools import service,item,prop
        tree=ET.parse(folder/'VRPlace.rbxlx').getroot()
        flag=item('BoolValue','HexagonVRStudioMenuTest',service(tree,'ReplicatedStorage'));prop(flag,'bool','Value','true')
        ET.ElementTree(tree).write(folder/'VRPlace.rbxlx',encoding='utf8',xml_declaration=True)
    code="game:Load('rbxasset://HexagonVR/"+session+"/VRPlace.rbxlx');local p=game.Players:CreateLocalPlayer("+str(user_id)+");game:GetService('RunService'):Run();p:LoadCharacter();print('HEXAGON_VR_LOCAL_READY')"
    if auto_vr:
        code+=";spawn(function() local s=game:GetService('ServerScriptService'):WaitForChild('HexagonVRServer');s:WaitForChild('HexagonVRTestToggle');repeat wait(.1) until p.Character and p.Character:FindFirstChild('Torso');wait(2);s.HexagonVRTestToggle:Fire(p) end)"
    if local_client:
        if native_directory:
            from native_renderer import launch_studio
            return launch_studio(exe,code,folder,native_directory),folder
        si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0 if hidden else 3
        process=subprocess.Popen([str(exe),'-script',code],startupinfo=si)
        return process,folder
    # A local Studio session otherwise reaches the legacy 500/minute budget.
    # Stage startup flags only for this process and restore the exact old file.
    flag_path=exe.parent/'ClientSettings/ClientAppSettings.json'
    original=flag_path.read_bytes() if flag_path.exists() else None
    flags=json.loads(original) if original else {}
    flags.update({'FIntUserHttpRequestsPerMinuteLimit':'12000','DFIntUserHttpRequestsPerMinuteLimit':'12000'})
    staged=json.dumps(flags).encode();flag_path.parent.mkdir(exist_ok=True);flag_path.write_bytes(staged)
    flag_lock=threading.Lock()
    def restore_flags():
        with flag_lock:
            if flag_path.exists() and flag_path.read_bytes()==staged:
                if original is None:flag_path.unlink()
                else:flag_path.write_bytes(original)
    code="game:Load('rbxasset://HexagonVR/"+session+"/VRPlace.rbxlx');local p=game.Players:CreateLocalPlayer("+str(user_id)+");game:GetService('RunService'):Run();p:LoadCharacter();print('HEXAGON_VR_LOCAL_READY')"
    code+=";spawn(function() while true do wait(.5);local c=workspace.CurrentCamera;if c then pcall(function() game:GetService('HttpService'):PostAsync('http://127.0.0.1:"+str(port)+"/viewport?key="+key+"',game:GetService('HttpService'):JSONEncode({width=c.ViewportSize.x,height=c.ViewportSize.y,fov=c.FieldOfView}),Enum.HttpContentType.ApplicationJson) end) end end end)"
    if auto_vr:
        code+=";spawn(function() local s=game:GetService('ServerScriptService'):WaitForChild('HexagonVRServer');s:WaitForChild('HexagonVRTestToggle');repeat wait(.1) until p.Character and p.Character:FindFirstChild('Torso');wait(2);s.HexagonVRTestToggle:Fire(p) end)"
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0 if hidden else 1
    try:process=subprocess.Popen([str(exe),'-script',code],startupinfo=si)
    except Exception:restore_flags();raise
    process._vr_restore_flags=restore_flags
    return process,folder

def main():
    global VERBOSE
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--launch',type=Path);p.add_argument('--user-id',type=int,default=0)
    p.add_argument('--install',type=Path);p.add_argument('--output',type=Path);p.add_argument('--url',default='http://127.0.0.1:18765')
    p.add_argument('--port',type=int,default=18765);p.add_argument('--host',default='127.0.0.1');p.add_argument('--key')
    p.add_argument('--scale',type=float,default=3);p.add_argument('--relay',help='Existing reachable relay URL; publishes tracking with the same --key')
    p.add_argument('--relay-only',action='store_true');p.add_argument('--mock',action='store_true');p.add_argument('--probe',action='store_true')
    p.add_argument('--preview',action='store_true',help='Experimental monoscopic headset preview; no stereo depth')
    p.add_argument('--window-hwnd',type=int);p.add_argument('--crop',default='0,0,0,0',help='Preview trim in pixels: left,top,right,bottom')
    p.add_argument('--hidden',action='store_true');p.add_argument('--seconds',type=float,default=0)
    p.add_argument('--auto-vr',action='store_true',help='Enable /vr automatically in the local demo')
    p.add_argument('--wait-for-headset',action='store_true',help='Wait for the wireless headset before opening the game')
    p.add_argument('--fov',type=float,default=120);p.add_argument('--camera-forward',type=float,default=.45)
    p.add_argument('--turn-speed',type=float,default=None,help='Smooth turn speed, 15 to 180 degrees per second')
    p.add_argument('--view-mode',choices=['native','wide'],default='native',help='Headset angular scale or intentional wider/zoomed-out view')
    p.add_argument('--arm-outset',type=float,default=.4,help='Extra outward offset per arm in studs')
    p.add_argument('--arm-forward',type=float,default=.3,help='Forward hand-anchor offset along each controller aim, in studs')
    p.add_argument('--attach-player',action='store_true',help='Wait for the Hexagon Player window instead of starting Studio')
    p.add_argument('--http-compat',action='store_true',help='Legacy diagnostic HTTP service; not used by the current game scripts')
    p.add_argument('--studio-test',action='store_true',help='Start the bundled supported Studio game and open its VR menu')
    p.add_argument('--diagnostics',action='store_true',help='Show detailed tracking and capture logs')
    p.add_argument('--eye-scale',type=float,default=1,help='Scale the SteamVR recommended eye resolution, from 0.5 to 1.5')
    p.add_argument('--native-renderer',action='store_true',help='Direct stereo GPU rendering in the verified 2015 client')
    p.add_argument('--capture-preview',action='store_true',help='Use the previous monoscopic desktop-capture renderer')
    p.add_argument('--protocol',help=argparse.SUPPRESS)
    p.add_argument('--no-launch-integration',action='store_true',help='Do not temporarily route Hexagon launches through the early graphics loader')
    p.add_argument('--native-directory',type=Path,help=argparse.SUPPRESS)
    p.add_argument('--install-assets',action='store_true',help='Install bundled weapon models and sounds in existing Hexagon clients, then exit')
    args=p.parse_args()
    from weapon_assets import install_assets
    install_assets()
    if args.install_assets:
        print('HexagonVR Marketplace weapon assets installed.');return
    if args.protocol:
        from launch_integration import handle_protocol
        handle_protocol(args.protocol)
        return
    from launch_integration import repair_stale_routing
    repair_stale_routing()
    for name in ('arm_forward','arm_outset'):
        if not math.isfinite(getattr(args,name))or not 0<=getattr(args,name)<=1:p.error(name.replace('_','-')+' must be between 0 and 1 studs')
    eye_resolution((64,64),args.eye_scale)
    VERBOSE=args.diagnostics
    saved_preferences=load_settings(USER_ROOT/'vr-settings.json')
    args.turn_speed=turn_speed(args.turn_speed if args.turn_speed is not None else saved_preferences.get('turn_speed',65))
    if args.studio_test:
        args.launch=USER_ROOT/'VR-Demo.rbxlx' if (USER_ROOT/'VR-Demo.rbxlx').exists()else ROOT/'VR-Demo.rbxlx';args.auto_vr=True;args.preview=True;args.wait_for_headset=True
    if not any((args.launch,args.install,args.probe,args.relay,args.relay_only,args.http_compat,args.mock)):
        args.attach_player=True;args.preview=True;args.wait_for_headset=True
    native_directory=args.native_directory or (ROOT/'native' if getattr(sys,'frozen',False) else USER_ROOT/'native' if (USER_ROOT/'native/HexagonVRNative.dll').exists()else USER_ROOT/'build/native')
    if not any((args.install,args.probe,args.mock,args.relay,args.relay_only,args.http_compat,args.capture_preview)):args.native_renderer=True
    if args.native_renderer:args.preview=False;args.wait_for_headset=True
    args.local_client=not(args.http_compat or args.relay_only or args.relay)
    if args.probe:
        import openvr
        print(json.dumps({'steamvr_installed':openvr.isRuntimeInstalled(),'headset_present':openvr.isHmdPresent(),'display':'native stereo GPU renderer'}));return
    config_path=USER_ROOT/'bridge-config.json'
    if args.key:key=args.key
    elif config_path.exists():key=json.loads(config_path.read_text())['key']
    else:key=secrets.token_urlsafe(24);config_path.write_text(json.dumps({'key':key},indent=2))
    if args.install:
        from game_tools import install
        dest=args.output or args.install.with_name(args.install.stem+'-VR.rbxlx')
        print(install(args.install,dest,args.url,key,args.user_id));return
    configure_console()
    state=State(key);server=serve(state,args.host,args.port) if not args.local_client else None;stop=threading.Event();preview=None;process=None;folder=None;vr=None;system=None;compositor=None;transport=None;last_bind=0;hwnd=None;native=None
    last_message=None;launch_host=None
    def status(message):
        nonlocal last_message
        if message!=last_message:print(message,flush=True);last_message=message
    print('Launch SteamVR and connect your headset.',flush=True)
    status('enter a game with support for hexagonVR')
    if args.relay:
        def publisher():
            while not stop.wait(1/30):
                try:
                    req=urllib.request.Request(args.relay.rstrip('/')+'/pose?key='+urllib.parse.quote(key),json.dumps(state.read()).encode(),{'Content-Type':'application/json'},method='POST')
                    with urllib.request.urlopen(req,timeout=2) as response:response.read()
                except Exception as e:debug('Relay unavailable:',type(e).__name__,flush=True);stop.wait(1)
        threading.Thread(target=publisher,daemon=True).start()
    try:
        if args.attach_player and args.native_renderer and not args.no_launch_integration:
            from launch_integration import ProtocolHost
            launch_host=ProtocolHost(native_directory)
            launch_host.start()
        if args.launch:
            while True:
                try:
                    process,folder=launch_place(args.launch,key,args.port,args.hidden,args.user_id,args.auto_vr,args.local_client,menu_test=False,native_directory=native_directory if args.native_renderer else None,native_scale=args.scale,native_eye_scale=args.eye_scale)
                    break
                except Exception as error:
                    import openvr as vr
                    if not isinstance(error,vr.OpenVRError):raise
                    status('Launch SteamVR and connect your headset to continue.');time.sleep(1)
        from vr_actions import Actions
        actions=Actions(legacy_chat=False);tracker=Tracker(args.scale);start=time.monotonic();last_status=start;last_window_check=0
        left_held=0;last_tuning=None;last_vr_settings=None;last_vr_check=0;haptics={}
        def disconnect():
            nonlocal transport,preview,system,compositor,native
            if native:native.close();native=None
            if transport:transport.close();transport=None
            if preview:preview.close();preview=None
            if system is not None:vr.shutdown();system=None;compositor=None
            state.viewport=None;tracker.origin=None
        while not args.seconds or time.monotonic()-start<args.seconds:
            if launch_host:
                try:launch_host.poll()
                except (RuntimeError,OSError,ValueError) as error:
                    status('Unable to start the VR client; check the Hexagon installation and Windows Security ('+type(error).__name__+').')
            if process and process.poll() is not None:break
            if args.relay_only:time.sleep(.05);continue
            if time.monotonic()-last_vr_check>.25:
                last_vr_check=time.monotonic();settings_file=USER_ROOT/'vr-settings.json'
                if settings_file.exists():
                    try:
                        content=settings_file.read_text()
                        if content!=last_vr_settings:
                            settings=json.loads(content)
                            for key in ('arm_forward','arm_outset'):
                                if key in settings and isinstance(settings[key],(int,float))and math.isfinite(settings[key]):setattr(args,key,max(0,min(1,float(settings[key]))))
                            if 'turn_speed'in settings:args.turn_speed=turn_speed(settings['turn_speed'])
                            last_vr_settings=content
                    except (OSError,ValueError):pass
            if args.local_client:
                if transport is None and time.monotonic()-last_bind>2:
                    last_bind=time.monotonic()
                    hwnd=args.window_hwnd or (find_window(process.pid) if process else find_player_window() if args.attach_player else None)
                    if hwnd or (process and args.hidden):
                        target_pid=process.pid if process else None
                        if target_pid is None:target_pid=window_pid(hwnd)
                        try:
                            from client_transport import LocalTransport
                            transport=LocalTransport(target_pid,allow_studio=bool(process))
                            debug('Local render-thread mailbox connected to PID',target_pid,flush=True)
                        except (RuntimeError,OSError) as error:debug('Waiting for local mailbox:',error,flush=True)
                if transport is None:
                    status('enter a game with support for hexagonVR');time.sleep(.2);continue
            if args.native_renderer and transport:
                from native_renderer import renderer_active
                if not renderer_active(transport.pid):
                    status('Keep HexagonVR open and launch the game again through Hexagon for native rendering.')
                    try:transport.push({'tracked':False})
                    except (RuntimeError,OSError):disconnect()
                    time.sleep(.2);continue
            if not args.mock and system is None:
                import openvr as vr
                try:
                    system=vr.init(vr.VRApplication_Scene if args.preview or args.native_renderer else vr.VRApplication_Background)
                    compositor=vr.VRCompositor() if args.preview or args.native_renderer else None
                    status('hexagonVR is running | Y: menu | grip: grab')
                except vr.OpenVRError as error:
                    if system is not None:vr.shutdown();system=None;compositor=None
                    if not args.wait_for_headset:raise
                    status('Launch SteamVR and connect your headset to continue.')
                    if transport:
                        try:transport.push({'tracked':False})
                        except (RuntimeError,OSError):disconnect()
                    time.sleep(.25);continue
            if args.mock:
                t=time.monotonic()-start;head=np.eye(4);head[:3,3]=(0,1.6,0)
                left=head.copy();left[:3,3]=(-.35,1.3+.15*math.sin(t*2),-.35)
                right=head.copy();right[:3,3]=(.35,1.3+.15*math.cos(t*2),-.35)
                pose=tracker.convert(head,left,right)
                time.sleep(1/60)
            else:
                poses=compositor.waitGetPoses((vr.TrackedDevicePose_t*vr.k_unMaxTrackedDeviceCount)(),None)[0] if compositor else system.getDeviceToAbsoluteTrackingPose(vr.TrackingUniverseStanding,0,vr.k_unMaxTrackedDeviceCount)
                if not poses[vr.k_unTrackedDeviceIndex_Hmd].bPoseIsValid:
                    state.publish({'tracked':False})
                    if transport:
                        try:transport.push({'tracked':False})
                        except (RuntimeError,OSError):disconnect()
                    time.sleep(.02);continue
                head=matrix34(poses[0].mDeviceToAbsoluteTracking.m)
                left,move,left_trigger,lb=openvr_inputs(vr,system,poses,vr.TrackedControllerRole_LeftHand)
                right,turn,trigger,rb=openvr_inputs(vr,system,poses,vr.TrackedControllerRole_RightHand)
                a=1<<vr.k_EButton_A;menu_button=1<<vr.k_EButton_ApplicationMenu
                pose=tracker.convert(head,left,right,move,bool(rb&a),turn[0],False);left_held=lb
                pose['buttons']=controller_buttons(vr,left_trigger,trigger,lb,rb)
                pose['uiAxis']=turn[1]
                if not compositor:time.sleep(1/90)
            pose['fov']=120 if args.native_renderer else preview.fov if preview else args.fov
            pose['nativeRendering']=args.native_renderer
            pose['armForward']=args.arm_forward
            pose['cameraForward']=args.camera_forward
            pose['turnSpeed']=args.turn_speed
            offset_hands(pose,args.arm_outset,args.arm_forward)
            state.publish(pose)
            camera_ready=not args.native_renderer
            if args.local_client:
                if transport:
                    try:
                        transport.push(pose)
                        command=transport.ui_command()
                        if command:
                            kind,a,b=command
                            if kind==1:tracker.origin=None
                            elif kind in (2,3):
                                args.view_mode='native' if kind==2 else 'wide'
                                if preview:preview.set_view_mode(args.view_mode)
                                print('VR view:',args.view_mode,flush=True)
                            elif kind==8:
                                args.arm_forward=round(args.arm_forward+.15,2)
                                if args.arm_forward>.91:args.arm_forward=0
                                settings_path=USER_ROOT/'vr-settings.json'
                                try:
                                    current=json.loads(settings_path.read_text())if settings_path.exists()else{}
                                    current['arm_forward']=args.arm_forward;settings_path.write_text(json.dumps(current,indent=2)+'\n')
                                except (OSError,ValueError):pass
                            elif kind==9 and a in(0,1)and 100<=b<=3999:
                                haptics[a]=(time.monotonic()+.035,b)
                            elif kind==10 and 15<=a<=180:
                                args.turn_speed=turn_speed(a)
                                try:save_setting(USER_ROOT/'vr-settings.json','turn_speed',args.turn_speed)
                                except OSError:debug('Turn speed changed, but the preference file could not be saved.',flush=True)
                            elif actions.receive(kind,a,b,hwnd,transport.pid,token=transport.ui_token)=='leave':break
                        chat_result=actions.poll_result(transport.pid)
                        if chat_result:transport.report_chat(*chat_result)
                        if actions.last_send_token!=actions.last_confirmed_token and transport.chat_confirmed(actions.last_send_token):
                            actions.last_confirmed_token=actions.last_send_token
                            debug('VR chat confirmed by the game.',flush=True)
                        measured=transport.viewport()
                        if measured:state.viewport=measured
                        active=transport.camera_enabled()
                        camera_ready=bool(active)if active is not None else measured is not None
                        if args.native_renderer and camera_ready:
                            if native is None:
                                from native_renderer import write_config,attach,NativePresenter
                                write_config(system,vr,native_directory,args.scale,args.eye_scale);attach(transport.pid,native_directory)
                                native=NativePresenter(transport.pid,native_directory)
                            native.set_pose(transport.sequence,head,transport.active_ack_address())
                            status('hexagonVR native stereo | Y: menu | grip: grab')
                        elif args.native_renderer:status('Waiting for the game VR camera; type /vr if VR was turned off.')
                    except (RuntimeError,OSError) as error:
                        debug('Local client disconnected:',error,flush=True);disconnect();continue
            if process and state.viewport is not None and hasattr(process,'_vr_restore_flags'):process._vr_restore_flags()
            if system is not None:
                for hand,(until,strength)in tuple(haptics.items()):
                    if time.monotonic()<until:pulse_controller(vr,system,hand,strength)
                    else:del haptics[hand]
            if native:
                if camera_ready:native.submit(vr,compositor)
                elif native.suspend():compositor.clearLastSubmittedFrame()
                if time.monotonic()-last_status>5:
                    (USER_ROOT/'native-status.json').write_text(json.dumps({'mode':'native stereo GPU','pid':native.pid,'eye_resolution':[native.width,native.height],'scene_frames_received':native.frames,'submissions':native.submitted,'render_pose_sequence':native.pose_sequence,'desktop_capture':False},indent=2)+'\n')
            if args.preview and not args.mock:
                if preview is None:
                    hwnd=args.window_hwnd or (find_window(process.pid) if process else find_player_window() if args.attach_player else None)
                    if hwnd:
                        preview=Preview(hwnd,tuple(int(x) for x in args.crop.split(',')),[system.getProjectionRaw(e) for e in (vr.Eye_Left,vr.Eye_Right)],state,args.fov,[np.array(system.getProjectionMatrix(e,.1,100).m) for e in (vr.Eye_Left,vr.Eye_Right)],eye_size=eye_resolution(system.getRecommendedRenderTargetSize(),args.eye_scale))
                        preview.set_view_mode(args.view_mode)
                        debug('Capture started for game window',hwnd,flush=True)
                if preview:
                    if time.monotonic()-preview.last_resolution_check>2:
                        preview.last_resolution_check=time.monotonic()
                        preview.eye_renderer.resize(eye_resolution(system.getRecommendedRenderTargetSize(),args.eye_scale))
                    if args.attach_player and time.monotonic()-last_window_check>1:
                        last_window_check=time.monotonic();current_window=find_player_window()
                        if current_window and current_window!=preview.hwnd:
                            preview.start_capture(current_window)
                            debug('Video reattached to the current Hexagon client window',flush=True)
                    live_settings=USER_ROOT/'preview-settings.json'
                    if live_settings.exists():
                        try:
                            source=live_settings.read_text()
                            if source!=last_tuning:
                                tuning=json.loads(source);last_tuning=source
                                if 'crop' in tuning:preview.crop=tuple(tuning['crop'])
                                if 'headset_fov' in tuning:preview.set_fov(tuning['headset_fov'])
                                if 'view_mode' in tuning:args.view_mode=tuning['view_mode'];preview.set_view_mode(args.view_mode)
                        except (ValueError,KeyError,OSError):pass
                    preview.submit(vr,compositor)
            if time.monotonic()-last_status>5:
                debug('Tracking:',state.seq,'| local render ack:',transport.last_ack_sequence if transport else None,'| local acknowledgement ms:',round(sum(transport.latencies)/len(transport.latencies),1) if transport and transport.latencies else None,'| capture/submit:',(preview.frames,preview.submitted) if preview else 'no window','viewport:',state.viewport,'camera enabled:',transport.camera_enabled()if transport else None,flush=True);last_status=time.monotonic()
    except KeyboardInterrupt:pass
    finally:
        if launch_host:launch_host.close()
        state.publish({'tracked':False});stop.set()
        if transport:transport.close()
        if native:native.close()
        if preview:preview.close()
        if vr and system is not None:vr.shutdown()
        if server:server.shutdown()
        if process and process.poll() is None:process.terminate();process.wait(timeout=10)
        if process and hasattr(process,'_vr_restore_flags'):process._vr_restore_flags()
        if folder:
            import shutil
            intended=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions'
            resolved=folder.resolve()
            if resolved.is_relative_to(intended.resolve()) and resolved.parent.name=='HexagonVR' and len(resolved.name)==12 and all(c in '0123456789abcdef' for c in resolved.name):shutil.rmtree(resolved)

if __name__=='__main__':
    try:main()
    except Exception as e:
        import traceback
        print('HexagonVR:',type(e).__name__,repr(e),file=sys.stderr);traceback.print_exc();sys.exit(1)
