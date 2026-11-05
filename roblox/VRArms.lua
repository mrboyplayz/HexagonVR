-- Private first-person limbs follow tracked grips, independent of body physics.
local M={}
local offset=CFrame.Angles(math.rad(90),0,0)*CFrame.new(0,1,0)
local function strip(node)
    for _,child in ipairs(node:GetChildren())do
        if child:IsA('JointInstance')or child:IsA('LuaSourceContainer')or child:IsA('Sound')or child:IsA('TouchTransmitter')then child:Destroy()
        else strip(child)end
    end
end
function M.new()
    local self={originals={},copies={},transparency=.45}
    function self:clear()
        for part,previous in pairs(self.originals)do if part.Parent then part.LocalTransparencyModifier=previous end end
        if self.model then self.model:Destroy()end
        self.originals={};self.copies={};self.model=nil;self.character=nil
    end
    function self:prepare(character)
        if self.character==character and self.model then return end
        self:clear();self.character=character
        local model=Instance.new('Model');model.Name='HexagonVRLocalArms';self.model=model
        for _,original in ipairs(character:GetChildren())do
            if original.Name=='Left Arm'or original.Name=='Right Arm'or original.Name=='Torso'or original.Name=='Head'then
                if original:IsA('BasePart')then
                    local copy=original:Clone();strip(copy);copy.FormFactor=Enum.FormFactor.Custom;copy.Anchored=true;copy.CanCollide=false;copy.LocalTransparencyModifier=0;copy.Parent=model
                    if original.Name=='Left Arm'or original.Name=='Right Arm'then
                        copy.Size=Vector3.new(original.Size.x*.55,original.Size.y,original.Size.z*.55)
                        self.copies[original.Name=='Left Arm'and'left'or'right']=copy
                        self.originals[original]=original.LocalTransparencyModifier
                    else copy.Transparency=1 end
                end
            elseif original:IsA('Shirt')or original:IsA('Pants')or original:IsA('BodyColors')or original:IsA('CharacterMesh')then
                original:Clone().Parent=model
            end
        end
        local humanoid=Instance.new('Humanoid');humanoid.Name='Humanoid';humanoid.Parent=model
        pcall(function()humanoid.NameDisplayDistance=0;humanoid.HealthDisplayDistance=0 end)
    end
    function self:update(character,hands,grips,torsoFrame)
        if not character then self:clear();return end
        self:prepare(character);self.model.Parent=workspace.CurrentCamera
        for original in pairs(self.originals)do if original.Parent then original.LocalTransparencyModifier=1 end end
        for hand,copy in pairs(self.copies)do
            local frame=grips[hand]or hands[hand]
            copy.Transparency=frame and self.transparency or 1
            if frame then
                local torso=torsoFrame or(character:FindFirstChild('Torso')and character.Torso.CFrame)
                if torso then
                    local shoulder=torso:pointToWorldSpace(Vector3.new(hand=='left'and -1.15 or 1.15,.55,0))
                    local delta=shoulder-frame.p;local length=delta.magnitude
                    if length>.0001 then
                        local y=delta/length;local x=frame:vectorToWorldSpace(Vector3.new(1,0,0));x=x-y*x:Dot(y)
                        if x.magnitude<.01 then x=(math.abs(y.y)<.9 and Vector3.new(0,1,0)or Vector3.new(0,0,1)):Cross(y)end
                        x=x.unit;local z=x:Cross(y)
                        copy.Size=Vector3.new(copy.Size.x,math.max(.2,length),copy.Size.z)
                        local p=frame.p+y*(copy.Size.y/2)
                        copy.CFrame=CFrame.new(p.x,p.y,p.z,x.x,y.x,z.x,x.y,y.y,z.y,x.z,y.z,z.z)
                    else copy.Size=Vector3.new(copy.Size.x,.2,copy.Size.z);copy.CFrame=frame*CFrame.Angles(math.rad(90),0,0)*CFrame.new(0,copy.Size.y/2,0)end
                else copy.CFrame=frame*offset end
            end
        end
        for _,name in ipairs({'Head','Torso'})do
            local original=character:FindFirstChild(name);local copy=self.model:FindFirstChild(name)
            if original and copy then copy.CFrame=original.CFrame end
        end
    end
    return self
end
return M
