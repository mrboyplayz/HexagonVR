-- Tracking describes the eyes. Avatar head and neck are placed behind them.
local B={EyeForward=.45,EyeHeight=.12,HeadHalfHeight=.5,NeckHeight=1,TurnSpeed=65}
local function wrap(angle)return(angle+math.pi)%(2*math.pi)-math.pi end
function B.sample(eyes,previous,dt,forward)
    local head=eyes*CFrame.new(0,-B.EyeHeight,forward or B.EyeForward)
    local look=head.lookVector
    local yaw
    if look.x*look.x+look.z*look.z<.01 then
        local right=head:vectorToWorldSpace(Vector3.new(1,0,0));yaw=math.atan2(-right.z,right.x)
    else yaw=math.atan2(-look.x,-look.z)end
    yaw=previous+wrap(yaw-previous)
    local target=yaw*.6
    local limit=math.rad(55)
    if math.abs(wrap(yaw-target))>limit then target=yaw-(yaw>=0 and limit or-limit)end
    local bodyYaw=previous+wrap(target-previous)*(1-math.exp(-math.max(0,math.min(.1,dt))*8))
    local rotation=CFrame.Angles(0,bodyYaw,0)
    local neck=head:pointToWorldSpace(Vector3.new(0,-B.HeadHalfHeight,0))
    local torso=CFrame.new(neck-rotation:vectorToWorldSpace(Vector3.new(0,B.NeckHeight,0)))*rotation
    return head,torso,bodyYaw
end
function B.eyes(head,forward)return head*CFrame.new(0,B.EyeHeight,-(forward or B.EyeForward))end
return B
