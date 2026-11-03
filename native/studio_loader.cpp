// Loads a graphics test module into a fresh, hash-verified offline Studio only.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <string>
#include <vector>
#include <fstream>
#include <filesystem>
#include <sstream>
#include <iomanip>
#include <iostream>

static std::wstring absolute(const wchar_t* p){wchar_t out[32768];if(!GetFullPathNameW(p,32768,out,nullptr))throw std::runtime_error("Invalid path");return out;}
static std::string hashFile(const std::wstring& path){
    HANDLE file=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);
    if(file==INVALID_HANDLE_VALUE)throw std::runtime_error("Studio not found");
    BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0);BCryptCreateHash(alg,&hash,nullptr,0,nullptr,0,0);
    unsigned char buffer[65536],digest[32];DWORD n=0;
    while(ReadFile(file,buffer,sizeof(buffer),&n,nullptr)&&n)BCryptHashData(hash,buffer,n,0);
    BCryptFinishHash(hash,digest,32,0);BCryptDestroyHash(hash);BCryptCloseAlgorithmProvider(alg,0);CloseHandle(file);
    std::ostringstream out;for(auto x:digest)out<<std::hex<<std::setfill('0')<<std::setw(2)<<unsigned(x);return out.str();
}
static uintptr_t remoteLoadLibrary(DWORD pid){
    auto address=GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LoadLibraryW");HMODULE owner=nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(address),&owner);
    wchar_t path[MAX_PATH];GetModuleFileNameW(owner,path,MAX_PATH);std::wstring name(path);name=name.substr(name.find_last_of(L"\\/")+1);
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE,pid);MODULEENTRY32W e{};e.dwSize=sizeof(e);uintptr_t result=0;
    if(Module32FirstW(snapshot,&e))do{if(!_wcsicmp(e.szModule,name.c_str())){result=reinterpret_cast<uintptr_t>(e.modBaseAddr)+(reinterpret_cast<uintptr_t>(address)-reinterpret_cast<uintptr_t>(owner));break;}}while(Module32NextW(snapshot,&e));
    CloseHandle(snapshot);return result;
}
static void inject(HANDLE process,DWORD pid,const std::wstring& dll){
    SIZE_T size=(dll.size()+1)*sizeof(wchar_t);void* remote=VirtualAllocEx(process,nullptr,size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    SIZE_T written=0;if(!remote||!WriteProcessMemory(process,remote,dll.c_str(),size,&written)||written!=size)throw std::runtime_error("Could not stage native module path");
    uintptr_t load=0;DWORD started=GetTickCount();
    while(!load&&GetTickCount()-started<5000){
        if(WaitForSingleObject(process,0)!=WAIT_TIMEOUT)throw std::runtime_error("The isolated Studio process exited during startup");
        load=remoteLoadLibrary(pid);if(!load)Sleep(10);
    }
    if(!load)throw std::runtime_error("Could not resolve the target loader");
    HANDLE thread=CreateRemoteThread(process,nullptr,0,reinterpret_cast<LPTHREAD_START_ROUTINE>(load),remote,0,nullptr);
    if(!thread||WaitForSingleObject(thread,15000)!=WAIT_OBJECT_0)throw std::runtime_error("Native module loading timed out");
    DWORD result=0;GetExitCodeThread(thread,&result);CloseHandle(thread);VirtualFreeEx(process,remote,0,MEM_RELEASE);
    if(!result)throw std::runtime_error("The native graphics module did not load");
}
static int attachExisting(DWORD pid,const std::wstring& dll){
    HANDLE process=OpenProcess(SYNCHRONIZE|PROCESS_CREATE_THREAD|PROCESS_QUERY_INFORMATION|PROCESS_VM_OPERATION|PROCESS_VM_WRITE|PROCESS_VM_READ,FALSE,pid);
    if(!process)throw std::runtime_error("Could not open the supported game process");
    HANDLE event=nullptr;
    try{
        wchar_t path[32768];DWORD size=32768;if(!QueryFullProcessImageNameW(process,0,path,&size))throw std::runtime_error("Could not verify the target game");
        auto digest=hashFile(path);
        if(digest!="432aa5e86c66275d1a27c4e5c6833c8a23ccc0d8e9114eef7c134ba2d6953b9d"&&digest!="007a6ab91703730b3f9635b0558ec0e87db92d3c84dbe649d2f42a2f7718271b")throw std::runtime_error("Unsupported executable; no module was loaded");
        std::wstring mapping=L"Local\\HexagonVR.Native.Frame."+std::to_wstring(pid);HANDLE existing=OpenFileMappingW(FILE_MAP_READ,FALSE,mapping.c_str());
        if(existing){CloseHandle(existing);CloseHandle(process);std::cout<<"Native renderer already active"<<std::endl;return 0;}
        std::wstring name=L"Local\\HexagonVR.Native.Ready."+std::to_wstring(pid);event=CreateEventW(nullptr,TRUE,FALSE,name.c_str());
        inject(process,pid,dll);
        if(WaitForSingleObject(event,15000)!=WAIT_OBJECT_0)throw std::runtime_error("Native renderer did not initialize");
        CloseHandle(event);CloseHandle(process);std::cout<<"Native renderer connected"<<std::endl;return 0;
    }catch(...){if(event)CloseHandle(event);CloseHandle(process);throw;}
}
int wmain(int argc,wchar_t** argv){
    if(argc==4&&std::wstring(argv[1])==L"--attach"){
        try{return attachExisting(DWORD(std::stoul(argv[2])),absolute(argv[3]));}
        catch(const std::exception& error){std::cerr<<error.what()<<std::endl;return 1;}
    }
    if(argc!=5){std::cerr<<"Usage: studio_loader STUDIO_EXE GRAPHICS_DLL STARTUP_SCRIPT PID_FILE\n";return 2;}
    PROCESS_INFORMATION pi{};HANDLE job=nullptr,event=nullptr;
    try{
        std::wstring exe=absolute(argv[1]),dll=absolute(argv[2]),scriptFile=absolute(argv[3]),pidFile=absolute(argv[4]);
        if(hashFile(exe)!="007a6ab91703730b3f9635b0558ec0e87db92d3c84dbe649d2f42a2f7718271b")throw std::runtime_error("Only the verified 2015 Studio test executable is supported");
        std::ifstream in{std::filesystem::path(scriptFile)};std::string code((std::istreambuf_iterator<char>(in)),{});
        if(code.empty()||code.find("game:Load('rbxasset://HexagonVR/")!=0)throw std::runtime_error("A staged offline HexagonVR test is required");
        std::wstring command=L"\""+exe+L"\" -script \""+std::wstring(code.begin(),code.end())+L"\"";
        STARTUPINFOW si{};si.cb=sizeof(si);si.dwFlags=STARTF_USESHOWWINDOW;si.wShowWindow=SW_SHOWMAXIMIZED;
        if(!CreateProcessW(exe.c_str(),command.data(),nullptr,nullptr,FALSE,CREATE_SUSPENDED,nullptr,nullptr,&si,&pi))throw std::runtime_error("Could not create Studio test");
        job=CreateJobObjectW(nullptr,nullptr);JOBOBJECT_EXTENDED_LIMIT_INFORMATION limit{};limit.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        if(!job||!SetInformationJobObject(job,JobObjectExtendedLimitInformation,&limit,sizeof(limit))||!AssignProcessToJobObject(job,pi.hProcess))throw std::runtime_error("Could not isolate the Studio test process");
        std::wstring name=L"Local\\HexagonVR.Native.Ready."+std::to_wstring(pi.dwProcessId);event=CreateEventW(nullptr,TRUE,FALSE,name.c_str());
        ResumeThread(pi.hThread);CloseHandle(pi.hThread);pi.hThread=nullptr;
        DWORD started=GetTickCount();
        while(!remoteLoadLibrary(pi.dwProcessId)&&GetTickCount()-started<5000)Sleep(5);
        inject(pi.hProcess,pi.dwProcessId,dll);
        if(WaitForSingleObject(event,15000)!=WAIT_OBJECT_0)throw std::runtime_error("Native renderer did not initialize");
        std::ofstream pid{std::filesystem::path(pidFile)};pid<<pi.dwProcessId;pid.close();
        std::cout<<"Offline native graphics test PID "<<pi.dwProcessId<<std::endl;
        WaitForSingleObject(pi.hProcess,INFINITE);DWORD exit=0;GetExitCodeProcess(pi.hProcess,&exit);
        CloseHandle(pi.hProcess);CloseHandle(event);CloseHandle(job);return int(exit);
    }catch(const std::exception& error){std::cerr<<error.what()<<std::endl;if(pi.hProcess){TerminateProcess(pi.hProcess,1);CloseHandle(pi.hProcess);}if(pi.hThread)CloseHandle(pi.hThread);if(event)CloseHandle(event);if(job)CloseHandle(job);return 1;}
}
