-- Public chat submitted by the game itself. No desktop keyboard input.
local Chat={}
function Chat.start(remote,config,isActive,command)
    local Players=game:GetService("Players")
    local Run=game:GetService("RunService")
    local Service=game:GetService("Chat")
    local jobs,last,completed={},{},{}
    local function reply(player,id,ok,text)
        completed[player]={id=id,ok=ok,text=text}
        if player.Parent then remote:FireClient(player,"chatResult",id,ok,text)end
    end
    local function alive(player,job)
        return player.Parent and jobs[player]==job and not job.expired
    end
    local function filtered(text,recipient)
        local ok,value=pcall(function()return Service:FilterStringForPlayerAsync(text,recipient)end)
        return ok and type(value)=="string"and #value>0 and #value<=2048 and value or nil
    end
    remote.OnServerEvent:connect(function(player,action,data)
        if action~="chat"then return end
        if type(data)~="table"or type(data.id)~="number"or data.id~=math.floor(data.id)or data.id<1 or data.id>999999 then return end
        local id=data.id
        if completed[player]and completed[player].id==id then
            local row=completed[player];remote:FireClient(player,"chatResult",id,row.ok,row.text);return
        end
        if jobs[player]then
            if jobs[player].id~=id then reply(player,id,false,"A message is still being sent.")end
            return
        end
        if type(data.text)~="string"or #data.text>140 or data.text:find("%c")then reply(player,id,false,"Enter a message of up to 140 characters.");return end
        local text=data.text:match("^%s*(.-)%s*$")
        if text==""then reply(player,id,false,"Enter a message first.");return end
        if last[player]and tick()-last[player]<(config.ChatInterval or 1.5)then reply(player,id,false,"Please wait a moment before sending again.");return end
        local lower=string.lower(text)
        if lower=="/vr"or lower=="/unvr"then
            last[player]=tick();command(player,lower);reply(player,id,true,"Done.");return
        end
        if text:sub(1,1)=="/"then reply(player,id,false,"This keyboard uses public chat. Use normal chat for other commands.");return end
        if not isActive(player)then reply(player,id,false,"Turn VR on before using this keyboard.");return end
        last[player]=tick()
        local job={id=id,deadline=tick()+(config.ChatTimeout or 12),expired=false,replied=false}
        jobs[player]=job
        spawn(function()
            -- Confirm the sender's own filtered copy before delivering anywhere.
            local own=filtered(text,player)
            if not alive(player,job)then if jobs[player]==job then jobs[player]=nil end;return end
            if not own then jobs[player]=nil;reply(player,id,false,"Chat is unavailable right now. Your text is kept.");return end
            remote:FireClient(player,"chatDisplay",player,own)
            job.replied=true;reply(player,id,true,"Sent.")
            local recipients={}
            for _,recipient in ipairs(Players:GetPlayers())do if recipient~=player then recipients[#recipients+1]=recipient end end
            job.remaining=#recipients
            if job.remaining==0 then jobs[player]=nil;return end
            for _,recipient in ipairs(recipients)do spawn(function()
                local value=filtered(text,recipient)
                if alive(player,job)and recipient.Parent and value then remote:FireClient(recipient,"chatDisplay",player,value)end
                job.remaining=job.remaining-1
                if job.remaining==0 and jobs[player]==job then jobs[player]=nil end
            end)end
        end)
    end)
    Run.Stepped:connect(function()
        for player,job in pairs(jobs)do
            if not job.expired and tick()>job.deadline then
                job.expired=true;jobs[player]=nil
                if not job.replied then reply(player,job.id,false,"Chat took too long. Your text is kept.")end
            end
        end
    end)
    Players.PlayerRemoving:connect(function(player)jobs[player]=nil;last[player]=nil;completed[player]=nil end)
end
return Chat
