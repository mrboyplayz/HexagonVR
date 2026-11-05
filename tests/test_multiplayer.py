import unittest
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''
time=1
function tick()return time end
function wait()end
function spawn(fn)fn()end
function print()end
function event()
 local e={listeners={}}
 function e:connect(fn)local c={active=true};function c:disconnect()self.active=false end;self.listeners[#self.listeners+1]={fn=fn,c=c};return c end
 function e:Fire(...)for _,v in ipairs(self.listeners)do if v.c.active then v.fn(...)end end end
 return e
end
local cf={};cf.__index=cf
function cf:toObjectSpace(b)return CFrame.new(b.x-self.x,b.y-self.y,b.z-self.z)end
function cf.__mul(a,b)return CFrame.new(a.x+b.x,a.y+b.y,a.z+b.z)end
CFrame={new=function(x,y,z)return setmetatable({x=x or 0,y=y or 0,z=z or 0},cf)end,Angles=function()return CFrame.new()end}
Vector3={new=function(x,y,z)return{x=x or 0,y=y or 0,z=z or 0,magnitude=math.sqrt((x or 0)^2+(y or 0)^2+(z or 0)^2)}end}
local objects={}
local methods={}
function methods:GetChildren()local out={};for _,o in ipairs(objects)do if o.Parent==self then out[#out+1]=o end end;return out end
function methods:FindFirstChild(name)for _,o in ipairs(self:GetChildren())do if o.Name==name then return o end end end
function methods:IsA(kind)return self.kind==kind end
function methods:Destroy()self.Parent=nil end
function methods:Move(value)self.moving=value end
function methods:FireAllClients(...)self.messages[#self.messages+1]={...}end
function methods:FireClient(player,...)self.messages[#self.messages+1]={player,...}end
Instance={new=function(kind)
 local o=setmetatable({kind=kind,Name=kind,C0=CFrame.new(),C1=CFrame.new(),CFrame=CFrame.new(),messages={}}, {__index=methods});objects[#objects+1]=o
 if kind=='RemoteEvent'then o.OnServerEvent=event()end
 if kind=='BindableEvent'then o.Event=event()end
 return o
end}
workspace=Instance.new('Workspace')
Players=Instance.new('Players');Players.players={};Players.PlayerAdded=event();Players.PlayerRemoving=event()
function Players:GetPlayers()return self.players end
RS=Instance.new('ReplicatedStorage');Run={Stepped=event(),IsStudio=function()return true end}
game={GetService=function(_,name)return({Players=Players,ReplicatedStorage=RS,RunService=Run})[name]end}
script=Instance.new('Script');script.Parent=Instance.new('ServerScriptService');script.Parent.VRConfig={};script.Parent.VRChat={}
config={AllowedUserIds={},AutoEnable=false,TrackingTimeout=2,WalkSpeed=12,MaxReach=12,ArmRotationDegrees=90}
function require(module)if module==script.Parent.VRChat then return chat_module end;return config end
function character()
 local char=Instance.new('Model');char.Parent=workspace
 for _,name in ipairs({'Torso','Head','Left Arm','Right Arm','HumanoidRootPart'})do local p=Instance.new('Part');p.Name=name;p.Parent=char end
 local hum=Instance.new('Humanoid');hum.Parent=char;hum.Health=100;hum.AutoRotate=true;hum.WalkSpeed=16;hum.Died=event()
 for _,name in ipairs({'Neck','Left Shoulder','Right Shoulder'})do local motor=Instance.new('Motor6D');motor.Name=name;motor.Parent=char:FindFirstChild('Torso')end
 return char
end
function player(name,id)
 local p=Instance.new('Player');p.Name=name;p.userId=id;p.Parent=Players;p.Chatted=event();p.CharacterAdded=event();p.Character=character();Players.players[#Players.players+1]=p;return p
end
A=player('Alpha',101);B=player('Bravo',202)
function torso(p)return p.Character:FindFirstChild('Torso')end
function vr(p)return torso(p):FindFirstChild('HexagonVR_head')end
function pose(seq,x)return{seq=seq,tracked=true,head={x,1.5,0,1,0,0,0,1,0,0,0,1},left={-1,.5,0,1,0,0,0,1,0,0,0,1},right={1,.5,0,1,0,0,0,1,0,0,0,1}}end
'''

class MultiplayerTests(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime();self.lua.execute(FIXTURE);self.lua.globals().chat_module=self.lua.execute((ROOT/'roblox/VRChat.lua').read_text());self.lua.execute((ROOT/'roblox/VRServer.lua').read_text());self.lua.execute("remote=RS:FindFirstChild('HexagonVR');toggle=script:FindFirstChild('HexagonVRTestToggle')")
 def test_two_players_have_independent_rigs_and_rate_limits(self):
  self.lua.execute('''
  toggle.Event:Fire(A);toggle.Event:Fire(B)
  assert(vr(A)and vr(B),'Second VR player was rejected')
  remote.OnServerEvent:Fire(A,'pose',pose(1,1))
  remote.OnServerEvent:Fire(B,'pose',pose(1,3))
  assert(vr(A).C0.x==1 and vr(B).C0.x==3,'One player consumed the other rate limit')
  time=1.02;remote.OnServerEvent:Fire(A,'pose',pose(2,2));assert(vr(A).C0.x==1,'Own rate limit not enforced')
  time=1.05;remote.OnServerEvent:Fire(B,'pose',pose(2,4));assert(vr(B).C0.x==4)
  ''')
 def test_grip_edges_are_not_dropped_by_the_pose_rate_limit(self):
  self.lua.execute('''
  toggle.Event:Fire(A);local initial=pose(1,1);initial.buttons=0
  remote.OnServerEvent:Fire(A,'pose',initial)
  time=1.015;local press=pose(2,2);press.buttons=64
  remote.OnServerEvent:Fire(A,'pose',press);assert(vr(A).C0.x==2,'Grip press was delayed by pose throttling')
  time=1.030;local release=pose(3,3);release.buttons=0
  remote.OnServerEvent:Fire(A,'pose',release);assert(vr(A).C0.x==3,'Grip release was delayed by pose throttling')
  time=1.031;local spam=pose(4,4);spam.buttons=64
  remote.OnServerEvent:Fire(A,'pose',spam);assert(vr(A).C0.x==3,'Grip edges bypassed the minimum safety interval')
  ''')
 def test_repeated_enable_requests_do_not_toggle_either_player_off(self):
  self.lua.execute("remote.OnServerEvent:Fire(A,'enable');remote.OnServerEvent:Fire(A,'enable');remote.OnServerEvent:Fire(B,'enable');time=3;remote.OnServerEvent:Fire(A,'enable');assert(vr(A)and vr(B));remote.OnServerEvent:Fire(A,'toggle');assert(not vr(A)and vr(B))")
 def test_timeout_does_not_stop_other_player(self):
  self.lua.execute('''
  toggle.Event:Fire(A);toggle.Event:Fire(B)
  remote.OnServerEvent:Fire(A,'pose',pose(1,1));remote.OnServerEvent:Fire(B,'pose',pose(1,3))
  time=3.9;remote.OnServerEvent:Fire(B,'pose',pose(2,4));Run.Stepped:Fire()
  assert(not vr(A)and torso(A):FindFirstChild('Neck'),'Timed-out rig not restored')
  assert(vr(B)and vr(B).C0.x==4,'Other player stopped on timeout')
  assert(A.Character:FindFirstChild('Humanoid').AutoRotate and not B.Character:FindFirstChild('Humanoid').AutoRotate)
  ''')
 def test_reset_disconnect_and_respawn_are_scoped(self):
  self.lua.execute('''
  toggle.Event:Fire(A);toggle.Event:Fire(B)
  remote.OnServerEvent:Fire(A,'reset');assert(A.Character:FindFirstChild('Humanoid').Health==0)
  assert(B.Character:FindFirstChild('Humanoid').Health==100,'Reset affected another player')
  A.Character:FindFirstChild('Humanoid').Died:Fire();assert(not vr(A)and vr(B))
  time=2;A.Character=character();A.CharacterAdded:Fire(A.Character);toggle.Event:Fire(A);assert(vr(A)and vr(B))
  local oldA=A.Character;A.Character=character();A.CharacterAdded:Fire(A.Character)
  assert(oldA:FindFirstChild('Torso'):FindFirstChild('Neck')and vr(B),'Respawn affected another player')
  Players.PlayerRemoving:Fire(B);assert(not vr(B)and torso(B):FindFirstChild('Neck'))
  ''')
 def test_optional_allowlist_and_bad_pose_are_isolated(self):
  self.lua.execute('''
  config.AllowedUserIds={101};toggle.Event:Fire(A);toggle.Event:Fire(B);assert(vr(A)and not vr(B))
  time=2;config.AllowedUserIds={};toggle.Event:Fire(B)
  remote.OnServerEvent:Fire(A,'pose',pose(1,1));remote.OnServerEvent:Fire(B,'pose',pose(1,3))
  local bad=pose(2,2);bad.head[4]=100;time=2.1;remote.OnServerEvent:Fire(A,'pose',bad)
  assert(vr(A).C0.x==1,'Malformed rotation was applied');assert(vr(B).C0.x==3)
  ''')
if __name__=='__main__':unittest.main()
