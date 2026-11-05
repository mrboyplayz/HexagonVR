from pathlib import Path
import json,os,shutil,struct,sys,time,uuid,xml.etree.ElementTree as ET
import numpy as np,openvr
ROOT=Path(__file__).resolve().parents[1];KIT=ROOT;sys.path.insert(0,str(KIT))
from native_renderer import launch_studio,NativePresenter
from client_transport import LocalTransport
from game_tools import make_demo,install,service,item,prop
relief=float(sys.argv[1])if len(sys.argv)>1 else .45
(ROOT/'build').mkdir(exist_ok=True)
session=uuid.uuid4().hex[:12];native=ROOT/'build'/('scope-gpu-'+session);native.mkdir()
for name in ('HexagonVRNative.dll','HexagonVRStudioLoader.exe','HexagonVRTextureHost64.dll'):shutil.copyfile(KIT/'build/native'/name,native/name)
eye=np.eye(4,dtype=float);transforms=[]
for x in(-.09,.09):
    m=eye.copy();m[0,3]=x;transforms.extend(m.reshape(-1))
(native/'native-config.bin').write_bytes(struct.pack('<III32f8fI',0x48565232,512,512,*transforms,*([-1,1,-1,1]*2),2))
exe=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions/version-18d4f802f49c6c9d/RobloxStudioBeta.exe';folder=exe.parent/'content/HexagonVR'/session;folder.mkdir(parents=True)
make_demo(native/'base.rbxlx');install(native/'base.rbxlx',folder/'VRPlace.rbxlx','','')
tree=ET.parse(folder/'VRPlace.rbxlx').getroot();node=item('Script','ScopeGPUFixture',service(tree,'ServerScriptService'));prop(node,'ProtectedString','Source',(ROOT/'tests/scope_gpu_fixture.lua').read_text());prop(node,'bool','Disabled','false');ET.ElementTree(tree).write(folder/'VRPlace.rbxlx',encoding='utf8',xml_declaration=True)
code="game:Load('rbxasset://HexagonVR/"+session+"/VRPlace.rbxlx');local p=game.Players:CreateLocalPlayer(0);game:GetService('RunService'):Run();p:LoadCharacter()"
os.environ['HEXAGONVR_TEST_HIDDEN']='1'
process=presenter=transport=None
class Compositor:
    def submit(self,eye,texture,**kwargs):assert texture.handle
    def clearLastSubmittedFrame(self):pass
def frame(x,y,z):return[x,y,z,1,0,0,0,1,0,0,0,1]
try:
    process=launch_studio(exe,code,folder,native);deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        try:transport=LocalTransport(process.pid,allow_studio=True);break
        except RuntimeError:time.sleep(.3)
    assert transport,'Scope test mailbox unavailable'
    assert all(n in transport.cells for n in('scope_frame','scope_params')),'Actual scope Value objects were not identified'
    presenter=NativePresenter(process.pid,native);compositor=Compositor();active=0;deadline=time.monotonic()+30;submitted=False
    while time.monotonic()<deadline:
        pose={'tracked':True,'head':frame(0,1.5,0),'right':frame(-.0087,.895,-relief-.304),'left':frame(-.3,.8,-1),'buttons':64,'nativeRendering':True,'fov':120,'cameraForward':.45,'move':[0,0]}
        transport.push(pose);scoped=transport.scope();active+=bool(scoped)
        head=np.eye(4);head[:3,3]=(0,1.5,0);presenter.set_pose(transport.sequence,head,transport.active_ack_address());presenter.set_scope(scoped)
        if transport.camera_enabled():
            if not submitted:presenter.started=time.monotonic();submitted=True
            presenter.submit(openvr,compositor)
        if list(native.glob('native-scope-*.ppm')):break
        time.sleep(.01)
    reports='\n'.join(p.read_text(errors='replace')for p in native.glob('native-report-*.jsonl'))
    print('Native frames',presenter.frames,'scope samples',active,'directory',native,flush=True)
    print(reports[-1800:],flush=True)
    assert active>5 and presenter.frames>60 and '"native_scope_ready":true'in reports,'Native scope did not render'
    path=next(native.glob('native-scope-*.ppm'))
    raw=path.read_bytes();header,raw=raw.split(b'\n255\n',1);image=np.frombuffer(raw,np.uint8).reshape(512,512,3)
    red=(image[:,:,0]>image[:,:,1]*1.4)&(image[:,:,0]>image[:,:,2]*1.4)&(image[:,:,0]>65)
    columns=np.where(red.sum(0)>40)[0];assert len(columns)>180,'The scope target was not magnified as expected'
    eyePath=next(native.glob('native-right-*.ppm'));eyeRaw=eyePath.read_bytes().split(b'\n255\n',1)[1];eyeImage=np.frombuffer(eyeRaw,np.uint8).reshape(512,512,3)
    eyeRed=(eyeImage[:,:,0]>eyeImage[:,:,1]*1.4)&(eyeImage[:,:,0]>eyeImage[:,:,2]*1.4)&(eyeImage[:,:,0]>65)
    assert eyeRed.sum()>500,'The lens image was occluded in the headset eye texture'
    cx=round((.5-.045/(relief-.025))*512);centre=eyeRed[246:266,cx-10:cx+10]
    assert centre.sum()>150,'The magnified lens was not visible in its projected eye-space position'
    record=json.loads((KIT/'WEAPON-VALIDATION.json').read_text());record['scope_gpu_pass']=True;record['scope_gpu_frames']=presenter.frames;record['scope_resolution']=[512,512];record['scope_target_red_width_pixels']=len(columns);record['scope_eye_relief_test_studs']=relief;record['scope_visible_eye_red_pixels']=int(eyeRed.sum());record['scope_gpu_capture']=str(path.relative_to(ROOT));(KIT/'WEAPON-VALIDATION.json').write_text(json.dumps(record,indent=2)+'\n')
    record['scope_lens_centre_red_pixels']=int(centre.sum());(KIT/'WEAPON-VALIDATION.json').write_text(json.dumps(record,indent=2)+'\n')
    print('HEXAGON_SCOPE_GPU_PASS red target width',len(columns),'lens centre red pixels',int(centre.sum()),flush=True)
finally:
    if presenter:presenter.close()
    if transport:transport.close()
    if process and process.poll()is None:process.terminate();process.wait(timeout=10)
