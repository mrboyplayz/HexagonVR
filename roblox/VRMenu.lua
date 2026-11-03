-- Private, world-space menu. Only normal engine chat is displayed here.
local Menu={}
function Menu.new(player,box,remote)
    local self={opened=false,page="menu",draft="",shift=false,buttons={},messages={},queue={},serial=math.random(1,500000),pending=nil,lastButtons=0,scroll=0,notice="",hover=nil}
    local panel=Instance.new("Part");panel.Name="HexagonVRMenu";panel.FormFactor=Enum.FormFactor.Custom
    panel.Size=Vector3.new(4.8,3.8,.05);panel.Anchored=true;panel.CanCollide=false;panel.Transparency=1
    self.panel=panel
    local gui=Instance.new("SurfaceGui");gui.Name="HexagonVRMenuSurface";gui.Face=Enum.NormalId.Front
    gui.CanvasSize=Vector2.new(1100,870);gui.Adornee=panel
    local playerGui=player:WaitForChild("PlayerGui")
    local assets="rbxasset://textures/ui/Settings/"
    local hosted=require(script:WaitForChild("VRMenuAssets"))
    local function texture(path)return hosted[path]or assets..path end
    local background=Instance.new("Frame");background.Size=UDim2.new(1,0,1,0);background.BackgroundColor3=Color3.new(41/255,41/255,41/255);background.BackgroundTransparency=.2;background.BorderSizePixel=0;background.Parent=gui
    local cursor=Instance.new("Frame");cursor.Size=UDim2.new(0,12,0,12);cursor.BackgroundColor3=Color3.new(1,1,1);cursor.BorderSizePixel=0;cursor.ZIndex=10;cursor.Visible=false;cursor.Parent=background
    local function text(value,x,y,w,h,size)
        local l=Instance.new("TextLabel");l.Position=UDim2.new(0,x,0,y);l.Size=UDim2.new(0,w,0,h)
        l.BackgroundTransparency=1;l.TextColor3=Color3.new(1,1,1);l.Font=Enum.Font.SourceSans;l.FontSize=size or Enum.FontSize.Size32
        l.BorderSizePixel=0;l.Text=value;l.TextWrapped=true;l.ZIndex=3;l.Parent=background;return l
    end
    local function image(path,x,y,w,h,sliced)
        local i=Instance.new("ImageLabel");i.BackgroundTransparency=1;i.BorderSizePixel=0;i.Image=texture(path)
        i.Position=UDim2.new(0,x,0,y);i.Size=UDim2.new(0,w,0,h);i.ZIndex=2;i.Parent=background
        if sliced then i.ScaleType=Enum.ScaleType.Slice;i.SliceCenter=Rect.new(unpack(sliced))end
        return i
    end
    local function button(value,x,y,w,h,action)
        local plate=image("MenuBarAssets/MenuButton.png",x,y,w,h,{8,6,46,44})
        local l=text(value,x,y-2,w,h);l.Font=Enum.Font.SourceSansBold
        self.buttons[#self.buttons+1]={x=x,y=y,w=w,h=h,label=l,plate=plate,action=action};return l
    end
    function self:command(kind,a,b)
        if #self.queue>180 then self.notice="Please wait for the bridge.";return false end
        self.serial=self.serial%999999+1
        self.queue[#self.queue+1]={self.serial*16+kind,a or 0,b or 0};return true
    end
    function self:mailbox()
        local v=box.ui.Value
        if v.x<0 or v.x>127 or v.x~=math.floor(v.x) then return end
        if self.pending and v.y==self.pending[1] then self.pending=nil end
        if not self.pending and #self.queue>0 then self.pending=table.remove(self.queue,1)end
        local p=self.pending or {0,0,0};box.ui_out.Value=Vector3.new(p[1],p[2],p[3])
    end
    function self:send()
        local message=self.draft:match("^%s*(.-)%s*$")
        if message=="" then return end
        if #self.queue>140 then self.notice="A message is still being sent.";self:draw();return end
        self:command(5)
        for offset=1,#message,6 do
            local function pack(start)local n=0;for j=0,2 do n=n+(message:byte(start+j)or 0)*256^j end;return n end
            self:command(6,pack(offset),pack(offset+3))
        end
        self:command(7);self.draft="";self.notice="Sending through Roblox chat...";self:draw()
    end
    function self:draw()
        for _,child in ipairs(background:GetChildren())do if child~=cursor then child:Destroy()end end
        self.buttons={}
        local confirm=self.page=="confirmLeave"or self.page=="confirmReset"
        if not confirm then
            image("MenuBarAssets/MenuBackground.png",40,48,1020,82,{4,4,6,6})
            local tabs={{"menu","Players","Radial/PlayerList.png"},{"settings","Settings","MenuBarIcons/GameSettingsTab.png"},{"chat","Chat","Radial/Chat.png"},{"help","Help","MenuBarIcons/HelpTab.png"}}
            for index,tab in ipairs(tabs)do
                local x=40+(index-1)*255;local selected=self.page==tab[1]
                local icon=image(tab[3],x+20,68,42,38);icon.ImageTransparency=selected and 0 or .5
                local title=text(tab[2],x+80,60,165,58);title.Font=Enum.Font.SourceSansBold;title.TextXAlignment=Enum.TextXAlignment.Left;title.TextTransparency=selected and 0 or .5
                local underline=nil
                if selected then underline=image("MenuBarAssets/MenuSelection.png",x,124,255,6,{3,1,4,5})end
                self.buttons[#self.buttons+1]={x=x,y=48,w=255,h=82,label=title,icon=icon,tab=true,selected=selected,action=function()self.page=tab[1];self:draw()end}
            end
        end
        if self.page=="confirmLeave" or self.page=="confirmReset" then
            local leave=self.page=="confirmLeave"
            text(leave and "Are you sure you want to leave the game?"or"Are you sure you want to reset your character?",90,245,920,120,Enum.FontSize.Size48).Font=Enum.Font.SourceSansBold
            button(leave and "Don't Leave"or"Don't Reset",180,430,350,80,function()self.page="menu";self:draw()end)
            button(leave and "Leave"or"Reset",570,430,350,80,function()
                if leave then self:command(4)else remote:FireServer("reset")end
                self:setOpen(false)
            end)
        elseif self.page=="chat" then
            local rows={};local last=math.max(0,#self.messages-self.scroll)
            for i=math.max(1,last-5),last do rows[#rows+1]=self.messages[i]end
            local chat=text(table.concat(rows,"\n"),60,155,980,155,Enum.FontSize.Size28);chat.TextYAlignment=Enum.TextYAlignment.Top;chat.TextXAlignment=Enum.TextXAlignment.Left
            local draft=text(self.draft==""and"To chat, select the keys below"or self.draft.."|",70,320,960,58,Enum.FontSize.Size32)
            draft.BackgroundTransparency=.6;draft.BackgroundColor3=Color3.new(0,0,0);draft.TextXAlignment=Enum.TextXAlignment.Left
            local lines={"1234567890","qwertyuiop","asdfghjkl","zxcvbnm,./"}
            local symbols={['1']='!',['2']='@',['3']='#',['4']='$',['5']='%',['6']='^',['7']='&',['8']='*',['9']='(',['0']=')',[',']='<',['.']='>',['/']='?'}
            for row,line in ipairs(lines)do
                local width=91;local start=(1100-#line*(width+9))/2
                for col=1,#line do
                    local char=line:sub(col,col);local shown=self.shift and(symbols[char]or char:upper())or char
                    button(shown,start+(col-1)*(width+9),385+(row-1)*72,width,62,function()
                        if #self.draft<140 then self.draft=self.draft..shown end;self:draw()
                    end)
                end
            end
            button(self.shift and "SHIFT"or"Shift",40,680,150,64,function()self.shift=not self.shift;self:draw()end)
            button("Space",205,680,360,64,function()if #self.draft<140 then self.draft=self.draft.." "end;self:draw()end)
            button("Backspace",580,680,230,64,function()self.draft=self.draft:sub(1,-2);self:draw()end)
            button("Enter",825,680,235,64,function()self:send()end)
        elseif self.page=="settings"then
            local function row(name,value,y,action)
                local label=text(name,70,y,440,64);label.TextXAlignment=Enum.TextXAlignment.Left
                if action then button(value,560,y,460,64,action)else text(value,560,y,460,64)end
            end
            row("Camera Mode","First Person",190)
            row("Movement Mode","Head Relative",278)
            row("Turn Mode","Snap Turn (30 degrees)",366)
            if self.nativeRendering then row("View Scale","Native Headset Projection",454)
            else row("View Scale",self.wide and "<  Wide  >"or"<  Headset  >",454,function()self.wide=not self.wide;self:command(self.wide and 3 or 2);self:draw()end)end
            row("Arm Forward",tostring(math.floor((self.armForward or .3)*100/3+.5)).." cm  >",542,function()self:command(8)end)
            row("Headset Position","Recenter",630,function()self:command(1);self:setOpen(false)end)
        elseif self.page=="help"then
            local rows={{"Move","Left thumbstick"},{"Turn","Right thumbstick"},{"Jump","A button"},{"Menu / Chat","Y button / B button"},{"Select / Use Tool","Right trigger"},{"Recenter","X button"}}
            for index,row in ipairs(rows)do
                local y=170+(index-1)*75;local name=text(row[1],80,y,430,60);name.Font=Enum.Font.SourceSansBold;name.TextXAlignment=Enum.TextXAlignment.Left
                text(row[2],550,y,460,60)
            end
        else
            local title=text("Players",65,160,970,65,Enum.FontSize.Size36);title.Font=Enum.Font.SourceSansBold;title.TextXAlignment=Enum.TextXAlignment.Left
            local members=game.Players:GetPlayers();table.sort(members,function(a,b)return a.Name<b.Name end)
            local first=math.max(1,math.min(#members-4,self.playerScroll or 0)+1)
            for index=first,math.min(#members,first+3)do
                local member=members[index];local y=245+(index-first)*94
                local row=image("MenuBarAssets/MenuButton.png",55,y,990,80,{8,6,46,44});row.ImageTransparency=.25
                image("Radial/PlayerList.png",75,y+17,44,44)
                local name=text(member.Name,145,y,650,80,Enum.FontSize.Size36);name.Font=Enum.Font.SourceSansBold;name.TextXAlignment=Enum.TextXAlignment.Left
                if member==player then text("You",850,y,160,80)end
            end
        end
        if not confirm then
            button("Reset Character",40,766,325,72,function()self.page="confirmReset";self:draw()end)
            button("Leave Game",387,766,325,72,function()self.page="confirmLeave";self:draw()end)
            button("Resume Game",734,766,325,72,function()self:setOpen(false)end)
            text(self.page=="chat"and(self.notice~=""and self.notice or"Right thumbstick scrolls chat")or"Point and select with the right trigger",60,self.page=="chat"and 744 or 704,980,self.page=="chat"and 22 or 38,self.page=="chat"and Enum.FontSize.Size18 or Enum.FontSize.Size24)
        end
    end
    function self:setOpen(open,page)
        self.opened=open
        if page then self.page=page end
        if open then
            local camera=workspace.CurrentCamera;local head=camera.CoordinateFrame
            local look=head.lookVector;look=Vector3.new(look.x,0,look.z)
            if look.magnitude<.01 then look=Vector3.new(0,0,-1)else look=look.unit end
            local position=head.p+look*5.5+Vector3.new(0,-.35,0)
            panel.CFrame=CFrame.new(position,position-look);panel.Parent=camera;self:draw()
        else panel.Parent=nil end
        gui.Parent=open and playerGui or nil;cursor.Visible=false
    end
    function self:update(worldRight,mask,axis)
        local function down(bit)return math.floor(mask/bit)%2==1 end
        local function pressed(bit)return down(bit)and math.floor(self.lastButtons/bit)%2==0 end
        if not down(1)then self.consumeTrigger=false end
        if pressed(2)then self:setOpen(not self.opened,"menu")end
        if pressed(4)then self:setOpen(not(self.opened and self.page=="chat"),"chat")end
        if self.opened and self.page=="chat"and math.abs(axis)>.65 and tick()-(self.lastScroll or 0)>.25 then
            self.lastScroll=tick();self.scroll=math.max(0,math.min(math.max(0,#self.messages-6),self.scroll+(axis<0 and 1 or -1)));self:draw()
        end
        if self.opened and self.page=="menu"and math.abs(axis)>.65 and tick()-(self.lastScroll or 0)>.25 then
            self.lastScroll=tick();self.playerScroll=math.max(0,math.min(math.max(0,#game.Players:GetPlayers()-4),(self.playerScroll or 0)+(axis>0 and 1 or -1)));self:draw()
        end
        cursor.Visible=false;self.hover=nil
        if self.opened and down(1)then self.consumeTrigger=true end
        if self.opened and worldRight then
            local origin=panel.CFrame:pointToObjectSpace(worldRight.p)
            local direction=panel.CFrame:vectorToObjectSpace(worldRight.lookVector)
            if math.abs(direction.z)>.001 then
                local distance=(-panel.Size.z/2-origin.z)/direction.z
                if distance>0 then
                    local hit=origin+direction*distance
                    local x=(.5-hit.x/panel.Size.x)*1100;local y=(.5-hit.y/panel.Size.y)*870
                    if x>=0 and x<=1100 and y>=0 and y<=870 then
                        cursor.Visible=true;cursor.Position=UDim2.new(0,x-8,0,y-8)
                        for _,b in ipairs(self.buttons)do if x>=b.x and x<=b.x+b.w and y>=b.y and y<=b.y+b.h then self.hover=b;break end end
                    end
                end
            end
            for _,b in ipairs(self.buttons)do
                if b.plate then b.plate.Image=texture(b==self.hover and "MenuBarAssets/MenuButtonSelected.png"or"MenuBarAssets/MenuButton.png")end
                if b.tab then b.label.TextTransparency=(b.selected or b==self.hover)and 0 or .5;b.icon.ImageTransparency=b.label.TextTransparency end
            end
            if pressed(1)and self.hover then self.hover.action()end
        end
        local tool=nil
        if player.Character then for _,child in ipairs(player.Character:GetChildren())do if child:IsA("Tool")then tool=child;break end end end
        local activate=not self.opened and down(1)and not self.consumeTrigger
        if tool~=self.tool and self.tool then pcall(function()self.tool:Deactivate()end)end
        if tool and (tool~=self.tool or activate~=self.activated)then pcall(function()if activate then tool:Activate()else tool:Deactivate()end end)end
        self.tool=tool;self.activated=activate;self.lastButtons=mask
        return self.opened
    end
    local function incoming(kind,sender,message,recipient)
        if kind==Enum.PlayerChatType.Whisper and sender~=player and recipient~=player then return end
        if kind==Enum.PlayerChatType.Team and sender and sender.TeamColor~=player.TeamColor then return end
        self.messages[#self.messages+1]=(sender and sender.Name or "Player")..": "..tostring(message)
        if #self.messages>40 then table.remove(self.messages,1)end
        if self.opened and self.page=="chat"then self:draw()end
    end
    -- Some 2015 builds reserve PlayerChatted for CoreScripts. Chatted is the
    -- ordinary game event; no custom server chat or filtering path is added.
    local connected=pcall(function()game.Players.PlayerChatted:connect(incoming)end)
    if not connected then
        local function watch(sender)
            sender.Chatted:connect(function(message,recipient)
                if recipient and sender~=player and recipient~=player then return end
                incoming(recipient and Enum.PlayerChatType.Whisper or Enum.PlayerChatType.All,sender,message,recipient)
            end)
        end
        for _,sender in ipairs(game.Players:GetPlayers())do watch(sender)end
        game.Players.PlayerAdded:connect(watch)
    end
    self:draw();return self
end
return Menu
