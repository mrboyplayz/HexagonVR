local ok,err=pcall(function()
    local p=game.Players.LocalPlayer or game.Players:GetPlayers()[1]
    repeat wait(.1)until p.Character and p.Character:FindFirstChild('HumanoidRootPart')
    local char=p.Character;local root=char.HumanoidRootPart;root.Anchored=true;root.CFrame=CFrame.new(0,5,10)
    local W=require(game.ServerScriptService.VRWeapons).new({Weapons={Enabled=true,SpawnPosition=Vector3.new(100,0,100),RespawnSeconds=9999}})
    local G=require(game.ReplicatedStorage.HexagonVRWeaponGeometry)
    local function expect(v,text)assert(v,text);print('RIFLE_CHECK',text)end
    local function find(kind)for _,i in ipairs(W.items)do if i.kind==kind then return i end end end
    local session={character=char,root=root,humanoid=char.Humanoid};local right=CFrame.new(0,5,0);local left=CFrame.new(-3,5,0)
    local function pose(mask)W:update(p,session,{right=right,left=left},mask,false);wait(.02)end
    for _,item in ipairs(W.items)do item.root.Anchored=true end
    local function pickup(gun,x)
        pose(0);W:move(gun,CFrame.new(x,5,0));right=gun.root.CFrame*gun.grip;pose(64)
        expect(gun.owner.Value==p,'Grip picks up '..gun.kind)
    end
    local function load(gun,mag)
        local entry=gun.root.CFrame*G.magazineFrame(gun.layout,0)
        W:move(mag,entry);left=entry;pose(96)
        expect(mag.owner.Value==p,'The matching '..gun.kind..' magazine is a physical pickup')
        for n=0,24 do left=entry*CFrame.new(0,gun.layout.InsertDepth*n/24,0);pose(96)end
        for n=1,8 do pose(96)end
        expect(gun.gun.magazine==mag and not mag.owner.Value and not gun.gun.chamber,'Fully seating a '..gun.kind..' magazine does not chamber a round')
        pose(64)
    end
    local m16,mag=find('M16'),find('M16Magazine');pickup(m16,0);load(m16,mag)
    left=m16.slidePart.CFrame;pose(96);expect(m16.slideGrab.Value=='left','The M16 charging handle can be gripped')
    left=left*CFrame.new(0,0,.24);pose(96);pose(64)
    expect(m16.gun.chamber and mag.rounds==29,'Pulling and releasing the M16 handle chambers exactly one round')
    expect(W:shot(m16,p,char),'The loaded M16 fires');wait(.11);expect(W:shot(m16,p,char),'The M16 cycles subsequent rounds')
    expect(mag.rounds==27,'M16 cycling consumes one round for each fired shot')
    local awp,awpmag=find('AWP'),find('AWPMagazine');pickup(awp,4);load(awp,awpmag)
    local function openBolt()
        left=awp.slidePart.CFrame;pose(96);expect(awp.slideGrab.Value=='left','The AWP bolt handle can be gripped')
        left=left*CFrame.new(0,.12,0);pose(96);left=left*CFrame.new(0,0,.32);pose(96)
        expect(awp.gun.slideOpen and awp.boltLift.Value>.9,'Lifting and drawing the AWP bolt opens the action')
    end
    local function closeBolt()
        local held=W.players[p].held.left;local point=awp.root.CFrame:pointToObjectSpace(left.p)
        left=awp.root.CFrame*CFrame.new(point.x,held.startY+.12,held.start);pose(96)
        left=awp.root.CFrame*CFrame.new(point.x,held.startY,held.start);pose(96);pose(64)
    end
    openBolt();closeBolt()
    expect(awp.gun.chamber and awpmag.rounds==9 and awp.boltLift.Value==0,'Closing and locking the AWP bolt chambers one round')
    expect(W:shot(awp,p,char),'The chambered AWP fires')
    expect(not awp.gun.chamber and awp.gun.spent and awpmag.rounds==9,'An AWP shot leaves a spent casing and does not auto-feed')
    wait(1.12);expect(not W:shot(awp,p,char),'The AWP cannot fire again without cycling its bolt')
    openBolt();expect(not awp.gun.spent,'Opening the AWP bolt extracts the spent casing')
    pose(64);expect(awp.gun.slideOpen and awpmag.rounds==9,'Releasing an open AWP bolt leaves it open instead of spring-loading a round')
    left=awp.slidePart.CFrame;pose(96);closeBolt()
    expect(awp.gun.chamber and awpmag.rounds==8,'Re-gripping and closing the AWP bolt chambers the next round')
    local client=require(game.StarterGui.HexagonVRClient.VRWeaponClient).new(p)
    client:update({right=right,left=left},64,false)
    local box=Instance.new('Folder')
    for _,name in ipairs({'scope_frame','scope_params','scope_state'})do local v=Instance.new(name=='scope_frame'and'CFrameValue'or'Vector3Value');v.Name=name;v.Parent=box end
    local scope=require(game.StarterGui.HexagonVRClient.VRScope).new(p,box,client)
    local lens=client:visualRoot(awp.model).CFrame*awp.layout.ScopeFrame
    workspace.CurrentCamera.CoordinateFrame=lens*CFrame.new(0,0,.45);scope:update(1,false,true)
    expect(box.scope_state.Value.y==1 and box.scope_params.Value.y==4,'The aligned AWP scope requests a 4x lens image')
    workspace.CurrentCamera.CoordinateFrame=lens*CFrame.new(.8,0,.45);scope:update(2,false,true);expect(box.scope_state.Value.y==0,'Moving outside the scope eye box disables magnification')
    workspace.CurrentCamera.CoordinateFrame=lens*CFrame.new(0,0,.45);scope:update(3,true,true);expect(box.scope_state.Value.y==0,'Opening the menu disables the scope pass')
    local wall=Instance.new('Part');wall.Anchored=true;wall.Size=Vector3.new(2,2,.1);wall.CFrame=lens*CFrame.new(0,0,-.2);wall.Parent=workspace
    scope:update(4,false,true);expect(box.scope_state.Value.y==0,'An obstructed scope cannot reveal a scene through a wall');wall:Destroy()
    local fx=client.fx;local before=0;for _,part in ipairs(fx.folder:GetChildren())do if part.Name=='Casing'then before=before+1 end end
    fx:shot(client:visualRoot(awp.model),awp.layout,awp.root.CFrame,nil,1)
    local after=0;for _,part in ipairs(fx.folder:GetChildren())do if part.Name=='Casing'then after=after+1 end end
    expect(after==before,'AWP shot feedback keeps the casing in the rifle until the bolt opens')
    fx:eject(awp.layout,awp.root.CFrame,1)
    after=0;for _,part in ipairs(fx.folder:GetChildren())do if part.Name=='Casing'then after=after+1 end end
    expect(after==before+1,'The extracted AWP casing uses the shared cartridge mesh effect')
    client:update({right=right,left=left},0,false);scope:update(5,false,true)
    expect(box.scope_state.Value.y==0,'Releasing the grip disables the scope immediately before server ownership catches up')
    print('HEXAGON_RIFLES_ENGINE_PASS')
end)
if not ok then print('HEXAGON_RIFLES_ENGINE_FAIL',err)end
