local ok,err=pcall(function()
    local player=game.Players.LocalPlayer or game.Players:GetPlayers()[1]
    repeat wait(.1)until player.Character and player.Character:FindFirstChild('HumanoidRootPart')
    local root=player.Character.HumanoidRootPart;root.Anchored=true;root.CFrame=CFrame.new(0,5,10)
    local W=require(game.ServerScriptService.VRWeapons).new({Weapons={Enabled=true,RespawnSeconds=9999}})
    local G=require(game.ReplicatedStorage.HexagonVRWeaponGeometry)
    local gun,mag
    for _,item in ipairs(W.items)do item.root.Anchored=true;if item.kind=='AK47'then gun=item elseif item.kind=='AKMagazine'and not mag then mag=item end end
    local client=require(game.StarterGui.HexagonVRClient.VRWeaponClient).new(player)
    local function expect(value,text)assert(value,text);print('MOTION_CHECK',text)end
    local primary=CFrame.new(0,5,0);local base=primary*gun.grip:inverse()
    local front=CFrame.new(base:pointToWorldSpace(gun.layout.Foregrip))
    gun.owner.Value=player;gun.hand.Value='right';gun.supportGrab.Value=''
    gun.supportAnchor.Value=primary:pointToObjectSpace(front.p)
    gun.root.CFrame=base
    local function render(left,right,buttons)
        client.lastAt=tick()-1/90;client:update({left=left,right=right},buttons or 96,false)
        return client:visualRoot(gun.model).CFrame
    end
    local steady=render(front,primary)
    expect(client.visualHands.left~=nil and client:state(gun.model).supportPendingAt~=nil,'The foregrip engages locally on squeeze before a server acknowledgement')
    gun.supportGrab.Value='left'
    local acknowledged=render(front,primary)
    expect(steady.lookVector:Dot(acknowledged.lookVector)>.9999,'Server foregrip confirmation preserves the locally captured contact')
    wait(.1)
    client.handFilters={}
    local rotatedFront=front*CFrame.Angles(.8,1.2,.7)
    local fixed=render(rotatedFront,primary)
    expect(fixed.lookVector:Dot(steady.lookVector)>.9999,'Support-wrist rotation cannot steer or roll the gun')
    local grip=client.visualHands.left
    local expected=fixed*G.supportGrip(gun.layout,'left')
    expect((grip.p-expected.p).magnitude<.001 and grip.lookVector:Dot(expected.lookVector)>.9999,'The support hand uses the authored position and wrist rotation')
    local follows=true
    for n=1,40 do
        local cf=render(CFrame.new(front.p+Vector3.new(math.sin(n*.2)*.8,.2,0))*CFrame.Angles(0,n*.1,.4),primary)
        local actual=client.handOrigin*client.handFilters.left.filtered
        if(cf*gun.grip):vectorToWorldSpace(gun.supportAnchor.Value).unit:Dot((actual.p-primary.p).unit)<.9999 then follows=false end
    end
    expect(follows,'Support-controller position steers the rifle using the preset grip vector')
    client.handFilters={}
    local turned=primary*CFrame.Angles(.1,.6,.2)
    local aimed=render(rotatedFront,turned)
    expect((aimed*gun.grip):vectorToWorldSpace(gun.supportAnchor.Value).unit:Dot((rotatedFront.p-turned.p).unit)>.9999 and((aimed*gun.grip).p-turned.p).magnitude<.001,'Both controller positions steer aim while the rear grip stays at the trigger hand')
    local attached=client.visualHands.left
    expect((attached.p-(aimed*G.supportGrip(gun.layout,'left')).p).magnitude<.001,'The preset front hand stays on the moving gun')
    client.handFilters={};render(front,primary,64)
    expect(client.visualHands.left==nil,'Releasing the support grip immediately frees the hand')
    local calibrated=require(game.StarterGui.HexagonVRClient.VRWeaponClient).new(player,{armForward=.3,command=function()end})
    local rawPrimary=CFrame.new(0,5,0);local rawFront=CFrame.new(rawPrimary.p+gun.layout.Grip:pointToObjectSpace(gun.layout.Foregrip))
    local rear=rawPrimary*CFrame.new(0,0,-.3);gun.root.CFrame=rear*gun.grip:inverse()
    calibrated:update({right=rear,left=rawFront*CFrame.new(0,0,-.3)},96,false);wait(.1)
    calibrated:update({right=rear,left=rawFront*CFrame.new(0,0,-.3)},96,false)
    local beforeOffset=calibrated:visualRoot(gun.model).CFrame
    for n=1,30 do calibrated.lastAt=tick()-1/90;calibrated:update({right=rear,left=rawFront*CFrame.Angles(.5,.8,.4)*CFrame.new(0,0,-.3)},96,false)end
    expect(calibrated:visualRoot(gun.model).CFrame.lookVector:Dot(beforeOffset.lookVector)>.9999,'Forward hand calibration cannot turn support-wrist rotation into an aiming wobble')
    calibrated:update({},0,true);gun.root.CFrame=base;client.handFilters={}
    gun.insertedModel.Value=mag.model;mag.mount.Value=gun.model
    mag.owner.Value=player;mag.hand.Value='left';mag.root.CFrame=base*gun.magOffset
    gun.supportGrab.Value='';client.handFilters={}
    local distant=CFrame.new(-3,5,0)
    render(distant,primary)
    local visible=client:visualRoot(gun.model);local visibleMag=client:visualRoot(mag.model)
    expect((visibleMag.Position-(visible.CFrame*gun.magOffset).p).magnitude<.001,'A mounted magazine cannot be overwritten by a stale free-hand ownership update')
    mag.model.Parent=nil;mag.model.Parent=W.folder
    render(distant,primary)
    expect((visibleMag.Position-(client:visualRoot(gun.model).CFrame*gun.magOffset).p).magnitude<.001,'Magazine attachment is independent of model iteration order')
    local fixed=true
    for n=1,90 do
        local move=CFrame.new(math.sin(n*.1),.2*math.cos(n*.1),0)*CFrame.Angles(.15*math.sin(n*.1),.4*math.sin(n*.08),.1*math.cos(n*.1))
        render(distant,move*primary)
        local gunCF=client:visualRoot(gun.model).CFrame
        if(visibleMag.Position-(gunCF*gun.magOffset).p).magnitude>.001 then fixed=false end
    end
    expect(fixed,'The magazine remains rigid through combined gun translation, pitch, yaw, and roll')
    -- Start an extraction in the rendered gun frame, then deliver an obsolete
    -- server baseline. Local grip acquisition must preserve the starting pose.
    client.handFilters={};mag.owner.Value=nil;mag.hand.Value='';render(distant,primary,64)
    local bottom=CFrame.new((client:visualRoot(gun.model).CFrame):pointToWorldSpace(gun.layout.RemovePoint))
    render(bottom,primary,96)
    gun.removingHand.Value='left';gun.removalStart.Value=100
    for n=1,20 do render(bottom*CFrame.new(0,-.2,0),primary,96)end
    local gunCF=client:visualRoot(gun.model).CFrame
    local extracted=gunCF:toObjectSpace(visibleMag.CFrame)
    expect(extracted.p.y<gun.magOffset.p.y-.15 and extracted.p.y>gun.magOffset.p.y-.25,'Magazine extraction uses the local grip baseline without snapping to stale server coordinates')
    local beforeDetach=visibleMag.CFrame
    mag.mount.Value=nil;gun.insertedModel.Value=nil;mag.owner.Value=player;mag.hand.Value='left';mag.heldGrip.Value=CFrame.new()
    render(bottom*CFrame.new(0,-.2,0),primary,96)
    expect((visibleMag.Position-beforeDetach.p).magnitude<.001,'Detaching the magazine preserves its rendered position during the ownership handoff')
    beforeDetach=visibleMag.CFrame;mag.heldGrip.Value=CFrame.new(2,2,2)
    render(bottom*CFrame.new(0,-.2,0),primary,96)
    expect((visibleMag.Position-beforeDetach.p).magnitude<.001,'A delayed server grip update cannot move an already held magazine')
    gun.removingHand.Value='';mag.loadingInto.Value=gun.model;mag.loadingStart.Value=100;mag.loadingProgress.Value=.2
    client.handFilters={};local left=base*G.magazineFrame(gun.layout,.2)*client:state(mag.model).localGrip
    render(left,primary,96)
    for n=1,30 do render(CFrame.new(0,gun.layout.InsertDepth*.2,0)*left,primary,96)end
    gunCF=client:visualRoot(gun.model).CFrame
    local expected=gunCF*G.magazineFrame(gun.layout,.4)
    expect((visibleMag.Position-expected.p).magnitude<.003,'Guided loading measures hand travel in one render frame even when the server baseline is delayed')
    local seatedHand=CFrame.new(0,gun.layout.InsertDepth*.75,0)*left
    for n=1,30 do render(seatedHand,primary,96)end
    beforeDetach=visibleMag.CFrame;mag.loadingInto.Value=nil
    render(seatedHand,primary,96)
    expect((visibleMag.Position-beforeDetach.p).magnitude<.003,'A brief gap between guide and mount metadata cannot yank the magazine back to the hand')
    gun.insertedModel.Value=mag.model
    render(seatedHand,primary,96)
    local gap=(visibleMag.Position-(client:visualRoot(gun.model).CFrame*gun.magOffset).p).magnitude
    expect(gap<.025,'Magazine latching eases through the remaining gap without a large snap')
    for n=1,30 do
        render(seatedHand,primary,96)
        local nextGap=(visibleMag.Position-(client:visualRoot(gun.model).CFrame*gun.magOffset).p).magnitude
        assert(nextGap<=gap+.0001,'Magazine latching reversed during a metadata handoff');gap=nextGap
    end
    expect((visibleMag.Position-(client:visualRoot(gun.model).CFrame*gun.magOffset).p).magnitude<.001,'The guide-to-mounted handoff cannot show a frame of free-hand magazine motion')
    client:update({},0,true)
    expect(mag.root.LocalTransparencyModifier==0 and not visibleMag.Parent.Parent,'Interrupted reloads restore the shared magazine and remove the private visual')
    -- A new locally predicted guide must ignore a previous reload's progress.
    mag.owner.Value=player;mag.hand.Value='left';mag.mount.Value=nil;gun.insertedModel.Value=nil;mag.loadingInto.Value=nil;mag.loadingProgress.Value=1
    client.handFilters={}
    local entry=base*G.magazineFrame(gun.layout,0)
    render(entry,primary,96)
    local magState=client:state(mag.model)
    expect(magState.loadingFor==gun.model and magState.guidePendingAt~=nil,'The local reload guide starts before a server acknowledgement')
    expect((client:visualRoot(mag.model).Position-entry.p).magnitude<.001,'Starting another reload cannot reuse a stale fully-loaded progress value')
    client:update({},0,true);client.handFilters={}
    local rotation=(entry-entry.p)*CFrame.Angles(0,0,math.rad(20))
    local top=entry:pointToWorldSpace(mag.layout.Top)
    local tilted=CFrame.new(top-rotation:vectorToWorldSpace(mag.layout.Top))*rotation
    render(tilted,primary,96)
    local tiltedVisual=client:visualRoot(mag.model).CFrame
    expect((tiltedVisual.p-tilted.p).magnitude<.001 and tiltedVisual:vectorToWorldSpace(Vector3.new(0,1,0)):Dot(tilted:vectorToWorldSpace(Vector3.new(0,1,0)))>.99999,'Entering the magwell preserves a tilted hand pose instead of snapping into alignment')
    for n=1,30 do render(CFrame.new(0,gun.layout.InsertDepth*.25,0)*tilted,primary,96)end
    local quarter=client:visualRoot(mag.model).CFrame
    expect(quarter:vectorToWorldSpace(Vector3.new(0,1,0)):Dot(tilted:vectorToWorldSpace(Vector3.new(0,1,0)))>math.cos(math.rad(5)),'A shallow insertion applies only gentle alignment assistance')
    for n=1,30 do render(CFrame.new(0,gun.layout.InsertDepth,0)*tilted,primary,96)end
    expect((client:visualRoot(mag.model).Position-(client:visualRoot(gun.model).CFrame*gun.magOffset).p).magnitude<.003,'Alignment reaches the seated socket only after a full physical push')
    client:update({},0,true)
    gun.owner.Value=player;gun.hand.Value='right';gun.root.LocalTransparencyModifier=1
    render(distant,primary,64)
    gun.owner.Value=nil;gun.hand.Value=''
    render(distant,primary,0)
    expect(gun.root.LocalTransparencyModifier==0 and gun.slidePart.LocalTransparencyModifier==0,'Dropping restores every authoritative gun part even after stale local hiding')
    local other=Instance.new('Model');other.Name='OtherPlayerIdentity';gun.owner.Value=other;gun.hand.Value='right'
    local authoritativeGun,authoritativeSlide=gun.root.CFrame,gun.slidePart.CFrame
    gun.slideOffset.Value=gun.layout.SlideRest*CFrame.new(0,0,.3)
    render(distant,primary,96)
    expect((gun.root.Position-authoritativeGun.p).magnitude<.001 and(gun.slidePart.Position-authoritativeSlide.p).magnitude<.001,'A client never rewrites another player\'s replicated weapon parts in FD')
    print('HEXAGON_MOTION_ENGINE_PASS')
end)
if not ok then print('HEXAGON_MOTION_ENGINE_FAIL',err)end
