from pathlib import Path
import json,os,subprocess,sys,time,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));(ROOT/'build').mkdir(exist_ok=True)
from game_tools import install,service,item,prop
exe=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions/version-18d4f802f49c6c9d/RobloxStudioBeta.exe'
folder=exe.parent/'content/HexagonVRIdleMotionTest';folder.mkdir(exist_ok=True)
install(ROOT/'VR-Demo.rbxlx',folder/'Test.rbxlx','','')
tree=ET.parse(folder/'Test.rbxlx').getroot();node=item('LocalScript','IdleMotionTest',service(tree,'StarterGui'))
prop(node,'ProtectedString','Source',(ROOT/'tests/idle_motion.lua').read_text());prop(node,'bool','Disabled','false')
ET.ElementTree(tree).write(folder/'Test.rbxlx',encoding='utf8',xml_declaration=True)
logs=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Roblox/logs';before=set(logs.glob('*.txt'))
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
code="game:Load('rbxasset://HexagonVRIdleMotionTest/Test.rbxlx');local p=game.Players:CreateLocalPlayer(0);game:GetService('RunService'):Run();p:LoadCharacter()"
process=subprocess.Popen([str(exe),'-script',code],startupinfo=startup)
try:
    deadline=time.monotonic()+45;result=''
    while time.monotonic()<deadline:
        time.sleep(.5);result='\n'.join(p.read_text(errors='replace')for p in set(logs.glob('*.txt'))-before)
        if 'HEXAGON_IDLE_MOTION_PASS'in result or'HEXAGON_IDLE_MOTION_FAIL'in result:break
    (ROOT/'build/idle-motion-test-log.txt').write_text(result)
    lines=list(dict.fromkeys(x.split('          ')[-1]for x in result.splitlines()if any(v in x for v in('IDLE_MOTION_','IdleMotionTest','Error:'))))
    print('\n'.join(lines),flush=True)
    assert 'HEXAGON_IDLE_MOTION_PASS'in result,'Unanchored idle/movement regression failed'
    path=ROOT/'WEAPON-VALIDATION.json';record=json.loads(path.read_text());record['idle_motion_pass']=True;record['idle_motion_checks']=[x for x in lines if x.startswith('IDLE_MOTION_CHECK')];record['idle_motion_metrics']=[x for x in lines if x.startswith('IDLE_MOTION_METRIC')];path.write_text(json.dumps(record,indent=2)+'\n')
finally:
    if process.poll()is None:process.terminate();process.wait(timeout=10)
