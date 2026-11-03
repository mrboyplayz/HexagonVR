-- First-person tracking and locomotion execute locally every frame.
local Players=game:GetService("Players")
local RS=game:GetService("ReplicatedStorage")
local Run=game:GetService("RunService")
local player=Players.LocalPlayer
local remote=RS:WaitForChild("HexagonVR")
local enabled=false
local wanted,lastWake=true,0
local savedCamera,hidden,baseline={},{},{}
local lastInput,lastSequence,lastSent,lastTurn=0,nil,0,nil
local mailboxDormant=false
local gui=Instance.new("ScreenGui");gui.Name="HexagonVRStatus";gui.Parent=player:WaitForChild("PlayerGui")
local label=Instance.new("TextLabel");label.Size=UDim2.new(0,600,0,28);label.Position=UDim2.new(.5,-300,1,-40)
label.BackgroundTransparency=.3;label.BackgroundColor3=Color3.new(0,0,0);label.TextColor3=Color3.new(1,1,1)
label.FontSize=Enum.FontSize.Size18;label.Text="Type /vr to use VR";label.Parent=gui
local privateStorage=player:WaitForChild("PlayerScripts")
local box=privateStorage:FindFirstChild("HexagonVRLocalMailbox")
local initial={head={12001.125,23002.25,34003.5},left={13001.125,24002.25,35003.5},right={14001.125,25002.25,36003.5},control={16001.125,26002.25,36003.5},move={15001.125,25002.25,35003.5},settings={17001.125,27002.25,37003.5},ack={26002.25,56002.25,66003.5},move_ack={15001.125,25002.25,77003.5},settings_ack={17001.125,27002.25,78003.5},viewport={18001.125,28002.25,38003.5},position={19001.125,29002.25,39003.5}}
initial.ui={20001.125,30002.25,40003.5};initial.ui_ack={20001.125,30002.25,81003.5};initial.ui_out={21001.125,31002.25,41003.5}
initial.camera_state={26002.25,0,82003.5}
if not box then
    box=Instance.new("Folder");box.Name="HexagonVRLocalMailbox";box.Parent=privateStorage
    for name,values in pairs(initial) do
        local isFrame=name=="head" or name=="left" or name=="right"
        local value=Instance.new(isFrame and "CFrameValue" or "Vector3Value")
        value.Name=name;value.Value=isFrame and CFrame.new(unpack(values)) or Vector3.new(unpack(values));value.Parent=box
    end
end
if not box:FindFirstChild("camera_state")then
    local value=Instance.new("Vector3Value");value.Name="camera_state";value.Value=Vector3.new(unpack(initial.camera_state));value.Parent=box
end
local menu=require(script:WaitForChild("VRMenu")).new(player,box,remote)
local chatUI=require(script:WaitForChild("VRChatClient")).new(player,menu)
local studioMenuShown=false
local function walk(object,fn)for _,v in ipairs(object:GetChildren())do fn(v);walk(v,fn)end end
local function restore()
    menu:setOpen(false)
    for part,value in pairs(hidden)do if part.Parent then part.LocalTransparencyModifier=value end end
    hidden={};baseline={}
    if savedCamera.camera and savedCamera.camera.Parent then
        savedCamera.camera.CameraType=savedCamera.kind;savedCamera.camera.CameraSubject=savedCamera.subject;savedCamera.camera.FieldOfView=savedCamera.fov
    end
    savedCamera={}
    local hum=player.Character and player.Character:FindFirstChild("Humanoid")
    if hum then hum:Move(Vector3.new(),false) end
end
remote.OnClientEvent:connect(function(action,who,value,reason)
    if action=="chatDisplay"then chatUI:display(who,value);return end
    if action=="chatResult"then menu:chatResult(who,value,reason);return end
    if action=="message" then label.Text=who;return end
    if who~=player then return end
    if action=="mode" then
        wanted=value or(wanted and(reason=="tracking lost"or reason=="respawn"or reason=="death"))
        if value and not enabled then
            local camera=workspace.CurrentCamera
            savedCamera={camera=camera,kind=camera.CameraType,subject=camera.CameraSubject,fov=camera.FieldOfView}
            baseline={};lastTurn=nil
        elseif not value then
            restore()
            if RS:FindFirstChild("HexagonVRStudioMenuTest")then studioMenuShown=false end
        end
        enabled=value;label.Text=enabled and "VR | Y menu | B chat | A jump | X recenter" or "VR off | type /vr to use VR"
    end
end)
remote:FireServer("ready")
local function render()
    local control=box.control.Value
    box.ack.Value=Vector3.new(control.y,56002.25,66003.5)
    local input=box.move.Value;local settings=box.settings.Value
    box.move_ack.Value=Vector3.new(input.x,input.y,77003.5)
    box.settings_ack.Value=Vector3.new(settings.x,settings.y,78003.5)
    local ui=box.ui.Value
    menu.nativeRendering=math.floor(settings.z)==4
    local forward=(settings.z-math.floor(settings.z))*10
    if math.abs((menu.armForward or 0)-forward)>.01 then
        menu.armForward=forward
        if menu.opened and menu.page=="settings"then menu:draw()end
    end
    box.ui_ack.Value=Vector3.new(ui.x,ui.y,81003.5)
    menu:mailbox()
    if control.y~=lastSequence then lastSequence=control.y;lastInput=tick() end
    if control.y~=initial.control[2] then mailboxDormant=false end
    if tick()-lastInput>1 and not mailboxDormant then
        for name,values in pairs(initial)do
            local isFrame=name=="head"or name=="left"or name=="right"
            box[name].Value=isFrame and CFrame.new(unpack(values))or Vector3.new(unpack(values))
        end
        lastSequence=initial.control[2];mailboxDormant=true
        return
    end
    local flags=control.x
    local tracked=flags>=1 and flags<=7 and flags==math.floor(flags) and tick()-lastInput<.35
    box.camera_state.Value=Vector3.new(control.y,enabled and tracked and 1 or 0,82003.5)
    if tracked and not enabled and wanted and tick()-lastWake>1 then lastWake=tick();remote:FireServer("enable")end
    if not enabled or not tracked then
        if menu.opened then menu:setOpen(false)end
        if enabled and tick()-lastInput>.35 then
            local hum=player.Character and player.Character:FindFirstChild("Humanoid")
            if hum then hum:Move(Vector3.new(),false)end
        end
        return
    end
    local char=player.Character
    local root=char and char:FindFirstChild("HumanoidRootPart")
    local torso=char and char:FindFirstChild("Torso")
    local hum=char and char:FindFirstChild("Humanoid")
    if not root or not torso or not hum then return end
    if lastTurn and control.z~=lastTurn and not menu.opened then
        local delta=math.max(-1,math.min(1,control.z-lastTurn))
        root.CFrame=root.CFrame*CFrame.Angles(0,math.rad(-30*delta),0)
    end
    lastTurn=control.z
    local head=box.head.Value
    local left=math.floor(flags/2)%2==1 and box.left.Value or nil
    local right=math.floor(flags/4)%2==1 and box.right.Value or nil
    local camera=workspace.CurrentCamera
    camera.CameraType=Enum.CameraType.Scriptable
    camera.CoordinateFrame=root.CFrame*head*CFrame.new(0,0,-math.max(0,math.min(1,settings.y)))
    camera.Focus=camera.CoordinateFrame*CFrame.new(0,0,-8)
    camera.FieldOfView=math.max(1,math.min(120,settings.x))
    box.viewport.Value=Vector3.new(camera.ViewportSize.x,camera.ViewportSize.y,camera.FieldOfView)
    box.position.Value=Vector3.new(root.Position.x,root.Position.z,control.y)
    if not studioMenuShown and RS:FindFirstChild("HexagonVRStudioMenuTest")then
        studioMenuShown=true;menu:setOpen(true,"menu")
        print("HEXAGON_VR_STUDIO_MENU_OPEN")
    end
    local blocked=menu:update(right and root.CFrame*right or nil,ui.x>=0 and ui.x<=127 and ui.x or 0,ui.z)
    for _,row in ipairs({{"head",head},{"left",left},{"right",right}})do
        local weld=torso:FindFirstChild("HexagonVR_"..row[1])
        if weld then
            if not baseline[weld]then baseline[weld]=weld.C0 end
            if row[2]then
                local target=row[2]
                if row[1]~="head"then target=target*CFrame.Angles(math.rad(90),0,0)*CFrame.new(0,1,0)end
                weld.C0=torso.CFrame:toObjectSpace(root.CFrame*target)*weld.C1
            else weld.C0=baseline[weld]end
        end
    end
    local vector=Vector3.new(input.x,0,input.y)
    if blocked then vector=Vector3.new()end
    if vector.magnitude>1 then vector=vector.unit end
    local direction=camera.CoordinateFrame.lookVector;direction=Vector3.new(direction.x,0,direction.z)
    if direction.magnitude>.01 then hum:Move(CFrame.new(Vector3.new(),direction):vectorToWorldSpace(vector),false)end
    if input.z>.5 and not blocked then hum.Jump=true end
    walk(char,function(part)
        if part:IsA("BasePart")and(part.Name=="Head"or part.Parent:IsA("Hat")or part.Parent:IsA("Accessory"))then
            if hidden[part]==nil then hidden[part]=part.LocalTransparencyModifier end
            part.LocalTransparencyModifier=1
        end
    end)
    if tick()-lastSent>=.05 then
        lastSent=tick()
        remote:FireServer("pose",{seq=control.y,head={head:components()},left=left and {left:components()}or nil,right=right and {right:components()}or nil,tracked=true})
    end
end
Run:BindToRenderStep("HexagonVR",Enum.RenderPriority.Last.Value,render)
print("HEXAGON_VR_LOCAL_MAILBOX_READY")
