from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from client_transport import LocalTransport
from vr_actions import Actions


class UIOrderingTests(unittest.TestCase):
    def transport(self,values,last=0):
        t=LocalTransport.__new__(LocalTransport);t.ui_outputs=list(values);t.vec=values.get;t.ui_token=last;return t

    def test_old_begin_copy_does_not_reset_a_message_before_enter(self):
        begin=100*16+5;data=101*16+6;end=102*16+7
        values={1:(float(begin),0.,0.)};t=self.transport(values)
        class Backend:
            def __init__(self):self.messages=[]
            def send(self,*args):self.messages.append(args)
        backend=Backend();actions=Actions(backend)
        actions.receive(*t.ui_command(),10,20)
        t.ui_outputs.append(2);values[2]=(float(data),float(int.from_bytes(b'hey','little')),0.)
        actions.receive(*t.ui_command(),10,20)
        self.assertIsNone(t.ui_command())
        values[2]=(float(end),0.,0.)
        actions.receive(*t.ui_command(),10,20);actions.jobs.join()
        self.assertEqual(backend.messages,[(10,20,'hey')])
        self.assertIsNone(t.ui_command())

    def test_wrap_is_forward_and_stale_pre_wrap_commands_are_ignored(self):
        last=999999*16+6;values={1:(float(last),0.,0.),2:(float(16+7),0.,0.)};t=self.transport(values,last)
        self.assertEqual(t.ui_command(),(7,0,0));self.assertIsNone(t.ui_command())

    def test_serial_zero_is_not_a_command(self):
        self.assertIsNone(self.transport({1:(6.,0.,0.)}).ui_command())


if __name__=='__main__':unittest.main()
