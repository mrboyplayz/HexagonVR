#pragma once
// An additional scene pass feeds a depth-tested, world-space circular optic.
// It leaves the surrounding headset projections unchanged.
namespace optic {
struct Input {stereo::Matrix lens=stereo::identity();float radius=.105f,zoom=4,length=1.32f;bool enabled=false;};
class Renderer {
    ID3D11Texture2D* texture=nullptr;
    ID3D11RenderTargetView* target=nullptr;
    ID3D11DepthStencilView* depth=nullptr;
    ID3D11ShaderResourceView* image=nullptr;
    ID3D11Buffer *globals=nullptr,*quadConstants=nullptr;
    ID3D11VertexShader* vertex=nullptr;ID3D11PixelShader* pixel=nullptr;
    ID3D11SamplerState* sampler=nullptr;
    ID3D11DepthStencilState* lensDepth=nullptr;
    ID3D11RasterizerState* raster=nullptr;
    Input current;bool ready=false,attempted=false,activeFrame=false;
    static constexpr UINT resolution=512;
    template<class T>static void drop(T*&p){if(p){p->Release();p=nullptr;}}
public:
    bool initialize(ID3D11DeviceContext* context){
        if(attempted)return ready;attempted=true;
        ID3D11Device* device=nullptr;context->GetDevice(&device);bool ok=true;
        D3D11_TEXTURE2D_DESC td{};td.Width=td.Height=resolution;td.MipLevels=td.ArraySize=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.SampleDesc.Count=1;td.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
        ok=SUCCEEDED(device->CreateTexture2D(&td,nullptr,&texture))&&SUCCEEDED(device->CreateRenderTargetView(texture,nullptr,&target))&&SUCCEEDED(device->CreateShaderResourceView(texture,nullptr,&image));
        ID3D11Texture2D* z=nullptr;td.Format=DXGI_FORMAT_D24_UNORM_S8_UINT;td.BindFlags=D3D11_BIND_DEPTH_STENCIL;
        ok=ok&&SUCCEEDED(device->CreateTexture2D(&td,nullptr,&z))&&SUCCEEDED(device->CreateDepthStencilView(z,nullptr,&depth));drop(z);
        D3D11_BUFFER_DESC bd{};bd.ByteWidth=384;bd.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
        ok=ok&&SUCCEEDED(device->CreateBuffer(&bd,nullptr,&globals));bd.ByteWidth=128;
        ok=ok&&SUCCEEDED(device->CreateBuffer(&bd,nullptr,&quadConstants));
        const char* shader=R"HLSL(
cbuffer Scope : register(b0) {row_major float4x4 vp;float4 origin;float4 rightAxis;float4 upAxis;float4 options;};
struct Out {float4 p:SV_Position;float2 uv:TEXCOORD0;};
Out vs(uint id:SV_VertexID){
    const float2 corners[6]={float2(-1,1),float2(1,1),float2(-1,-1),float2(-1,-1),float2(1,1),float2(1,-1)};
    float2 q=corners[id];Out o;o.p=mul(vp,float4(origin.xyz+options.x*(q.x*rightAxis.xyz+q.y*upAxis.xyz),1));
    o.p.z=max(.00001,o.p.z);o.uv=float2(q.x*.5+.5,.5-q.y*.5);return o;
}
Texture2D scene:register(t0);SamplerState sampleScene:register(s0);
float4 ps(Out i):SV_Target{
    float2 p=i.uv*2-1;float r=dot(p,p);clip(1-r);
    float3 color=scene.Sample(sampleScene,i.uv).rgb;
    float cross=max((abs(p.x)<.004&&abs(p.y)>.025)?1:0,(abs(p.y)<.004&&abs(p.x)>.025)?1:0);
    float dotLine=100;
    [unroll]for(int n=-3;n<=3;n++){if(n!=0){dotLine=min(dotLine,length(p-float2(n*.19,0)));dotLine=min(dotLine,length(p-float2(0,n*.19)));}}
    if(cross>0||dotLine<.014||r>.96)color=float3(.005,.005,.005);
    return float4(color,1);
})HLSL";
        ID3DBlob *vs=nullptr,*ps=nullptr,*error=nullptr;
        HRESULT vr=D3DCompile(shader,strlen(shader),nullptr,nullptr,nullptr,"vs","vs_4_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&vs,&error);drop(error);
        HRESULT pr=D3DCompile(shader,strlen(shader),nullptr,nullptr,nullptr,"ps","ps_4_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&ps,&error);drop(error);
        ok=ok&&SUCCEEDED(vr)&&SUCCEEDED(pr);
        if(vs&&ps)ok=ok&&SUCCEEDED(device->CreateVertexShader(vs->GetBufferPointer(),vs->GetBufferSize(),nullptr,&vertex))&&SUCCEEDED(device->CreatePixelShader(ps->GetBufferPointer(),ps->GetBufferSize(),nullptr,&pixel));drop(vs);drop(ps);
        D3D11_SAMPLER_DESC sd{};sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;sd.MaxLOD=D3D11_FLOAT32_MAX;
        ok=ok&&SUCCEEDED(device->CreateSamplerState(&sd,&sampler));
        D3D11_DEPTH_STENCIL_DESC dd{};dd.DepthEnable=TRUE;dd.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ZERO;dd.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;
        ok=ok&&SUCCEEDED(device->CreateDepthStencilState(&dd,&lensDepth));
        D3D11_RASTERIZER_DESC rd{};rd.FillMode=D3D11_FILL_SOLID;rd.CullMode=D3D11_CULL_NONE;rd.DepthClipEnable=TRUE;
        ok=ok&&SUCCEEDED(device->CreateRasterizerState(&rd,&raster));drop(device);ready=ok;return ready;
    }
    void begin(ID3D11DeviceContext*ctx,const Input&input){
        current=input;activeFrame=input.enabled&&initialize(ctx);
        if(activeFrame){float clear[4]={.03f,.04f,.06f,1};ctx->ClearRenderTargetView(target,clear);ctx->ClearDepthStencilView(depth,D3D11_CLEAR_DEPTH|D3D11_CLEAR_STENCIL,1,0);}
    }
    bool active()const{return activeFrame;}
    void capture(ID3D11DeviceContext*ctx,const std::filesystem::path&path){
        if(!activeFrame)return;ID3D11Device* device=nullptr;ctx->GetDevice(&device);
        D3D11_TEXTURE2D_DESC desc{};texture->GetDesc(&desc);desc.BindFlags=desc.MiscFlags=0;desc.Usage=D3D11_USAGE_STAGING;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
        ID3D11Texture2D* staging=nullptr;
        if(SUCCEEDED(device->CreateTexture2D(&desc,nullptr,&staging))){
            ctx->CopyResource(staging,texture);D3D11_MAPPED_SUBRESOURCE mapped{};
            if(SUCCEEDED(ctx->Map(staging,0,D3D11_MAP_READ,0,&mapped))){
                std::vector<unsigned char> rgb(resolution*resolution*3);
                for(UINT y=0;y<resolution;y++)for(UINT x=0;x<resolution;x++)for(UINT c=0;c<3;c++)rgb[(y*resolution+x)*3+c]=static_cast<const unsigned char*>(mapped.pData)[y*mapped.RowPitch+x*4+c];
                ctx->Unmap(staging,0);std::ofstream file(path,std::ios::binary);file<<"P6\n"<<resolution<<' '<<resolution<<"\n255\n";file.write(reinterpret_cast<const char*>(rgb.data()),rgb.size());
            }
        }
        drop(staging);drop(device);
    }
    template<class Draw>void scenePass(ID3D11DeviceContext*ctx,const float*source,bool sharedPixel,Draw draw){
        if(!activeFrame)return;float data[96];std::memcpy(data,source,sizeof(data));
        auto camera=current.lens;for(int i=0;i<3;i++)camera.m[i][3]-=camera.m[i][2]*current.length;
        float distance=0;for(int i=0;i<3;i++)distance+=(source[28+i]-current.lens.m[i][3])*current.lens.m[i][2];
        float half=std::clamp(current.radius/(std::max(.15f,distance)*current.zoom),.025f,.5f);
        if(!stereo::cameraGlobals(source,data,camera,half))return;
        ctx->UpdateSubresource(globals,0,nullptr,data,0,0);ctx->VSSetConstantBuffers(0,1,&globals);if(sharedPixel)ctx->PSSetConstantBuffers(0,1,&globals);
        ctx->OMSetRenderTargets(1,&target,depth);D3D11_VIEWPORT view{0,0,float(resolution),float(resolution),0,1};D3D11_RECT rect{0,0,LONG(resolution),LONG(resolution)};
        ctx->RSSetViewports(1,&view);ctx->RSSetScissorRects(1,&rect);draw();
    }
    template<class Draw>void composite(ID3D11DeviceContext*ctx,ID3D11RenderTargetView**eyes,ID3D11DepthStencilView**z,const stereo::Matrix*vp,UINT width,UINT height,Draw draw){
        if(!activeFrame)return;
        ID3D11RenderTargetView* oldTargets[8]{};ID3D11DepthStencilView* oldDepth=nullptr;ctx->OMGetRenderTargets(8,oldTargets,&oldDepth);
        ID3D11VertexShader* oldVS=nullptr;ID3D11PixelShader* oldPS=nullptr;ID3D11GeometryShader* oldGS=nullptr;
        ctx->VSGetShader(&oldVS,nullptr,nullptr);ctx->PSGetShader(&oldPS,nullptr,nullptr);ctx->GSGetShader(&oldGS,nullptr,nullptr);
        ID3D11Buffer *oldVC=nullptr,*oldPC=nullptr;ctx->VSGetConstantBuffers(0,1,&oldVC);ctx->PSGetConstantBuffers(0,1,&oldPC);
        ID3D11ShaderResourceView* oldImage=nullptr;ID3D11SamplerState* oldSampler=nullptr;ctx->PSGetShaderResources(0,1,&oldImage);ctx->PSGetSamplers(0,1,&oldSampler);
        ID3D11InputLayout* oldLayout=nullptr;D3D11_PRIMITIVE_TOPOLOGY oldTopology;ctx->IAGetInputLayout(&oldLayout);ctx->IAGetPrimitiveTopology(&oldTopology);
        ID3D11BlendState* oldBlend=nullptr;float factor[4];UINT mask;ctx->OMGetBlendState(&oldBlend,factor,&mask);
        ID3D11DepthStencilState* oldDS=nullptr;UINT reference;ctx->OMGetDepthStencilState(&oldDS,&reference);
        ID3D11RasterizerState* oldRS=nullptr;ctx->RSGetState(&oldRS);UINT count=16;D3D11_VIEWPORT oldViews[16];ctx->RSGetViewports(&count,oldViews);
        UINT rectCount=16;D3D11_RECT oldRects[16];ctx->RSGetScissorRects(&rectCount,oldRects);
        ID3D11Predicate* predicate=nullptr;BOOL predicated=FALSE;ctx->GetPredication(&predicate,&predicated);ctx->SetPredication(nullptr,FALSE);
        ctx->IASetInputLayout(nullptr);ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        ctx->VSSetShader(vertex,nullptr,0);ctx->PSSetShader(pixel,nullptr,0);ctx->GSSetShader(nullptr,nullptr,0);
        ctx->VSSetConstantBuffers(0,1,&quadConstants);ctx->PSSetConstantBuffers(0,1,&quadConstants);ctx->PSSetShaderResources(0,1,&image);ctx->PSSetSamplers(0,1,&sampler);
        ctx->OMSetBlendState(nullptr,nullptr,~0u);ctx->OMSetDepthStencilState(lensDepth,0);ctx->RSSetState(raster);
        D3D11_VIEWPORT view{0,0,float(width),float(height),0,1};D3D11_RECT rect{0,0,LONG(width),LONG(height)};ctx->RSSetViewports(1,&view);ctx->RSSetScissorRects(1,&rect);
        for(int eye=0;eye<2;eye++){
            float data[32]{};std::memcpy(data,&vp[eye],64);
            for(int i=0;i<3;i++){data[16+i]=current.lens.m[i][3]+current.lens.m[i][2]*.025f;data[20+i]=current.lens.m[i][0];data[24+i]=current.lens.m[i][1];}data[28]=current.radius;
            ctx->UpdateSubresource(quadConstants,0,nullptr,data,0,0);ctx->OMSetRenderTargets(1,&eyes[eye],z[eye]);draw();
        }
        ctx->PSSetShaderResources(0,1,&oldImage);ctx->PSSetSamplers(0,1,&oldSampler);ctx->VSSetConstantBuffers(0,1,&oldVC);ctx->PSSetConstantBuffers(0,1,&oldPC);
        ctx->VSSetShader(oldVS,nullptr,0);ctx->PSSetShader(oldPS,nullptr,0);ctx->GSSetShader(oldGS,nullptr,0);ctx->IASetInputLayout(oldLayout);ctx->IASetPrimitiveTopology(oldTopology);
        ctx->OMSetRenderTargets(8,oldTargets,oldDepth);ctx->OMSetBlendState(oldBlend,factor,mask);ctx->OMSetDepthStencilState(oldDS,reference);ctx->RSSetState(oldRS);ctx->RSSetViewports(count,oldViews);ctx->RSSetScissorRects(rectCount,oldRects);ctx->SetPredication(predicate,predicated);
        for(auto&t:oldTargets)drop(t);drop(oldDepth);drop(oldVS);drop(oldPS);drop(oldGS);drop(oldVC);drop(oldPC);drop(oldImage);drop(oldSampler);drop(oldLayout);drop(oldBlend);drop(oldDS);drop(oldRS);drop(predicate);
    }
};
}
