The native graphics module uses [MinHook](https://github.com/TsudaKageyu/minhook), pinned to the revision in `vendor/minhook/UPSTREAM.md`. Its BSD license is included as MINHOOK-LICENSE.txt.

Native binaries are compiled with [LLVM-MinGW](https://github.com/mstorsjo/llvm-mingw). The compiler archive URL and SHA-256 are pinned in `native/toolchain.json`. The LLVM Apache license with LLVM exceptions is included as LLVM-LICENSE.txt. The compiler itself is downloaded into the ignored build directory and is not included in the runtime package.

SteamVR access uses the OpenVR Python dependency. The injected graphics module does not initialize SteamVR or include a separate OpenVR runtime. Python dependency notices are bundled by PyInstaller with their packages.
