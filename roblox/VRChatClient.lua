-- Display only the server-filtered text delivered to this player.
local ChatUI={}
function ChatUI.new(player,menu)
    local Starter=game:GetService("StarterGui")
    local fallback,lines=nil,{}
    local function panel(text)
        lines[#lines+1]=text;if #lines>6 then table.remove(lines,1)end
        if not fallback or not fallback.Parent then
            local gui=Instance.new("ScreenGui");gui.Name="HexagonVRChatDisplay";gui.Parent=player:WaitForChild("PlayerGui")
            fallback=Instance.new("TextLabel");fallback.Name="PublicChat";fallback.Position=UDim2.new(0,8,0,235);fallback.Size=UDim2.new(0,320,0,155)
            fallback.BackgroundColor3=Color3.new(0,0,0);fallback.BackgroundTransparency=.45;fallback.BorderSizePixel=0
            fallback.Font=Enum.Font.SourceSans;fallback.FontSize=Enum.FontSize.Size18;fallback.TextColor3=Color3.new(1,1,1)
            fallback.TextXAlignment=Enum.TextXAlignment.Left;fallback.TextYAlignment=Enum.TextYAlignment.Top;fallback.TextWrapped=true;fallback.Parent=gui
        end
        fallback.Text=table.concat(lines,"\n")
    end
    local self={}
    function self:display(sender,text)
        if not sender or type(text)~="string"then return end
        local ok,blocked=pcall(function()return Starter:GetCore("GetBlockedUserIds")end)
        if ok and type(blocked)=="table"then for _,id in ipairs(blocked)do if id==sender.userId then return end end end
        menu:addMessage(sender,text)
        local line=sender.Name..": "..text
        local shown=pcall(function()Starter:SetCore("ChatMakeSystemMessage",{Text=line,Color=Color3.new(1,1,1),Font=Enum.Font.SourceSans,FontSize=Enum.FontSize.Size18})end)
        if not shown then panel(line)end
        local head=sender.Character and sender.Character:FindFirstChild("Head")
        if head then pcall(function()game:GetService("Chat"):Chat(head,text,Enum.ChatColor.White)end)end
    end
    return self
end
return ChatUI
