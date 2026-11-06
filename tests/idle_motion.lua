wait(2)
local ok,err=pcall(function()
    local player=game.Players.LocalPlayer;local char=player.Character
    repeat wait(.1);char=player.Character until char and char:FindFirstChild('HumanoidRootPart')
    local root=char.HumanoidRootPart;local hum=char.Humanoid
    root.CFrame=CFrame.new(0,5,20);root.Velocity=Vector3.new();root.RotVelocity=Vector3.new()
    wait(1)
    local remote=game.ReplicatedStorage:WaitForChild('HexagonVR')
    local box=player.PlayerScripts:WaitForChild('HexagonVRLocalMailbox');local seq=1000;local handWidth=1
    local function expect(value,text)assert(value,text);print('IDLE_MOTION_CHECK',text)end
    local function runFor(seconds,headAt,move,jump)
        local begin=tick();local start=root.Position;local maximum=0;local highest=start.y
        repeat
            local t=tick()-begin
            box.head.Value=headAt and headAt(t)or CFrame.new(0,1.5,0)
            box.left.Value=CFrame.new(-handWidth,.3,-.5);box.right.Value=CFrame.new(handWidth,.3,-.5)
            box.move.Value=move or Vector3.new(0,0,jump and t<.08 and 1 or 0)
            box.ui.Value=Vector3.new();box.settings.Value=Vector3.new(110,.45,4)
            seq=seq+1;box.control.Value=Vector3.new(7,seq,65*4+1)
            wait(.01)
            local d=root.Position-start;maximum=math.max(maximum,Vector3.new(d.x,0,d.z).magnitude);highest=math.max(highest,root.Position.y)
        until tick()-begin>seconds
        return maximum,highest-start.y
    end
    remote:FireServer('enable');runFor(1)
    expect(not root.Anchored,'The drift regression uses a freely simulated character')
    local drift=runFor(5)
    print('IDLE_MOTION_METRIC neutral_max_xz',drift)
    expect(drift<.05,'Stationary headset/controllers with zero stick input cannot propel the character')
    local movingHead=runFor(3,function(t)return CFrame.new(.1*math.sin(t*3),1.5,.1*math.cos(t*3))*CFrame.Angles(.15*math.sin(t*4),.8*math.sin(t*2),0)end)
    print('IDLE_MOTION_METRIC moving_head_max_xz',movingHead)
    expect(movingHead<.1,'Physical head turns and small tracking movements cannot push the walking body')
    handWidth=.2
    local overlapping=runFor(2)
    expect(overlapping<.05,'Holding the private arms inside the body cannot create a collision impulse')
    handWidth=1
    local distance=runFor(1.5,nil,Vector3.new(0,-1,0))
    expect(distance>8,'Intentional stick locomotion still moves the character')
    runFor(.75)
    local stopped=runFor(2)
    expect(stopped<.05,'Releasing the stick stops the body without drift resuming')
    local _,height=runFor(2,nil,nil,true)
    expect(height>1,'Jump input still lifts the freely simulated character')
    remote:FireServer('toggle');wait(.2)
    expect(not workspace.CurrentCamera:FindFirstChild('HexagonVRLocalArms'),'Leaving VR removes the first-person appearance rig')
    print('HEXAGON_IDLE_MOTION_PASS')
end)
if not ok then print('HEXAGON_IDLE_MOTION_FAIL',err)end
