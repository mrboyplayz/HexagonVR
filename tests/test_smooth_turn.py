from pathlib import Path
import math,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bridge import turn_command

class SmoothTurnTests(unittest.TestCase):
    def test_hold_is_a_continuous_rate_not_a_single_snap(self):
        angle=0
        for _ in range(90):angle+=65*turn_command(-1)/90
        self.assertAlmostEqual(angle,-65)
        self.assertEqual(turn_command(-1),turn_command(-1))
    def test_small_input_is_slower_and_noise_does_not_turn(self):
        self.assertEqual(turn_command(.1),0)
        self.assertAlmostEqual(turn_command(.6),.5)
        self.assertEqual(turn_command(float('nan')),0)
        self.assertEqual(turn_command(float('inf')),0)
        self.assertEqual(turn_command(20),1)

if __name__=='__main__':unittest.main()
