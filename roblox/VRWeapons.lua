-- Physical pickups for the Hexagon 2015 engine. No Marketplace scripts execute.
local M={}
local State=require(script.Parent.VRWeaponState)
local Assets=require(script.Parent.VRWeaponAssets)
local Geometry=require(game:GetService("ReplicatedStorage"):WaitForChild("HexagonVRWeaponGeometry"))
local Debris=game:GetService("Debris")
local Run=game:GetService("RunService")
local GRIP={left=32,right=64}
local TRIGGER={left=128,right=1}
local HANDS={"left","right"}
local function down(mask,bit)return math.floor(mask/bit)%2==1 end
local function value(kind,name,v,parent)
    local o=Instance.new(kind);o.Name=name;o.Value=v;o.Parent=parent;return o
end
local function part(name,size,color,parent)
    local p=Instance.new("Part");p.Name=name;p.FormFactor=Enum.FormFactor.Custom;p.Size=size;p.BrickColor=BrickColor.new(color)
    p.TopSurface=Enum.SurfaceType.Smooth;p.BottomSurface=Enum.SurfaceType.Smooth
    p.CanCollide=false;p.Parent=parent;return p
end
local function mesh(p,id,texture,scale)
    local m=Instance.new("SpecialMesh");m.MeshType=Enum.MeshType.FileMesh
    m.MeshId=id;m.TextureId=texture or"";m.Scale=scale;m.Parent=p
end
local function joint(root,p,offset)
    p.CFrame=root.CFrame*offset
    local w=Instance.new("Weld");w.Part0=root;w.Part1=p;w.C0=offset;w.Parent=root;return w
end
local function sound(p,id,volume,pitch)
    if not id or id==""then return end
    local s=Instance.new("Sound");s.SoundId=id;s.Volume=volume or .5;s.Pitch=pitch or 1;s.Parent=p
    s:Play();Debris:AddItem(s,4)
end
local function humanoid(partHit)
    local node=partHit
    while node and node~=workspace do
        local h=node:FindFirstChild("Humanoid")
        if h then return h,node end
        node=node.Parent
    end
end
function M.new(config)
    local C=config.Weapons or{}
    local self={items={},players={},enabled=C.Enabled~=false,remote=game:GetService("ReplicatedStorage"):FindFirstChild("HexagonVR")}
    if not self.enabled then return self end
    local old=workspace:FindFirstChild("HexagonVRWeapons")
    if old then old:Destroy()end
    local folder=Instance.new("Model");folder.Name="HexagonVRWeapons";folder.Parent=workspace;self.folder=folder
    local origin=C.SpawnPosition or Vector3.new(0,0,-5)
    local function create(kind,position)
        local model=Instance.new("Model");model.Name=kind;model.Parent=folder
        local p=part("Handle",Vector3.new(.3,.6,.3),"Dark stone grey",model)
        p.CFrame=CFrame.new(position);p.CanCollide=true;p.Anchored=false
        local layout=Geometry[kind]
        local item={kind=kind,model=model,root=p,spawn=p.CFrame,lastUse=tick(),hitAt={},layout=layout,grip=layout.Grip}
        item.owner=value("ObjectValue","Owner",nil,model);item.hand=value("StringValue","Hand","",model)
        item.roundValue=value("IntValue","Rounds",0,model)
        item.mount=value("ObjectValue","MountedTo",nil,model)
        item.heldGrip=value("CFrameValue","HeldGrip",item.grip,model)
        value("StringValue","VRKind",kind,model)
        if layout.MagazineItem then
            item.loadingInto=value("ObjectValue","LoadingInto",nil,model)
            item.loadingStart=value("NumberValue","LoadingStartY",0,model)
            item.loadingProgress=value("NumberValue","LoadingProgress",0,model)
        end
        if kind=="Crowbar"then
            p.Size=layout.Size
            p.BrickColor=BrickColor.new("Institutional white")
            mesh(p,Assets.crowbar_mesh,Assets.crowbar_texture,layout.Scale)
        elseif layout.Gun then
            p.Size=layout.Size
            p.BrickColor=BrickColor.new("Institutional white")
            mesh(p,Assets[layout.Mesh],Assets[layout.Texture],layout.Scale)
            local slide=part("Slide",layout.SlideSize,"Institutional white",model)
            if layout.SlideMesh then mesh(slide,Assets[layout.SlideMesh],Assets[layout.SlideTexture],layout.Scale)
            else slide.BrickColor=BrickColor.new("Really black");slide.Material=Enum.Material.Metal end
            item.slideRest=layout.SlideRest
            item.slide=joint(p,slide,item.slideRest)
            item.slidePart=slide
            if layout.BoltStem then
                item.boltStem=part("BoltStem",Vector3.new(.07,.07,.25),"Really black",model);joint(slide,item.boltStem,layout.BoltStem)
            end
            item.slideOffset=value("CFrameValue","SlideOffset",item.slideRest,model)
            item.slideGrab=value("StringValue","SlideHand","",model)
            item.slideGrabZ=value("NumberValue","SlideGrabZ",0,model)
            item.slideGrabY=value("NumberValue","SlideGrabY",0,model)
            item.boltLift=value("NumberValue","BoltLift",0,model)
            item.supportGrab=value("StringValue","SupportHand","",model)
            item.supportAnchor=value("Vector3Value","SupportAnchor",Vector3.new(0,0,-1),model)
            item.removingHand=value("StringValue","RemovingHand","",model)
            item.removalStart=value("NumberValue","RemovalStartY",0,model)
            item.shotCount=value("IntValue","ShotCount",0,model)
            item.insertedModel=value("ObjectValue","InsertedMagazine",nil,model)
            item.gun=State.new(kind=="Pistol"and(C.MagazineCapacity or layout.Capacity)or layout.Capacity,layout.HoldOpen,layout.ManualBolt)
            item.chamberValue=value("BoolValue","Chambered",false,model)
            item.lockValue=value("BoolValue","SlideLocked",false,model)
            item.magOffset=layout.Magazine
            item.mouth=layout.Mouth
            item.slidePoint=layout.SlidePoint
            item.muzzle=layout.Muzzle
            item.magBlock=0
        else
            p.Size=layout.Size
            p.BrickColor=BrickColor.new(layout.Texture and"Institutional white"or"Dark stone grey")
            mesh(p,Assets[layout.Mesh],Assets[layout.Texture]or"",layout.Scale)
            item.rounds=kind=="Magazine"and(C.MagazineCapacity or layout.Capacity)or layout.Capacity;item.roundValue.Value=item.rounds
        end
        model.PrimaryPart=p;self.items[#self.items+1]=item
        return item
    end
    self.create=create
    create("Crowbar",origin+Vector3.new(-2,1.9,0))
    create("Pistol",origin+Vector3.new(0,1.5,0))
    for n=1,C.SpareMagazines or 4 do create("Magazine",origin+Vector3.new(1.4+n*.65,1.2,0))end
    create("AK47",origin+Vector3.new(-5,1.8,-1.2))
    for n=1,3 do create("AKMagazine",origin+Vector3.new(-8+n*.8,1.2,1.2))end
    create("M16",origin+Vector3.new(8,1.8,-1.2));for n=1,3 do create("M16Magazine",origin+Vector3.new(7+n*.65,1.2,1.4))end
    create("AWP",origin+Vector3.new(-11,1.8,-1.5));for n=1,3 do create("AWPMagazine",origin+Vector3.new(-12+n*.65,1.2,1.4))end

    function self:setSlide(item,travel,lift)
        if lift~=nil then item.boltLift.Value=lift end
        item.boltTravel=travel
        local offset=item.slideRest*CFrame.new(0,0,travel)*CFrame.Angles(0,0,(item.layout.BoltAngle or 0)*item.boltLift.Value)
        item.slide.C0=offset;item.slideOffset.Value=offset
        item.slidePart.CFrame=item.root.CFrame*offset
        if item.boltStem then item.boltStem.CFrame=item.slidePart.CFrame*item.layout.BoltStem end
    end
    function self:move(item,cf)
        item.root.CFrame=cf
        if item.layout.Wearable then
            item.lastWorldFrame=cf;item.freeFrame=nil
            for _,part in ipairs(item.hatParts)do if part~=item.root then part.CFrame=cf*item.hatOffsets[part]end end
        end
        if item.gun then
            item.slidePart.CFrame=cf*item.slideOffset.Value
            if item.boltStem then item.boltStem.CFrame=item.slidePart.CFrame*item.layout.BoltStem end
            if item.lens then item.lens.CFrame=cf*item.layout.ScopeFrame*CFrame.Angles(0,math.pi/2,0)end
            if item.gun.magazine then item.gun.magazine.root.CFrame=cf*item.magOffset end
        end
    end
    function self:anchor(item,anchored)
        item.root.Anchored=anchored
        if item.layout.Wearable then for _,part in ipairs(item.hatParts)do part.Anchored=anchored end end
        if item.slidePart then item.slidePart.Anchored=anchored end
        if item.boltStem then item.boltStem.Anchored=anchored end
        if item.lens then item.lens.Anchored=anchored end
        if item.gun and item.gun.magazine then item.gun.magazine.root.Anchored=anchored end
    end

    function self:sync(item)
        if item.gun then
            item.insertedModel.Value=item.gun.magazine and item.gun.magazine.model or nil
            item.chamberValue.Value=item.gun.chamber;item.lockValue.Value=item.gun.slideLocked
            item.roundValue.Value=item.gun.magazine and item.gun.magazine.rounds or 0
            if item.gun.magazine then item.gun.magazine.roundValue.Value=item.gun.magazine.rounds end
        else item.roundValue.Value=item.rounds or 0 end
    end
    function self:take(item,player,hand,cf,grip)
        if item.owner.Value or item.inserted then return false end
        if item.layout.Wearable then
            self.hats:markVR(item,player)
            grip=item.root.CFrame:toObjectSpace(cf);self.hats:detach(item)
        end
        item.owner.Value=player;item.hand.Value=hand;self:anchor(item,true);item.root.CanCollide=false
        item.root.Velocity=Vector3.new();item.root.RotVelocity=Vector3.new()
        item.heldGrip.Value=grip or item.grip
        if item.gun then item.baseFrame=cf*item.grip:inverse();item.recoilPitch=0;item.recoilYaw=0 end
        self:move(item,cf*item.heldGrip.Value:inverse());item.previous=nil;item.lastUse=tick()
        self.players[player].held[hand]={kind="item",item=item,grip=item.heldGrip.Value};return true
    end
    function self:release(player,hand,allowEquip)
        local ps=self.players[player];local held=ps and ps.held[hand]
        if not held then return end
        ps.held[hand]=nil
        if held.kind=="slide"then
            local gun=held.item
            if not gun.layout.ManualBolt and held.opened and gun.gun.slideOpen then State.close(gun.gun);sound(gun.root,Assets[gun.layout.RackCloseSound or"slide_release"],.35)end
            gun.slideHand=nil;gun.slideGrab.Value=""
            self:setSlide(gun,gun.layout.ManualBolt and(gun.boltTravel or 0)or(gun.gun.slideLocked and gun.layout.LockedTravel or 0))
            self:sync(gun);return
        elseif held.kind=="remove"then held.item.removingHand.Value="";return
        elseif held.kind=="support"then held.item.supportGrab.Value="";return end
        local item=held.item
        if item.guide then item.guide=nil;item.loadingInto.Value=nil;item.loadingProgress.Value=0 end
        -- A gun's secondary slide hand must detach before the gun drops.
        for _,other in ipairs(HANDS)do
            local h=ps.held[other]
            if h and h.item==item and h.kind~="item"then self:release(player,other)end
        end
        if item.layout.Wearable and allowEquip and self.hats:tryEquip(item,player)then return end
        if item.layout.Wearable then item.freeFrame=item.root.CFrame end
        item.owner.Value=nil;item.hand.Value="";self:anchor(item,false);item.root.CanCollide=true
        local velocity=item.velocity or Vector3.new()
        item.root.Velocity=velocity.magnitude>35 and velocity.unit*35 or velocity
        item.root.RotVelocity=Vector3.new();item.previous=nil;item.lastUse=tick()
        pcall(function()item.root:SetNetworkOwner(nil)end)
        if item.gun and item.gun.magazine then
            local mag=item.gun.magazine
            mag.root.Anchored=false;mag.root.CanCollide=false
        end
    end
    function self:dropPlayer(player)
        if not self.players[player]then return end
        for _,hand in ipairs(HANDS)do self:release(player,hand)end
        self.players[player]=nil
    end
    function self:handFrames(player)
        local result={};local ps=self.players[player];if not ps then return result end
        for _,hand in ipairs(HANDS)do
            local held=ps.held[hand]
            if held and held.kind=="support"then result[hand]=held.item.root.CFrame*Geometry.supportGrip(held.item.layout,hand)
            elseif held and held.kind=="item"then result[hand]=held.item.root.CFrame*held.grip end
        end
        return result
    end
    function self:grab(player,hand,cf,worldHands)
        local ps=self.players[player]
        -- Prefer the other hand's slide or magazine over a nearby loose pickup.
        local other=hand=="left"and"right"or"left"
        local held=ps.held[other]
        if held and held.kind=="item"and held.item.gun then
            local gun=held.item;local point=gun.root.CFrame:pointToObjectSpace(cf.p)
            local slidePoint=gun.slidePart.CFrame:pointToObjectSpace(cf.p)
            local half=gun.layout.SlideSize/2
            local gap=Vector3.new(math.max(0,math.abs(slidePoint.x)-half.x),math.max(0,math.abs(slidePoint.y)-half.y),math.max(0,math.abs(slidePoint.z)-half.z)).magnitude
            local function support()
                local primary=worldHands[other]
                if not primary or(cf.p-primary.p).magnitude<.45 then return false end
                ps.held[hand]={kind="support",item=gun};gun.supportAnchor.Value=gun.layout.Grip:pointToObjectSpace(gun.layout.Foregrip)
                gun.supportState={}
                gun.supportGrab.Value=hand;return true
            end
            if Geometry.supportContact(gun.layout,gun.root.CFrame,worldHands[other],cf)then
                if support()then return end
            elseif gap<gun.layout.SlideGrabRadius and point.y>(gun.layout.ManualBolt and .1 or gun.layout.RemovePoint.y+.5)then
                local startZ=point.z-(gun.boltTravel or 0)/gun.layout.RackGain
                local startY=point.y-gun.boltLift.Value*(gun.layout.BoltLift or 0)
                ps.held[hand]={kind="slide",item=gun,start=startZ,startY=startY,opened=gun.gun.slideOpen,unlocked=gun.boltLift.Value>.75}
                gun.slideHand=hand;gun.slideGrab.Value=hand;gun.slideGrabZ.Value=startZ;gun.slideGrabY.Value=startY;return
            elseif gun.gun.magazine and(point-gun.layout.RemovePoint).magnitude<.7 then
                ps.held[hand]={kind="remove",item=gun,start=point.y}
                gun.removingHand.Value=hand;gun.removalStart.Value=point.y;return
            elseif gun.layout.Foregrip and(point-gun.layout.Foregrip).magnitude<.65 then
                if support()then return end
            end
        end
        local nearest,score=nil,math.huge
        for _,item in ipairs(self.items)do
            if item.model.Parent and not item.owner.Value and not item.inserted then
                local localPoint=item.root.CFrame:pointToObjectSpace(cf.p)
                local half=item.root.Size/2
                local closest=Vector3.new(math.max(-half.x,math.min(half.x,localPoint.x)),math.max(-half.y,math.min(half.y,localPoint.y)),math.max(-half.z,math.min(half.z,localPoint.z)))
                local surface=item.root.CFrame:pointToWorldSpace(closest)
                local nearby=(surface-cf.p).magnitude
                local target=(item.root.CFrame*item.grip).p
                local offset=target-cf.p;local distance=offset.magnitude
                local radius=item.layout.Wearable and(C.HatGrabRadius or .65)or(C.GrabRadius or 2.5)
                local pointed=not item.layout.Wearable and distance>.01 and distance<=(C.DistanceGrabRange or 6)and cf.lookVector:Dot(offset.unit)>.94
                if nearby<=radius or pointed then
                    local blocked=self:trace(cf.p,target-cf.p,ps.character)
                    if blocked and item.layout.Wearable and item.wearerCharacter and blocked:IsDescendantOf(item.wearerCharacter)then blocked=nil end
                    local rank=nearby<=radius and nearby or distance+3
                    if not blocked and rank<score then nearest=item;score=rank end
                end
            end
        end
        if nearest then self:take(nearest,player,hand,cf)end
    end
    function self:trace(origin,delta,character)
        if delta.magnitude<.001 then return nil,origin end
        return workspace:FindPartOnRayWithIgnoreList(Ray.new(origin,delta),{folder,character,workspace.CurrentCamera},false,true)
    end
    function self:setRecoil(item,recoil,defer)
        if not item.gun then return end
        local pitch,yaw=0,0
        if type(recoil)=="table"then
            if type(recoil[1])=="number"and recoil[1]==recoil[1]then pitch=math.max(0,math.min(12,recoil[1]))end
            if type(recoil[2])=="number"and recoil[2]==recoil[2]then yaw=math.max(-4,math.min(4,recoil[2]))end
        end
        item.recoilPitch=pitch;item.recoilYaw=yaw
        if item.baseFrame and not defer then self:move(item,Geometry.applyRecoil(item.layout,item.baseFrame,pitch,yaw))end
    end
    function self:trigger(player,session,hand,pressed,recoil)
        local ps=self.players[player]
        if not ps or(hand~="left"and hand~="right")or type(pressed)~="boolean"then return end
        ps.triggers=ps.triggers or{}
        local previous=ps.triggers[hand];ps.triggers[hand]=pressed
        if not pressed or previous or ps.blocked or tick()-ps.lastAt>.2 then return end
        local held=ps.held[hand]
        if held and held.kind=="item"and held.item.gun and recoil then self:setRecoil(held.item,recoil)end
        if held and held.kind=="item"and held.item.gun and session.humanoid and session.humanoid.Health<=0 then return end
        if held and held.kind=="item"and held.item.gun then self:shot(held.item,player,session.character)end
    end
    function self:shot(item,player,character)
        if item.slideHand or(item.layout.ManualBolt and item.boltLift.Value>.05)then return end
        local fired,reason=State.fire(item.gun,tick(),item.kind=="Pistol"and(C.FireInterval or item.layout.Interval)or item.layout.Interval)
        self:sync(item)
        if not fired then return false,reason end
        local cf=item.root.CFrame
        local muzzle=cf:pointToWorldSpace(item.muzzle)
        -- Old-engine rays skip a part containing their start point. Trace from
        -- the avatar's head so a grip/barrel inside a wall cannot shoot past it.
        local head=character:FindFirstChild("Head")
        local origin=head and head.Position or cf:pointToWorldSpace(item.grip.p)
        local obstruction,obstructedAt,obstructedNormal=self:trace(origin,muzzle-origin,character)
        local hit,position,normal=obstruction,obstructedAt,obstructedNormal
        if not obstruction then hit,position,normal=self:trace(muzzle,cf.lookVector*(item.layout.Range or C.Range or 300),character)end
        if hit then local h,target=humanoid(hit);if h and target~=character then h:TakeDamage(item.layout.Damage or C.GunDamage or 25)end end
        item.shotCount.Value=item.shotCount.Value+1
        if self.remote then self.remote:FireAllClients("weaponShot",item.model,{count=item.shotCount.Value,frame=cf,position=position,normal=normal,hit=hit,ammo=item.roundValue.Value,chamber=item.gun.chamber})end
        if not item.layout.ManualBolt then
            self:setSlide(item,item.layout.SlideTravel)
            delay(.07,function()if item.model.Parent and not item.slideHand then self:setSlide(item,item.gun.slideLocked and item.layout.LockedTravel or 0)end end)
        end
        return true
    end
    function self:swing(item,character,dt)
        local cf=item.root.CFrame
        local bottom=cf:pointToWorldSpace(item.layout.Bottom)
        local tip=cf:pointToWorldSpace(item.layout.Tip)
        local previous=item.previous;item.previous={bottom=bottom,tip=tip,cf=cf}
        if not previous or dt<=0 or dt>.18 then return end
        local travel=(tip-previous.tip).magnitude
        local speed=travel/dt
        if speed<(C.SwingSpeed or 5)or speed>(C.MaxHandSpeed or 65)then return end
        if tick()-(item.swingAt or 0)>.4 then item.swingAt=tick();sound(item.root,Assets.crowbar_swing,.3)end
        -- Sweep the shaft at several points, with wall checks before damage.
        local steps=math.min(12,math.max(1,math.ceil(travel/.3)))
        for n=0,steps do
            local t=n/steps;local a=previous.bottom+(bottom-previous.bottom)*t;local b=previous.tip+(tip-previous.tip)*t
            local head=character:FindFirstChild("Head")
            local wall=head and self:trace(head.Position,a-head.Position,character)
            local hit
            if not wall or humanoid(wall)then hit=self:trace(a,b-a,character)end
            if hit then
                local h,target=humanoid(hit)
                if h and target~=character and tick()-(item.hitAt[h]or-math.huge)>(C.HitCooldown or .5)then
                    item.hitAt[h]=tick();h:TakeDamage(C.CrowbarDamage or 20);sound(item.root,Assets.crowbar_hit,.45)
                end
            end
        end
    end
    function self:loadMagazine(player,hand,held,other,cf,dt)
        local mag=held.item;local ps=self.players[player]
        local gun=other and other.kind=="item"and other.item.gun and other.item or nil
        local compatible=gun and gun.layout.MagazineKind==mag.kind and not gun.gun.magazine and tick()>gun.magBlock
        if mag.guide and(not compatible or mag.guide.gun~=gun)then
            mag.guide=nil;mag.loadingInto.Value=nil;mag.loadingProgress.Value=0
        end
        if not compatible or not cf then return end
        local point=gun.root.CFrame:pointToObjectSpace(cf.p)
        local up=mag.root.CFrame:vectorToWorldSpace(Vector3.new(0,1,0)):Dot(gun.root.CFrame:vectorToWorldSpace(Vector3.new(0,1,0)))
        if not mag.guide then
            if Geometry.magazineEntry(gun.layout,mag.layout,gun.root.CFrame,mag.root.CFrame)then
                mag.guide={gun=gun,start=point,smooth=gun.root.CFrame:toObjectSpace(mag.root.CFrame),began=tick()}
                mag.loadingStart.Value=point.y;mag.loadingProgress.Value=0;mag.loadingInto.Value=gun.model
            end
        end
        local guide=mag.guide
        if not guide then return end
        local travel=point.y-guide.start.y
        if travel<-.22 or up<.3 or Vector3.new(point.x-guide.start.x,0,point.z-guide.start.z).magnitude>.75 then
            mag.guide=nil;mag.loadingInto.Value=nil;mag.loadingProgress.Value=0;return
        end
        local progress=math.max(0,math.min(1,travel/gun.layout.InsertDepth))
        local freeFrame=gun.root.CFrame:toObjectSpace(cf*held.grip:inverse())
        local target=Geometry.guidedMagazineFrame(gun.layout,progress,freeFrame)
        guide.smooth=guide.smooth:lerp(target,1-math.exp(-math.max(.001,dt)*35))
        mag.root.CFrame=gun.root.CFrame*guide.smooth;mag.loadingProgress.Value=progress
        local gap=(mag.root.Position-(gun.root.CFrame*gun.magOffset).p).magnitude
        if progress>=.98 and gap<.09 and tick()-guide.began>.06 then
            ps.held[hand]=nil;ps.requireRelease[hand]=true
            mag.guide=nil;mag.loadingInto.Value=nil;mag.loadingProgress.Value=1
            mag.owner.Value=nil;mag.hand.Value="";mag.inserted=gun;mag.mount.Value=gun.model
            mag.root.Anchored=true;mag.root.CanCollide=false;mag.root.CFrame=gun.root.CFrame*gun.magOffset
            mag.weld=joint(gun.root,mag.root,gun.magOffset)
            State.insert(gun.gun,mag);self:sync(gun);sound(gun.root,Assets.magazine_in,.35)
        end
    end
    function self:update(player,session,worldHands,mask,blocked,recoil,releases)
        if not self.enabled then return end
        local ps=self.players[player]
        if not ps then ps={held={},requireRelease={},lastMask=mask,lastAt=tick(),lastRoot=session.root.Position};self.players[player]=ps end
        ps.character=session.character
        ps.session=session;ps.blocked=blocked
        local now=tick();local dt=now-ps.lastAt;ps.lastAt=now
        if(session.root.Position-ps.lastRoot).magnitude>8 then self:dropPlayer(player);return end
        ps.lastRoot=session.root.Position
        if blocked then
            for _,hand in ipairs(HANDS)do self:release(player,hand)end
            ps.lastMask=mask;return
        end
        for _,hand in ipairs(HANDS)do
            local cf=worldHands[hand];local held=ps.held[hand]
            if not cf or not down(mask,GRIP[hand])then
                if cf and held and held.kind=="item"then
                    local item=held.item;local target=cf*held.grip:inverse();local release=type(releases)=="table"and releases[hand]or nil
                    if release and release.model==item.model and(release.frame.p-target.p).magnitude<2.5 then
                        target=release.frame;item.velocity=release.velocity
                    else item.velocity=dt>0 and(target.p-item.root.Position)/dt or Vector3.new()end
                    self:move(item,target)
                end
                self:release(player,hand,cf~=nil and not down(mask,GRIP[hand]));ps.requireRelease[hand]=nil
            elseif not held and not ps.requireRelease[hand]then self:grab(player,hand,cf,worldHands)end
        end
        -- First move primary objects. Secondary-hand interactions use their new frames.
        for _,hand in ipairs(HANDS)do
            local held=ps.held[hand];local cf=worldHands[hand]
            if held and held.kind=="item"and cf then
                local item=held.item;local other=ps.held[hand=="left"and"right"or"left"]
                local support=other and other.kind=="support"and worldHands[hand=="left"and"right"or"left"]or nil
                local target
                if item.gun then
                    item.supportState=item.supportState or{}
                    local forward=session.handForward or 0
                    item.supportState.rawLine=support and((support*CFrame.new(0,0,forward)).p-(cf*CFrame.new(0,0,forward)).p)or nil
                    target=Geometry.heldFrame(item.layout,cf,support,item.supportAnchor.Value,item.supportState)
                    item.baseFrame=target
                    self:setRecoil(item,type(recoil)=="table"and recoil[hand]or nil,true)
                    target=Geometry.applyRecoil(item.layout,target,item.recoilPitch or 0,item.recoilYaw or 0)
                else target=cf*held.grip:inverse()end
                item.velocity=dt>0 and(target.p-item.root.Position)/dt or Vector3.new()
                self:move(item,target);item.lastUse=now
                if item.kind=="Crowbar"then self:swing(item,session.character,dt)end
            end
        end
        for _,hand in ipairs(HANDS)do
            local held=ps.held[hand];local cf=worldHands[hand]
            if held and cf and held.kind=="slide"then
                local item=held.item;local point=item.root.CFrame:pointToObjectSpace(cf.p)
                local lift=item.layout.ManualBolt and math.max(0,math.min(1,(point.y-held.startY)/item.layout.BoltLift))or 0
                if lift>.75 then held.unlocked=true end
                local pull=math.max(0,math.min(item.layout.SlideTravel,(point.z-held.start)*item.layout.RackGain))
                if item.layout.ManualBolt and not held.unlocked then pull=0 end
                if pull>=item.layout.RackTravel and not held.opened then
                    held.opened=true;local ejected=State.open(item.gun);sound(item.root,Assets[item.layout.RackPullSound or"slide_pull"],.35)
                    if ejected and item.layout.ManualBolt and self.remote then self.remote:FireAllClients("weaponEject",item.model,{frame=item.root.CFrame,number=item.shotCount.Value})end
                end
                if item.layout.ManualBolt and pull>.025 then lift=1 end
                self:setSlide(item,pull,lift)
                if held.opened and pull<.025 and(not item.layout.ManualBolt or lift<.15)then
                    if item.layout.ManualBolt then State.close(item.gun);self:setSlide(item,0,0);sound(item.root,Assets[item.layout.RackCloseSound],.35);self:sync(item)end
                    self:release(player,hand);ps.requireRelease[hand]=true
                end
            elseif held and cf and held.kind=="remove"then
                local gun=held.item;local point=gun.root.CFrame:pointToObjectSpace(cf.p)
                local travel=math.max(0,held.start-point.y)
                if gun.gun.magazine then gun.gun.magazine.root.CFrame=gun.root.CFrame*Geometry.magazineFrame(gun.layout,1-travel/gun.layout.InsertDepth)end
                if travel>=gun.layout.InsertDepth*.95 then
                    local mag=State.remove(gun.gun)
                    ps.held[hand]=nil;gun.removingHand.Value=""
                    if mag then
                        mag.inserted=nil;mag.mount.Value=nil;if mag.weld then mag.weld:Destroy();mag.weld=nil end
                        mag.root.Anchored=true;gun.magBlock=now+.6
                        local grip=mag.root.CFrame:toObjectSpace(cf)
                        self:take(mag,player,hand,cf,grip);self:sync(gun);sound(gun.root,Assets.magazine_out,.3)
                    end
                end
            end
        end
        for _,hand in ipairs(HANDS)do
            local held=ps.held[hand];local other=ps.held[hand=="left"and"right"or"left"]
            if held and held.kind=="item"and held.item.layout.MagazineItem then
                self:loadMagazine(player,hand,held,other,worldHands[hand],dt)
            end
            held=ps.held[hand]
            self:trigger(player,session,hand,down(mask,TRIGGER[hand]))
        end
        ps.lastMask=mask
    end
    self.hats=require(script.Parent.VRHats).new(self,C)
    function self:registerHat(hat,wearer)return self.hats:register(hat,wearer)end
    Run.Stepped:connect(function()
        for player,ps in pairs(self.players)do
            if not ps.blocked and tick()-ps.lastAt<.18 and ps.session then
                for _,hand in ipairs(HANDS)do
                    local held=ps.held[hand]
                    if held and held.kind=="item"and held.item.gun and held.item.layout.Automatic and ps.triggers and ps.triggers[hand]then self:shot(held.item,player,ps.session.character)end
                end
            end
        end
        for index=#self.items,1,-1 do
            local item=self.items[index]
            if item.layout.Wearable and not item.model.Parent then
                self.hats.byHat[item.model]=nil
                for _,ps in pairs(self.players)do for _,hand in ipairs(HANDS)do if ps.held[hand]and ps.held[hand].item==item then ps.held[hand]=nil end end end
                table.remove(self.items,index)
            elseif item.layout.Wearable then self.hats:step(item)
            elseif not item.owner.Value and not item.inserted and(item.root.Position.y<-100 or tick()-item.lastUse>(C.RespawnSeconds or 90))then
                if item.gun then
                    local mag=State.remove(item.gun)
                    if mag then mag.inserted=nil;mag.mount.Value=nil;if mag.weld then mag.weld:Destroy();mag.weld=nil end;mag.root.Anchored=false;mag.root.CanCollide=true;mag.root.CFrame=mag.spawn end
                    item.gun=State.new(item.layout.Capacity,item.layout.HoldOpen,item.layout.ManualBolt);self:setSlide(item,0,0)
                elseif item.layout.MagazineItem then item.rounds=item.layout.Capacity end
                self:anchor(item,false);self:move(item,item.spawn);item.root.Velocity=Vector3.new();item.root.RotVelocity=Vector3.new();item.lastUse=tick();self:sync(item)
            end
        end
    end)
    return self
end
return M
