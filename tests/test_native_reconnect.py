import sys,mmap,os,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_renderer import attach,renderer_active

@unittest.skipUnless(os.name=='nt','Windows shared mapping')
class NativeReconnectTests(unittest.TestCase):
 def test_running_renderer_does_not_launch_an_attach_executable(self):
  pid=1000000000+os.getpid()
  with mmap.mmap(-1,3448,tagname='Local\\HexagonVR.Native.Frame.'+str(pid)):
   self.assertTrue(renderer_active(pid))
   with patch('native_renderer.subprocess.run',side_effect=AssertionError('Redundant attach executable launched')):
    attach(pid,Path('missing-native-tools'))
  self.assertFalse(renderer_active(pid))

if __name__=='__main__':unittest.main()
