"""Persistent helper preferences and the compact turn-control mailbox field."""
from pathlib import Path
import json,math

def turn_speed(value):
    if isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value):return 65
    return max(15,min(180,int(round(value))))

def encode_turn(axis,speed):
    axis=float(axis)if isinstance(axis,(int,float))and math.isfinite(axis)else 0.
    return turn_speed(speed)*4+max(-1.,min(1.,axis))+1

def load_settings(path):
    try:
        data=json.loads(Path(path).read_text())
        return data if isinstance(data,dict)else{}
    except (OSError,ValueError):return{}

def save_setting(path,name,value):
    path=Path(path);settings=load_settings(path);settings[name]=value
    temporary=path.with_name(path.name+'.tmp');temporary.write_text(json.dumps(settings,indent=2)+'\n');temporary.replace(path)
