from pathlib import Path
import json,os,subprocess,sys,time,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));(ROOT/'build').mkdir(exist_ok=True)
from game_tools import install,service,item,prop
exe=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions/version-18d4f802f49c6c9d/RobloxStudioBeta.exe';folder=exe.parent/'content/HexagonVRRifleTest';folder.mkdir(exist_ok=True)
install(ROOT/'VR-Demo.rbxlx',folder/'Test.rbxlx','','')
tree=ET.parse(folder/'Test.rbxlx').getroot()
for n in tree.findall('.//Item[@class="Script"]')+tree.findall('.//Item[@class="LocalScript"]'):prop(n,'bool','Disabled','true')
node=item('Script','RifleRegressionTest',service(tree,'ServerScriptService'));prop(node,'ProtectedString','Source',(ROOT/'tests/new_rifles.lua').read_text());prop(node,'bool','Disabled','false');ET.ElementTree(tree).write(folder/'Test.rbxlx',encoding='utf8',xml_declaration=True)
logs=Path(os.environ['LOCALAPPDATA'])/'Hexagon/Roblox/logs';before=set(logs.glob('*.txt'));startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
code="game:Load('rbxasset://HexagonVRRifleTest/Test.rbxlx');local p=game.Players:CreateLocalPlayer(0);game:GetService('RunService'):Run();p:LoadCharacter()"
process=subprocess.Popen([str(exe),'-script',code],startupinfo=startup)
try:
    deadline=time.monotonic()+35;result=''
    while time.monotonic()<deadline:
        time.sleep(.5);result='\n'.join(p.read_text(errors='replace')for p in set(logs.glob('*.txt'))-before)
        if 'HEXAGON_RIFLES_ENGINE_PASS'in result or'HEXAGON_RIFLES_ENGINE_FAIL'in result:break
    (ROOT/'build/rifle-test-log.txt').write_text(result);lines=[x for x in result.splitlines()if any(v in x for v in('RIFLE_CHECK','HEXAGON_RIFLES_ENGINE','RifleRegressionTest'))];print('\n'.join(lines),flush=True)
    assert 'HEXAGON_RIFLES_ENGINE_PASS'in result,'New rifle regression failed'
    path=ROOT/'WEAPON-VALIDATION.json';record=json.loads(path.read_text());record['rifles_engine_pass']=True;record['rifle_checks']=[x for x in lines if'RIFLE_CHECK'in x];path.write_text(json.dumps(record,indent=2)+'\n')
finally:
    if process.poll()is None:process.terminate();process.wait(timeout=10)
