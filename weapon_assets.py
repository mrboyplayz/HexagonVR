"""Install this kit's bundled Marketplace assets in installed Hexagon clients."""
from pathlib import Path
import hashlib, json, os, shutil, sys

def install_assets(source=None, versions=None):
    source=Path(source or Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'assets')
    versions=Path(versions or Path(os.environ['LOCALAPPDATA'])/'Hexagon/Versions')
    if not source.is_dir():return []
    installed=[]
    for version in versions.glob('version-*'):
        if not any((version/name).is_file()for name in ('RobloxPlayerBeta.exe','RobloxStudioBeta.exe')):continue
        destination=version/'content/HexagonVRWeapons'
        destination.mkdir(parents=True,exist_ok=True)
        manifest_path=destination/'installed-assets.json'
        previous=json.loads(manifest_path.read_text())if manifest_path.exists()else{}
        current={}
        for asset in source.iterdir():
            if asset.suffix not in ('.mesh','.png','.mp3'):continue
            target=destination/asset.name
            digest=hashlib.sha256(asset.read_bytes()).hexdigest();current[asset.name]=digest
            if target.exists():
                actual=hashlib.sha256(target.read_bytes()).hexdigest()
                if actual!=digest:
                    if previous.get(asset.name)!=actual:raise RuntimeError('An existing weapon asset differs: '+str(target))
                    shutil.copyfile(asset,target)
            else:shutil.copyfile(asset,target)
        manifest_path.write_text(json.dumps(current,indent=2))
        installed.append(destination)
    return installed

if __name__=='__main__':
    for path in install_assets():print(path)
