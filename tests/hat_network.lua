local ok,err=pcall(function()
    local player=game.Players.LocalPlayer
    repeat wait(.1);player=game.Players.LocalPlayer until player and player.Character and player.Character:FindFirstChild('HumanoidRootPart')
    local root=player.Character.HumanoidRootPart;local RS=game:GetService('ReplicatedStorage')
    local remote=RS:WaitForChild('HexagonVR');local stage=RS:WaitForChild('HatTestStage');local control=RS:WaitForChild('HatTestControl')
    local folder=workspace:WaitForChild('HexagonVRWeapons')
    local enabled=false;remote.OnClientEvent:connect(function(action,who,value)if action=='mode'and who==player then enabled=value end end)
    remote:FireServer('enable');local deadline=tick()+5
    repeat remote:FireServer('enable');wait(.2)until enabled or tick()>deadline
    assert(enabled,'Hat client could not enter VR')
    local client=require(game.StarterGui.HexagonVRClient.VRWeaponClient).new(player)
    local seq=0;local hand=root.CFrame*CFrame.new(0,0,-2);local buttons=0
    local function send()
        client:update({right=hand},buttons,false);seq=seq+1
        remote:FireServer('pose',{seq=seq,tracked=true,head={CFrame.new(0,1.5,0):components()},right={root.CFrame:toObjectSpace(hand):components()},trackingRoot={root.CFrame:components()},buttons=buttons,weaponRelease=client:releaseState()})
    end
    local function untilTrue(test,message,timeout)
        local by=tick()+(timeout or 5)
        repeat send();wait(.06)until test()or tick()>by
        assert(test(),message)
    end
    local function nextStage(value)control:FireServer(value);untilTrue(function()return stage.Value>=value end,'Stage acknowledgement missing')end
    local function waitStage(value)untilTrue(function()return stage.Value>=value end,'Other hat client did not reach stage '..value,15)end
    local function check(value,message)assert(value,message);print('HAT_NETWORK_CHECK',message)end
    local function otherPlayer(id)
        for _,p in ipairs(game.Players:GetPlayers())do if p.userId==id then return p end end
    end
    local hat
    untilTrue(function()
        local p=otherPlayer(124);hat=p and p.Character and p.Character:FindFirstChild('Shared Hat Test')
        return hat and hat:FindFirstChild('Wearer')and hat:FindFirstChild('HeadOffset')
    end,'Original worn hat was not registered')
    local originalOffset=hat.HeadOffset.Value
    local function grab()
        buttons=0;hand=hat.Handle.CFrame*CFrame.new(.35,.1,.1);send();wait(.08)
        buttons=64;local by=tick()+5
        repeat
            if hat.Owner.Value~=player then hand=hat.Handle.CFrame*CFrame.new(.35,.1,.1)end
            send();wait(.04)
        until hat.Owner.Value==player or tick()>by
        assert(hat.Owner.Value==player,'Grip did not acquire the hat')
        for n=1,5 do send();wait(.02)end
    end
    local function equip(target)
        hand=target.Character.Head.CFrame*originalOffset*hat.HeldGrip.Value
        for n=1,18 do send();wait(.025)end
        buttons=0;untilTrue(function()return hat.Wearer.Value==target and hat.Parent==target.Character end,'Hat did not equip on the target head')
    end
    if player.userId==124 then
        check(hat.Wearer.Value==player,'The original wearer receives the registered hat')
        print('HAT_NETWORK_OBSERVER_READY');nextStage(1);waitStage(2)
        check(hat.Owner.Value and hat.Owner.Value.userId==123 and hat.Parent==folder,'A different VR player can take a worn hat')
        check(hat.Handle.LocalTransparencyModifier==0 and #client.visuals:GetChildren()==0,'Stealing a hat remains visible on the other client without private clones')
        nextStage(3);waitStage(4)
        local other=otherPlayer(123)
        check(hat.Parent==other.Character and hat.Wearer.Value==other,'The stolen hat equips on the grabbing player and replicates')
        grab();check(hat.Owner.Value==player,'The original wearer can grab the hat back from another player');nextStage(5);waitStage(6)
        equip(other);check(hat.Wearer.Value==other,'A VR player can place a held hat on somebody else');nextStage(7);waitStage(8)
        check(hat.Parent==folder and not hat.Owner.Value and not hat.Wearer.Value and not hat.Handle.Anchored and hat.Handle.LocalTransparencyModifier==0,'A dropped shared hat stays physical and visible to the second client')
        nextStage(9);waitStage(10)
        check(hat.Parent==player.Character and hat.Wearer.Value==player,'A ground hat can be returned to its original wearer')
        check((hat.Handle.Position-(player.Character.Head.CFrame*originalOffset).p).magnitude<.04,'Transferring hats preserves their original head fit')
        nextStage(11);print('HEXAGON_HAT_NETWORK_OBSERVER_PASS');return
    end
    waitStage(1);grab()
    check(hat.Owner.Value==player and hat.Parent==folder,'The first client grips another player\'s original hat through the server')
    local pivot=(client:visualRoot(hat).CFrame*hat.HeldGrip.Value).p
    hand=CFrame.new(hand.p)*(hand-hand.p)*CFrame.Angles(0,.8,0)
    for n=1,16 do send();wait(.025)end
    check(((client:visualRoot(hat).CFrame*hat.HeldGrip.Value).p-pivot).magnitude<.04,'The networked held hat rotates around the off-center touch point')
    nextStage(2);waitStage(3);equip(player);nextStage(4);waitStage(5)
    check(hat.Owner.Value and hat.Owner.Value.userId==124 and hat.Handle.LocalTransparencyModifier==0,'The first client sees the second player holding the hat')
    nextStage(6);waitStage(7);grab()
    hand=root.CFrame*CFrame.new(1.5,0,-2)
    for n=1,15 do send();wait(.025)end
    buttons=0;untilTrue(function()return not hat.Owner.Value end,'Ground release did not reach the server');wait(.2)
    untilTrue(function()return not hat.Owner.Value and not hat.Wearer.Value and hat.Parent==folder and not hat.Handle.Anchored end,'Ground release did not become physical')
    check(not hat.Wearer.Value and hat.Parent==folder and not hat.Handle.Anchored,'Releasing away from heads leaves the same shared hat on the ground')
    nextStage(8);waitStage(9);grab();equip(otherPlayer(124));nextStage(10);waitStage(11)
    print('HEXAGON_HAT_NETWORK_PASS')
end)
if not ok then print('HEXAGON_HAT_NETWORK_FAIL',err)end
