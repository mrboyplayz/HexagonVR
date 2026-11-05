wait(1)
local ok,err=pcall(function()
    local player=game.Players.LocalPlayer
    repeat wait(.1);player=game.Players.LocalPlayer until player and player.Character and player.Character:FindFirstChild('HumanoidRootPart')
    local char=player.Character;local root=char.HumanoidRootPart;root.Anchored=true;root.CFrame=CFrame.new(0,5,0)
    local remote=game.ReplicatedStorage:WaitForChild('HexagonVR');remote:FireServer('enable');wait(.3)
    local box=player.PlayerScripts:WaitForChild('HexagonVRLocalMailbox')
    local right=CFrame.new(1,.5,-.6);local left=CFrame.new(-1,.5,-.6)
    box.head.Value=CFrame.new(0,1.5,0);box.right.Value=right;box.left.Value=left;box.move.Value=Vector3.new();box.ui.Value=Vector3.new();box.settings.Value=Vector3.new(110,.45,4)
    local seq=1000
    local function frame()seq=seq+1;box.control.Value=Vector3.new(7,seq,65*4+1);wait(.02)end
    for n=1,15 do frame()end
    local function expect(value,text)assert(value,text);print('ARMS_CHECK',text)end
    local model=workspace.CurrentCamera:FindFirstChild('HexagonVRLocalArms')
    expect(model and model:FindFirstChild('Right Arm')and model:FindFirstChild('Left Arm'),'Tracked first-person arms render as private camera descendants')
    expect(math.abs(model['Right Arm'].Transparency-.45)<.001 and char['Right Arm'].Transparency==0 and char['Right Arm'].LocalTransparencyModifier==1,'Only the local arm copies are semi-transparent; shared arm transparency stays unchanged')
    local beforeRight=right;local beforeLeft=left
    local maximum=0
    local Run=game:GetService('RunService')
    Run:BindToRenderStep('ArmEndpointRegression',Enum.RenderPriority.Last.Value+10,function()
        maximum=math.max(maximum,(root.CFrame:pointToObjectSpace(model['Right Arm'].CFrame:pointToWorldSpace(Vector3.new(0,-model['Right Arm'].Size.y/2,0)))-beforeRight.p).magnitude,(root.CFrame:pointToObjectSpace(model['Left Arm'].CFrame:pointToWorldSpace(Vector3.new(0,-model['Left Arm'].Size.y/2,0)))-beforeLeft.p).magnitude)
    end)
    for n=1,80 do
        box.head.Value=CFrame.new(.2*math.sin(n*.05),1.5,0)*CFrame.Angles(.5*math.sin(n*.09),math.rad(-120+n*3),.15*math.cos(n*.08));frame()
    end
    Run:UnbindFromRenderStep('ArmEndpointRegression')
    expect(maximum<.002,'Physical head turns and moving shoulders cannot move stationary tracked wrists')
    local Body=require(game.ReplicatedStorage.HexagonVRBody);local yaw=0
    for n=1,60 do local h,t;h,t,yaw=Body.sample(CFrame.Angles(0,math.rad(170),0),yaw,1/90)end
    local stable=true
    for degrees=171,200 do local old=yaw;local h,t;h,t,yaw=Body.sample(CFrame.Angles(0,math.rad(degrees),0),yaw,1/90);if yaw<old-.01 then stable=false end end
    expect(stable,'Torso follow stays continuous across the rear-facing head-yaw boundary')
    remote:FireServer('toggle');wait(.15)
    expect(not workspace.CurrentCamera:FindFirstChild('HexagonVRLocalArms')and char['Right Arm'].LocalTransparencyModifier==0,'Leaving VR removes private limbs and restores the real arms')
    print('HEXAGON_ARMS_ENGINE_PASS')
end)
if not ok then print('HEXAGON_ARMS_ENGINE_FAIL',err)end
