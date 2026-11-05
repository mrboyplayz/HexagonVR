-- Rear-hand anchored two-hand poses, guided magazines, and visible weapon recoil.
local M={}
local Geometry=require(game:GetService("ReplicatedStorage"):WaitForChild("HexagonVRWeaponGeometry"))
local FX=require(script:WaitForChild("VRWeaponFX"))
local function down(mask,bit)return math.floor(mask/bit)%2==1 end
local function parts(node,out)
    out=out or{}
    for _,child in ipairs(node:GetChildren())do
        if child:IsA("BasePart")then out[#out+1]=child end
        parts(child,out)
    end
    return out
end
local function stripClone(node)
    for _,child in ipairs(node:GetChildren())do
        if child:IsA("BasePart")or child:IsA("JointInstance")or child:IsA("Sound")or child:IsA("ValueBase")or child:IsA("LuaSourceContainer")then child:Destroy()
        else stripClone(child)end
    end
end
local function frameAngle(a,b)
    local dot=math.min(a.lookVector:Dot(b.lookVector),a:vectorToWorldSpace(Vector3.new(0,1,0)):Dot(b:vectorToWorldSpace(Vector3.new(0,1,0))))
    return math.acos(math.max(-1,math.min(1,dot)))
end
local function spring(x,v,omega,dt)
    local c=v+omega*x;local decay=math.exp(-omega*dt)
    return (x+c*dt)*decay,(v-omega*c*dt)*decay
end
function M.new(player,menu,remote)
    -- Instance wrappers can leave a weak-key table while the engine still owns
    -- their parts. Keep suppression state until it is explicitly restored.
    local self={fx=FX.new(),cache={},lastButtons=0,lastAt=tick(),sentTriggers={},visualHands={},aim={},handFilters={},heldFrames={},releaseFrames={},releaseAt={}}
    local visuals=Instance.new("Model");visuals.Name="HexagonVRPredictedWeapons";visuals.Parent=workspace.CurrentCamera;self.visuals=visuals
    function self:state(model)
        local s=self.cache[model]
        if not s then
            local count=model:FindFirstChild("ShotCount")
            s={confirmed=count and count.Value or 0,predicted=count and count.Value or 0,ammo=0,
                recoil=0,velocity=0,yaw=0,yawVelocity=0,slide=0,lastShot=-math.huge,eventAt=-math.huge}
            self.cache[model]=s
        end
        return s
    end
    function self:aimState()return self.aim end
    function self:releaseState()return self.releaseFrames end
    function self:visualRoot(model)
        local s=self.cache[model]
        return s and s.visual and s.visual.Parent and s.visual:FindFirstChild("Handle")or model:FindFirstChild("Handle")
    end
    function self:visual(model)
        local s=self:state(model)
        if not s.visual then
            s.visual=Instance.new("Model");s.visual.Name=model.Name;s.hidden={};s.copies={}
            for _,original in ipairs(parts(model))do
                    local copy=original:Clone()
                    stripClone(copy)
                    copy.Anchored=true;copy.CanCollide=false;copy.LocalTransparencyModifier=0;copy.Parent=s.visual
                    s.copies[original]=copy
            end
        end
        s.rendered=true;s.visual.Parent=visuals
        for _,original in ipairs(parts(model))do
                if s.hidden[original]==nil then s.hidden[original]=true end
                original.LocalTransparencyModifier=1
        end
        return s.visual:FindFirstChild("Handle"),s.visual
    end
    function self:finishVisuals()
        for model,s in pairs(self.cache)do
            if s.visual and not s.rendered then
                s.visual.Parent=nil
                for original in pairs(s.hidden)do if original.Parent then original.LocalTransparencyModifier=0 end end
                s.hidden={}
                if not model.Parent then s.visual:Destroy();s.visual=nil end
            end
            if not model.Parent then self.cache[model]=nil end
        end
    end
    function self:stableHands(input,dt)
        local character=player.Character;local root=character and character:FindFirstChild("HumanoidRootPart")
        local origin=root and root.CFrame or CFrame.new();local output={}
        self.handOrigin=origin;self.rawHands={}
        local forward=menu and menu.armForward or 0
        for _,hand in ipairs({"left","right"})do
            local raw=input[hand]
            if raw then
                local current=origin:toObjectSpace(raw*CFrame.new(0,0,forward));local state=self.handFilters[hand]
                if not state or(current.p-state.raw.p).magnitude>2 then state={raw=current,filtered=current};self.handFilters[hand]=state end
                local positionSpeed=(current.p-state.raw.p).magnitude/math.max(.001,dt)
                local angle=frameAngle(current,state.raw)
                local rate=24+math.min(140,positionSpeed*16+angle/math.max(.001,dt)*65)
                local difference=(current.p-state.filtered.p).magnitude
                local angularDifference=frameAngle(current,state.filtered)
                if difference>.0025 or angularDifference>math.rad(.08)then state.filtered=state.filtered:lerp(current,1-math.exp(-dt*rate))end
                state.raw=current;self.rawHands[hand]=origin*state.filtered;output[hand]=self.rawHands[hand]*CFrame.new(0,0,-forward)
            else self.handFilters[hand]=nil end
        end
        return output
    end
    function self:feedback(model,layout,cf,position,number,hand)
        local root=self:visualRoot(model);if not root then return end
        local s=self:state(model);s.lastShot=tick()
        local support=model:FindFirstChild("SupportHand")
        local stability=support and support.Value~=""and .65 or 1
        s.recoil=math.min(12,s.recoil+layout.Recoil*.4*stability)
        s.velocity=s.velocity+layout.Recoil*38*stability
        s.yawVelocity=s.yawVelocity+(number%2==0 and 1 or -1)*(layout.YawKick or .6)*30*stability
        self.fx:shot(root,layout,cf,position,number)
        if menu and hand then menu:command(9,hand=="left"and 0 or 1,layout.Automatic and 2400 or 3000)end
    end
    function self:confirmShot(model,data)
        if not model or not model.Parent or type(data)~="table"then return end
        local layout=Geometry.forModel(model);if not layout or not layout.Gun then return end
        local owner=model:FindFirstChild("Owner");local s=self:state(model)
        local predicted=owner and owner.Value==player and s.predicted>=data.count
        s.confirmed=data.count;s.predicted=math.max(s.predicted,data.count)
        s.ammo=data.ammo+(data.chamber and 1 or 0);s.eventAt=tick()
        if not predicted then self:feedback(model,layout,data.frame,data.position,data.count)end
        self.fx:impact(data.position,data.normal,data.hit)
    end
    function self:confirmEject(model,data)
        if not model or not model.Parent or type(data)~="table"then return end
        local layout=Geometry.forModel(model)
        if layout and layout.ManualBolt then self.fx:eject(layout,data.frame,data.number or 0)end
    end
    function self:update(hands,buttons,blocked)
        local now=tick();local dt=math.max(.001,math.min(.05,now-self.lastAt));self.lastAt=now
        local previous=self.lastButtons;self.lastButtons=buttons;self.visualHands={}
        for _,hand in ipairs({"left","right"})do
            local bit=hand=="left"and 32 or 64
            if down(previous,bit)and not down(buttons,bit)then
                local held=self.heldFrames[hand]
                if held then self.releaseFrames[hand]={model=held.model,frame={held.frame:components()},velocity={held.velocity.x,held.velocity.y,held.velocity.z}};self.releaseAt[hand]=now end
            elseif down(buttons,bit)or(self.releaseAt[hand]and now-self.releaseAt[hand]>.3)then self.releaseFrames[hand]=nil;self.releaseAt[hand]=nil end
        end
        for _,s in pairs(self.cache)do s.rendered=false end
        visuals.Parent=workspace.CurrentCamera
        self.fx.folder.Parent=workspace.CurrentCamera
        if remote then
            for _,hand in ipairs({"left","right"})do
                local pressed=not blocked and down(buttons,hand=="left"and 128 or 1)
                if self.sentTriggers[hand]~=pressed then
                    self.sentTriggers[hand]=pressed;remote:FireServer("weaponTrigger",{hand=hand,pressed=pressed,recoil=self.aim[hand]})
                end
            end
        end
        local folder=workspace:FindFirstChild("HexagonVRWeapons");self.aim={}
        if not folder or blocked then
            self.handFilters={};self.heldFrames={};self.releaseFrames={};self.releaseAt={}
            for _,s in pairs(self.cache)do
                s.localHeld=false;s.localGrip=nil;s.wasMounted=nil;s.removeSnapshot=nil;s.mountFrame=nil;s.loadingFor=nil;s.loadingSmooth=nil
                s.supportHand=nil;s.supportAnchor=nil;s.supportBlend=nil;s.aimRotation=nil
                s.seatBlend=nil;s.guidePendingAt=nil;s.guideConfirmed=nil;s.rejectedGuide=nil
            end
            self:finishVisuals();return
        end
        hands=self:stableHands(hands,dt)
        local occupied={}
        for _,model in ipairs(folder:GetChildren())do
            local owner=model:FindFirstChild("Owner");local hand=model:FindFirstChild("Hand")
            if owner and owner.Value==player and hand then occupied[hand.Value]=model end
        end
        for _,model in ipairs(folder:GetChildren())do
            local owner=model:FindFirstChild("Owner");local hand=model:FindFirstChild("Hand");local root=model:FindFirstChild("Handle")
            local layout=Geometry.forModel(model)
            if owner and root and layout and not layout.MagazineItem then
                local s=self:state(model);local localOwner=owner.Value==player;local heldHand=hand and hand.Value
                if localOwner and(not s.localHeld or heldHand~=s.lastHeldHand)then
                    if now-s.lastShot>.15 then s.recoil=0;s.velocity=0;s.yaw=0;s.yawVelocity=0 end
                    s.aimRotation=nil;s.supportBlend=nil;s.supportHand=nil;s.supportAnchor=nil;s.wearGrip=nil;s.supportState=nil;s.supportPendingAt=nil;s.supportRejected=nil
                end
                s.localHeld=localOwner
                if localOwner then s.lastHeldHand=heldHand end
                if localOwner then
                    local originalRoot=root
                    local renderedModel=model
                    if localOwner then root,renderedModel=self:visual(model)end
                    local support=model:FindFirstChild("SupportHand");local anchor=model:FindFirstChild("SupportAnchor")
                    if layout.Gun then
                        s.recoil,s.velocity=spring(s.recoil,s.velocity,16,dt)
                        s.yaw,s.yawVelocity=spring(s.yaw,s.yawVelocity,18,dt)
                        s.recoil=math.max(0,math.min(12,s.recoil));s.yaw=math.max(-4,math.min(4,s.yaw))
                    end
                    local mount=model:FindFirstChild("MountedTo")
                    if localOwner and hands[heldHand]and down(buttons,heldHand=="left"and 32 or 64)and not(mount and mount.Value)then
                        if layout.Gun then
                            local supportHand=support and support.Value or""
                            local other=heldHand=="left"and"right"or"left"
                            local squeezed=hands[other]and down(buttons,other=="left"and 32 or 64)
                            local rack=model:FindFirstChild("SlideHand");local removing=model:FindFirstChild("RemovingHand")
                            if not squeezed then s.supportPendingAt=nil;s.supportRejected=nil
                            elseif supportHand~=""then s.supportPendingAt=nil
                            elseif s.supportPendingAt then
                                if now-s.supportPendingAt<.35 and not occupied[other]then supportHand=other
                                else s.supportPendingAt=nil;s.supportRejected=true end
                            elseif not s.supportRejected and not occupied[other]and(not rack or rack.Value=="")and(not removing or removing.Value=="")and Geometry.supportContact(layout,root.CFrame,hands[heldHand],hands[other])then
                                s.supportPendingAt=now;supportHand=other
                            end
                            local front=supportHand~=""and supportHand~=heldHand and down(buttons,supportHand=="left"and 32 or 64)and hands[supportHand]or nil
                            if not front then s.supportHand=nil;s.supportAnchor=nil;s.supportState=nil
                            elseif s.supportHand~=supportHand then
                                s.supportHand=supportHand;s.supportAnchor=layout.Grip:pointToObjectSpace(layout.Foregrip)
                                s.supportState={}
                            end
                            if front and s.supportState then s.supportState.rawLine=self.rawHands[supportHand].p-self.rawHands[heldHand].p end
                            local desired=Geometry.heldFrame(layout,hands[heldHand],front,s.supportAnchor or(anchor and anchor.Value or nil),s.supportState)
                            -- Smooth the solved aim in the avatar's space. Smoothing a
                            -- correction in rear-wrist space temporarily adds wrist yaw
                            -- back into a two-hand gun, producing a large sideways kick.
                            local aimedGrip=self.handOrigin:toObjectSpace(desired*layout.Grip)
                            local rotation=aimedGrip-aimedGrip.p
                            if front then s.supportBlend=1;s.aimRotation=rotation
                            elseif s.supportBlend then s.supportBlend=s.supportBlend*math.exp(-dt*28);if s.supportBlend<.01 then s.supportBlend=nil end end
                            if s.supportBlend and not front then s.aimRotation=(s.aimRotation or rotation):lerp(rotation,1-math.exp(-dt*35))
                            else s.aimRotation=rotation end
                            local originRotation=self.handOrigin-self.handOrigin.p
                            s.baseFrame=CFrame.new(hands[heldHand].p)*originRotation*s.aimRotation*layout.Grip:inverse()
                            root.CFrame=Geometry.applyRecoil(layout,s.baseFrame,s.recoil,s.yaw)
                        else
                            local grip=model:FindFirstChild("HeldGrip")
                            local heldGrip=grip and grip.Value or layout.Grip
                            if layout.Wearable then
                                if not s.wearGrip then s.wearGrip=originalRoot.CFrame:toObjectSpace(hands[heldHand])end
                                heldGrip=s.wearGrip
                            end
                            root.CFrame=hands[heldHand]*heldGrip:inverse()
                            if layout.Wearable then
                                for original,copy in pairs(s.copies)do
                                    local offset=original:FindFirstChild("VRHatOffset")
                                    if original~=originalRoot and offset then copy.CFrame=root.CFrame*offset.Value end
                                end
                            end
                            self.visualHands[heldHand]=root.CFrame*heldGrip
                        end
                    end
                    if layout.Gun then
                        local chamber=model:FindFirstChild("Chambered");local rounds=model:FindFirstChild("Rounds");local shots=model:FindFirstChild("ShotCount")
                        local rack=model:FindFirstChild("SlideHand");local rackHand=rack and rack.Value or""
                        if localOwner and now-s.eventAt>.12 and shots and shots.Value>=s.confirmed then
                            s.confirmed=shots.Value;s.predicted=math.max(s.predicted,s.confirmed)
                            s.ammo=(rounds and rounds.Value or 0)+(chamber and chamber.Value and 1 or 0)
                        end
                        local trigger=heldHand=="left"and 128 or 1
                        if layout.ManualBolt and chamber and not chamber.Value then s.manualConsumed=false end
                        if not down(buttons,trigger)and now-s.lastShot>.4 then s.predicted=s.confirmed end
                        if localOwner and down(buttons,trigger)and rackHand==""and(layout.Automatic or not down(previous,trigger))then
                            if now-s.lastShot>=layout.Interval then
                                local remaining=s.ammo-math.max(0,s.predicted-s.confirmed)
                                local bolt=model:FindFirstChild("BoltLift")
                                local ready=chamber and chamber.Value and(not layout.ManualBolt or(not s.manualConsumed and(not bolt or bolt.Value<.05)))
                                if remaining>0 and ready then
                                    s.predicted=s.predicted+1
                                    if layout.ManualBolt then s.manualConsumed=true end
                                    local cf=root.CFrame;local origin=cf:pointToWorldSpace(layout.Muzzle)
                                    local _,position=workspace:FindPartOnRayWithIgnoreList(Ray.new(origin,cf.lookVector*300),{folder,workspace.CurrentCamera,player.Character},false,true)
                                    self:feedback(model,layout,cf,position,s.predicted,heldHand)
                                    if s.baseFrame then root.CFrame=Geometry.applyRecoil(layout,s.baseFrame,s.recoil,s.yaw)end
                                elseif not down(previous,trigger)then self.fx:dry(root)end
                            end
                        end
                        if localOwner then
                            self.aim[heldHand]={s.recoil,s.yaw}
                            self.visualHands[heldHand]=root.CFrame*layout.Grip
                            if s.supportHand and s.supportAnchor and hands[s.supportHand]then
                                self.visualHands[s.supportHand]=root.CFrame*Geometry.supportGrip(layout,s.supportHand)
                            end
                        end
                        local slide=renderedModel:FindFirstChild("Slide");local offset=model:FindFirstChild("SlideOffset")
                        local start=model:FindFirstChild("SlideGrabZ");local locked=model:FindFirstChild("SlideLocked")
                        local target=offset and layout.SlideRest:toObjectSpace(offset.Value).p.z or 0
                        local lift=model:FindFirstChild("BoltLift");lift=lift and lift.Value or 0
                        if localOwner and rackHand~=""and hands[rackHand]then
                            if down(buttons,rackHand=="left"and 32 or 64)then
                                local point=root.CFrame:pointToObjectSpace(hands[rackHand].p)
                                target=math.max(0,math.min(layout.SlideTravel,(point.z-start.Value)*layout.RackGain))
                                if layout.ManualBolt then
                                    local startY=model:FindFirstChild("SlideGrabY");lift=math.max(0,math.min(1,(point.y-startY.Value)/layout.BoltLift))
                                    if target>.025 then lift=1 end
                                end
                            elseif not layout.ManualBolt then target=locked and locked.Value and(rounds and rounds.Value==0)and layout.LockedTravel or 0 end
                        elseif not layout.ManualBolt and now-s.lastShot<.035 then target=layout.SlideTravel end
                        s.slide=s.slide+(target-s.slide)*(1-math.exp(-dt*65))
                        if slide then slide.CFrame=root.CFrame*layout.SlideRest*CFrame.new(0,0,s.slide)*CFrame.Angles(0,0,(layout.BoltAngle or 0)*lift)end
                        local stem=renderedModel:FindFirstChild("BoltStem");if stem and slide then stem.CFrame=slide.CFrame*layout.BoltStem end
                        local lens=renderedModel:FindFirstChild("ScopeLens");if lens then lens.CFrame=root.CFrame*layout.ScopeFrame*CFrame.Angles(0,math.pi/2,0)end
                    end
                end
            end
        end
        -- Resolve each magazine once, after every gun pose. Mounted state wins
        -- over a stale free-hand ownership field during replication handoffs.
        for _,model in ipairs(folder:GetChildren())do
            local layout=Geometry.forModel(model)
            if layout and layout.MagazineItem then
                local s=self:state(model);local owner=model:FindFirstChild("Owner");local hand=model:FindFirstChild("Hand")
                local root=self:visualRoot(model);local loading=model:FindFirstChild("LoadingInto");local mount=model:FindFirstChild("MountedTo")
                if mount and mount.Value and not s.lastMount and s.lastHeldHand and menu then menu:command(9,s.lastHeldHand=="left"and 0 or 1,1600)end
                s.lastMount=mount and mount.Value or nil
                local mountedTo=mount and mount.Value
                if not mountedTo then
                    for _,candidate in ipairs(folder:GetChildren())do
                        local inserted=candidate:FindFirstChild("InsertedMagazine")
                        if inserted and inserted.Value==model and(not owner or owner.Value~=player or s.loadingFor==candidate or(s.wasMounted==candidate and not s.wasRemoving))then mountedTo=candidate;break end
                    end
                end
                local mountedOwner=mountedTo and mountedTo:FindFirstChild("Owner")
                local gun=loading and loading.Value
                if gun then s.lastGuideAt=now;s.guidePendingAt=nil;s.guideConfirmed=true
                elseif s.loadingFor and s.guidePendingAt and now-s.guidePendingAt<.35 then gun=s.loadingFor
                elseif s.loadingFor and s.lastGuideAt and now-s.lastGuideAt<.12 and hand and hands[hand.Value]then
                    local previousGun=self:visualRoot(s.loadingFor);local previousLayout=Geometry[s.loadingFor.Name]
                    if previousGun and previousLayout and s.loadingStartY then
                        local point=previousGun.CFrame:pointToObjectSpace(hands[hand.Value].p)
                        local progress=(point.y-s.loadingStartY)/previousLayout.InsertDepth
                        if progress>.85 and s.loadingStartPoint and Vector3.new(point.x-s.loadingStartPoint.x,0,point.z-s.loadingStartPoint.z).magnitude<.3 then gun=s.loadingFor end
                    end
                end
                if mountedTo and mountedOwner and mountedOwner.Value==player then
                    local gunRoot=self:visualRoot(mountedTo);local gunLayout=Geometry[mountedTo.Name]
                    if gunRoot and gunLayout then
                        root=self:visual(model)
                        if hand and hand.Value~=""then self.visualHands[hand.Value]=nil end
                        local removal=mountedTo:FindFirstChild("RemovingHand");local start=mountedTo:FindFirstChild("RemovalStartY")
                        local primary=mountedTo:FindFirstChild("Hand");local other=primary and primary.Value=="left"and"right"or"left"
                        if hands[other]and down(buttons,other=="left"and 32 or 64)and not down(previous,other=="left"and 32 or 64)then
                            local point=gunRoot.CFrame:pointToObjectSpace(hands[other].p)
                            if(point-gunLayout.RemovePoint).magnitude<.7 then
                                local previousFrame=gunRoot.CFrame*(s.mountFrame or gunLayout.Magazine)
                                s.removeSnapshot={hand=other,y=point.y,grip=previousFrame:toObjectSpace(hands[other]),at=now}
                            end
                        end
                        local removeHand=removal and removal.Value or""
                        local snapshot=s.removeSnapshot
                        if snapshot and not down(buttons,snapshot.hand=="left"and 32 or 64)then s.removeSnapshot=nil;snapshot=nil end
                        if removeHand==""and snapshot and now-snapshot.at<.15 then removeHand=snapshot.hand end
                        local frame=gunLayout.Magazine
                        if s.loadingFor==mountedTo and s.loadingSmooth then s.seatBlend=s.loadingSmooth;s.mountFrame=nil end
                        if removeHand~=""and start and hands[removeHand]and down(buttons,removeHand=="left"and 32 or 64)then
                            s.wasRemoving=true
                            local point=gunRoot.CFrame:pointToObjectSpace(hands[removeHand].p)
                            local startY=snapshot and snapshot.hand==removeHand and snapshot.y or start.Value
                            frame=Geometry.magazineFrame(gunLayout,1-math.max(0,startY-point.y)/gunLayout.InsertDepth)
                            s.mountFrame=(s.mountFrame or gunLayout.Magazine):lerp(frame,1-math.exp(-dt*45));frame=s.mountFrame
                            local grip=snapshot and snapshot.grip or model.HeldGrip.Value
                            local position=(gunRoot.CFrame*frame*grip).p
                            self.visualHands[removeHand]=CFrame.new(position)*(hands[removeHand]-hands[removeHand].p)
                        else
                            s.mountFrame=nil;s.wasRemoving=nil
                            if s.seatBlend then
                                s.seatBlend=s.seatBlend:lerp(gunLayout.Magazine,1-math.exp(-dt*45));frame=s.seatBlend
                                if(s.seatBlend.p-gunLayout.Magazine.p).magnitude<.001 then s.seatBlend=nil;frame=gunLayout.Magazine end
                            end
                        end
                        root.CFrame=gunRoot.CFrame*frame
                        s.wasMounted=mountedTo;s.lastMountFrame=frame
                    end
                    s.loadingFor=nil;s.loadingSmooth=nil
                elseif owner and owner.Value==player and hand and hands[hand.Value]and down(buttons,hand.Value=="left"and 32 or 64)then
                    root=self:visual(model)
                    local grip=model:FindFirstChild("HeldGrip")
                    if s.wasMounted then
                        local oldGun=self:visualRoot(s.wasMounted)
                        local lastFrame=oldGun and oldGun.CFrame*(s.lastMountFrame or Geometry[s.wasMounted.Name].Magazine)or root.CFrame
                        s.localGrip=lastFrame:toObjectSpace(hands[hand.Value]);s.wasMounted=nil;s.removeSnapshot=nil;s.mountFrame=nil;s.wasRemoving=nil
                    elseif not s.localHeld or s.lastHeldHand~=hand.Value then s.localGrip=layout.Grip end
                    s.localGrip=s.localGrip or layout.Grip
                    root.CFrame=hands[hand.Value]*s.localGrip:inverse()
                    self.visualHands[hand.Value]=root.CFrame*s.localGrip
                    s.lastHeldHand=hand.Value
                    if not gun and s.loadingFor and s.guidePendingAt then
                        s.rejectedGuide=s.loadingFor;s.loadingFor=nil;s.loadingSmooth=nil;s.guidePendingAt=nil
                    end
                    if not gun and not mountedTo then
                        for _,candidate in ipairs(folder:GetChildren())do
                            local candidateLayout=Geometry[candidate.Name];local candidateOwner=candidate:FindFirstChild("Owner");local candidateHand=candidate:FindFirstChild("Hand")
                            local inserted=candidate:FindFirstChild("InsertedMagazine")
                            if candidateLayout and candidateLayout.Gun and candidateLayout.MagazineKind==model.Name and candidateOwner and candidateOwner.Value==player and candidateHand and candidateHand.Value~=hand.Value and inserted and not inserted.Value then
                                local candidateRoot=self:visualRoot(candidate)
                                if candidateRoot and Geometry.magazineEntry(candidateLayout,layout,candidateRoot.CFrame,root.CFrame)and s.rejectedGuide~=candidate then
                                    gun=candidate;s.guidePendingAt=now;s.guideConfirmed=false;break
                                elseif s.rejectedGuide==candidate and candidateRoot and not Geometry.magazineEntry(candidateLayout,layout,candidateRoot.CFrame,root.CFrame)then s.rejectedGuide=nil end
                            end
                        end
                    end
                    if gun then
                        local gunRoot=self:visualRoot(gun);local gunLayout=Geometry[gun.Name]
                        if gunRoot and gunLayout then
                            local point=gunRoot.CFrame:pointToObjectSpace(hands[hand.Value].p)
                            if s.loadingFor~=gun then
                                local progress=loading and loading.Value==gun and model:FindFirstChild("LoadingProgress")or nil
                                s.loadingFor=gun;s.loadingSmooth=gunRoot.CFrame:toObjectSpace(root.CFrame)
                                s.loadingStartY=point.y-math.max(0,math.min(1,progress and progress.Value or 0))*gunLayout.InsertDepth
                                s.loadingStartPoint=point
                            end
                            local progress=math.max(0,math.min(1,(point.y-s.loadingStartY)/gunLayout.InsertDepth))
                            local up=root.CFrame:vectorToWorldSpace(Vector3.new(0,1,0)):Dot(gunRoot.CFrame:vectorToWorldSpace(Vector3.new(0,1,0)))
                            local lateral=Vector3.new(point.x-s.loadingStartPoint.x,0,point.z-s.loadingStartPoint.z).magnitude
                            if point.y-s.loadingStartY<-.22 or lateral>.75 or up<.3 then
                                s.rejectedGuide=gun;s.loadingFor=nil;s.loadingSmooth=nil;s.guidePendingAt=nil
                            else
                                local target=Geometry.guidedMagazineFrame(gunLayout,progress,gunRoot.CFrame:toObjectSpace(root.CFrame))
                                s.loadingSmooth=s.loadingSmooth:lerp(target,1-math.exp(-dt*35));root.CFrame=gunRoot.CFrame*s.loadingSmooth
                                self.visualHands[hand.Value]=root.CFrame*s.localGrip
                            end
                        end
                    else s.loadingFor=nil;s.loadingSmooth=nil end
                else
                    s.loadingFor=nil;s.loadingSmooth=nil;s.localGrip=nil;s.wasMounted=nil;s.removeSnapshot=nil;s.mountFrame=nil;s.seatBlend=nil;s.guidePendingAt=nil;s.rejectedGuide=nil;s.wasRemoving=nil
                end
                s.localHeld=owner and owner.Value==player
            end
        end
        local heldFrames={}
        for model,s in pairs(self.cache)do
            local owner=model:FindFirstChild("Owner");local hand=model:FindFirstChild("Hand");local mount=model:FindFirstChild("MountedTo")
            if s.rendered and owner and owner.Value==player and hand and hands[hand.Value]and down(buttons,hand.Value=="left"and 32 or 64)and not(mount and mount.Value)then
                local frame=self:visualRoot(model).CFrame;local old=self.heldFrames[hand.Value]
                local velocity=old and old.model==model and(frame.p-old.frame.p)/dt or Vector3.new()
                if velocity.magnitude>35 then velocity=velocity.unit*35 end
                heldFrames[hand.Value]={model=model,frame=frame,velocity=velocity}
            end
        end
        self.heldFrames=heldFrames;self:finishVisuals()
    end
    return self
end
return M
