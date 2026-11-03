from pathlib import Path
import sys
import unittest
from lupa.lua51 import LuaRuntime
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_multiplayer import FIXTURE

ROOT=Path(__file__).resolve().parents[1]


class InternalChatTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime();self.lua.execute(FIXTURE)
        self.lua.execute('''
        requests={};failFor=nil;active=true
        ChatService={FilterStringForPlayerAsync=function(_,text,recipient)
          requests[#requests+1]={text,recipient}
          if recipient==failFor then error('filter unavailable')end
          return 'filtered for '..recipient.Name
        end}
        local get=game.GetService
        game.GetService=function(self,name)if name=='Chat'then return ChatService end;return get(self,name)end
        remote=Instance.new('RemoteEvent');commands={}
        function send(player,id,text)remote.OnServerEvent:Fire(player,'chat',{id=id,text=text,author=B})end
        function displays(recipient)
          local rows={};for _,r in ipairs(remote.messages)do if r[1]==recipient and r[2]=='chatDisplay'then rows[#rows+1]=r end end;return rows
        end
        function result(player)
          for i=#remote.messages,1,-1 do local r=remote.messages[i];if r[1]==player and r[2]=='chatResult'then return r end end
        end
        ''')
        self.lua.globals().module=self.lua.execute((ROOT/'roblox/VRChat.lua').read_text())
        self.lua.execute("module.start(remote,{ChatInterval=1.5,ChatTimeout=12},function()return active end,function(p,text)commands[#commands+1]={p,text}end)")

    def test_each_recipient_gets_only_their_filtered_copy_and_real_author(self):
        self.lua.execute("send(A,1,'private input');assert(#displays(A)==1 and #displays(B)==1);assert(displays(A)[1][4]=='filtered for Alpha');assert(displays(B)[1][4]=='filtered for Bravo');assert(displays(B)[1][3]==A);assert(result(A)[4]==true)")

    def test_filter_failure_never_falls_back_to_raw_text(self):
        self.lua.execute("failFor=A;send(A,1,'private input');assert(#displays(A)==0 and #displays(B)==0);assert(result(A)[4]==false)")

    def test_one_recipient_failure_does_not_expose_unfiltered_text(self):
        self.lua.execute("failFor=B;send(A,1,'private input');assert(#displays(A)==1 and #displays(B)==0);assert(result(A)[4]==true)")

    def test_duplicate_request_does_not_send_twice(self):
        self.lua.execute("send(A,1,'hello');send(A,1,'hello');assert(#displays(A)==1 and #displays(B)==1)")

    def test_limits_and_private_chat_commands_do_not_broadcast(self):
        self.lua.execute("send(A,1,'/w Bravo secret');assert(#displays(B)==0 and result(A)[4]==false);send(A,2,string.rep('x',141));assert(result(A)[4]==false);send(A,3,'line'..string.char(10)..'line');assert(result(A)[4]==false)")

    def test_sender_rate_limit_is_independent_of_other_players(self):
        self.lua.execute("send(A,1,'one');send(A,2,'two');assert(result(A)[4]==false);send(B,1,'other');assert(result(B)[4]==true)")

    def test_vr_commands_are_internal_and_not_public_messages(self):
        self.lua.execute("send(A,1,'/unvr');assert(#commands==1 and commands[1][1]==A and commands[1][2]=='/unvr');assert(#displays(A)==0 and #displays(B)==0);assert(result(A)[4]==true)")

    def test_timed_out_filter_cannot_deliver_late(self):
        self.lua.execute("deferred={};spawn=function(f)deferred[#deferred+1]=f end;send(A,1,'one');time=20;Run.Stepped:Fire();assert(result(A)[4]==false);deferred[1]();assert(#displays(A)==0 and #displays(B)==0);time=22;send(A,2,'two');assert(#deferred==2)")

    def test_hung_filter_does_not_permanently_block_the_senders_keyboard(self):
        self.lua.execute("deferred={};spawn=function(f)deferred[#deferred+1]=f end;send(A,1,'one');time=20;Run.Stepped:Fire();send(A,2,'two');assert(#deferred==2);deferred[1]();assert(#displays(A)==0 and #displays(B)==0)")


if __name__=='__main__':unittest.main()
