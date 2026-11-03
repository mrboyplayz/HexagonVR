"""Local pose mailbox for the user's exact Hexagon 0.217 build.

Only game-created, marker-identified Value cells are written. A render-thread
acknowledgement validates every vector input before tracking begins. No Lua VM
hooks, executable patches, account data, or remote process are used.
"""
import ctypes as C,struct,time,hashlib,os
from ctypes import wintypes as W
from pathlib import Path

IDENTITY=(1,0,0,0,1,0,0,0,1)
SENTINELS={
 'head':(12001.125,23002.25,34003.5),
 'left':(13001.125,24002.25,35003.5),
 'right':(14001.125,25002.25,36003.5),
 'control':(16001.125,26002.25,36003.5),
 'move':(15001.125,25002.25,35003.5),
 'settings':(17001.125,27002.25,37003.5),
 'ack':(26002.25,56002.25,66003.5),
 'move_ack':(15001.125,25002.25,77003.5),
 'settings_ack':(17001.125,27002.25,78003.5),
 'viewport':(18001.125,28002.25,38003.5),
 'position':(19001.125,29002.25,39003.5),
 'ui':(20001.125,30002.25,40003.5),
 'ui_ack':(20001.125,30002.25,81003.5),
 'ui_out':(21001.125,31002.25,41003.5),
 'camera_state':(26002.25,0,82003.5),
 'chat_result':(23001.125,33002.25,43003.5),
 'chat_result_ack':(23001.125,33002.25,84003.5),
 'chat_focus':(26002.25,0,85003.5),
 'chat_confirm':(23001.125,33002.25,86003.5),
}

class MBI(C.Structure):
    _fields_=[('base',C.c_void_p),('allocation',C.c_void_p),('allocationProtect',W.DWORD),('partition',W.WORD),('size',C.c_size_t),('state',W.DWORD),('protect',W.DWORD),('type',W.DWORD)]

class LocalTransport:
    def __init__(self,pid,allow_studio=False):
        self.k=C.WinDLL('kernel32',use_last_error=True)
        self.k.OpenProcess.restype=W.HANDLE
        self.k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        self.k.WriteProcessMemory.argtypes=self.k.ReadProcessMemory.argtypes
        self.k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MBI),C.c_size_t]
        self.k.CloseHandle.argtypes=[W.HANDLE]
        self.handle=self.k.OpenProcess(0x438,False,pid)
        if not self.handle:raise OSError(C.get_last_error(),'Could not open the Hexagon test process')
        self.sequence=100;self.cells={};self.acks=[];self.viewport_cells=[];self.position_cells=[];self.pid=pid;self.last_ack=time.monotonic();self.last_ack_sequence=-1;self.sent_times={};self.latencies=[]
        try:
            path=C.create_unicode_buffer(32768);size=W.DWORD(len(path))
            if not self.k.QueryFullProcessImageNameW(W.HANDLE(self.handle),0,path,C.byref(size)):raise OSError('Could not verify client path')
            exe=Path(path.value);allowed=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions'
            if not exe.is_relative_to(allowed):raise RuntimeError('This process is outside the Hexagon installation')
            if exe.name not in (['RobloxPlayerBeta.exe','RobloxStudioBeta.exe'] if allow_studio else ['RobloxPlayerBeta.exe']):raise RuntimeError('Unexpected target program')
            digest=hashlib.sha256(exe.read_bytes()).hexdigest()
            hashes={'432aa5e86c66275d1a27c4e5c6833c8a23ccc0d8e9114eef7c134ba2d6953b9d'}
            if allow_studio:hashes.add('007a6ab91703730b3f9635b0558ec0e87db92d3c84dbe649d2f42a2f7718271b')
            if digest not in hashes:raise RuntimeError('Unsupported Hexagon executable version')
            self.bind()
        except Exception:self.close();raise
    def read(self,address,size):
        b=C.create_string_buffer(size);n=C.c_size_t()
        self.k.ReadProcessMemory(self.handle,C.c_void_p(address),b,size,C.byref(n))
        return b.raw[:n.value]
    def write(self,address,data):
        n=C.c_size_t();b=C.create_string_buffer(data)
        if not self.k.WriteProcessMemory(self.handle,C.c_void_p(address),b,len(data),C.byref(n)) or n.value!=len(data):raise OSError('Local pose write failed')
    def vec(self,address):
        data=self.read(address,12)
        return struct.unpack('<3f',data) if len(data)==12 else None
    def scan(self,patterns):
        found={name:[] for name in patterns};address=0x10000
        while address<0x7fff0000:
            mbi=MBI()
            if not self.k.VirtualQueryEx(self.handle,C.c_void_p(address),C.byref(mbi),C.sizeof(mbi)):break
            base=mbi.base or address;end=base+mbi.size
            if mbi.state==0x1000 and mbi.type==0x20000 and not mbi.protect&0x101:
                for start in range(base,end,1024*1024):
                    data=self.read(start,min(1024*1024+64,end-start))
                    for name,pattern in patterns.items():
                        offset=0
                        while True:
                            at=data.find(pattern,offset)
                            if at<0:break
                            candidate=start+at
                            if candidate%4==0:found[name].append(candidate)
                            offset=at+1
            address=max(end,address+4096)
        return {name:sorted(set(values)) for name,values in found.items()}
    def heartbeat(self,flags=0,turn=0):
        self.sequence=(self.sequence+1)%1000000
        self.write(self.cells['control'],struct.pack('<3f',flags,self.sequence,turn))
    def bind(self):
        patterns={name:struct.pack('<12f',*IDENTITY,*v) if name in ('head','left','right') else struct.pack('<3f',*v) for name,v in SENTINELS.items()}
        found=self.scan(patterns)
        if not all(found[name] for name in ('head','left','right')):raise RuntimeError('Local pose mailbox is not loaded yet')
        self.acks=found['ack'];self.viewport_cells=found['viewport'];self.position_cells=found['position'];self.ui_outputs=found['ui_out'];self.ui_token=0;self.camera_state_cells=found.get('camera_state',[])
        self.chat_focus_cells=found.get('chat_focus',[]);self.chat_confirm_cells=found.get('chat_confirm',[])
        if not self.acks or not self.viewport_cells:raise RuntimeError('Mailbox acknowledgement/output was not found')
        for address in found['control']:
            if self.read(address,12)!=patterns['control']:continue
            self.sequence+=1;test=struct.pack('<3f',0,self.sequence,0);self.write(address,test);time.sleep(.06)
            if any(v and abs(v[0]-self.sequence)<.01 and v[1:]==SENTINELS['ack'][1:] for a in self.acks if (v:=self.vec(a))):self.cells['control']=address;break
            if self.read(address,12)==test:self.write(address,patterns['control'])
        if 'control' not in self.cells:raise RuntimeError('Render thread did not acknowledge the local control cell')
        def instance_vtable(address):
            raw=self.read(address,4)
            if len(raw)!=4:return False
            table=struct.unpack('<I',raw)[0];info=MBI()
            if not self.k.VirtualQueryEx(self.handle,C.c_void_p(table),C.byref(info),C.sizeof(info))or info.type!=0x1000000:return False
            function=self.read(table,4)
            if len(function)!=4:return False
            pointer=struct.unpack('<I',function)[0]
            if not self.k.VirtualQueryEx(self.handle,C.c_void_p(pointer),C.byref(info),C.sizeof(info)):return False
            return info.type==0x1000000 and bool(info.protect&0xf0)
        offsets=[offset for offset in range(4,257,4) if instance_vtable(self.cells['control']-offset)]
        for name in ('head','left','right'):
            candidates=[a for a in found[name] if self.read(a,48)==patterns[name]]
            if len(candidates)>1:
                candidates=[a for a in candidates if any(instance_vtable(a-offset) for offset in offsets)]
            if len(candidates)!=1:raise RuntimeError('Could not identify the actual '+name+' Value object; candidates '+str(len(candidates))+' offsets '+str(offsets))
            self.cells[name]=candidates[0]
        channels=[('move',(.125,.25,0),'move_ack'),('settings',(110,.35,3),'settings_ack')]
        if found['ui']:channels.append(('ui',(0,0,0),'ui_ack'))
        if found['chat_result']:channels.append(('chat_result',(123,0,43003.5),'chat_result_ack'))
        for name,test_values,ack_name in channels:
            for address in found[name]:
                if self.read(address,12)!=patterns[name]:continue
                self.heartbeat();test=struct.pack('<3f',*test_values);self.write(address,test);time.sleep(.06)
                if any(v and abs(v[0]-test_values[0])<.001 and abs(v[1]-test_values[1])<.001 and v[2]==SENTINELS[ack_name][2] for a in found[ack_name] if (v:=self.vec(a))):self.cells[name]=address;break
                if self.read(address,12)==test:self.write(address,patterns[name])
            if name not in self.cells:raise RuntimeError('Render thread did not acknowledge '+name)
        self.last_ack=time.monotonic()
    def acknowledgement(self):
        values=[v[0] for a in self.acks if (v:=self.vec(a)) and v[1:]==SENTINELS['ack'][1:] and v[0].is_integer() and 0<=v[0]<=self.sequence]
        if not values:return None
        seq=max(values)
        if seq!=self.last_ack_sequence:
            self.last_ack_sequence=seq;self.last_ack=time.monotonic()
            if seq in self.sent_times:self.latencies=(self.latencies+[(self.last_ack-self.sent_times[seq])*1000])[-60:]
            self.sent_times={n:t for n,t in self.sent_times.items() if n>seq}
        return seq
    def viewport(self):
        for address in self.viewport_cells:
            v=self.vec(address)
            if v and 64<=v[0]<=16384 and 64<=v[1]<=16384 and 1<=v[2]<=120 and v[0].is_integer() and v[1].is_integer():return {'width':v[0],'height':v[1],'fov':v[2]}
    def active_ack_address(self):
        current=[(v[0],a)for a in self.acks if (v:=self.vec(a))and v[1:]==SENTINELS['ack'][1:]and v[0].is_integer()and 0<=v[0]<=self.sequence]
        return max(current,key=lambda row:row[0])[1]if current else 0
    def camera_enabled(self):
        cells=getattr(self,'camera_state_cells',[])
        if not cells:return None # Older game support has no explicit camera state.
        values=[v for a in cells if(v:=self.vec(a))and v[2]==SENTINELS['camera_state'][2]and v[0].is_integer()and 0<=v[0]<=self.sequence and v[1]in(0,1)]
        return bool(max(values,key=lambda row:row[0])[1])if values else False
    def report_chat(self,token,code):
        if 'chat_result'in self.cells:self.write(self.cells['chat_result'],struct.pack('<3f',token,code,43003.5))
    def chat_focused(self):
        values=[v for a in getattr(self,'chat_focus_cells',[])if(v:=self.vec(a))and v[2]==85003.5 and v[0].is_integer()and 0<=v[0]<=self.sequence and v[1]in(-1,0,1)]
        value=max(values,key=lambda row:row[0])[1]if values else -1
        return None if value==-1 else bool(value)
    def chat_confirmed(self,token):
        return bool(token)and any((v:=self.vec(a))and v==(float(token),1.,86003.5)for a in getattr(self,'chat_confirm_cells',[]))
    def position(self):
        values=[v for a in self.position_cells if (v:=self.vec(a)) and v[2].is_integer() and 0<=v[2]<=self.sequence]
        return max(values,key=lambda v:v[2]) if values else None
    def push(self,pose):
        self.acknowledgement()
        if time.monotonic()-self.last_ack>1:raise RuntimeError('The local render-thread heartbeat stopped')
        flags=0
        if pose.get('tracked') and pose.get('head'):
            flags=1
            for name,bit in [('head',1),('left',2),('right',4)]:
                data=pose.get(name)
                if data:
                    self.write(self.cells[name],struct.pack('<12f',*data[3:],*data[:3]))
                    if name!='head':flags+=bit
        move=pose.get('move') or [0,0]
        self.write(self.cells['move'],struct.pack('<3f',move[0],move[1],1 if pose.get('jump') else 0))
        encoded=(4 if pose.get('nativeRendering')else 3)+max(0,min(1,pose.get('armForward',0)))/10
        self.write(self.cells['settings'],struct.pack('<3f',pose.get('fov',110),pose.get('cameraForward',.35),encoded))
        if 'ui' in self.cells:self.write(self.cells['ui'],struct.pack('<3f',pose.get('buttons',0),self.ui_token,pose.get('uiAxis',0)))
        self.heartbeat(flags,pose.get('turn',0))
        self.sent_times[self.sequence]=time.monotonic()
    def ui_command(self):
        candidates=[]
        for address in self.ui_outputs:
            v=self.vec(address)
            if not v or not all(x.is_integer() and 0<=x<16777216 for x in v):continue
            token=int(v[0]);kind=token%16
            if token<=16 or kind not in range(1,9):continue
            serial=token//16
            if not 1<=serial<=999999:continue
            delta=(serial-self.ui_token//16)%999999 if self.ui_token else serial
            if self.ui_token and not 0<delta<=499999:continue
            candidates.append((delta,token,kind,int(v[1]),int(v[2])))
        if candidates:
            chosen=min(candidates)if self.ui_token else max(candidates)
            _,self.ui_token,kind,a,b=chosen
            return kind,a,b
    def close(self):
        if getattr(self,'handle',None):self.k.CloseHandle(self.handle);self.handle=None
