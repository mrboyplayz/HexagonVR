local ok,err=pcall(function()
    local player=game.Players.LocalPlayer
    repeat wait(.1);player=game.Players.LocalPlayer until player and player.Character and player.Character:FindFirstChild('HumanoidRootPart')
    local root=player.Character.HumanoidRootPart
    local remote=game.ReplicatedStorage:WaitForChild('HexagonVR')
    local folder=workspace:WaitForChild('HexagonVRWeapons')
    local gun=folder:WaitForChild('AK47');local magazine=folder:WaitForChild('AKMagazine')
    local layout=require(game.ReplicatedStorage.HexagonVRWeaponGeometry)
    local grip=layout.AK47.Grip
    if player.userId==124 then
        local observer=require(game.StarterGui.HexagonVRClient.VRWeaponClient).new(player)
        assert(workspace.FilteringEnabled==false,'Network test is not FD')
        local mesh
        for _,child in ipairs(gun.Handle:GetChildren())do if child:IsA('SpecialMesh')then mesh=child end end
        assert(mesh and string.sub(mesh.MeshId,1,8)=='https://','Observer received a weapon that requires locally installed mesh files')
        local active=false
        remote.OnClientEvent:connect(function(action,who,value)if action=='mode'and who==player then active=value end end)
        remote:FireServer('enable');local enabledUntil=tick()+5
        repeat wait(.05)until active or tick()>enabledUntil
        assert(active,'Second VR player could not enable VR')
        local pistol=folder:WaitForChild('Pistol');local secondHand=pistol.Handle.CFrame*layout.Pistol.Grip
        local secondSequence=0
        local function secondPose(buttons)
            secondSequence=secondSequence+1
            remote:FireServer('pose',{seq=secondSequence,tracked=true,head={CFrame.new(0,1.5,0):components()},right={root.CFrame:toObjectSpace(secondHand):components()},trackingRoot={root.CFrame:components()},buttons=buttons})
        end
        local untilGrab=tick()+4
        repeat secondPose(64);wait(.06)until pistol.Owner.Value==player or tick()>untilGrab
        assert(pistol.Owner.Value==player,'Second VR player could not pick up the pistol')
        print('NETWORK_PICKUP_CHECK Second VR player independently picks up a weapon')
        print('NETWORK_OBSERVER_READY')
        local sawHeld=false;local droppedAt;local heldAt;local sawSupport=false;local deadline=tick()+35
        while tick()<deadline do
            secondPose(64);observer:update({right=secondHand},64,false)
            if gun.Owner.Value and gun.Owner.Value.userId==123 then
                sawHeld=true
                heldAt=heldAt or tick()
                assert(gun.Handle.LocalTransparencyModifier==0,'Owner visibility suppression leaked to another client')
                assert(pistol.Owner.Value==player,'First VR player consumed the second player\'s pickup ownership')
                assert(#observer.visuals:GetChildren()==1,'Remote client received another player\'s private weapon clones')
                if gun.SupportHand.Value=='left'and tick()-heldAt>.25 then
                    local arm=gun.Owner.Value.Character:FindFirstChild('Left Arm')
                    local wrist=arm and arm.CFrame:pointToWorldSpace(Vector3.new(0,-1,0))
                    assert(wrist and(wrist-(gun.Handle.CFrame*layout.supportGrip(layout.AK47,'left')).p).magnitude<.2,'The remote avatar support hand did not follow the preset grip')
                    sawSupport=true
                end
            elseif sawHeld then
                droppedAt=droppedAt or tick()
                assert(gun.Parent==folder and gun.Handle.Parent==gun,'Dropped weapon was deleted from the other client')
                assert(gun.Handle.LocalTransparencyModifier==0 and gun.Handle.Transparency<1,'Dropped weapon is hidden on the observer')
                if tick()-droppedAt>.7 then
                    assert(gun.Handle.Position.y>-.5,'Dropped weapon fell through the map')
                    print('NETWORK_PICKUP_CHECK Another client sees the shared held gun without local asset files')
                    print('NETWORK_PICKUP_CHECK Dropped gun remains visible and physical on the observer')
                    assert(sawSupport,'Observer never saw the replicated preset support grip')
                    print('NETWORK_PICKUP_CHECK Other players see the support hand fixed to the authored foregrip')
                    local releasedBy=tick()+1
                    repeat secondPose(0);observer:update({},0,false);wait(.06)until not pistol.Owner.Value or tick()>releasedBy
                    assert(not pistol.Owner.Value,'Second VR player could not release its weapon')
                    print('NETWORK_PICKUP_CHECK Both VR players can hold independent weapons simultaneously and release them')
                    print('HEXAGON_NETWORK_OBSERVER_PASS');return
                end
            end
            wait(.02)
        end
        error('Observer never saw a held and released weapon')
    end
    local enabled=false
    remote.OnClientEvent:connect(function(action,who,value)if action=='mode'and who==player then enabled=value end end)
    remote:FireServer('enable');local deadline=tick()+5
    repeat wait(.05)until enabled or tick()>deadline
    assert(enabled,'Network client could not enable VR')
    local seq=0;local client
    local function send(buttons,left,right)
        if client then client:update({left=left,right=right},buttons,false)end
        seq=seq+1
        local function localFrame(cf)return cf and{root.CFrame:toObjectSpace(cf):components()}or nil end
        remote:FireServer('pose',{seq=seq,tracked=true,head={CFrame.new(0,1.5,0):components()},left=localFrame(left),right=localFrame(right),trackingRoot={root.CFrame:components()},buttons=buttons,weaponRelease=client and client:releaseState()or nil})
    end
    local right=gun.Handle.CFrame*grip
    send(0,nil,right);wait(.07)
    deadline=tick()+3
    repeat send(64,nil,right);wait(.06)until gun.Owner.Value==player or tick()>deadline
    assert(gun.Owner.Value==player,'Server did not grant the client gun ownership')
    print('NETWORK_PICKUP_CHECK Separate client grips AK-47 through the remote server')
    local left=CFrame.new((gun.Handle.CFrame*grip):pointToWorldSpace(Vector3.new(0,0,-1.9)))
    deadline=tick()+3
    repeat send(96,left,right);wait(.06)until gun.SupportHand.Value=='left'or tick()>deadline
    assert(gun.SupportHand.Value=='left','Server did not grant the support grip')
    client=require(game.StarterGui.HexagonVRClient.VRWeaponClient).new(player)
    client:update({left=left,right=right},96,false)
    for n=1,7 do send(96,left,right);wait(.02)end
    local visible=client:visualRoot(gun);local steady=visible.CFrame
    for n=1,12 do send(96,left,right);client:update({left=left,right=right},96,false);wait(.02)end
    assert(visible~=gun.Handle and(visible.Position-steady.p).magnitude<.02,'Replicated gun movement disturbed the private render pose')
    print('NETWORK_PICKUP_CHECK Replicated two-hand AK stays stable in the separate client')
    gun=nil
    for n=1,35 do
        local garbage={};for k=1,2000 do garbage[k]={k,tostring(k)..tostring(n)}end
        garbage=nil;pcall(collectgarbage,'collect')
        send(96,left,right);client:update({left=left,right=right},96,false);wait(.02)
    end
    gun=folder:WaitForChild('AK47')
    print('NETWORK_PICKUP_CHECK Held visibility state survives garbage collection in a real client')
    send(0,nil,right)
    for n=1,45 do send(0,nil,right);client:update({left=left,right=right},0,false);wait(.02)end
    assert(gun.Owner.Value==nil,'Release did not reach the server')
    assert(gun.Handle.LocalTransparencyModifier==0,'Dropped gun stayed locally hidden')
    assert(gun.Handle.Parent==gun and gun.Parent==folder and gun.Handle.Position.y>-.5,'Dropped gun disappeared or fell through the map')
    print('NETWORK_PICKUP_CHECK Dropped gun restores visibility and remains physical on its owning client')
    local magHand=magazine.Handle.CFrame
    send(0,magHand,right);wait(.07)
    deadline=tick()+3
    repeat send(32,magHand,right);wait(.06)until magazine.Owner.Value==player or tick()>deadline
    assert(magazine.Owner.Value==player,'Server did not grant the magazine grip')
    print('NETWORK_PICKUP_CHECK Separate client grips a magazine through the remote server')
    send(0,magHand,right);wait(.15)
    assert(magazine.Owner.Value==nil,'Magazine release did not replicate')
    client:update({},0,true)
    print('HEXAGON_NETWORK_PICKUP_PASS')
end)
if not ok then print('HEXAGON_NETWORK_PICKUP_FAIL',err)end
