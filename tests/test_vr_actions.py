import sys,struct,unittest
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from vr_actions import Actions,NativeChat

class Backend:
    def __init__(self):self.messages=[];self.closed=[]
    def send(self,*args):self.messages.append(args)
    def leave(self,*args):self.closed.append(args)

class Tests(unittest.TestCase):
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
            def SetForegroundWindow(self,*args):pass
        sender.u=User();sender.is_target=lambda hwnd,pid:False;sender.key=lambda *a,**kw:events.append(a)
        with self.assertRaises(RuntimeError):sender.send(10,20,'hello')
        self.assertEqual(events,[])
    def test_changing_focus_does_not_press_enter(self):
        sender=NativeChat();events=[]
        class User:
            def SetForegroundWindow(self,*args):pass
        sender.u=User();checks=iter([True,True,False]);sender.is_target=lambda *a:next(checks)
        sender.key=lambda *a,**kw:events.append((a,kw))
        with self.assertRaises(RuntimeError):sender.send(10,20,'hello')
        self.assertFalse(any(args==(13,)for args,kw in events))
    def test_control_characters_cannot_inject_key_commands(self):
        b=Backend();a=Actions(b);a.receive(5,0,0,10,20)
        data=b'a\r\nb\x00\x00'
        a.receive(6,int.from_bytes(data[:3],'little'),int.from_bytes(data[3:],'little'),10,20)
        a.receive(7,0,0,10,20);a.jobs.join();self.assertEqual(b.messages,[])

if __name__=='__main__':unittest.main()
