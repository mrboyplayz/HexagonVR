from pathlib import Path
import json,os,subprocess,sys,time,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));(ROOT/'build').mkdir(exist_ok=True)
from game_tools import install,service,item,prop
version=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions/version-18d4f802f49c6c9d'
folder=version/'content/HexagonVRHatNetworkTest';folder.mkdir(exist_ok=True)
install(ROOT/'VR-Demo.rbxlx',folder/'Test.rbxlx','','',filtering_enabled=False)
tree=ET.parse(folder/'Test.rbxlx').getroot()
for node in tree.findall('.//Item[@class="LocalScript"]'):prop(node,'bool','Disabled','true')
test=item('LocalScript','HatNetworkTest',service(tree,'StarterGui'))
prop(test,'ProtectedString','Source',(ROOT/'tests/hat_network.lua').read_text());prop(test,'bool','Disabled','false')
fixture=item('Script','HatNetworkFixture',service(tree,'ServerScriptService'))
prop(fixture,'ProtectedString','Source',(ROOT/'tests/hat_network_fixture.lua').read_text());prop(fixture,'bool','Disabled','false')
ET.ElementTree(tree).write(folder/'Test.rbxlx',encoding='utf8',xml_declaration=True)
logs=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Roblox/logs';before=set(logs.glob('*.txt'))
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
server_code="local place = 'rbxasset://HexagonVRHatNetworkTest/Test.rbxlx';game:Load(place);game:GetService('NetworkServer'):Start(53648);game:GetService('RunService'):Run();print('HAT_SERVER_READY')"
client_code="local client=game:GetService('NetworkClient');client.ConnectionAccepted:connect(function(address,replicator)replicator:RequestCharacter()end);game:GetService('RunService'):Run();client:PlayerConnect(123,'localhost',53648,0,20)"
processes=[]
def read_logs():return '\n'.join(p.read_text(errors='replace')for p in set(logs.glob('*.txt'))-before)
def until_marker(marker,seconds):
    deadline=time.monotonic()+seconds;result=''
    while time.monotonic()<deadline:
        time.sleep(.5);result=read_logs()
        if marker in result or 'HEXAGON_HAT_NETWORK_FAIL'in result:break
    return result
try:
    server=subprocess.Popen([str(version/'RobloxStudioBeta.exe'),'-script',server_code],startupinfo=startup);processes.append(server)
    result=until_marker('          HAT_SERVER_READY',20)
    assert '          HAT_SERVER_READY'in result,'Hat network server did not start'
    observer=subprocess.Popen([str(version/'RobloxStudioBeta.exe'),'-script',client_code.replace('PlayerConnect(123,','PlayerConnect(124,')],startupinfo=startup);processes.append(observer)
    result=until_marker('HAT_NETWORK_OBSERVER_READY',20)
    assert 'HAT_NETWORK_OBSERVER_READY'in result,'Hat observer did not become ready'
    client=subprocess.Popen([str(version/'RobloxStudioBeta.exe'),'-script',client_code],startupinfo=startup);processes.append(client)
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        time.sleep(.5);result=read_logs()
        if ('HEXAGON_HAT_NETWORK_PASS'in result and 'HEXAGON_HAT_NETWORK_OBSERVER_PASS'in result)or 'HEXAGON_HAT_NETWORK_FAIL'in result:break
    (ROOT/'build/hat-network-log.txt').write_text(result)
    lines=[x for x in result.splitlines()if any(v in x for v in('HAT_NETWORK','Error:','HatNetworkTest','HatNetworkFixture'))]
    print('\n'.join(lines),flush=True)
    assert 'HEXAGON_HAT_NETWORK_PASS'in result and 'HEXAGON_HAT_NETWORK_OBSERVER_PASS'in result,'Multiplayer hat test failed'
    path=ROOT/'WEAPON-VALIDATION.json';record=json.loads(path.read_text())
    record['hat_network_pass']=True;record['hat_network_clients']=2;record['hat_network_checks']=[x for x in lines if'HAT_NETWORK_CHECK'in x];path.write_text(json.dumps(record,indent=2)+'\n')
finally:
    for process in reversed(processes):
        if process.poll()is None:process.terminate();process.wait(timeout=10)
