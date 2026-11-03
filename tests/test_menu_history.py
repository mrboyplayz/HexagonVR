from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
from test_multiplayer import FIXTURE

ROOT = Path(__file__).resolve().parents[1]
GUI = r'''
Vector2={new=function(x,y)return{x=x or 0,y=y or 0}end}
Color3={new=function(...)return{...}end}
UDim2={new=function(...)return{...}end};Rect={new=function(...)return{...}end}
Enum=setmetatable({},{__index=function(t,k)local v=setmetatable({},{__index=function(_,n)return n end});rawset(t,k,v);return v end})
local create=Instance.new
Instance.new=function(kind)
 local o=create(kind);o.Changed=event();o.TextBounds=Vector2.new(800,300);o.CanvasPosition=Vector2.new()
 function o:WaitForChild(name)return assert(self:FindFirstChild(name),name)end
 function o:FireServer(...)self.messages[#self.messages+1]={...}end
 return o
end
Players.ChildAdded=event();Players.ChildRemoved=event();game.Players=Players
gui=Instance.new('PlayerGui');gui.Parent=A
function A:WaitForChild(name)return assert(self:FindFirstChild(name),name)end
script=Instance.new('ModuleScript');local assets=Instance.new('ModuleScript');assets.Name='VRMenuAssets';assets.Parent=script
require=function()return{}end
box=Instance.new('Folder');remote=Instance.new('RemoteEvent')
for _,name in ipairs({'ui','ui_out'})do local v=Instance.new('Vector3Value');v.Name=name;v.Value=Vector3.new();v.Parent=box end
function hasText(value)
 local function walk(node)
  for _,child in ipairs(node:GetChildren())do if child.Text==value or walk(child)then return true end end
  return false
 end
 return walk(gui)
end
'''


class MenuHistoryTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute(FIXTURE + GUI)
        self.lua.globals().module = self.lua.execute((ROOT / 'roblox/VRMenu.lua').read_text(encoding='utf8'))
        self.lua.execute('menu=module.new(A,box,remote)')

    def test_all_received_history_survives_menu_recreation(self):
        self.lua.execute("for i=1,150 do menu:addMessage(A,'message '..i)end;assert(#menu.messages==150);local nextMenu=module.new(A,box,remote);assert(#nextMenu.messages==150);assert(nextMenu.messages[1]=='Alpha: message 1' and nextMenu.messages[150]=='Alpha: message 150')")

    def test_late_join_chat_arrives_immediately_and_disconnect_cleans_up(self):
        self.lua.execute("local c=player('Charlie',303);Players.ChildAdded:Fire(c);c.Chatted:Fire('hello');assert(menu.messages[1]=='Charlie: hello');Players.ChildRemoved:Fire(c);c.Chatted:Fire('gone');assert(#menu.messages==1)")

    def test_private_messages_for_other_players_are_not_added(self):
        self.lua.execute("local c=player('Charlie',303);Players.ChildAdded:Fire(c);B.Chatted:Fire('secret',c);assert(#menu.messages==0);B.Chatted:Fire('for you',A);assert(#menu.messages==1)")

    def test_long_message_scroll_and_oldest_and_latest_are_reachable(self):
        self.lua.execute("for i=1,80 do menu:addMessage(A,'message '..i)end;menu.page='chat';menu.opened=true;menu:draw(math.huge);assert(menu.chatView.CanvasPosition.y==menu.chatMaximum);menu:scrollChat(1);assert(menu.chatView.CanvasPosition.y<menu.chatMaximum);for i=1,200 do menu:scrollChat(1)end;assert(menu.scroll==74 and menu.chatView.CanvasPosition.y==0);for i=1,200 do menu:scrollChat(-1)end;assert(menu.scroll==0 and menu.chatView.CanvasPosition.y==menu.chatMaximum)")

    def test_incoming_messages_preserve_older_page_and_latest_follows(self):
        self.lua.execute("for i=1,80 do menu:addMessage(A,'message '..i)end;menu.opened=true;menu.page='chat';menu.scroll=10;menu:draw(0);menu:addMessage(B,'new');assert(menu.scroll==11 and menu.chatView.CanvasPosition.y==0);menu.scroll=0;menu:draw(math.huge);menu:addMessage(B,'newer');assert(menu.scroll==0 and menu.chatView.CanvasPosition.y==menu.chatMaximum)")

    def test_text_layout_updates_do_not_snap_manual_scrolling_back_to_latest(self):
        self.lua.execute("for i=1,10 do menu:addMessage(A,'message '..i)end;menu.page='chat';menu:draw(math.huge);menu.chatView.CanvasPosition=Vector2.new(0,0);menu.chatView:GetChildren()[1].Changed:Fire('TextBounds');assert(menu.chatView.CanvasPosition.y==0);menu:scrollChat(1);assert(menu.scroll==1)")

    def test_player_pagination_clamps_after_departures_and_updates_for_joins(self):
        self.lua.execute("for i=1,11 do player('Player'..i,400+i)end;menu.opened=true;menu.page='menu';menu:scrollPlayers(100);assert(menu.playerScroll==9);table.remove(Players.players);Players.ChildRemoved:Fire(B);assert(menu.playerScroll==8);local c=player('Zed',500);Players.ChildAdded:Fire(c);menu:scrollPlayers(4);assert(menu.playerScroll==9);menu:scrollPlayers(-100);assert(menu.playerScroll==0)")

    def test_enter_uses_remote_without_desktop_input_and_keeps_draft_until_receipt(self):
        self.lua.execute("menu.draft='hello';menu:send();assert(#menu.queue==0 and #remote.messages==1 and remote.messages[1][1]=='chat');assert(menu.draft=='hello');menu:chatResult(menu.sending.id,true,'Sent.');assert(menu.draft=='' and menu.notice=='Sent.')")


if __name__ == '__main__':
    unittest.main()
