import sys,struct,unittest
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from vr_actions import Actions,NativeChat,ChatFocusError
from unittest.mock import patch

class Backend:
    def __init__(self):self.messages=[];self.closed=[]
    def send(self,*args):self.messages.append(args)
    def leave(self,*args):self.closed.append(args)

class Tests(unittest.TestCase):
    def test_shortcuts_use_hardware_scan_codes_and_unicode_stays_unicode(self):
        import ctypes as C
        sender=NativeChat();events=[]
        class User:
            def MapVirtualKeyW(self,vk,mode):return 0x35 if vk==0xBF else 0xE01D
            def SendInput(self,count,pointer,size):
                key=C.cast(pointer,C.POINTER(sender.I)).contents.data.keyboard
                events.append((key.vk,key.scan,key.flags));return 1
        sender.u=User()
        sender.key(0xBF);sender.key(0xBF,up=True);sender.key(0xA3);sender.key(scan=ord('x'),unicode=True)
        self.assertEqual(events,[(0,0x35,8),(0,0x35,10),(0,0x1D,9),(0,ord('x'),4)])
    def test_keyboard_packets_once_and_no_partial_send(self):
        b=Backend();a=Actions(b)
        a.receive(6,0,0,10,20);a.receive(7,0,0,10,20)
        self.assertEqual(b.messages,[])
        message='Hello world /vr!'
        a.receive(5,0,0,10,20)
        data=message.encode()
        for i in range(0,len(data),6):
            packet=data[i:i+6].ljust(6,b'\0')
            a.receive(6,int.from_bytes(packet[:3],'little'),int.from_bytes(packet[3:],'little'),10,20)
        a.receive(7,0,0,10,20);a.receive(7,0,0,10,20);a.jobs.join()
        self.assertEqual(b.messages,[(10,20,message)])
        self.assertEqual(a.receive(4,0,0,10,20),'leave');self.assertEqual(b.closed,[(10,20)])
    def test_wrong_foreground_never_types(self):
        sender=NativeChat();events=[]
        class User:
            def IsIconic(self,*args):return False
            def SetForegroundWindow(self,*args):pass
            def ShowWindow(self,*args):pass
        sender.u=User();sender.window_for=lambda pid:10;sender.is_target=lambda hwnd,pid:False;sender.key=lambda *a,**kw:events.append(a)
        with self.assertRaises(RuntimeError):sender.send(10,20,'hello')
        self.assertEqual(events,[])
    def test_changing_focus_does_not_press_enter(self):
        sender=NativeChat();events=[]
        class User:
            def IsIconic(self,*args):return False
            def SetForegroundWindow(self,*args):pass
            def ShowWindow(self,*args):pass
        sender.u=User();sender.window_for=lambda pid:10;checks=iter([True,True,False]);sender.is_target=lambda *a:next(checks)
        sender.key=lambda *a,**kw:events.append((a,kw))
        with self.assertRaises(RuntimeError):sender.send(10,20,'hello')
        self.assertFalse(any(args==(13,)for args,kw in events))
    def test_control_characters_cannot_inject_key_commands(self):
        b=Backend();a=Actions(b);a.receive(5,0,0,10,20)
        data=b'a\r\nb\x00\x00'
        a.receive(6,int.from_bytes(data[:3],'little'),int.from_bytes(data[3:],'little'),10,20)
        a.receive(7,0,0,10,20);a.jobs.join();self.assertEqual(b.messages,[])
    def test_send_refreshes_the_game_window_and_waits_for_chat_focus(self):
        sender=NativeChat();events=[];windows=[]
        class User:
            def IsIconic(self,*args):return False
            def ShowWindow(self,hwnd,*args):windows.append(hwnd)
            def SetForegroundWindow(self,hwnd):windows.append(hwnd)
        sender.u=User();sender.window_for=lambda pid:30;sender.is_target=lambda *args:True
        sender.key=lambda *args,**kw:events.append((args,kw))
        focused=iter([False,False,True])
        sender.send(10,20,'x',focus_check=lambda pid:next(focused))
        self.assertEqual(windows,[30])
        self.assertTrue(any(args==(13,)for args,kw in events))
    def test_protected_core_chat_focus_does_not_block_enter(self):
        sender=NativeChat();events=[]
        class User:
            def IsIconic(self,*args):return False
            def ShowWindow(self,*args):pass
            def SetForegroundWindow(self,*args):pass
        sender.u=User();sender.window_for=lambda pid:10;sender.is_target=lambda *args:True
        sender.key=lambda *args,**kw:events.append((args,kw))
        with patch('vr_actions.time.monotonic',side_effect=[0,0,3]):sender.send(10,20,'x',focus_check=lambda pid:False)
        self.assertTrue(any(kw.get('unicode')for args,kw in events))
        self.assertTrue(any(args==(13,)for args,kw in events))
    def test_failed_send_returns_feedback_to_only_the_requesting_game(self):
        class Fail(Backend):
            def send(self,*args):raise RuntimeError('Cannot focus game')
        actions=Actions(Fail());token=100*16+5
        actions.receive(5,0,0,10,20,token=token);actions.receive(6,int.from_bytes(b'hi','little'),0,10,20);actions.receive(7,0,0,10,20);actions.jobs.join()
        self.assertEqual(actions.poll_result(20),(token,2))
        self.assertIsNone(actions.poll_result(20))

if __name__=='__main__':unittest.main()
