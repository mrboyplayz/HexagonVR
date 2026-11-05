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
    M16={
        Gun=true,Mesh="m16_mesh",Texture="m16_texture",SlideMesh="m16_bolt_mesh",SlideTexture="m16_texture",MagazineKind="M16Magazine",Capacity=30,Interval=.095,Automatic=true,HoldOpen=true,
        Damage=24,Range=450,Recoil=3.7,YawKick=.5,RecoilBack=.026,FireSound="m16_fire",Casing="rifle_casing_mesh",CasingScale=Vector3.new(.045,.055,.045),
        Size=Vector3.new(.3,.95,4.3),Scale=Vector3.new(1,1,1),Grip=CFrame.new(0,-.31,.32),
        SlideRest=CFrame.new(0,.19,.1),SlideSize=Vector3.new(.24,.1,.68),
        SlideTravel=.3,RackTravel=.17,LockedTravel=.24,RackGain=1.3,SlideGrabRadius=.36,
        Magazine=CFrame.new(0,-.41738,-.27669),Mouth=Vector3.new(0,-.56,-.27669),RemovePoint=Vector3.new(0,-.65,-.27),
        InsertDepth=.55,RockAngle=0,SlidePoint=Vector3.new(0,.19,.1),Muzzle=Vector3.new(0,.12,-2.8),Eject=CFrame.new(.16,.1,-.05),
        Foregrip=Vector3.new(0,-.12,-1.1),
    },
    M16Magazine={MagazineItem=true,Mesh="m16_magazine_mesh",Texture="m16_texture",Capacity=30,
        Size=Vector3.new(.17,.54,.35),Scale=Vector3.new(1,1,1),Grip=CFrame.new(),Top=Vector3.new(0,.265,0)},
    AWP={
        Gun=true,Mesh="awp_mesh",Texture="awp_texture",SlideMesh="awp_bolt_mesh",SlideTexture="awp_texture",
        MagazineKind="AWPMagazine",Capacity=10,Interval=1.1,Automatic=false,HoldOpen=false,ManualBolt=true,
        Damage=100,Range=1000,Recoil=8,YawKick=.65,RecoilBack=.045,FireSound="awp_fire",Casing="rifle_casing_mesh",CasingScale=Vector3.new(.055,.07,.055),
        RackPullSound="awp_bolt_pull",RackCloseSound="awp_bolt_close",
        Size=Vector3.new(.36,1,4.8),Scale=Vector3.new(1,1,1),Grip=CFrame.new(-.0117,-.105,.066),
        SlideRest=CFrame.new(.04278,.27489,-.05722),SlideSize=Vector3.new(.28,.23,.76),
        SlideTravel=.36,RackTravel=.25,LockedTravel=0,RackGain=1.2,SlideGrabRadius=.34,BoltLift=.11,BoltAngle=math.rad(60),
        Magazine=CFrame.new(-.01008,.004,-.26658),Mouth=Vector3.new(-.01,-.11,-.26658),RemovePoint=Vector3.new(-.01,-.15,-.26658),
        InsertDepth=.38,RockAngle=0,SlidePoint=Vector3.new(.16,.27,-.05),Muzzle=Vector3.new(.026,.309,-3.343),Eject=CFrame.new(.16,.3,-.12),
        Foregrip=Vector3.new(0,-.08,-1.05),ScopeFrame=CFrame.new(-.003,.5,.37),ScopeRadius=.105,ScopeZoom=4,ScopeLength=1.32,
    },
    AWPMagazine={MagazineItem=true,Mesh="awp_magazine_mesh",Texture="awp_texture",Capacity=10,
        Size=Vector3.new(.16,.24,.42),Scale=Vector3.new(1,1,1),Grip=CFrame.new(),Top=Vector3.new(0,.115,0)},
}
function G.forModel(model)
    local kind=model:FindFirstChild("VRKind")
    return G[kind and kind.Value or model.Name]
end
function G.supportContact(layout,gunFrame,primary,secondary)
    if not layout.Foregrip or not primary or not secondary or(secondary.p-primary.p).magnitude<.45 then return false end
    local point=gunFrame:pointToObjectSpace(secondary.p)
    return(point-layout.Foregrip).magnitude<.65
end
local function axisAngle(axis,angle)
    local x,y,z=axis.x,axis.y,axis.z;local c,s=math.cos(angle),math.sin(angle);local t=1-c
    return CFrame.new(0,0,0,t*x*x+c,t*x*y-s*z,t*x*z+s*y,t*x*y+s*z,t*y*y+c,t*y*z-s*x,t*x*z-s*y,t*y*z+s*x,t*z*z+c)
end
function G.supportRotation(reference,current)
    if reference.magnitude<.001 or current.magnitude<.001 then return CFrame.new()end
    local a,b=reference.unit,current.unit;local dot=math.max(-1,math.min(1,a:Dot(b)))
    local axis=a:Cross(b);local length=axis.magnitude
    if length<.00001 then
        if dot>0 then return CFrame.new()end
        axis=a:Cross(math.abs(a.y)<.9 and Vector3.new(0,1,0)or Vector3.new(1,0,0));length=axis.magnitude
    end
    return axisAngle(axis/length,math.acos(dot))
end
local function twist(frame,axis)
    local m={frame:components()};local a,b,c,d,e,f,g,h,i=m[4],m[5],m[6],m[7],m[8],m[9],m[10],m[11],m[12]
    local w,x,y,z;local trace=a+e+i
    if trace>0 then local s=math.sqrt(trace+1)*2;w=s/4;x=(h-f)/s;y=(c-g)/s;z=(d-b)/s
    elseif a>e and a>i then local s=math.sqrt(1+a-e-i)*2;w=(h-f)/s;x=s/4;y=(b+d)/s;z=(c+g)/s
    elseif e>i then local s=math.sqrt(1+e-a-i)*2;w=(c-g)/s;x=(b+d)/s;y=s/4;z=(f+h)/s
    else local s=math.sqrt(1+i-a-e)*2;w=(d-b)/s;x=(c+g)/s;y=(f+h)/s;z=s/4 end
    local along=x*axis.x+y*axis.y+z*axis.z
    if math.abs(along)+math.abs(w)<.00001 then return CFrame.new()end
    return axisAngle(axis,2*math.atan2(along,w))
end
function G.heldFrame(layout,primary,support,anchor,state)
    if not support or not layout.Foregrip then
        if state then state.rotation=nil;state.engagedAt=nil end
        return primary*layout.Grip:inverse()
    end
    local reference=layout.Grip:pointToObjectSpace(layout.Foregrip)
    if reference.magnitude<.001 then return primary*layout.Grip:inverse()end
    local rotation=state and state.rotation or(primary-primary.p)
    local line=state and state.rawLine or(support.p-primary.p)
    -- Two tracked grip positions determine pitch/yaw. The rear wrist supplies
    -- twist only; it cannot clamp or steer the barrel away from the front hand.
    -- At coincident hands keep the last solution until the direction is defined.
    if line.magnitude>.25 then
        rotation=G.supportRotation(rotation:vectorToWorldSpace(reference),line)*rotation
        rotation=rotation*twist(rotation:toObjectSpace(primary-primary.p),reference.unit)
    end
    if state then
        state.rotation=rotation;state.engagedAt=state.engagedAt or tick()
        local t=math.max(0,math.min(1,(tick()-state.engagedAt)/.08));t=t*t*(3-2*t)
        rotation=(primary-primary.p):lerp(rotation,t)
    end
    return CFrame.new(primary.p)*rotation*layout.Grip:inverse()
end
function G.recoilFrame(layout,pitch,yaw)
    return CFrame.new(0,0,math.max(0,pitch)*(layout.RecoilBack or .03))*CFrame.Angles(math.rad(pitch),math.rad(yaw or 0),math.rad((yaw or 0)*.2))
end
function G.supportGrip(layout,hand)
    return CFrame.new(layout.Foregrip)*CFrame.Angles(0,0,math.rad(hand=="left"and -15 or 15))
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
