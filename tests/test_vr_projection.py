import sys,unittest,math
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from bridge import projection_plan,Tracker,State,serve
import numpy as np
import urllib.request,urllib.error,json,time

class Tests(unittest.TestCase):
    def test_quest_rays_preserved_at_all_aspects(self):
        frusta=[(-1.2799415588,.9004040360,-1.1917536259,1.1106126308),(-.9004040360,1.2799415588,-1.1917536259,1.1106126308)]
        for aspect in (1,721/455,16/9,2):
            fov,eyes=projection_plan(frusta,aspect)
            ty=math.tan(math.radians(fov/2));tx=ty*aspect
            for raw,b in zip(frusta,eyes):
                for uv in b:self.assertGreaterEqual(uv,0);self.assertLessEqual(uv,1)
                recovered=((b[0]*2-1)*tx,(b[2]*2-1)*tx,(b[1]*2-1)*ty,(b[3]*2-1)*ty)
                np.testing.assert_allclose(recovered,raw,atol=1e-12)
    def test_room_calibration(self):
        t=Tracker(3);h=np.eye(4);h[:3,3]=(12,1.7,-9)
        left=h.copy();left[:3,3]+=( -.4,-.3,-.2)
        p=t.convert(h,left)
        np.testing.assert_allclose(p['head'][:3],(0,1.5,0),atol=1e-10)
        np.testing.assert_allclose(p['left'][:3],(-1.2,.6,-.6),atol=1e-10)
        h[0,3]+=.1;p=t.convert(h);self.assertAlmostEqual(p['head'][0],.3)
    def test_snap_turn_requires_release(self):
        t=Tracker();h=np.eye(4)
        self.assertEqual(t.convert(h,turn_axis=1)['turn'],1)
        self.assertEqual(t.convert(h,turn_axis=1)['turn'],1)
        t.convert(h,turn_axis=0)
        self.assertEqual(t.convert(h,turn_axis=-1)['turn'],0)
    def test_relay_auth_and_freshness(self):
        s=State('test-key');http=serve(s,'127.0.0.1',0)
        url='http://127.0.0.1:'+str(http.server_port)+'/pose'
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(url)
            self.assertEqual(error.exception.code,403)
            packet=Tracker().convert(np.eye(4))
            req=urllib.request.Request(url+'?key=test-key',json.dumps(packet).encode(),{'Content-Type':'application/json'})
            with urllib.request.urlopen(req) as r:self.assertTrue(json.load(r)['ok'])
            with urllib.request.urlopen(url+'?key=test-key') as r:self.assertTrue(json.load(r)['tracked'])
            s.updated-=1
            self.assertFalse(s.read()['tracked'])
        finally:http.shutdown();http.server_close()

if __name__ == "__main__":
    unittest.main()
