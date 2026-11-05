import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vr_activity import VRActivity

class Backend:
    def __init__(self):self.calls=[]
    def notify(self,pid):self.calls.append(pid);return True

def pose(x=0,buttons=0):
    return {'tracked':True,'head':[x,1.5,0,1,0,0,0,1,0,0,0,1],'left':None,'right':None,'buttons':buttons,'move':[0,0],'turn':0}

class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.now=0.;self.backend=Backend();self.activity=VRActivity(self.backend,lambda:self.now)
    def test_twenty_five_minutes_of_real_motion_keeps_reporting_client_input(self):
        for n in range(3001):
            self.now=n*.5;self.activity.update(123,pose(math.sin(n*.1)*.2),True)
        self.assertEqual(len(self.backend.calls),51)
        self.assertEqual(set(self.backend.calls),{123})
    def test_static_tracking_noise_is_not_permanent_activity(self):
        for n in range(1201):
            self.now=n*.5;self.activity.update(123,pose(math.sin(n)*.001),True)
        self.assertLessEqual(len(self.backend.calls),2)
    def test_no_notifications_when_vr_camera_is_off_or_tracking_is_lost(self):
        for n in range(100):
            self.now=n*31;self.activity.update(123,pose(n),False)
            p=pose(n);p['tracked']=False;self.activity.update(123,p,True)
        self.assertEqual(self.backend.calls,[])
    def test_movement_and_firing_count_as_activity_without_head_motion(self):
        for n in range(60):
            self.now=n*31;p=pose();p['move']=[0,1]if n%2 else[0,0];p['buttons']=1 if n%2==0 else 0
            self.activity.update(123,p,True)
        self.assertEqual(len(self.backend.calls),60)
    def test_reconnect_uses_only_the_new_verified_client_pid(self):
        self.activity.update(123,pose(),True);self.activity.update(124,pose(),True)
        self.assertEqual(self.backend.calls,[123,124])
    def test_wrist_roll_counts_even_when_controller_aim_and_position_are_fixed(self):
        for n in range(5):
            self.now=n*31;p=pose();a=n*.1;c,s=math.cos(a),math.sin(a)
            p['right']=[0,1,0,c,-s,0,s,c,0,0,0,1];self.activity.update(123,p,True)
        self.assertEqual(len(self.backend.calls),5)

if __name__=='__main__':unittest.main()
