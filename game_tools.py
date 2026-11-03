"""Install the Lua kit into a copy of an XML place; never overwrite the input."""
from pathlib import Path
import json, uuid, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent

def item(kind, name, parent):
    node=ET.SubElement(parent,'Item',{'class':kind,'referent':'RBX'+uuid.uuid4().hex})
    props=ET.SubElement(node,'Properties');ET.SubElement(props,'string',{'name':'Name'}).text=name
    return node

def prop(node, tag, name, value):
    props=node.find('Properties')
    old=props.find('*[@name="'+name+'"]')
    if old is not None: props.remove(old)
    p=ET.SubElement(props,tag,{'name':name});p.text=str(value)
    return p

def service(tree, kind):
    found=next((x for x in tree.findall('Item') if x.get('class')==kind),None)
    return found if found is not None else item(kind,kind,tree)

def install(source, target, url, key, user_id=0, local_fast_poll=False):
    source,target=Path(source),Path(target)
    if source.resolve()==target.resolve(): raise ValueError('Choose a new output path.')
    tree=ET.parse(source).getroot()
    if tree.tag!='roblox': raise ValueError('Input must be an XML .rbxlx place.')
    ss=service(tree,'ServerScriptService'); sg=service(tree,'StarterGui')
    for parent,names in [(ss,('HexagonVRServer','VRConfig')),(sg,('HexagonVRClient',))]:
        for child in list(parent.findall('Item')):
            if child.findtext('./Properties/string[@name="Name"]') in names: parent.remove(child)
    cfg=(ROOT/'roblox/VRConfig.lua').read_text()
    cfg=cfg.replace('http://127.0.0.1:18765',url).replace('CHANGE_ME',key)
    if user_id:cfg=cfg.replace('AllowedUserIds = {},','AllowedUserIds = {'+str(int(user_id))+'},')
    if local_fast_poll:cfg=cfg.replace('PollRate = 6,','PollRate = 30,')
    for parent,kind,name,text in [(ss,'ModuleScript','VRConfig',cfg),(ss,'Script','HexagonVRServer',(ROOT/'roblox/VRServer.lua').read_text()),(sg,'LocalScript','HexagonVRClient',(ROOT/'roblox/VRClient.lua').read_text())]:
        node=item(kind,name,parent);prop(node,'ProtectedString','Source',text)
        if kind!='ModuleScript': prop(node,'bool','Disabled','false')
        if kind=='LocalScript':
            module=item('ModuleScript','VRMenu',node)
            prop(module,'ProtectedString','Source',(ROOT/'roblox/VRMenu.lua').read_text())
            texture_module=item('ModuleScript','VRMenuAssets',module)
            prop(texture_module,'ProtectedString','Source',(ROOT/'roblox/VRMenuAssets.lua').read_text())
    target.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(tree).write(target,encoding='utf-8',xml_declaration=True)
    return target

def make_demo(target):
    tree=ET.Element('roblox',{'version':'4'})
    ET.SubElement(tree,'External').text='null';ET.SubElement(tree,'External').text='nil'
    ws=service(tree,'Workspace')
    def part(name,pos,size,color):
        node=item('Part',name,ws);prop(node,'bool','Anchored','true')
        prop(node,'token','TopSurface','0');prop(node,'token','BottomSurface','0')
        for name_,v in [('size',size)]:
            p=prop(node,'Vector3',name_,'')
            for k,val in zip('XYZ',v):ET.SubElement(p,k).text=str(val)
        p=prop(node,'CoordinateFrame','CFrame','')
        for k,val in zip(('X','Y','Z','R00','R01','R02','R10','R11','R12','R20','R21','R22'),(*pos,1,0,0,0,1,0,0,0,1)):ET.SubElement(p,k).text=str(val)
        p=prop(node,'Color3','Color','')
        for k,val in zip('rgb',color):ET.SubElement(p,k).text=str(val)
        return node
    part('Baseplate',(0,-.5,0),(120,1,120),(.23,.26,.30))
    for i in range(5):part('DepthMarker'+str(i),(-8+i*4,2,-10-i*6),(2,4,2),(.2,.5+i*.08,.9))
    part('LeftWall',(-16,3,-10),(1,6,28),(.9,.35,.22))
    part('RightWall',(16,3,-10),(1,6,28),(.25,.8,.45))
    service(tree,'Players');service(tree,'ReplicatedStorage');service(tree,'ServerScriptService');service(tree,'StarterGui')
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(tree).write(target,encoding='utf-8',xml_declaration=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('target');p.add_argument('--url',default='http://127.0.0.1:18765');p.add_argument('--key',required=True);p.add_argument('--user-id',type=int,default=0)
    a=p.parse_args();print(install(a.source,a.target,a.url,a.key,a.user_id))
