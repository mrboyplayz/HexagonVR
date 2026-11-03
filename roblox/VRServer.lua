-- Lua 5.1 / Hexagon 0.217. Each player owns an independent R6 VR session.
local Players=game:GetService("Players")
local RS=game:GetService("ReplicatedStorage")
local Run=game:GetService("RunService")
local C=require(script.Parent.VRConfig)
local remote=RS:FindFirstChild("HexagonVR")or Instance.new("RemoteEvent")
remote.Name="HexagonVR";remote.Parent=RS
local sessions,requested={},{}
local function tell(player,text)remote:FireClient(player,"message",text)end
local function allowed(player)
    local list=C.AllowedUserIds or {}
    if #list==0 then return true end
    for _,id in ipairs(list)do if tonumber(id)==player.userId then return true end end
    return false
end
local function leave(player,reason)
    local state=sessions[player]
    if not state then return end
    sessions[player]=nil
    if state.death then state.death:disconnect()end
    for _,row in ipairs(state.joints)do
        if row.weld and row.weld.Parent then row.weld:Destroy()end
        if row.motor then
            if row.parent.Parent then row.motor.Parent=row.parent else row.motor:Destroy()end
        end
    end
    if state.humanoid.Parent then
        state.humanoid.AutoRotate=state.autoRotate;state.humanoid.WalkSpeed=state.walkSpeed
        state.humanoid:Move(Vector3.new(),false)
    end
    remote:FireAllClients("mode",player,false,reason)
    print("HEXAGON_VR_OFF",player.Name,reason or"toggle")
end
local function enter(player)
    if sessions[player]then return end
    if not allowed(player)then tell(player,"VR is not enabled for this account in this game's VRConfig.");return end
    local char=player.Character
    local torso=char and char:FindFirstChild("Torso")
    local root=char and char:FindFirstChild("HumanoidRootPart")
    local hum=char and char:FindFirstChild("Humanoid")
    if not torso or not root or not hum or hum.Health<=0 then tell(player,"VR needs a living R6 character.");return end
    local joints={}
    for _,spec in ipairs({{"Neck","Head","head"},{"Left Shoulder","Left Arm","left"},{"Right Shoulder","Right Arm","right"}})do
        local motor=torso:FindFirstChild(spec[1]);local part=char:FindFirstChild(spec[2])
        if not motor or not motor:IsA("Motor6D")or not part then tell(player,"Your R6 neck or shoulder joints are missing.");return end
        joints[#joints+1]={motor=motor,parent=motor.Parent,part=part,key=spec[3],c0=motor.C0,c1=motor.C1}
    end
    for _,row in ipairs(joints)do
        row.motor.Parent=nil;row.weld=Instance.new("Weld");row.weld.Name="HexagonVR_"..row.key
        row.weld.Part0=torso;row.weld.Part1=row.part;row.weld.C0=row.c0;row.weld.C1=row.c1;row.weld.Parent=torso
    end
    local state={character=char,torso=torso,root=root,humanoid=hum,joints=joints,autoRotate=hum.AutoRotate,walkSpeed=hum.WalkSpeed,lastSequence=-1,lastPoseAt=tick()+25,remotePoseAt=-math.huge}
    sessions[player]=state;hum.AutoRotate=false;hum.WalkSpeed=C.WalkSpeed
    state.death=hum.Died:connect(function()if sessions[player]==state then leave(player,"death")end end)
    remote:FireAllClients("mode",player,true)
    print("HEXAGON_VR_ON",player.Name)
end
local function command(player,text)
    text=string.lower(string.match(text or"","^%s*(.-)%s*$"))
    if text~="/vr"and text~="/unvr"then return end
    if requested[player]and tick()-requested[player]<.5 then return end
    requested[player]=tick()
    if sessions[player]then leave(player,"toggle")elseif text=="/vr"then enter(player)end
end
local function setup(player)
    player.Chatted:connect(function(text)command(player,text)end)
    local function characterAdded(character)
        leave(player,"respawn")
        if C.AutoEnable and allowed(player)then spawn(function()
            local deadline=tick()+20
            repeat wait(.1)until(character and character:FindFirstChild("Torso"))or tick()>deadline
            wait(2)
            if player.Character==character and player.Parent and not sessions[player]then enter(player)end
        end)end
    end
    player.CharacterAdded:connect(characterAdded)
    if player.Character and C.AutoEnable then characterAdded(player.Character)end
end
local function frame(a)
    if type(a)~="table"or #a~=12 then return nil end
    for i=1,12 do if type(a[i])~="number"or a[i]~=a[i]or math.abs(a[i])>10000 then return nil end end
    if Vector3.new(a[1],a[2],a[3]).magnitude>C.MaxReach then return nil end
    for row=0,2 do
        local length=0
        for col=0,2 do local x=a[4+row*3+col];length=length+x*x end
        if math.abs(length-1)>.05 then return nil end
        for other=row+1,2 do
            local dot=0;for col=0,2 do dot=dot+a[4+row*3+col]*a[4+other*3+col]end
            if math.abs(dot)>.05 then return nil end
        end
    end
    return CFrame.new(unpack(a))
end
local function apply(player,pose)
    local state=sessions[player]
    if not state then return end
    if not state.character.Parent or state.humanoid.Health<=0 then leave(player,"death");return end
    if type(pose)~="table"or not pose.tracked or type(pose.seq)~="number"or pose.seq~=pose.seq or pose.seq<0 or pose.seq>=1000000 or pose.seq~=math.floor(pose.seq)or pose.seq==state.lastSequence then return end
    local head=frame(pose.head)
    if not head then return end
    state.lastSequence=pose.seq;state.lastPoseAt=tick()
    local root=state.root.CFrame
    for _,row in ipairs(state.joints)do
        local target=row.key=="head"and head or frame(pose[row.key])
        if target then
            if row.key~="head"then target=target*CFrame.Angles(math.rad(C.ArmRotationDegrees),0,0)*CFrame.new(0,1,0)end
            row.weld.C0=state.torso.CFrame:toObjectSpace(root*target)*row.weld.C1
        else row.weld.C0=row.c0 end
    end
end
Players.PlayerAdded:connect(setup)
Players.PlayerRemoving:connect(function(player)requested[player]=nil;leave(player,"disconnect")end)
Run.Stepped:connect(function()
    local expired={}
    for player,state in pairs(sessions)do if tick()-state.lastPoseAt>C.TrackingTimeout then expired[#expired+1]=player end end
    for _,player in ipairs(expired)do leave(player,"tracking lost")end
end)
for _,player in ipairs(Players:GetPlayers())do setup(player)end
remote.OnServerEvent:connect(function(player,action,data)
    local state=sessions[player]
    if action=="reset"and state then state.humanoid.Health=0;return end
    if action=="toggle"then command(player,"/vr")end
    if action=="ready"and state then remote:FireClient(player,"mode",player,true)end
    if action=="pose"and state and tick()-state.remotePoseAt>=.04 then state.remotePoseAt=tick();apply(player,data)end
end)
-- Server-only integration-test hook; no externally supplied code is accepted.
local toggle=Instance.new("BindableEvent");toggle.Name="HexagonVRTestToggle";toggle.Parent=script
toggle.Event:connect(function(player)command(player,"/vr")end)
print("HEXAGON_VR_SERVER_READY_MULTIPLAYER")
