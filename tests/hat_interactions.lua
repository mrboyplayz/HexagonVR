local ok,err=pcall(function()
    local player=game.Players.LocalPlayer or game.Players:GetPlayers()[1]
    repeat wait(.1)until player.Character and player.Character:FindFirstChild('Head')
    local char=player.Character;local head=char.Head;local root=char.HumanoidRootPart
    root.Anchored=true;root.CFrame=CFrame.new(0,5,0);wait(.1)
    local W=require(game.ServerScriptService.VRWeapons).new({Weapons={Enabled=true,SpawnPosition=Vector3.new(100,0,100),RespawnSeconds=9999}})
    local function expect(value,text)assert(value,text);print('HAT_CHECK',text)end
    local hat=Instance.new('Hat');hat.Name='Offset Pivot Hat'
    local handle=Instance.new('Part');handle.Name='Handle';handle.Size=Vector3.new(1,.5,1);handle.CanCollide=false;handle.Parent=hat
    local offset=CFrame.new(.15,.8,.1)*CFrame.Angles(.1,.2,.05)
    hat.AttachmentPoint=offset:inverse()*CFrame.new(0,head.Size.y/2,0);handle.CFrame=head.CFrame*offset
    local brim=Instance.new('Part');brim.Name='Brim';brim.Size=Vector3.new(1.6,.2,1.2);brim.CanCollide=false;brim.CFrame=handle.CFrame*CFrame.new(.3,-.2,0);brim.Parent=hat
    local internal=Instance.new('Weld');internal.Part0=handle;internal.Part1=brim;internal.C0=CFrame.new(.3,-.2,0);internal.Parent=handle
    hat.Parent=char;wait(.2)
    local item=W:registerHat(hat,player)
    expect(item and item.wearer.Value==player and item.model==hat,'Existing worn hats are registered without making duplicate hats')
    local original=handle.CFrame
    local hand=original*CFrame.new(.4,.1,.1)*CFrame.Angles(.1,.4,0)
    local left=CFrame.new(-5,5,5);local session={character=char,root=root}
    local function pose(mask,right)W:update(player,session,{left=left,right=right or hand},mask,false)end
    pose(0);pose(64)
    expect(item.owner.Value==player and not item.wearer.Value and hat.Parent==W.folder,'Grip removes the actual hat from the head and owns it')
    expect((handle.Position-original.p).magnitude<.001,'Grabbing a hat away from its center preserves the current pose')
    local grip=item.heldGrip.Value
    expect(grip.p.magnitude>.25,'The held pivot records the off-center grab point')
    local rotated=CFrame.new(hand.p)*(hand-hand.p)*CFrame.Angles(0,math.pi/2,0)
    pose(64,rotated)
    expect(((handle.CFrame*grip).p-rotated.p).magnitude<.001,'Wrist rotation pivots the hat around the grabbed point')
    expect((handle.Position-original.p).magnitude>.2,'Off-center rotation moves the hat center rather than pivoting in place')
    expect((brim.Position-(handle.CFrame*item.hatOffsets[brim]).p).magnitude<.001,'A multipart hat stays together while held')
    local client=require(game.StarterGui.HexagonVRClient.VRWeaponClient).new(player)
    client:update({right=rotated,left=left},64,false)
    local visible=client:visualRoot(hat);local visibleBrim=visible.Parent:FindFirstChild('Brim')
    expect(visible~=handle and visibleBrim and(visibleBrim.Position-(visible.CFrame*item.hatOffsets[brim]).p).magnitude<.001,'Client prediction renders every hat part with the same held pivot')
    hand=CFrame.new(4,0,0)*rotated;pose(64,hand);pose(0,hand);client:update({right=hand},0,false)
    expect(hat.Parent==W.folder and not item.owner.Value and not item.wearer.Value and not handle.Anchored and handle.CanCollide,'Releasing away from heads leaves a physical ground pickup')
    expect(handle.LocalTransparencyModifier==0 and brim.LocalTransparencyModifier==0,'Dropped hats restore shared visibility for all parts')
    hand=handle.CFrame*CFrame.new(-.3,.1,0);pose(64,hand)
    expect(item.owner.Value==player,'A dropped hat can be picked up again')
    hand=head.CFrame*item.headOffset*item.heldGrip.Value;pose(64,hand);pose(0,hand);wait(.15)
    expect(hat.Parent==char and item.wearer.Value==player and not item.owner.Value,'Releasing the hat on a head re-equips it')
    expect((handle.Position-(head.CFrame*item.headOffset).p).magnitude<.005,'Re-equipped hats keep their original head attachment offset')
    local count=0
    local function joints(node)for _,joint in ipairs(node:GetChildren())do
        if joint:IsA('JointInstance')and((joint.Part0==head and joint.Part1==handle)or(joint.Part1==head and joint.Part0==handle))then count=count+1 end
        joints(joint)
    end end;joints(char)
    expect(count==1,'Re-equipping leaves one head attachment without competing welds')
    item.lastUse=tick()-10000;wait(.1)
    expect((handle.Position-(head.CFrame*item.headOffset).p).magnitude<.005 and hat.Parent==char,'Worn hats are excluded from ground-item respawn timers')
    hand=handle.CFrame*CFrame.new(.2,0,0);pose(64,hand)
    expect(item.owner.Value==player and hat.Parent==W.folder,'An equipped hat can be grabbed again')
    W:dropPlayer(player)
    expect(not item.owner.Value and hat.Parent==W.folder,'Tracking cleanup drops held hats without silently equipping them')
    local dropped=handle.CFrame;hat.Parent=char;wait(.15)
    expect(hat.Parent==W.folder and not item.wearer.Value,'Legacy touch pickup cannot silently reattach a dropped VR hat')
    local junk=Instance.new('Hat');junk.Name='Non VR Ground Hat'
    local junkHandle=Instance.new('Part');junkHandle.Name='Handle';junkHandle.Anchored=true;junkHandle.CFrame=CFrame.new(30,5,0);junkHandle.Parent=junk;junk.Parent=workspace
    local nested=Instance.new('Model');nested.Parent=workspace
    local nestedHat=junk:Clone();nestedHat.Parent=nested
    wait(.3)
    expect(not junk.Parent and not nestedHat.Parent,'Ground hats without server-recorded VR provenance are deleted, including nested hats')
    local untouched=Instance.new('Hat');untouched.Name='Untouched Avatar Hat'
    local untouchedHandle=Instance.new('Part');untouchedHandle.Name='Handle';untouchedHandle.Parent=untouched;untouched.Parent=char
    wait(.25);expect(untouched.Parent==char,'Cleanup preserves hats that are still being worn')
    untouched.Parent=workspace;wait(.1)
    expect(not untouched.Parent,'A non-VR avatar drop is removed rather than registered as a VR pickup')
    expect(hat.Parent==W.folder,'A hat actually handled by VR survives ground cleanup')
    local npc=Instance.new('Model');npc.Parent=workspace
    local npcHead=Instance.new('Part');npcHead.Name='Head';npcHead.Anchored=true;npcHead.CFrame=CFrame.new(50,5,0);npcHead.Parent=npc
    local npcHumanoid=Instance.new('Humanoid');npcHumanoid.Parent=npc
    local npcHat=Instance.new('Hat');local npcHandle=Instance.new('Part');npcHandle.Name='Handle';npcHandle.Parent=npcHat;npcHat.Parent=npc
    wait(.25);expect(npcHat.Parent==npc,'A hat worn by an NPC is not mistaken for a ground hat')
    npcHat.Parent=workspace;wait(.25);expect(not npcHat.Parent,'An unregistered NPC hat is removed after becoming a loose ground hat')
    print('HEXAGON_HATS_ENGINE_PASS')
end)
if not ok then print('HEXAGON_HATS_ENGINE_FAIL',err)end
