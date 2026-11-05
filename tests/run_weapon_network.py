from pathlib import Path
import hashlib,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));(ROOT/'build').mkdir(exist_ok=True)
from game_tools import make_demo,install,service,item,prop
version=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions/version-18d4f802f49c6c9d'
folder=version/'content/HexagonVRNetworkTest';folder.mkdir(exist_ok=True)
install(ROOT/'VR-Demo.rbxlx',folder/'Test.rbxlx','','',filtering_enabled=False)
tree=ET.parse(folder/'Test.rbxlx').getroot()
rs=service(tree,'ReplicatedStorage')
for node in list(rs.findall('Item')):
    if node.findtext('./Properties/string[@name="Name"]')=='HexagonVROfflineAssets':rs.remove(node)
if '--weak-cache'in sys.argv:
    for node in tree.findall('.//Item[@class="ModuleScript"]'):
        if node.findtext('./Properties/string[@name="Name"]')=='VRWeaponClient':
            source=node.find('./Properties/ProtectedString[@name="Source"]');source.text=source.text.replace('cache={}','cache=setmetatable({},{__mode="k"})',1)
for node in tree.findall('.//Item[@class="LocalScript"]'):prop(node,'bool','Disabled','true')
test=item('LocalScript','NetworkPickupTest',service(tree,'StarterGui'));prop(test,'ProtectedString','Source',(ROOT/'tests/network_pickup.lua').read_text());prop(test,'bool','Disabled','false')
fixture=item('Script','NetworkFixture',service(tree,'ServerScriptService'))
prop(fixture,'ProtectedString','Source',"game.Players.PlayerAdded:connect(function(p)wait(.25);p:LoadCharacter();repeat wait(.1)until p.Character and p.Character:FindFirstChild('HumanoidRootPart');p.Character.HumanoidRootPart.CFrame=CFrame.new(p.userId==124 and 8 or 0,5,0);p.Character.HumanoidRootPart.Anchored=true end);spawn(function()local folder=workspace:WaitForChild('HexagonVRWeapons');wait(.1);for _,model in ipairs(folder:GetChildren())do model.Handle.Anchored=true end end)")
prop(fixture,'bool','Disabled','false');ET.ElementTree(tree).write(folder/'Test.rbxlx',encoding='utf8',xml_declaration=True)
logs=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Roblox/logs';before=set(logs.glob('*.txt'))
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
server_code="local place = 'rbxasset://HexagonVRNetworkTest/Test.rbxlx';game:Load(place);game:GetService('NetworkServer'):Start(53648);game:GetService('RunService'):Run();print('NETWORK_SERVER_READY')"
client_code="local client = game:GetService('NetworkClient');client.ConnectionAccepted:connect(function(address,replicator)replicator:RequestCharacter()end);game:GetService('RunService'):Run();client:PlayerConnect(123,'localhost',53648,0,20);print('NETWORK_CLIENT_CONNECTED')"
processes=[]
try:
    server=subprocess.Popen([str(version/'RobloxStudioBeta.exe'),'-script',server_code],startupinfo=startup);processes.append(server)
    deadline=time.monotonic()+20;result=''
    while time.monotonic()<deadline:
        time.sleep(.5);result='\n'.join(p.read_text(errors='replace')for p in set(logs.glob('*.txt'))-before)
        if '          NETWORK_SERVER_READY'in result:break
    assert '          NETWORK_SERVER_READY'in result,'Network server did not start'
    client_exe=version/'RobloxStudioBeta.exe'
    if '--player'in sys.argv:
        from launch_integration import PLAYER_HASH
        client_exe=next(p for p in version.parent.glob('*/RobloxPlayerBeta.exe')if hashlib.sha256(p.read_bytes()).hexdigest()==PLAYER_HASH)
    observer=subprocess.Popen([str(client_exe),'-script',client_code.replace('PlayerConnect(123,','PlayerConnect(124,')],startupinfo=startup);processes.append(observer)
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        time.sleep(.5);result='\n'.join(p.read_text(errors='replace')for p in set(logs.glob('*.txt'))-before)
        if 'NETWORK_OBSERVER_READY'in result or 'HEXAGON_NETWORK_PICKUP_FAIL'in result:break
    assert 'NETWORK_OBSERVER_READY'in result,'Observer did not become ready'
    client=subprocess.Popen([str(client_exe),'-script',client_code],startupinfo=startup);processes.append(client)
    print('Network test processes:',server.pid,client.pid,observer.pid,'client:',client_exe.name,flush=True)
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        time.sleep(.5);result='\n'.join(p.read_text(errors='replace')for p in set(logs.glob('*.txt'))-before)
        if ('HEXAGON_NETWORK_PICKUP_PASS'in result and 'HEXAGON_NETWORK_OBSERVER_PASS'in result)or 'HEXAGON_NETWORK_PICKUP_FAIL'in result:break
    (ROOT/'build/network-pickup-log.txt').write_text(result)
    lines=[x for x in result.splitlines()if any(v in x for v in('NETWORK_','Error:','NetworkPickupTest'))]
    print('\n'.join(lines),flush=True)
    assert 'HEXAGON_NETWORK_PICKUP_PASS'in result,'Separate client/server pickup test did not pass'
    assert 'HEXAGON_NETWORK_OBSERVER_PASS'in result,'Observer visibility test did not pass'
    path=ROOT/'WEAPON-VALIDATION.json';record=json.loads(path.read_text())
    record['network_client_engine']=client_exe.name;record['network_pickup_checks']=[x for x in lines if'NETWORK_PICKUP_CHECK'in x]
    record['network_pickup_pass']=True;record['network_observer_pass']=True;record['network_clients']=2;record['network_filtering_enabled']=False;path.write_text(json.dumps(record,indent=2)+'\n')
finally:
    for process in reversed(processes):
        if process.poll()is None:process.terminate();process.wait(timeout=10)
