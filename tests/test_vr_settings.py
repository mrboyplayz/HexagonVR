from pathlib import Path
import json,math,struct,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vr_settings import turn_speed,encode_turn,load_settings,save_setting
from bridge import stable_grip,_GRIP_STATES,tracked_hand,_HAND_POSES
import numpy as np

class VRSettingsTests(unittest.TestCase):
    def test_turn_speed_bounds_and_invalid_preferences(self):
        self.assertEqual(turn_speed(-50),15)
        self.assertEqual(turn_speed(250),180)
        self.assertEqual(turn_speed(75.2),75)
        for value in (None,True,'fast',math.nan,math.inf):self.assertEqual(turn_speed(value),65)

    def test_mailbox_float32_preserves_speed_and_proportional_axis(self):
        for speed in (15,65,75,180):
            for axis in (-1,-.75,-.1,0,.1,.75,1):
                packed=struct.unpack('<f',struct.pack('<f',encode_turn(axis,speed)))[0]
                decoded=math.floor(packed/4)
                self.assertEqual(decoded,speed)
                self.assertAlmostEqual(packed-decoded*4-1,axis,places=4)

    def test_persistence_preserves_other_settings_and_recovers_bad_json(self):
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'vr-settings.json';path.write_text(json.dumps({'arm_forward':.3}))
            save_setting(path,'turn_speed',95)
            self.assertEqual(load_settings(path),{'arm_forward':.3,'turn_speed':95})
            self.assertFalse(path.with_name(path.name+'.tmp').exists())
            path.write_text('[');save_setting(path,'turn_speed',85)
            self.assertEqual(load_settings(path),{'turn_speed':85})

class GripStabilityTests(unittest.TestCase):
    def setUp(self):_GRIP_STATES.clear();_HAND_POSES.clear()
    def tearDown(self):_GRIP_STATES.clear();_HAND_POSES.clear()

    def test_brief_tracking_loss_holds_pose_then_expires_without_crossing_hands(self):
        pose=np.eye(4);pose[0,3]=1
        tracked_hand('left',pose,0)
        self.assertTrue(np.array_equal(tracked_hand('left',None,.06),pose))
        self.assertIsNone(tracked_hand('right',None,.06))
        self.assertIsNone(tracked_hand('left',None,.08))

    def test_brief_dropout_keeps_hold_but_deliberate_release_drops(self):
        self.assertTrue(stable_grip('left',True,0))
        self.assertTrue(stable_grip('left',False,.01))
        self.assertTrue(stable_grip('left',False,.04))
        self.assertTrue(stable_grip('left',True,.045))
        self.assertTrue(stable_grip('left',False,.1))
        self.assertFalse(stable_grip('left',False,.16))

    def test_each_controller_has_independent_hold_state(self):
        self.assertTrue(stable_grip('left',True,0))
        self.assertFalse(stable_grip('right',False,.02))
        self.assertTrue(stable_grip('right',True,.03))
        self.assertTrue(stable_grip('left',False,.04))
        self.assertFalse(stable_grip('left',False,.10))
        self.assertTrue(stable_grip('right',True,.10))

if __name__=='__main__':unittest.main()
