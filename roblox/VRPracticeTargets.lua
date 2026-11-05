-- Offline demo targets. Not installed into existing maps by the VR installer.
local parent=Instance.new("Model");parent.Name="VRPracticeTargets";parent.Parent=workspace
local function create(position,name)
    local target=Instance.new("Model");target.Name=name;target.Parent=parent
    local function block(label,offset,size,color)
        local p=Instance.new("Part");p.Name=label;p.FormFactor=Enum.FormFactor.Custom;p.Size=size
        p.Anchored=true;p.BrickColor=BrickColor.new(color);p.TopSurface=Enum.SurfaceType.Smooth;p.BottomSurface=Enum.SurfaceType.Smooth
        p.CFrame=CFrame.new(position+offset);p.Parent=target;return p
    end
    local torso=block("Torso",Vector3.new(0,3,0),Vector3.new(2,2,1),"Bright orange")
    local head=block("Head",Vector3.new(0,4.5,0),Vector3.new(2,1,1),"Bright yellow")
    block("Left Arm",Vector3.new(-1.5,3,0),Vector3.new(1,2,1),"Bright yellow")
    block("Right Arm",Vector3.new(1.5,3,0),Vector3.new(1,2,1),"Bright yellow")
    block("Left Leg",Vector3.new(-.5,1,0),Vector3.new(1,2,1),"Dark stone grey")
    block("Right Leg",Vector3.new(.5,1,0),Vector3.new(1,2,1),"Dark stone grey")
    local neck=Instance.new("Motor6D");neck.Name="Neck";neck.Part0=torso;neck.Part1=head;neck.C0=CFrame.new(0,1.5,0);neck.Parent=torso
    local hum=Instance.new("Humanoid");hum.Parent=target
    hum.Died:connect(function()delay(2,function()if parent.Parent then target:Destroy();create(position,name)end end)end)
end
create(Vector3.new(-4,0,-11),"Crowbar practice")
create(Vector3.new(4,0,-17),"Shooting practice")
