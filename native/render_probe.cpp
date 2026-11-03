// Experimental direct stereo draws for the verified 32-bit 2015 Studio build.
// Retains the original game pass; exports separate synchronized GPU eye textures.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <d3d11shader.h>
#include <atomic>
#include <map>
#include <mutex>
#include <vector>
#include <string>
#include <fstream>
#include <filesystem>
#include <sstream>
#include <cmath>
#include <cstdint>
#include "stereo_math.hpp"
#include "MinHook.h"

static HMODULE module;
static std::mutex dataLock,logLock;
static std::ofstream logfile;
static std::atomic<unsigned long> draws{0},globalDraws{0},presents{0};
static thread_local bool internal=false;
static std::map<ID3D11Buffer*,std::vector<unsigned char>> buffers;
struct Mapping{void* data;UINT size;};
static std::map<ID3D11Resource*,Mapping> mappings;
struct Shader{bool globals=false;UINT size=0;};
static std::map<ID3D11VertexShader*,Shader> shaders;
static bool dumped=false;
static std::wstring outputDirectory;
static std::atomic<unsigned long> nativeDraws{0},nativeFrames{0},invalidMatrices{0};
static std::atomic<bool> runtimeReady{false};
static UINT eyeWidth=0,eyeHeight=0,sourceWidth=0,sourceHeight=0;
static stereo::Matrix eyeTransforms[2];
static float frusta[2][4];
static ID3D11DeviceContext* sceneContext=nullptr;
static ID3D11Texture2D* eyeTextures[2]{};
static ID3D11RenderTargetView* eyeTargets[2]{};
static ID3D11DepthStencilView* eyeDepth[2]{};
struct Slot {ID3D11Texture2D* texture[2]{};ID3D11RenderTargetView* target[2]{};ID3D11DepthStencilView* depth[2]{};IDXGIKeyedMutex* mutex[2]{};HANDLE handle[2]{};};
static Slot slots[3];static int currentSlot=0;static bool canRender=false;
struct PoseItem{volatile UINT sequence;float pose[12];};
struct FramePacket {volatile LONG sequence;UINT magic,width,height;uint64_t frame,texture0,texture1;UINT draws,ready;volatile LONG enabled;DWORD heartbeat;float pose[12];UINT poseSequence,padding;uint64_t ackAddress;PoseItem poses[64];};
static_assert(sizeof(FramePacket)==3448,"Native frame protocol layout");
static FramePacket* packet=nullptr;static HANDLE packetMapping=nullptr;
static bool diagnosticCapture=false,diagnosticRender=false;
static float renderedPose[12]{};static UINT renderedPoseSequence=0;
static void snapshotPose(){
    renderedPoseSequence=0;if(!packet)return;uintptr_t address=uintptr_t(packet->ackAddress);MEMORY_BASIC_INFORMATION info{};
    if(address<0x10000||address>0x7ffe0000||!VirtualQuery(reinterpret_cast<void*>(address),&info,sizeof(info))||info.State!=MEM_COMMIT||(info.Protect&(PAGE_GUARD|PAGE_NOACCESS))||address+12>reinterpret_cast<uintptr_t>(info.BaseAddress)+info.RegionSize)return;
    const float* ack=reinterpret_cast<const float*>(address);float number=ack[0];
    if(!std::isfinite(number)||number<0||number>=1000000||number!=std::floor(number)||ack[1]!=56002.25f||ack[2]!=66003.5f)return;
    UINT seq=UINT(number);auto& slot=packet->poses[seq%64];if(slot.sequence!=seq)return;
    std::memcpy(renderedPose,slot.pose,sizeof(renderedPose));MemoryBarrier();if(slot.sequence==seq)renderedPoseSequence=seq;
}
static ID3D11Buffer* eyeConstants[2]{};
static ID3D11DepthStencilState* nativeDepthState=nullptr;
static ID3D11RasterizerState* nativeRasterizer=nullptr;
static ID3D11PixelShader* debugPixel=nullptr;
static UINT constantBytes=0;
static bool frameHasDraws=false,imagesWritten=false;
static float cameraY=1000;
using Present=HRESULT(STDMETHODCALLTYPE*)(IDXGISwapChain*,UINT,UINT);
static Present originalPresent;

static void log(const std::string& text){std::lock_guard<std::mutex> g(logLock);logfile<<text<<std::endl;}
template<class T>static void release(T*& p){if(p){p->Release();p=nullptr;}}
template<class T>static bool hook(void* address,void* replacement,T& original){
    if(original)return true;
    MH_STATUS status=MH_CreateHook(address,replacement,reinterpret_cast<void**>(&original));
    if(status!=MH_OK){log("{\"hook_error\":"+std::to_string(status)+"}");return false;}
    return MH_EnableHook(address)==MH_OK;
}

using CreateDevice=decltype(&D3D11CreateDevice);
static CreateDevice originalCreate;
using CreateDeviceAndSwap=decltype(&D3D11CreateDeviceAndSwapChain);
static CreateDeviceAndSwap originalCreateAndSwap;
using CreateVS=HRESULT(STDMETHODCALLTYPE*)(ID3D11Device*,const void*,SIZE_T,ID3D11ClassLinkage*,ID3D11VertexShader**);
static CreateVS originalVS;
using Map=HRESULT(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,ID3D11Resource*,UINT,D3D11_MAP,UINT,D3D11_MAPPED_SUBRESOURCE*);
static Map originalMap;
using Unmap=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,ID3D11Resource*,UINT);
static Unmap originalUnmap;
using Update=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,ID3D11Resource*,UINT,const D3D11_BOX*,const void*,UINT,UINT);
static Update originalUpdate;
using DrawIndexed=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT,INT);
static DrawIndexed originalIndexed;
using Draw=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT);
static Draw originalDraw;
using DrawIndexedInstanced=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT,UINT,INT,UINT);
static DrawIndexedInstanced originalIndexedInstanced;
using DrawInstanced=void(STDMETHODCALLTYPE*)(ID3D11DeviceContext*,UINT,UINT,UINT,UINT);
static DrawInstanced originalInstanced;

static UINT constantSize(ID3D11Resource* resource){
    if(!resource)return 0;
    ID3D11Buffer* buffer=nullptr;
    if(FAILED(resource->QueryInterface(__uuidof(ID3D11Buffer),reinterpret_cast<void**>(&buffer))))return 0;
    D3D11_BUFFER_DESC desc{};buffer->GetDesc(&desc);buffer->Release();
    return (desc.BindFlags&D3D11_BIND_CONSTANT_BUFFER)&&desc.ByteWidth<=65536?desc.ByteWidth:0;
}
static HRESULT STDMETHODCALLTYPE createVS(ID3D11Device* device,const void* code,SIZE_T length,ID3D11ClassLinkage* classes,ID3D11VertexShader** shader){
    HRESULT result=originalVS(device,code,length,classes,shader);
    if(SUCCEEDED(result)&&shader&&*shader){
        ID3D11ShaderReflection* reflection=nullptr;Shader info;
        if(SUCCEEDED(D3DReflect(code,length,IID_ID3D11ShaderReflection,reinterpret_cast<void**>(&reflection)))){
            D3D11_SHADER_BUFFER_DESC desc{};
            if(SUCCEEDED(reflection->GetConstantBufferByName("Globals")->GetDesc(&desc))){
                info.globals=true;info.size=desc.Size;
                auto variable=reflection->GetConstantBufferByName("Globals")->GetVariableByName("_G");
                D3D11_SHADER_VARIABLE_DESC var{};D3D11_SHADER_TYPE_DESC type{};
                variable->GetDesc(&var);variable->GetType()->GetMemberTypeByName("ViewProjection")->GetDesc(&type);
                std::ostringstream s;s<<"{\"shader_globals\":true,\"buffer_size\":"<<desc.Size<<",\"variable_offset\":"<<var.StartOffset<<",\"matrix_class\":"<<type.Class<<",\"matrix_offset\":"<<type.Offset<<"}";log(s.str());
            }
            reflection->Release();
        }
        std::lock_guard<std::mutex> g(dataLock);shaders[*shader]=info;
    }
    return result;
}
static HRESULT STDMETHODCALLTYPE mapBuffer(ID3D11DeviceContext* ctx,ID3D11Resource* resource,UINT sub,D3D11_MAP mode,UINT flags,D3D11_MAPPED_SUBRESOURCE* output){
    HRESULT result=originalMap(ctx,resource,sub,mode,flags,output);
    if(!internal&&SUCCEEDED(result)&&output&&output->pData){
        UINT size=constantSize(resource);
        if(size){std::lock_guard<std::mutex> g(dataLock);mappings[resource]={output->pData,size};}
    }
    return result;
}
static void STDMETHODCALLTYPE unmapBuffer(ID3D11DeviceContext* ctx,ID3D11Resource* resource,UINT sub){
    if(!internal){
        std::lock_guard<std::mutex> g(dataLock);auto it=mappings.find(resource);
        if(it!=mappings.end()){
            auto p=static_cast<const unsigned char*>(it->second.data);
            buffers[static_cast<ID3D11Buffer*>(resource)]=std::vector<unsigned char>(p,p+it->second.size);mappings.erase(it);
        }
    }
    originalUnmap(ctx,resource,sub);
}
static void STDMETHODCALLTYPE updateBuffer(ID3D11DeviceContext* ctx,ID3D11Resource* resource,UINT sub,const D3D11_BOX* box,const void* source,UINT row,UINT depth){
    if(!internal&&source){UINT size=constantSize(resource);if(size){
        auto p=static_cast<const unsigned char*>(source);std::lock_guard<std::mutex> g(dataLock);
        buffers[static_cast<ID3D11Buffer*>(resource)]=std::vector<unsigned char>(p,p+size);
    }}
    originalUpdate(ctx,resource,sub,box,source,row,depth);
}
static void inspectDraw(ID3D11DeviceContext* ctx){
    if(internal)return;
    ++draws;
    ID3D11VertexShader* shader=nullptr;ctx->VSGetShader(&shader,nullptr,nullptr);
    bool global=false;
    {std::lock_guard<std::mutex> g(dataLock);auto it=shaders.find(shader);global=it!=shaders.end()&&it->second.globals;}
    release(shader);if(!global)return;++globalDraws;
    if(dumped)return;
    ID3D11Buffer* cb=nullptr;ctx->VSGetConstantBuffers(0,1,&cb);
    std::vector<unsigned char> data;
    {std::lock_guard<std::mutex> g(dataLock);auto it=buffers.find(cb);if(it!=buffers.end())data=it->second;}
    release(cb);if(data.size()<128)return;
    ID3D11RenderTargetView* rt=nullptr;ID3D11DepthStencilView* ds=nullptr;ctx->OMGetRenderTargets(1,&rt,&ds);
    ID3D11Resource* resource=nullptr;ID3D11Texture2D* texture=nullptr;D3D11_TEXTURE2D_DESC td{};
    if(rt){rt->GetResource(&resource);resource->QueryInterface(__uuidof(ID3D11Texture2D),reinterpret_cast<void**>(&texture));if(texture)texture->GetDesc(&td);}
    D3D11_VIEWPORT view{};UINT count=1;ctx->RSGetViewports(&count,&view);
    if(!ds||td.Width<512||td.Height<256){release(texture);release(resource);release(rt);release(ds);return;}
    const float* values=reinterpret_cast<const float*>(data.data());
    std::ostringstream s;s<<"{\"globals_sample\":[";
    for(UINT i=0;i<32;++i){if(i)s<<',';if(std::isfinite(values[i]))s<<values[i];else s<<"null";}
    s<<"],\"target\":["<<td.Width<<','<<td.Height<<"],\"target_format\":"<<td.Format<<",\"viewport\":["<<view.Width<<','<<view.Height<<"],\"has_depth\":"<<(ds?"true":"false")<<"}";log(s.str());
    release(texture);release(resource);release(rt);release(ds);dumped=true;
}
static bool beginSlot(ID3D11DeviceContext* ctx,int index){
    auto& slot=slots[index];bool acquired[2]{};
    for(int i=0;i<2;++i){
        HRESULT r=slot.mutex[i]->AcquireSync(0,0);if(r==WAIT_TIMEOUT)r=slot.mutex[i]->AcquireSync(1,0);
        acquired[i]=r==S_OK;
        if(!acquired[i]){for(int j=0;j<i;++j)if(acquired[j])slot.mutex[j]->ReleaseSync(1);return false;}
    }
    currentSlot=index;float clear[4]={0,0,0,1};
    for(int i=0;i<2;++i){eyeTextures[i]=slot.texture[i];eyeTargets[i]=slot.target[i];eyeDepth[i]=slot.depth[i];ctx->ClearRenderTargetView(eyeTargets[i],clear);ctx->ClearDepthStencilView(eyeDepth[i],D3D11_CLEAR_DEPTH|D3D11_CLEAR_STENCIL,1,0);}
    canRender=true;return true;
}
static bool createEyes(ID3D11DeviceContext* ctx,UINT bytes){
    if(eyeTargets[0])return ctx==sceneContext&&bytes==constantBytes;
    ID3D11Device* device=nullptr;ctx->GetDevice(&device);bool ok=true;
    D3D11_TEXTURE2D_DESC color{};color.Width=eyeWidth;color.Height=eyeHeight;color.MipLevels=1;color.ArraySize=1;color.Format=DXGI_FORMAT_R8G8B8A8_UNORM;color.SampleDesc.Count=1;color.Usage=D3D11_USAGE_DEFAULT;color.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;color.MiscFlags=D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX;
    for(int ring=0;ring<3&&ok;++ring)for(int i=0;i<2&&ok;++i){
        auto& slot=slots[ring];
        ok=SUCCEEDED(device->CreateTexture2D(&color,nullptr,&slot.texture[i]))&&SUCCEEDED(device->CreateRenderTargetView(slot.texture[i],nullptr,&slot.target[i]));
        IDXGIResource* shared=nullptr;
        ok=ok&&SUCCEEDED(slot.texture[i]->QueryInterface(__uuidof(IDXGIResource),reinterpret_cast<void**>(&shared)));
        if(shared){ok=ok&&SUCCEEDED(shared->GetSharedHandle(&slot.handle[i]));release(shared);}
        ok=ok&&SUCCEEDED(slot.texture[i]->QueryInterface(__uuidof(IDXGIKeyedMutex),reinterpret_cast<void**>(&slot.mutex[i])));
        auto depth=color;depth.MiscFlags=0;depth.Format=DXGI_FORMAT_D24_UNORM_S8_UINT;depth.BindFlags=D3D11_BIND_DEPTH_STENCIL;ID3D11Texture2D* texture=nullptr;
        ok=ok&&SUCCEEDED(device->CreateTexture2D(&depth,nullptr,&texture))&&SUCCEEDED(device->CreateDepthStencilView(texture,nullptr,&slot.depth[i]));release(texture);
    }
    for(int i=0;i<2&&ok;++i){
        D3D11_BUFFER_DESC cb{};cb.ByteWidth=bytes;cb.Usage=D3D11_USAGE_DEFAULT;cb.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
        ok=ok&&SUCCEEDED(device->CreateBuffer(&cb,nullptr,&eyeConstants[i]));
    }
    D3D11_DEPTH_STENCIL_DESC ds{};ds.DepthEnable=TRUE;ds.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;ds.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
    ok=ok&&SUCCEEDED(device->CreateDepthStencilState(&ds,&nativeDepthState));
    D3D11_RASTERIZER_DESC rs{};rs.FillMode=D3D11_FILL_SOLID;rs.CullMode=D3D11_CULL_NONE;rs.DepthClipEnable=TRUE;
    ok=ok&&SUCCEEDED(device->CreateRasterizerState(&rs,&nativeRasterizer));
    wchar_t debugMode[8]{};GetEnvironmentVariableW(L"HEXAGONVR_NATIVE_DEBUG",debugMode,8);
    if(debugMode[0]=='1'){
        const char* code="float4 main():SV_Target{return float4(1,0,1,1);}";ID3DBlob* blob=nullptr;
        if(SUCCEEDED(D3DCompile(code,strlen(code),nullptr,nullptr,nullptr,"main","ps_4_0",0,0,&blob,nullptr))){device->CreatePixelShader(blob->GetBufferPointer(),blob->GetBufferSize(),nullptr,&debugPixel);release(blob);}
    }
    release(device);if(!ok){log("{\"native_eye_allocation\":false}");return false;}
    sceneContext=ctx;constantBytes=bytes;
    beginSlot(ctx,0);
    log("{\"native_eye_allocation\":true,\"width\":"+std::to_string(eyeWidth)+",\"height\":"+std::to_string(eyeHeight)+"}");return true;
}
template<class F>static void stereoDraw(ID3D11DeviceContext* ctx,F issue){
    bool active=diagnosticRender||(packet&&packet->enabled&&DWORD(GetTickCount()-packet->heartbeat)<2000);
    if(!active){issue();return;}
    inspectDraw(ctx);
    if(internal||!runtimeReady){issue();return;}
    ID3D11VertexShader* shader=nullptr;ctx->VSGetShader(&shader,nullptr,nullptr);bool global=false;
    {std::lock_guard<std::mutex> g(dataLock);auto it=shaders.find(shader);global=it==shaders.end()||it->second.globals;}
    release(shader);if(!global){issue();return;}
    ID3D11RenderTargetView* targets[8]{};ID3D11DepthStencilView* depth=nullptr;ctx->OMGetRenderTargets(8,targets,&depth);
    ID3D11Resource* resource=nullptr;ID3D11Texture2D* texture=nullptr;D3D11_TEXTURE2D_DESC td{};
    if(targets[0]){targets[0]->GetResource(&resource);resource->QueryInterface(__uuidof(ID3D11Texture2D),reinterpret_cast<void**>(&texture));if(texture)texture->GetDesc(&td);}
    bool candidate=td.Width>=512&&td.Height>=256&&td.Format==DXGI_FORMAT_R8G8B8A8_UNORM;
    ID3D11Buffer* cb=nullptr;ID3D11Buffer* pixelCB=nullptr;std::vector<unsigned char> data;
    if(candidate){ctx->VSGetConstantBuffers(0,1,&cb);ctx->PSGetConstantBuffers(0,1,&pixelCB);std::lock_guard<std::mutex> g(dataLock);auto it=buffers.find(cb);if(it!=buffers.end())data=it->second;}
    if(data.size()==384){
        auto left=data,right=data;bool valid=stereo::eyeGlobals(reinterpret_cast<const float*>(data.data()),reinterpret_cast<float*>(left.data()),eyeTransforms[0],frusta[0][0],frusta[0][1],frusta[0][2],frusta[0][3])&&stereo::eyeGlobals(reinterpret_cast<const float*>(data.data()),reinterpret_cast<float*>(right.data()),eyeTransforms[1],frusta[1][0],frusta[1][1],frusta[1][2],frusta[1][3]);
        if(valid){
            internal=true;
            if(createEyes(ctx,UINT(data.size()))&&canRender){
                if(!frameHasDraws)snapshotPose();
                UINT count=16;D3D11_VIEWPORT views[16]{};ctx->RSGetViewports(&count,views);
                UINT rectCount=16;D3D11_RECT rects[16]{};ctx->RSGetScissorRects(&rectCount,rects);
                D3D11_VIEWPORT eyeView{0,0,float(eyeWidth),float(eyeHeight),0,1};D3D11_RECT full{0,0,LONG(eyeWidth),LONG(eyeHeight)};
                ID3D11BlendState* blend=nullptr;FLOAT blendFactor[4];UINT sampleMask=0;ctx->OMGetBlendState(&blend,blendFactor,&sampleMask);
                ID3D11DepthStencilState* savedDepth=nullptr;UINT stencilRef=0;ctx->OMGetDepthStencilState(&savedDepth,&stencilRef);
                ID3D11RasterizerState* rasterizer=nullptr;ctx->RSGetState(&rasterizer);
                ID3D11Predicate* predicate=nullptr;BOOL predicateValue=FALSE;ctx->GetPredication(&predicate,&predicateValue);
                ID3D11PixelShader* pixelShader=nullptr;ctx->PSGetShader(&pixelShader,nullptr,nullptr);
                if(debugPixel){ctx->OMSetBlendState(nullptr,nullptr,~0u);ctx->OMSetDepthStencilState(nativeDepthState,0);ctx->RSSetState(nativeRasterizer);ctx->SetPredication(nullptr,FALSE);ctx->PSSetShader(debugPixel,nullptr,0);}
                const void* constants[2]={left.data(),right.data()};
                for(int i=0;i<2;++i){
                    ctx->UpdateSubresource(eyeConstants[i],0,nullptr,constants[i],0,0);
                    ctx->VSSetConstantBuffers(0,1,&eyeConstants[i]);if(pixelCB==cb)ctx->PSSetConstantBuffers(0,1,&eyeConstants[i]);
                    ctx->OMSetRenderTargets(1,&eyeTargets[i],eyeDepth[i]);ctx->RSSetViewports(1,&eyeView);ctx->RSSetScissorRects(1,&full);issue();
                }
                ctx->VSSetConstantBuffers(0,1,&cb);if(pixelCB==cb)ctx->PSSetConstantBuffers(0,1,&pixelCB);
                ctx->OMSetRenderTargets(8,targets,depth);ctx->RSSetViewports(count,views);ctx->RSSetScissorRects(rectCount,rects);
                ctx->OMSetBlendState(blend,blendFactor,sampleMask);ctx->OMSetDepthStencilState(savedDepth,stencilRef);ctx->RSSetState(rasterizer);ctx->SetPredication(predicate,predicateValue);ctx->PSSetShader(pixelShader,nullptr,0);
                release(blend);release(savedDepth);release(rasterizer);release(predicate);release(pixelShader);
                ++nativeDraws;frameHasDraws=true;sourceWidth=td.Width;sourceHeight=td.Height;cameraY=reinterpret_cast<const float*>(data.data())[29];
            }
            internal=false;
        }else ++invalidMatrices;
    }
    release(cb);release(pixelCB);release(texture);release(resource);release(depth);for(auto& target:targets)release(target);
    issue();
}
static void saveEyes(ID3D11DeviceContext* ctx){
    ID3D11Device* device=nullptr;ctx->GetDevice(&device);
    for(int i=0;i<2;++i){
        D3D11_TEXTURE2D_DESC desc{};eyeTextures[i]->GetDesc(&desc);desc.BindFlags=0;desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;ID3D11Texture2D* staging=nullptr;
        if(SUCCEEDED(device->CreateTexture2D(&desc,nullptr,&staging))){
            ctx->CopyResource(staging,eyeTextures[i]);D3D11_MAPPED_SUBRESOURCE mapped{};
            if(SUCCEEDED(ctx->Map(staging,0,D3D11_MAP_READ,0,&mapped))){
                std::vector<unsigned char> rgb(size_t(eyeWidth)*eyeHeight*3);
                for(UINT y=0;y<eyeHeight;++y)for(UINT x=0;x<eyeWidth;++x){auto in=static_cast<unsigned char*>(mapped.pData)+size_t(y)*mapped.RowPitch+x*4;auto out=rgb.data()+(size_t(y)*eyeWidth+x)*3;out[0]=in[0];out[1]=in[1];out[2]=in[2];}
                ctx->Unmap(staging,0);std::wstring path=outputDirectory+(i?L"\\native-right-":L"\\native-left-")+std::to_wstring(GetCurrentProcessId())+L".ppm";
                std::ofstream file(std::filesystem::path(path),std::ios::binary);file<<"P6\n"<<eyeWidth<<' '<<eyeHeight<<"\n255\n";file.write(reinterpret_cast<const char*>(rgb.data()),rgb.size());
            }
            release(staging);
        }
    }
    release(device);imagesWritten=true;log("{\"native_eye_images_written\":true}");
}
static HRESULT STDMETHODCALLTYPE present(IDXGISwapChain* chain,UINT sync,UINT flags){
    if(frameHasDraws&&sceneContext){
        ID3D11Texture2D* back=nullptr;D3D11_TEXTURE2D_DESC desc{};
        if(SUCCEEDED(chain->GetBuffer(0,__uuidof(ID3D11Texture2D),reinterpret_cast<void**>(&back)))){back->GetDesc(&desc);release(back);}
        if(desc.Width==sourceWidth&&desc.Height==sourceHeight){
            internal=true;++nativeFrames;
            if(diagnosticCapture&&!imagesWritten&&nativeFrames>120&&cameraY<20)saveEyes(sceneContext);
            sceneContext->Flush();for(int i=0;i<2;++i)slots[currentSlot].mutex[i]->ReleaseSync(1);
            if(packet){InterlockedIncrement(&packet->sequence);MemoryBarrier();packet->magic=0x48565246;packet->width=eyeWidth;packet->height=eyeHeight;packet->frame=nativeFrames;packet->texture0=reinterpret_cast<uintptr_t>(slots[currentSlot].handle[0]);packet->texture1=reinterpret_cast<uintptr_t>(slots[currentSlot].handle[1]);packet->draws=nativeDraws;packet->ready=1;std::memcpy(packet->pose,renderedPose,sizeof(renderedPose));packet->poseSequence=renderedPoseSequence;MemoryBarrier();InterlockedIncrement(&packet->sequence);}
            canRender=false;
            for(int step=1;step<3&&!canRender;++step)beginSlot(sceneContext,(currentSlot+step)%3);
            frameHasDraws=false;internal=false;
        }
    }
    if(sceneContext&&!canRender){internal=true;for(int step=1;step<3&&!canRender;++step)beginSlot(sceneContext,(currentSlot+step)%3);internal=false;}
    return originalPresent(chain,sync,flags);
}
static void STDMETHODCALLTYPE drawIndexed(ID3D11DeviceContext*c,UINT a,UINT b,INT d){stereoDraw(c,[&]{originalIndexed(c,a,b,d);});}
static void STDMETHODCALLTYPE draw(ID3D11DeviceContext*c,UINT a,UINT b){stereoDraw(c,[&]{originalDraw(c,a,b);});}
static void STDMETHODCALLTYPE drawIndexedInstanced(ID3D11DeviceContext*c,UINT a,UINT b,UINT d,INT e,UINT f){stereoDraw(c,[&]{originalIndexedInstanced(c,a,b,d,e,f);});}
static void STDMETHODCALLTYPE drawInstanced(ID3D11DeviceContext*c,UINT a,UINT b,UINT d,UINT e){stereoDraw(c,[&]{originalInstanced(c,a,b,d,e);});}
static void deviceReady(ID3D11Device** device,D3D_FEATURE_LEVEL* level){
    if(device&&*device){
        void** v=*reinterpret_cast<void***>(*device);hook(v[12],reinterpret_cast<void*>(createVS),originalVS);
        ID3D11DeviceContext* ctx=nullptr;(*device)->GetImmediateContext(&ctx);v=*reinterpret_cast<void***>(ctx);
        hook(v[12],reinterpret_cast<void*>(drawIndexed),originalIndexed);hook(v[13],reinterpret_cast<void*>(draw),originalDraw);
        hook(v[14],reinterpret_cast<void*>(mapBuffer),originalMap);hook(v[15],reinterpret_cast<void*>(unmapBuffer),originalUnmap);
        hook(v[20],reinterpret_cast<void*>(drawIndexedInstanced),originalIndexedInstanced);hook(v[21],reinterpret_cast<void*>(drawInstanced),originalInstanced);
        hook(v[48],reinterpret_cast<void*>(updateBuffer),originalUpdate);ctx->Release();
        log("{\"d3d11_device\":true,\"feature_level\":"+std::to_string(level?*level:0)+"}");
    }
}
static HRESULT WINAPI createDevice(IDXGIAdapter* adapter,D3D_DRIVER_TYPE type,HMODULE software,UINT flags,const D3D_FEATURE_LEVEL* levels,UINT count,UINT version,ID3D11Device** device,D3D_FEATURE_LEVEL* level,ID3D11DeviceContext** context){
    HRESULT result=originalCreate(adapter,type,software,flags,levels,count,version,device,level,context);
    if(SUCCEEDED(result))deviceReady(device,level);return result;
}
static HRESULT WINAPI createDeviceAndSwap(IDXGIAdapter* adapter,D3D_DRIVER_TYPE type,HMODULE software,UINT flags,const D3D_FEATURE_LEVEL* levels,UINT count,UINT version,const DXGI_SWAP_CHAIN_DESC* desc,IDXGISwapChain** chain,ID3D11Device** device,D3D_FEATURE_LEVEL* level,ID3D11DeviceContext** context){
    HRESULT result=originalCreateAndSwap(adapter,type,software,flags,levels,count,version,desc,chain,device,level,context);
    if(SUCCEEDED(result))deviceReady(device,level);return result;
}
static DWORD WINAPI worker(void*){
    wchar_t path[MAX_PATH];GetModuleFileNameW(module,path,MAX_PATH);std::wstring dir(path);dir=dir.substr(0,dir.find_last_of(L"\\/"));
    outputDirectory=dir;std::wstring filename=dir+L"\\native-report-"+std::to_wstring(GetCurrentProcessId())+L".jsonl";
    logfile.open(std::filesystem::path(filename),std::ios::trunc);
    log("{\"stage\":\"starting\",\"pid\":"+std::to_string(GetCurrentProcessId())+"}");
    std::wstring configPath=dir+L"\\native-config.bin";std::ifstream config(std::filesystem::path(configPath),std::ios::binary);UINT header[3]{};
    config.read(reinterpret_cast<char*>(header),sizeof(header));config.read(reinterpret_cast<char*>(eyeTransforms),sizeof(eyeTransforms));config.read(reinterpret_cast<char*>(frusta),sizeof(frusta));
    if(config&&header[0]==0x48565232&&header[1]>=64&&header[2]>=64&&header[1]<=8192&&header[2]<=8192){eyeWidth=header[1];eyeHeight=header[2];runtimeReady=true;log("{\"native_config\":true,\"width\":"+std::to_string(eyeWidth)+",\"height\":"+std::to_string(eyeHeight)+"}");}
    UINT diagnosticFlags=0;config.read(reinterpret_cast<char*>(&diagnosticFlags),sizeof(diagnosticFlags));diagnosticRender=(diagnosticFlags&1)!=0;diagnosticCapture=(diagnosticFlags&2)!=0;
    std::wstring mapName=L"Local\\HexagonVR.Native.Frame."+std::to_wstring(GetCurrentProcessId());packetMapping=CreateFileMappingW(INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,sizeof(FramePacket),mapName.c_str());
    if(packetMapping)packet=static_cast<FramePacket*>(MapViewOfFile(packetMapping,FILE_MAP_ALL_ACCESS,0,0,sizeof(FramePacket)));
    HMODULE library=LoadLibraryW(L"d3d11.dll");bool ok=library&&MH_Initialize()==MH_OK;
    HWND window=CreateWindowExW(0,L"STATIC",L"HexagonVR render initialization",WS_POPUP,0,0,16,16,nullptr,nullptr,module,nullptr);
    DXGI_SWAP_CHAIN_DESC swap{};swap.BufferDesc.Width=16;swap.BufferDesc.Height=16;swap.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;swap.SampleDesc.Count=1;swap.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;swap.BufferCount=1;swap.OutputWindow=window;swap.Windowed=TRUE;
    IDXGISwapChain* chain=nullptr;ID3D11Device* device=nullptr;ID3D11DeviceContext* ctx=nullptr;
    if(SUCCEEDED(D3D11CreateDeviceAndSwapChain(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&swap,&chain,&device,nullptr,&ctx))){
        void** v=*reinterpret_cast<void***>(chain);ok=ok&&hook(v[8],reinterpret_cast<void*>(present),originalPresent);
        deviceReady(&device,nullptr);
    }else ok=false;
    release(ctx);release(device);release(chain);DestroyWindow(window);
    ok=ok&&hook(reinterpret_cast<void*>(GetProcAddress(library,"D3D11CreateDevice")),reinterpret_cast<void*>(createDevice),originalCreate)&&hook(reinterpret_cast<void*>(GetProcAddress(library,"D3D11CreateDeviceAndSwapChain")),reinterpret_cast<void*>(createDeviceAndSwap),originalCreateAndSwap);
    log(ok?"{\"stage\":\"hooks_ready\"}":"{\"stage\":\"hook_initialization_failed\"}");
    std::wstring name=L"Local\\HexagonVR.Native.Ready."+std::to_wstring(GetCurrentProcessId());HANDLE event=OpenEventW(EVENT_MODIFY_STATE,FALSE,name.c_str());if(event){SetEvent(event);CloseHandle(event);}
    for(;;){Sleep(2000);std::ostringstream s;s<<"{\"draws\":"<<draws<<",\"globals_draws\":"<<globalDraws<<",\"native_draws\":"<<nativeDraws<<",\"native_frames\":"<<nativeFrames<<",\"invalid_matrices\":"<<invalidMatrices<<"}";log(s.str());}
    return 0;
}
BOOL WINAPI DllMain(HMODULE instance,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH){module=instance;DisableThreadLibraryCalls(instance);HANDLE t=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(t)CloseHandle(t);}return TRUE;}
