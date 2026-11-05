-- Local, immediate gun feedback. Damage and ammunition remain server controlled.
local M={}
local Assets=require(script:WaitForChild("VRWeaponAssets"))
local Debris=game:GetService("Debris")
local function part(name,parent)
    local p=Instance.new("Part");p.Name=name;p.FormFactor=Enum.FormFactor.Custom;p.Size=Vector3.new(.2,.2,.2)
    p.TopSurface=Enum.SurfaceType.Smooth;p.BottomSurface=Enum.SurfaceType.Smooth;p.CanCollide=false;p.Parent=parent;return p
end
local function play(parent,id,volume,pitch)
    if not id then return end
    local s=Instance.new("Sound");s.SoundId=id;s.Volume=volume;s.Pitch=pitch or 1;s.Parent=parent;s:Play();Debris:AddItem(s,4)
end
function M.new()
    local self={}
    local folder=Instance.new("Model");folder.Name="HexagonVRLocalFX";folder.Parent=workspace.CurrentCamera;self.folder=folder
    function self:dry(root)play(root,Assets.dry_fire,.25,1)end
    function self:impact(position,normal,hit)
        if not hit or not position then return end
        local dot=part("Impact",folder);dot.Anchored=true
        dot.CFrame=CFrame.new(position+(normal or Vector3.new())*.012)
        local shape=Instance.new("SpecialMesh");shape.MeshType=Enum.MeshType.Sphere;shape.Scale=Vector3.new(.18,.18,.18);shape.Parent=dot
        if hit.Anchored then dot.BrickColor=BrickColor.new("Really black");Debris:AddItem(dot,5)
        else dot.BrickColor=BrickColor.new("Institutional white");dot.Material=Enum.Material.Neon;Debris:AddItem(dot,.08)end
    end
    function self:eject(layout,cf,number)
        local casing=part("Casing",folder);casing.CFrame=cf*layout.Eject*CFrame.Angles(math.random(),math.random(),math.random())
        casing.BrickColor=BrickColor.new("Bright yellow");casing.Material=Enum.Material.Metal;casing.CanCollide=true
        local mesh=Instance.new("SpecialMesh");mesh.MeshType=Enum.MeshType.FileMesh;mesh.MeshId=Assets[layout.Casing];mesh.TextureId=Assets.casing_texture
        mesh.Scale=layout.CasingScale;mesh.Parent=casing
        casing.Velocity=cf:vectorToWorldSpace(Vector3.new(5+math.random()*3,2.5+math.random()*2,-.5+math.random()))
        casing.RotVelocity=Vector3.new(10+math.random()*14,math.random()*20,math.random()*24)
        local bounced=false;casing.Touched:connect(function(other)
            if not bounced and other.Parent~=folder and other.CanCollide then bounced=true;play(casing,Assets.casing_bounce,.12,.9+math.random()*.2)end
        end);Debris:AddItem(casing,3)
    end
    function self:shot(root,layout,cf,hitPosition,number)
        local muzzle=cf:pointToWorldSpace(layout.Muzzle)
        local audio=part("ShotAudio",folder);audio.Anchored=true;audio.Transparency=1;audio.CFrame=cf
        play(audio,Assets[layout.FireSound],.6,.97+math.random()*.06);Debris:AddItem(audio,4)
        local flash=part("MuzzleFlash",folder);flash.Anchored=true;flash.BrickColor=BrickColor.new("New Yeller");flash.Material=Enum.Material.Neon
        flash.CFrame=cf*CFrame.new(layout.Muzzle)*CFrame.new(0,0,-.12)
        local glow=Instance.new("SpecialMesh");glow.MeshType=Enum.MeshType.Sphere;glow.Scale=Vector3.new(.65,.65,2.2);glow.Parent=flash
        local light=Instance.new("PointLight");light.Color=Color3.new(1,.72,.3);light.Range=7;light.Brightness=1.6;light.Parent=flash;Debris:AddItem(flash,.035)
        if not layout.ManualBolt then self:eject(layout,cf,number)end
        if hitPosition and(not layout.Automatic or number%3==0)then
            local delta=hitPosition-muzzle
            if delta.magnitude>.1 then
                local beam=part("Tracer",folder);beam.Anchored=true;beam.BrickColor=BrickColor.new("New Yeller");beam.Material=Enum.Material.Neon
                beam.CFrame=CFrame.new(muzzle,hitPosition)*CFrame.new(0,0,-delta.magnitude/2)
                local shape=Instance.new("BlockMesh");shape.Scale=Vector3.new(.045,.045,delta.magnitude/.2);shape.Parent=beam;Debris:AddItem(beam,.03)
            end
        end
    end
    return self
end
return M
