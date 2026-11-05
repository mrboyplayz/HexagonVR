import math,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_renderer import NativePresenter,MAP_SIZE
from client_transport import LocalTransport

class ScopeProtocolTests(unittest.TestCase):
    def test_native_scope_uses_world_pose_without_overwriting_eye_pose_history(self):
        presenter=object.__new__(NativePresenter);presenter.map=bytearray([126])*MAP_SIZE
        presenter.set_scope({'frame':[7,8,9,0,0,1,0,1,0,-1,0,0],'radius':.105,'zoom':4,'length':1.32})
        self.assertEqual(presenter.map[:3448],bytearray([126])*3448)
        values=struct.unpack('<I12f3fII',presenter.map[3448:3520])
        self.assertEqual(values[0]%2,0);self.assertEqual(values[1:5],(0,0,1,7));self.assertEqual(values[5:9],(0,1,0,8));self.assertEqual(values[9:13],(-1,0,0,9));self.assertEqual(values[-2],1)
        self.assertAlmostEqual(values[14],4)
        presenter.set_scope(None);values=struct.unpack('<I12f3fII',presenter.map[3448:3520]);self.assertEqual(values[-2],0);self.assertEqual(values[0],4)
    def transport(self,state=(100,1,87003.5),params=(.105,4,1.32)):
        t=object.__new__(LocalTransport);t.cells={'scope_frame':1,'scope_params':2};t.scope_state_cells=[3];t.last_ack_sequence=100;t.sequence=101
        t.vec=lambda address:state if address==3 else params
        t.read=lambda address,size:struct.pack('<12f',1,0,0,0,1,0,0,0,1,7,8,9)
        return t
    def test_scope_output_preserves_cframe_rotation_and_translation(self):
        scope=self.transport().scope();self.assertEqual(scope['frame'],[7,8,9,1,0,0,0,1,0,0,0,1]);self.assertEqual(scope['zoom'],4)
    def test_stale_and_inactive_scope_outputs_are_ignored(self):
        self.assertIsNone(self.transport((90,1,87003.5)).scope());self.assertIsNone(self.transport((100,0,87003.5)).scope())
    def test_invalid_scope_parameters_are_not_sent_to_the_renderer(self):
        self.assertIsNone(self.transport(params=(.1,math.nan,1)).scope());self.assertIsNone(self.transport(params=(.1,99,1)).scope())
    def test_games_without_scope_output_remain_supported(self):
        t=self.transport();t.cells={};self.assertIsNone(t.scope())

if __name__=='__main__':unittest.main()
