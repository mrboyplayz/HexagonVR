-- Shared render and server transforms; forward is -Z, up is +Y.
local G={
    Hat={Wearable=true,Grip=CFrame.new()},
    Crowbar={
        Size=Vector3.new(1.6,4.2,.3),Scale=Vector3.new(1,1,1),
        Grip=CFrame.new(0,-1.25,0)*CFrame.Angles(math.rad(90),0,0),
        Bottom=Vector3.new(0,-1.25,0),Tip=Vector3.new(-.6,2,0),
    },
    Pistol={
        Gun=true,Mesh="pistol_mesh",Texture="pistol_texture",SlideMesh="slide_mesh",SlideTexture="slide_texture",
        MagazineKind="Magazine",Capacity=12,Interval=.18,Automatic=false,HoldOpen=true,
        Recoil=4.8,YawKick=.65,RecoilBack=.03,FireSound="fire",Casing="pistol_casing_mesh",CasingScale=Vector3.new(.045,.085,.045),
        InsertDepth=.86,RockAngle=0,
        Eject=CFrame.new(.2,.43,.02),RackGain=1.7,SlideGrabRadius=.65,
        Size=Vector3.new(.25,1.15,1.7),Scale=Vector3.new(.175831,.175831,.175831),
        Grip=CFrame.new(0,-.25,.19),SlideRest=CFrame.new(0,.447,-.077),
        Magazine=CFrame.new(0,-.09,.459),Mouth=Vector3.new(0,-.49,.459),
        SlidePoint=Vector3.new(0,.45,.2),Muzzle=Vector3.new(0,.48,-.9),
        SlideSize=Vector3.new(.2,.35,1.52),SlideTravel=.32,RackTravel=.17,LockedTravel=.28,
        RemovePoint=Vector3.new(0,-.75,.46),
    },
    Magazine={MagazineItem=true,Mesh="magazine_mesh",Capacity=12,Size=Vector3.new(.2,.98,.63),Scale=Vector3.new(.175831,.175831,.175831),Grip=CFrame.new(),Top=Vector3.new(0,.49,0)},
    AK47={
        Gun=true,Mesh="ak_mesh",Texture="ak_texture",SlideMesh="ak_bolt_mesh",SlideTexture="ak_texture",
        MagazineKind="AKMagazine",Capacity=30,Interval=.105,Automatic=true,HoldOpen=false,
        Recoil=4.5,YawKick=.85,RecoilBack=.035,FireSound="ak_fire",Casing="rifle_casing_mesh",CasingScale=Vector3.new(.045,.055,.045),
        InsertDepth=.4,RockAngle=math.rad(18),
        Eject=CFrame.new(.23,.34,.2),RackGain=1.8,SlideGrabRadius=.7,
        Size=Vector3.new(.4,1.1,4.2),Scale=Vector3.new(1,1,1),Grip=CFrame.new(0,-.12683,1.25792),
        SlideRest=CFrame.new(.0688,.33994,.21174),SlideSize=Vector3.new(.28,.2,1),
        Magazine=CFrame.new(.00012,-.17384,.41035),Mouth=Vector3.new(0,-.12,.41035),
        RemovePoint=Vector3.new(0,-.6,.5),SlidePoint=Vector3.new(.24,.34,.3),Muzzle=Vector3.new(0,.3,-1.43),
        Foregrip=Vector3.new(0,-.08,-.7),
        SlideTravel=.45,RackTravel=.2,LockedTravel=0,
    },
    AKMagazine={MagazineItem=true,Mesh="ak_magazine_mesh",Texture="ak_texture",Capacity=30,
        Size=Vector3.new(.2,.9,.71),Scale=Vector3.new(1,1,1),Grip=CFrame.new(),Top=Vector3.new(0,.45,.05)},
}
function G.forModel(model)
    local kind=model:FindFirstChild("VRKind")
    return G[kind and kind.Value or model.Name]
end
function G.supportRotation(reference,current)
    if reference.magnitude<.001 or current.magnitude<.001 then return CFrame.new()end
    local a,b=reference.unit,current.unit
    local dot=math.max(-1,math.min(1,a:Dot(b)))
    local axis=a:Cross(b);local length=axis.magnitude
    if length<.00001 then return CFrame.new()end
    axis=axis/length
    local function smooth(value)value=math.max(0,math.min(1,value));return value*value*(3-2*value)end
    -- Fade support as hands meet or cross instead of jumping to an identity
    -- correction at a distance threshold or flipping at an opposite vector.
    local confidence=smooth((current.magnitude-.08)/.37)*smooth((dot+1)/.5)
    local angle=math.min(math.rad(65),math.acos(dot))*confidence
    local x,y,z=axis.x,axis.y,axis.z;local c,s=math.cos(angle),math.sin(angle);local t=1-c
    return CFrame.new(0,0,0,t*x*x+c,t*x*y-s*z,t*x*z+s*y,t*x*y+s*z,t*y*y+c,t*y*z-s*x,t*x*z-s*y,t*y*z+s*x,t*z*z+c)
end
function G.heldFrame(layout,primary,support,anchor)
    local rotation=CFrame.new()
    if support and layout.Foregrip then
        local reference=anchor or layout.Grip:pointToObjectSpace(layout.Foregrip)
        rotation=G.supportRotation(reference,primary:vectorToObjectSpace(support.p-primary.p))
    end
    return primary*rotation*layout.Grip:inverse()
end
function G.recoilFrame(layout,pitch,yaw)
    return CFrame.new(0,0,math.max(0,pitch)*(layout.RecoilBack or .03))*CFrame.Angles(math.rad(pitch),math.rad(yaw or 0),math.rad((yaw or 0)*.2))
end
function G.applyRecoil(layout,base,pitch,yaw)
    return base*layout.Grip*G.recoilFrame(layout,pitch or 0,yaw or 0)*layout.Grip:inverse()
end
function G.magazineFrame(layout,progress)
    local remaining=1-math.max(0,math.min(1,progress))
    return CFrame.new(0,-layout.InsertDepth*remaining,0)*layout.Magazine*CFrame.Angles(-(layout.RockAngle or 0)*remaining,0,0)
end
function G.magazineEntry(layout,magLayout,gunFrame,magFrame)
    local top=gunFrame:pointToObjectSpace(magFrame:pointToWorldSpace(magLayout.Top))
    local entry=G.magazineFrame(layout,0):pointToWorldSpace(magLayout.Top)
    local offset=top-entry
    local up=magFrame:vectorToWorldSpace(Vector3.new(0,1,0)):Dot(gunFrame:vectorToWorldSpace(Vector3.new(0,1,0)))
    local facing=magFrame.lookVector:Dot(gunFrame.lookVector)
    return up>.72 and facing>.35 and math.abs(offset.y)<.15 and Vector3.new(offset.x,0,offset.z).magnitude<.28
end
function G.guidedMagazineFrame(layout,progress,freeFrame)
    local t=math.max(0,math.min(1,progress));local assist=t*t*(3-2*t)
    return freeFrame:lerp(G.magazineFrame(layout,t),assist)
end
return G
