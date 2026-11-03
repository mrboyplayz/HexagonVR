import sys,unittest
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from bridge import offset_hands
class Tests(unittest.TestCase):
    def test_forward_tracks_controller_aim(self):
        # Left points along -Z; right is turned 90 degrees and points along -X.
        pose={'left':[0,1,0,1,0,0,0,1,0,0,0,1],'right':[0,1,0,0,0,1,0,1,0,-1,0,0]}
        offset_hands(pose,.4,.3)
        self.assertEqual(pose['left'][:3],[-.4,1,-.3]);self.assertAlmostEqual(pose['right'][0],.1);self.assertEqual(pose['right'][1:3],[1,0])
    def test_missing_controller_is_supported(self):
        pose={'left':None,'right':None};offset_hands(pose,.4,.3);self.assertEqual(pose,{'left':None,'right':None})
if __name__ == "__main__":
    unittest.main()
