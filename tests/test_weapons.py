from pathlib import Path
import struct,sys, tempfile, types, unittest, xml.etree.ElementTree as ET
from unittest.mock import patch,Mock
from lupa.lua51 import LuaRuntime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bridge import controller_buttons,pulse_controller
from weapon_assets import install_assets
from game_tools import make_demo, install
ROOT=Path(__file__).resolve().parents[1]

class WeaponStateTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime();self.lua.globals().S=self.lua.execute((ROOT/'roblox/VRWeaponState.lua').read_text())

    def test_magazine_alone_cannot_fire_then_rack_consumes_exactly_one_round(self):
        self.lua.execute('''
        g=S.new(12);m={rounds=12};assert(S.insert(g,m));assert(not g.chamber)
        assert(not S.fire(g,1));assert(m.rounds==12)
        S.open(g);assert(S.close(g));assert(g.chamber and m.rounds==11)
        assert(S.fire(g,2));assert(g.chamber and m.rounds==10)
        ''')

    def test_last_shot_locks_slide_and_empty_mag_cannot_produce_ammo(self):
        self.lua.execute('''
        g=S.new();m={rounds=2};S.insert(g,m);S.open(g);S.close(g)
        assert(S.fire(g,1));assert(S.fire(g,2));assert(g.slideLocked and not g.chamber and m.rounds==0)
        for n=3,10 do assert(not S.fire(g,n));S.open(g);S.close(g)end
        assert(m.rounds==0 and not g.chamber)
        assert(S.remove(g)==m);full={rounds=12};S.insert(g,full);assert(not S.fire(g,11))
        S.open(g);S.close(g);assert(S.fire(g,12));assert(full.rounds==10)
        ''')

    def test_removing_mag_retains_chamber_and_racking_ejects_it(self):
        self.lua.execute('''
        g=S.new();m={rounds=12};S.insert(g,m);S.open(g);S.close(g)
        assert(S.remove(g)==m and g.chamber and m.rounds==11)
        assert(S.fire(g,1));assert(not S.fire(g,2));assert(not g.magazine)
        S.insert(g,m);S.open(g);S.close(g);assert(S.open(g));assert(not S.open(g))
        assert(m.rounds==10);S.close(g);assert(m.rounds==9)
        ''')

    def test_independent_guns_and_cooldown_and_slide_safety(self):
        self.lua.execute('''
        a=S.new();b=S.new();S.insert(a,{rounds=12});S.insert(b,{rounds=12})
        S.open(a);S.close(a);S.open(b);S.close(b)
        assert(S.fire(a,1));assert(not S.fire(a,1.01));assert(S.fire(b,1))
        S.open(a);assert(not S.fire(a,2));assert(b.chamber and b.magazine.rounds==10)
        assert(not S.insert(b,{rounds=500}));assert(b.magazine.rounds==10)
        ''')

    def test_ak_empty_magazine_does_not_lock_bolt_and_magazines_remain_distinct(self):
        self.lua.execute('''
        g=S.new(30,false);m={rounds=30};S.insert(g,m);S.open(g);S.close(g)
        for n=1,30 do assert(S.fire(g,n))end
        assert(m.rounds==0 and not g.chamber and not g.slideLocked)
        assert(not S.fire(g,31));S.open(g);S.close(g);assert(not g.chamber)
        ''')

class WeaponIntegrationTests(unittest.TestCase):
    def test_filtering_is_explicit_for_demo_and_can_be_disabled_for_a_target_place(self):
        with tempfile.TemporaryDirectory()as directory:
            a,b,c=[Path(directory)/name for name in('base.rbxlx','kept.rbxlx','fd.rbxlx')]
            make_demo(a);tree=ET.parse(a)
            field=tree.find('.//Item[@class="Workspace"]/Properties/bool[@name="FilteringEnabled"]')
            self.assertEqual(field.text,'false');field.text='true';tree.write(a)
            install(a,b,'','');install(a,c,'','',filtering_enabled=False)
            query='.//Item[@class="Workspace"]/Properties/bool[@name="FilteringEnabled"]'
            self.assertEqual(ET.parse(b).findtext(query),'true')
            self.assertEqual(ET.parse(c).findtext(query),'false')

    def test_live_assets_are_public_and_offline_assets_use_the_bundled_files(self):
        import json
        records=json.loads((ROOT/'assets/PUBLIC-ASSETS.json').read_text())
        lua=LuaRuntime();lua.execute("offline={Value=false}; game={GetService=function()return {FindFirstChild=function()return offline end}end}")
        source=(ROOT/'roblox/VRWeaponAssets.lua').read_text()
        live=lua.execute(source)
        for key,row in records.items():
            self.assertTrue(row['public_delivery_verified']);self.assertEqual(live[key],row['url'])
        lua.execute('offline.Value=true');offline=lua.execute(source)
        for key,row in records.items():self.assertEqual(offline[key],'rbxasset://HexagonVRWeapons/'+row['file'])

    def test_crowbar_mesh_has_explicit_world_size_instead_of_legacy_units(self):
        data=(ROOT/'assets/crowbar_mesh.mesh').read_bytes();self.assertTrue(data.startswith(b'version 2.00\n'))
        start=data.index(b'\n')+1;header,stride,face_size,count,faces=struct.unpack_from('<HBBII',data,start)
        ys=[struct.unpack_from('<3f',data,start+header+n*stride)[1]for n in range(count)]
        self.assertAlmostEqual(max(ys)-min(ys),4.2,places=5)
        self.assertEqual(len(data),start+header+count*stride+faces*face_size)
        self.assertEqual(stride,40)
        import math
        for n in range(count):
            self.assertTrue(all(math.isfinite(x)for x in struct.unpack_from('<9f',data,start+header+n*stride)))

    def test_controller_haptic_is_scoped_to_holding_hand_and_clamped(self):
        vr=types.SimpleNamespace(TrackedControllerRole_LeftHand=1,TrackedControllerRole_RightHand=2,k_unTrackedDeviceIndexInvalid=99)
        system=Mock();system.getTrackedDeviceIndexForControllerRole.return_value=7
        pulse_controller(vr,system,0,9000);system.getTrackedDeviceIndexForControllerRole.assert_called_with(1)
        system.triggerHapticPulse.assert_called_once_with(7,0,3999)
        system.getTrackedDeviceIndexForControllerRole.return_value=99;pulse_controller(vr,system,1,1000)
        system.triggerHapticPulse.assert_called_once()

    def test_studio_opens_before_a_disconnected_headset_is_ready(self):
        import bridge
        class NoHeadset(Exception):pass
        vr=types.SimpleNamespace(VRApplication_Background=3,OpenVRError=NoHeadset,init=Mock(side_effect=NoHeadset()),shutdown=Mock())
        native=types.SimpleNamespace(write_config=Mock(),launch_studio=Mock(return_value='test process'))
        with tempfile.TemporaryDirectory()as directory:
            base=Path(directory);exe=base/'Hexagon/Versions/version-18d4f802f49c6c9d/RobloxStudioBeta.exe'
            exe.parent.mkdir(parents=True);exe.touch();place=base/'base.rbxlx';make_demo(place)
            with patch.dict('os.environ',{'LOCALAPPDATA':str(base)}),patch.dict(sys.modules,{'openvr':vr,'native_renderer':native}):
                process,folder=bridge.launch_place(place,'test',18765,local_client=True,native_directory=base/'native')
            self.assertEqual(process,'test process');self.assertTrue((folder/'VRPlace.rbxlx').exists())
            native.launch_studio.assert_called_once();native.write_config.assert_not_called();vr.shutdown.assert_not_called()

    def test_y_is_the_only_menu_shortcut_and_b_and_x_are_free(self):
        vr=types.SimpleNamespace(k_EButton_A=7,k_EButton_ApplicationMenu=1,k_EButton_Grip=2)
        all_buttons=(1<<7)|(1<<1)|(1<<2)
        self.assertEqual(controller_buttons(vr,True,True,all_buttons,all_buttons),235)
        self.assertEqual(controller_buttons(vr,False,True,1<<1,1<<7),11)
        self.assertEqual(controller_buttons(vr,False,False,1<<2,1<<2),96)
        self.assertEqual(controller_buttons(vr,False,False,1<<7,1<<1),0)

    def test_asset_install_is_repeatable_updates_owned_assets_and_preserves_modified_files(self):
        with tempfile.TemporaryDirectory()as directory:
            base=Path(directory);source=base/'assets';source.mkdir();(source/'gun.mesh').write_bytes(b'first')
            versions=base/'versions';v=versions/'version-test';v.mkdir(parents=True);(v/'RobloxPlayerBeta.exe').touch()
            target=v/'content/HexagonVRWeapons/gun.mesh'
            install_assets(source,versions);install_assets(source,versions);self.assertEqual(target.read_bytes(),b'first')
            (source/'gun.mesh').write_bytes(b'second');install_assets(source,versions);self.assertEqual(target.read_bytes(),b'second')
            target.write_bytes(b'user edit')
            with self.assertRaises(RuntimeError):install_assets(source,versions)

    def test_reinstall_replaces_weapon_modules_without_duplicates(self):
        with tempfile.TemporaryDirectory()as directory:
            a,b,c=[Path(directory)/name for name in ('a.rbxlx','b.rbxlx','c.rbxlx')]
            make_demo(a);install(a,b,'','');install(b,c,'','')
            tree=ET.parse(c)
            for name in ('VRWeapons','VRHats','VRWeaponAssets','VRWeaponState','VRWeaponClient','VRWeaponFX','HexagonVRWeaponGeometry'):
                self.assertEqual(len(tree.findall('.//Item/Properties/string[@name="Name"][.="'+name+'"]')),2 if name=='VRWeaponAssets'else 1)

if __name__=='__main__':unittest.main()
