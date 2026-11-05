local function setup(player)
    spawn(function()
        repeat wait(.05)until player.Character and player.Character:FindFirstChild('HumanoidRootPart')
        local root=player.Character.HumanoidRootPart;root.Anchored=true;root.CFrame=CFrame.new(0,5,0)
        local gun=workspace:WaitForChild('HexagonVRWeapons'):WaitForChild('AWP')
        gun.Owner.Value=player;gun.Hand.Value='right';gun.Handle.Anchored=true
    end)
end
game.Players.PlayerAdded:connect(setup);for _,p in ipairs(game.Players:GetPlayers())do setup(p)end
local function box(name,position,size,color)
    local p=Instance.new('Part');p.Name=name;p.Anchored=true;p.Size=size;p.CFrame=CFrame.new(position);p.BrickColor=BrickColor.new(color);p.Parent=workspace
end
box('ScopeRedTarget',Vector3.new(0,6.5,-30),Vector3.new(2,4,1),'Bright red')
box('ScopeBlueTarget',Vector3.new(3,6.5,-30),Vector3.new(1,4,1),'Bright blue')
box('PeripheralTarget',Vector3.new(8,6.5,-30),Vector3.new(2,4,1),'New Yeller')
