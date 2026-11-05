-- Shared wearable instances: detach, hold at the touched point, and re-equip.
local M={}
local Players=game:GetService("Players")
local Geometry=require(game:GetService("ReplicatedStorage"):WaitForChild("HexagonVRWeaponGeometry"))
local function value(kind,name,initial,parent)
    local node=Instance.new(kind);node.Name=name;node.Value=initial;node.Parent=parent;return node
end
local function walk(node,fn)
    for _,child in ipairs(node:GetChildren())do fn(child);walk(child,fn)end
end
local function isHat(node)return node:IsA("Hat")or node:IsA("Accessory")end
local function inside(part,hat)return part and(part==hat or part:IsDescendantOf(hat))end
local function removeTouchPickup(item)
    walk(item.model,function(node)if node:IsA("TouchTransmitter")then node:Destroy()end end)
end
local function detachJoints(item)
    local function check(joint)
        if joint:IsA("JointInstance")then
            local a,b=inside(joint.Part0,item.model),inside(joint.Part1,item.model)
            if a~=b and(a or b)then joint.Part0=nil;joint.Part1=nil;joint:Destroy()end
        end
    end
    walk(item.model,check)
    -- Native hats can leave an attachment in a previous wearer's character.
    for _,player in ipairs(Players:GetPlayers())do if player.Character then walk(player.Character,check)end end
end
function M.new(weapons,config)
    local self={byHat={}}
    function self:markVR(item,player)
        item.vrCreator=item.vrCreator or player
    end
    function self:register(hat,wearer)
        if self.byHat[hat]then return self.byHat[hat]end
        if not isHat(hat)then return end
        local root=hat:FindFirstChild("Handle");if not root or not root:IsA("BasePart")then return end
        local character=wearer and wearer.Character or hat.Parent
        local head=character and character:FindFirstChild("Head")
        if not head or not wearer then hat:Destroy();return end
        local offset=head and head.CFrame:toObjectSpace(root.CFrame)or CFrame.new(0,.5,0)
        local item={kind="Hat",model=hat,root=root,layout=Geometry.Hat,grip=CFrame.new(),spawn=root.CFrame,lastUse=tick(),hitAt={},hatParts={},hatOffsets={},wearerCharacter=head and character or nil,headOffset=offset}
        item.owner=value("ObjectValue","Owner",nil,hat);item.hand=value("StringValue","Hand","",hat)
        item.heldGrip=value("CFrameValue","HeldGrip",CFrame.new(),hat)
        item.roundValue=value("IntValue","Rounds",0,hat);item.mount=value("ObjectValue","MountedTo",nil,hat)
        item.wearer=value("ObjectValue","Wearer",wearer,hat)
        value("StringValue","VRKind","Hat",hat);value("CFrameValue","HeadOffset",offset,hat)
        walk(hat,function(part)
            if part:IsA("BasePart")then
                item.hatParts[#item.hatParts+1]=part;item.hatOffsets[part]=root.CFrame:toObjectSpace(part.CFrame)
                value("CFrameValue","VRHatOffset",item.hatOffsets[part],part)
            end
        end)
        self.byHat[hat]=item;weapons.items[#weapons.items+1]=item
        if not head then hat.Parent=weapons.folder;root.CanCollide=true end
        return item
    end
    function self:detach(item)
        detachJoints(item);item.wearer.Value=nil;item.wearerCharacter=nil;item.model.Parent=weapons.folder
        removeTouchPickup(item)
        for _,part in ipairs(item.hatParts)do part.CanCollide=false end
    end
    function self:attach(item,player)
        local character=player.Character;local head=character and character:FindFirstChild("Head")
        local humanoid=character and character:FindFirstChild("Humanoid")
        if not head or not humanoid or humanoid.Health<=0 then return false end
        detachJoints(item)
        local frame=head.CFrame*item.headOffset
        weapons:move(item,frame)
        if item.model:IsA("Hat")then item.model.AttachmentPoint=item.headOffset:inverse()*CFrame.new(0,head.Size.y/2,0)end
        item.owner.Value=nil;item.hand.Value="";item.wearer.Value=player;item.wearerCharacter=character
        item.model.Parent=character
        detachJoints(item)
        weapons:move(item,frame)
        local joint=Instance.new("Weld");joint.Name="HexagonVRHatWeld";joint.Part0=head;joint.Part1=item.root;joint.C0=item.headOffset;joint.C1=CFrame.new();joint.Parent=item.root
        weapons:anchor(item,false)
        for _,part in ipairs(item.hatParts)do part.CanCollide=false;part.Velocity=Vector3.new();part.RotVelocity=Vector3.new()end
        item.lastUse=tick();item.previous=nil;return true
    end
    function self:tryEquip(item,actor)
        local anchor=(item.root.CFrame*item.headOffset:inverse()).p
        local best,distance=nil,config.HatEquipRadius or 1.1
        for _,player in ipairs(Players:GetPlayers())do
            local character=player.Character;local head=character and character:FindFirstChild("Head");local humanoid=character and character:FindFirstChild("Humanoid")
            if head and humanoid and humanoid.Health>0 then
                local gap=(head.Position-anchor).magnitude
                if gap<distance then
                    local hit=weapons:trace(anchor,head.Position-anchor,actor.Character)
                    if not hit or hit:IsDescendantOf(character)then best=player;distance=gap end
                end
            end
        end
        return best and self:attach(item,best)or false
    end
    function self:step(item)
        if item.wearerCharacter and item.model.Parent==item.wearerCharacter then return end
        if not item.vrCreator then item.model:Destroy();return end
        if item.model.Parent~=weapons.folder then
            -- The 2015 engine also auto-equips loose Hats on body contact.
            -- Only an explicit grip release near a head may equip a VR hat.
            local frame=item.freeFrame or item.lastWorldFrame or item.root.CFrame
            self:detach(item);weapons:anchor(item,item.owner.Value~=nil);weapons:move(item,frame)
            item.root.CanCollide=item.owner.Value==nil
            item.root.Velocity=item.velocity or Vector3.new()
        end
        removeTouchPickup(item)
        if not item.owner.Value then item.freeFrame=item.root.CFrame end
        if not item.owner.Value and item.root.Position.y<-100 then
            self:detach(item);weapons:anchor(item,false);weapons:move(item,CFrame.new((config.SpawnPosition or Vector3.new(0,0,-5))+Vector3.new(0,3,0)))
            item.root.CanCollide=true;item.root.Velocity=Vector3.new();item.root.RotVelocity=Vector3.new()
        end
    end
    local function character(player,char)
        local function added(node)
            if isHat(node)then spawn(function()wait(.1);if node.Parent==char then self:register(node,player)end end)end
        end
        for _,node in ipairs(char:GetChildren())do added(node)end
        char.ChildAdded:connect(added)
        spawn(function()
            local humanoid=char:FindFirstChild("Humanoid")or char:WaitForChild("Humanoid")
            humanoid.Died:connect(function()
                for _,item in pairs(self.byHat)do
                    if item.wearerCharacter==char and item.model.Parent==char then
                        if weapons.players[player]then self:markVR(item,player)end
                        if item.vrCreator then self:detach(item);weapons:anchor(item,false);item.root.CanCollide=true
                        else item.model:Destroy()end
                    end
                end
            end)
        end)
    end
    local function playerAdded(player)
        player.CharacterAdded:connect(function(char)character(player,char)end)
        if player.Character then character(player,player.Character)end
    end
    Players.PlayerAdded:connect(playerAdded)
    for _,player in ipairs(Players:GetPlayers())do playerAdded(player)end
    local function groundAdded(node)
        if not isHat(node)then return end
        spawn(function()
            wait(.2);if not node.Parent or self.byHat[node]then return end
            for _,player in ipairs(Players:GetPlayers())do if player.Character and node:IsDescendantOf(player.Character)then return end end
            local parent=node.Parent
            if parent:FindFirstChild('Humanoid')and parent:FindFirstChild('Head')then return end
            node:Destroy()
        end)
    end
    workspace.DescendantAdded:connect(groundAdded)
    workspace.ChildAdded:connect(groundAdded)
    walk(workspace,groundAdded)
    return self
end
return M
