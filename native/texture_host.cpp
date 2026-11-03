// Opens the client's shared eye textures in the 64-bit SteamVR helper.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d11.h>
#include <cstdint>
#include <map>
static ID3D11Device* device=nullptr;
static ID3D11DeviceContext* context=nullptr;
struct Entry{ID3D11Texture2D* texture=nullptr;IDXGIKeyedMutex* mutex=nullptr;};
static std::map<uint64_t,Entry> entries;
static Entry* held[2]{};
static uint64_t handles[2]{};
static HRESULT open(uint64_t handle,Entry*& entry){
    if(!device){HRESULT result=D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context);if(FAILED(result))return result;}
    auto it=entries.find(handle);if(it!=entries.end()){entry=&it->second;return S_OK;}
    Entry next;HRESULT result=device->OpenSharedResource(reinterpret_cast<HANDLE>(uintptr_t(handle)),__uuidof(ID3D11Texture2D),reinterpret_cast<void**>(&next.texture));
    if(FAILED(result))return result;
    result=next.texture->QueryInterface(__uuidof(IDXGIKeyedMutex),reinterpret_cast<void**>(&next.mutex));
    if(FAILED(result)){next.texture->Release();return result;}
    entry=&entries.emplace(handle,next).first->second;return S_OK;
}
extern "C" __declspec(dllexport) HRESULT __cdecl AcquireNativeEyes(uint64_t left,uint64_t right,void** outLeft,void** outRight){
    if(!left||!right||!outLeft||!outRight)return E_INVALIDARG;
    Entry* pair[2]{};HRESULT result=open(left,pair[0]);if(FAILED(result))return result;
    result=open(right,pair[1]);if(FAILED(result))return result;
    if(left!=handles[0]||right!=handles[1]){
        result=pair[0]->mutex->AcquireSync(1,0);if(result!=S_OK)return result==WAIT_TIMEOUT?S_FALSE:result;
        result=pair[1]->mutex->AcquireSync(1,0);if(result!=S_OK){pair[0]->mutex->ReleaseSync(1);return result==WAIT_TIMEOUT?S_FALSE:result;}
        for(auto old:held)if(old)old->mutex->ReleaseSync(0);
        held[0]=pair[0];held[1]=pair[1];handles[0]=left;handles[1]=right;
    }
    *outLeft=pair[0]->texture;*outRight=pair[1]->texture;return S_OK;
}
extern "C" __declspec(dllexport) void __cdecl CloseNativeEyes(){
    for(auto old:held)if(old)old->mutex->ReleaseSync(0);
    held[0]=held[1]=nullptr;handles[0]=handles[1]=0;
    for(auto& item:entries){item.second.mutex->Release();item.second.texture->Release();}entries.clear();
    if(context){context->Release();context=nullptr;}if(device){device->Release();device=nullptr;}
}
