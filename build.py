"""Build the native modules, demo, and standalone Windows EXE."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,urllib.request,zipfile

ROOT=Path(__file__).resolve().parent
def run(*args):subprocess.run([str(x)for x in args],cwd=ROOT,check=True)
def toolchain(override):
    if override:
        path=Path(override).resolve()
        if not(path/'bin/i686-w64-mingw32-clang++.exe').is_file():raise RuntimeError('Expected an LLVM-MinGW toolchain directory')
        return path
    metadata=json.loads((ROOT/'native/toolchain.json').read_text())
    cache=ROOT/'build/toolchain';cache.mkdir(parents=True,exist_ok=True)
    archive=cache/metadata['name'];expected=metadata['digest'].removeprefix('sha256:')
    if not archive.exists():
        print('Downloading pinned LLVM-MinGW compiler...',flush=True)
        with urllib.request.urlopen(metadata['browser_download_url'],timeout=120)as source,archive.open('wb')as dest:
            while block:=source.read(1024*1024):dest.write(block)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise RuntimeError('Compiler SHA-256 mismatch; remove the incomplete archive and retry')
    path=cache/metadata['name'].removesuffix('.zip')
    if not(path/'bin/i686-w64-mingw32-clang++.exe').exists():
        with zipfile.ZipFile(archive)as z:
            for name in z.namelist():
                if not(cache/name).resolve().is_relative_to(cache.resolve()):raise RuntimeError('Unsafe compiler archive path')
            z.extractall(cache)
    return path
def native_build(compiler,out=None):
    out=Path(out).resolve()if out else ROOT/'build/native';out.mkdir(parents=True,exist_ok=True)
    x86=compiler/'bin/i686-w64-mingw32-clang++.exe';x64=compiler/'bin/x86_64-w64-mingw32-clang++.exe';cc=compiler/'bin/i686-w64-mingw32-clang.exe'
    include='-I'+str(ROOT/'vendor/minhook/include');objects=[]
    for source in ('hook.c','buffer.c','trampoline.c','hde/hde32.c'):
        path=ROOT/'vendor/minhook/src'/source;obj=out/(path.stem+'.o');run(cc,'-c','-O2',include,path,'-o',obj);objects.append(obj)
    run(x86,'-std=c++17','-O2','-static','-shared',include,ROOT/'native/render_probe.cpp',*objects,'-ld3d11','-ld3dcompiler','-ldxguid','-o',out/'HexagonVRNative.dll')
    run(x86,'-std=c++17','-O2','-static','-municode',ROOT/'native/studio_loader.cpp','-lbcrypt','-o',out/'HexagonVRStudioLoader.exe')
    run(x64,'-std=c++17','-O2','-static','-shared',ROOT/'native/texture_host.cpp','-ld3d11','-ldxguid','-o',out/'HexagonVRTextureHost64.dll')
    run(x64,'-std=c++17','-O2','-static',ROOT/'native/test_stereo_math.cpp','-o',out/'test_stereo_math.exe')
    run(out/'test_stereo_math.exe')
    return out
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--toolchain',type=Path);p.add_argument('--native-only',action='store_true');p.add_argument('--native-output',type=Path);args=p.parse_args()
    if os.name!='nt':p.error('Windows x64 is required')
    compiler=toolchain(args.toolchain);native=native_build(compiler,args.native_output)
    from game_tools import make_demo,install
    demo=ROOT/'build/VR-Demo.rbxlx';base=ROOT/'build/base.rbxlx';make_demo(base);install(base,demo,'','',0)
    if args.native_only:return
    run(sys.executable,'-m','PyInstaller','--noconfirm','--onefile','--hide-console','hide-early','--name','HexagonVR','--distpath',ROOT/'dist','--workpath',ROOT/'build/pyinstaller','--specpath',ROOT/'build',
        '--add-data',str(ROOT/'roblox')+';roblox','--add-data',str(demo)+';.',
        '--add-data',str(ROOT/'assets')+';assets',
        *sum((['--add-data',str(ROOT/'native'/name)+';native']for name in ('MINHOOK-LICENSE.txt','LLVM-LICENSE.txt','THIRD-PARTY.md')),[]),
        *sum((['--add-data',str(native/name)+';native']for name in ('HexagonVRNative.dll','HexagonVRStudioLoader.exe','HexagonVRTextureHost64.dll')),[]),
        '--collect-all','openvr','--collect-all','glfw','--collect-all','windows_capture',ROOT/'bridge.py')
    dist=ROOT/'dist'
    archive=dist/'HexagonVR-Windows.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        z.write(dist/'HexagonVR.exe','HexagonVR.exe');z.write(demo,'VR-Demo.rbxlx')
        for name in ('README.md','LICENSE'):z.write(ROOT/name,name)
        for asset in (ROOT/'assets').iterdir():z.write(asset,'assets/'+asset.name)
        for name in ('MINHOOK-LICENSE.txt','LLVM-LICENSE.txt','THIRD-PARTY.md'):z.write(ROOT/'native'/name,'licenses/'+name)
        z.writestr('Start-VR.cmd','@echo off\r\ncd /d "%~dp0"\r\nHexagonVR.exe\r\n')
        z.writestr('Start-Studio-Test.cmd','@echo off\r\ncd /d "%~dp0"\r\nHexagonVR.exe --studio-test\r\n')
        z.writestr('Install-Weapon-Assets.cmd','@echo off\r\ncd /d "%~dp0"\r\nHexagonVR.exe --install-assets\r\npause\r\n')
        z.writestr('Add-VR-To-Place.cmd','@echo off\r\ncd /d "%~dp0"\r\nif "%~1"=="" exit /b 1\r\nHexagonVR.exe --install "%~1"\r\npause\r\n')
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in (dist/'HexagonVR.exe',archive)}
    (dist/'SHA256SUMS.txt').write_text('\n'.join(value+'  '+name for name,value in manifest.items())+'\n')
    print('Release artifacts:',dist,flush=True)
if __name__=='__main__':main()
