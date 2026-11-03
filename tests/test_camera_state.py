import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from client_transport import LocalTransport,SENTINELS


class CameraStateTests(unittest.TestCase):
    def transport(self,values):
        t=LocalTransport.__new__(LocalTransport)
        t.sequence=101;t.last_ack_sequence=100;t.acks=list(values);t.camera_state_cells=list(values)
        t.vec=values.get
        return t

    def test_fresh_camera_disabled_state_wins_over_stale_enabled_copy(self):
        t=self.transport({1:(100.,1.,82003.5),2:(101.,0.,82003.5)})
        self.assertFalse(t.camera_enabled())

    def test_future_sequences_and_wrong_markers_do_not_enable_camera(self):
        t=self.transport({1:(102.,1.,82003.5),2:(101.,1.,0.)})
        self.assertFalse(t.camera_enabled())

    def test_legacy_support_has_no_explicit_camera_state(self):
        t=self.transport({});self.assertIsNone(t.camera_enabled())

    def test_new_render_ack_is_used_before_the_next_push_updates_cached_ack(self):
        t=self.transport({1:(100.,*SENTINELS['ack'][1:]),2:(101.,*SENTINELS['ack'][1:])})
        self.assertEqual(t.active_ack_address(),2)


if __name__=='__main__':unittest.main()
