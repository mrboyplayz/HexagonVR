"""Direct3D stereo renderer handshake and shared GPU texture presentation."""
from pathlib import Path
import ctypes as C,json,mmap,struct,time,subprocess,sys

PACKET=struct.Struct('<IIIIQQQIIII12fIIQ')
MAP_SIZE=3448
def write_config(system,vr,directory,scale=3,eye_scale=1):
    directory=Path(directory);matrices=[];frusta=[]
    width,height=system.getRecommendedRenderTargetSize()
    width,height=(max(64,int(round(x*eye_scale/8))*8)for x in (width,height))
    for eye in (vr.Eye_Left,vr.Eye_Right):
        transform=system.getEyeToHeadTransform(eye).m
        matrices.extend([float(transform[r][c])*(scale if c==3 else 1)for r in range(3)for c in range(4)]+[0,0,0,1])
        frusta.extend(system.getProjectionRaw(eye))
    (directory/'native-config.bin').write_bytes(struct.pack('<III32f8fI',0x48565232,width,height,*matrices,*frusta,0))
    return width,height

class NativeGame:
    def __init__(self,process,pid):self.process=process;self.pid=pid
    def poll(self):return self.process.poll()
    def terminate(self):self.process.terminate()
    def wait(self,timeout=None):return self.process.wait(timeout=timeout)

def launch_studio(exe,code,folder,directory):
    directory=Path(directory).resolve();folder=Path(folder)
    script=folder/'native-startup.lua';pidfile=folder/'native-pid.txt';script.write_text(code)
    process=subprocess.Popen([str(directory/'HexagonVRStudioLoader.exe'),str(exe),str(directory/'HexagonVRNative.dll'),str(script),str(pidfile)])
    deadline=time.monotonic()+25
    while not pidfile.exists()and process.poll()is None and time.monotonic()<deadline:time.sleep(.05)
    if not pidfile.exists():
        if process.poll()is None:process.terminate();process.wait(timeout=10)
        raise RuntimeError('The native Studio renderer did not start')
    return NativeGame(process,int(pidfile.read_text()))

class NativePresenter:
    def __init__(self,pid,directory):
        self.pid=pid;self.map=mmap.mmap(-1,MAP_SIZE,tagname='Local\\HexagonVR.Native.Frame.'+str(pid),access=mmap.ACCESS_WRITE)
        self.host=C.CDLL(str(Path(directory).resolve()/'HexagonVRTextureHost64.dll'))
        self.host.AcquireNativeEyes.argtypes=[C.c_uint64,C.c_uint64,C.POINTER(C.c_void_p),C.POINTER(C.c_void_p)];self.host.AcquireNativeEyes.restype=C.c_long
        self.host.CloseNativeEyes.argtypes=[];self.host.CloseNativeEyes.restype=None
        self.last_frame=0;self.textures=None;self.frames=0;self.submitted=0;self.width=0;self.height=0;self.started=time.monotonic();self.pose=None;self.pose_sequence=0
    def read(self):
        raw=self.map[:PACKET.size];values=PACKET.unpack(raw)
        if values[0]%2 or values[0]!=struct.unpack('<I',self.map[:4])[0]or values[1]!=0x48565246 or not values[8]:return None
        return values
    def set_pose(self,sequence,head,ack_address):
        if head is None:return
        offset=120+(sequence%64)*52
        self.map[offset:offset+4]=struct.pack('<I',0xffffffff)
        self.map[offset+4:offset+52]=struct.pack('<12f',*head[:3,:].reshape(-1))
        self.map[offset:offset+4]=struct.pack('<I',sequence)
        self.map[112:120]=struct.pack('<Q',ack_address or 0)
    def submit(self,vr,compositor):
        self.map[48:56]=struct.pack('<II',1,C.windll.kernel32.GetTickCount()&0xffffffff)
        packet=self.read()
        if packet and packet[4]!=self.last_frame:
            left=C.c_void_p();right=C.c_void_p();result=self.host.AcquireNativeEyes(packet[5],packet[6],C.byref(left),C.byref(right))
            if result<0:raise RuntimeError('Could not open the native GPU textures: 0x'+format(result&0xffffffff,'08x'))
            if result==0:
                self.textures=(left.value,right.value);self.last_frame=packet[4];self.frames+=1;self.width,self.height=packet[2:4]
                self.pose=packet[11:23]if packet[23]else None;self.pose_sequence=packet[23]
        if self.textures:
            for eye,texture in zip((vr.Eye_Left,vr.Eye_Right),self.textures):
                if self.pose:
                    frame=vr.VRTextureWithPose_t();frame.handle=C.c_void_p(texture);frame.eType=vr.TextureType_DirectX;frame.eColorSpace=vr.ColorSpace_Gamma
                    for row in range(3):
                        for column in range(4):frame.mDeviceToAbsoluteTracking.m[row][column]=self.pose[row*4+column]
                    compositor.submit(eye,frame,submitFlags=vr.Submit_TextureWithPose)
                else:compositor.submit(eye,vr.Texture_t(C.c_void_p(texture),vr.TextureType_DirectX,vr.ColorSpace_Gamma))
            self.submitted+=1
        elif time.monotonic()-self.started>12:raise RuntimeError('The game did not produce native eye frames; desktop capture was not substituted')
    def close(self):
        self.map[48:52]=struct.pack('<I',0);self.host.CloseNativeEyes();self.map.close()

def attach(pid,directory):
    directory=Path(directory).resolve()
    result=subprocess.run([str(directory/'HexagonVRStudioLoader.exe'),'--attach',str(int(pid)),str(directory/'HexagonVRNative.dll')],capture_output=True,text=True,timeout=25)
    if result.returncode:raise RuntimeError(result.stderr.strip()or'Native graphics module did not initialize')
