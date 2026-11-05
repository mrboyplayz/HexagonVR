local RS=game:GetService('ReplicatedStorage')
local stage=Instance.new('IntValue');stage.Name='HatTestStage';stage.Parent=RS
local control=Instance.new('RemoteEvent');control.Name='HatTestControl';control.Parent=RS
control.OnServerEvent:connect(function(player,nextStage)
    if type(nextStage)=='number'and nextStage==stage.Value+1 then stage.Value=nextStage end
end)
game.Players.PlayerAdded:connect(function(player)
    wait(.25);player:LoadCharacter()
    repeat wait(.1)until player.Character and player.Character:FindFirstChild('HumanoidRootPart')
    local char=player.Character;local root=char.HumanoidRootPart
    root.CFrame=CFrame.new(player.userId==124 and 3 or 0,5,0);root.Anchored=true
    if player.userId==124 then
        local hat=Instance.new('Hat');hat.Name='Shared Hat Test'
        local handle=Instance.new('Part');handle.Name='Handle';handle.Size=Vector3.new(1,.5,1);handle.CanCollide=false;handle.Parent=hat
        local offset=CFrame.new(.1,.8,0)*CFrame.Angles(.1,.2,0)
        hat.AttachmentPoint=offset:inverse()*CFrame.new(0,char.Head.Size.y/2,0)
        handle.CFrame=char.Head.CFrame*offset;hat.Parent=char
    end
end)
spawn(function()
    local folder=workspace:WaitForChild('HexagonVRWeapons');wait(.1)
    for _,model in ipairs(folder:GetChildren())do model.Handle.Anchored=true end
end)
