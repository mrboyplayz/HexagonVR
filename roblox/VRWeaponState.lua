-- Engine-independent firearm state. Lua 5.1; all transitions run on the server.
local M={}
function M.new(capacity,holdOpen,manual)
    return {capacity=capacity or 12,holdOpen=holdOpen~=false,manual=manual,magazine=nil,chamber=false,spent=false,slideOpen=false,slideLocked=false,lastShot=-math.huge}
end
function M.insert(gun,magazine)
    if gun.magazine or not magazine or type(magazine.rounds)~="number"then return false end
    gun.magazine=magazine
    return true
end
function M.remove(gun)
    local magazine=gun.magazine;gun.magazine=nil;return magazine
end
function M.open(gun)
    if gun.slideOpen then return false end
    local ejected=gun.chamber or gun.spent;gun.chamber=false;gun.spent=false;gun.slideOpen=true
    return ejected
end
function M.close(gun)
    if not gun.slideOpen then return false end
    gun.slideOpen=false
    if gun.magazine and gun.magazine.rounds>0 then
        gun.magazine.rounds=gun.magazine.rounds-1;gun.chamber=true;gun.slideLocked=false
    else gun.slideLocked=gun.magazine~=nil and gun.holdOpen end
    return gun.chamber
end
function M.fire(gun,now,interval)
    if now-gun.lastShot<(interval or .18)then return false,"cooldown"end
    if gun.slideOpen or gun.slideLocked then return false,"slide"end
    gun.lastShot=now
    if not gun.chamber then return false,"empty"end
    gun.chamber=false
    if gun.manual then gun.spent=true;return true end
    if gun.magazine and gun.magazine.rounds>0 then
        gun.magazine.rounds=gun.magazine.rounds-1;gun.chamber=true
    elseif gun.magazine then gun.slideLocked=gun.holdOpen end
    return true
end
return M
