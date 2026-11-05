#include "stereo_math.hpp"
#include <cassert>
#include <iostream>
using namespace stereo;
static float xndc(const float* values,float x,float y,float z){
    const auto& p=*reinterpret_cast<const Matrix*>(values);
    float a=p.m[0][0]*x+p.m[0][1]*y+p.m[0][2]*z+p.m[0][3];
    float w=p.m[3][0]*x+p.m[3][1]*y+p.m[3][2]*z+p.m[3][3];return a/w;
}
int main(){
    float source[96]{};source[16]=source[21]=source[26]=1;source[28]=8;source[29]=4;source[30]=12;source[31]=1;
    Matrix v=identity();v.m[0][3]=-8;v.m[1][3]=-4;v.m[2][3]=-12;
    Matrix p{};p.m[0][0]=.8f;p.m[1][1]=1.4f;p.m[2][2]=-1.0001f;p.m[2][3]=-.50005f;p.m[3][2]=-1;
    auto vp=multiply(p,v);std::memcpy(source,&vp,64);
    Matrix el=identity(),er=identity();el.m[0][3]=-.09f;er.m[0][3]=.09f;
    float l[96]{},r[96]{};float left=-1.28f,right=.9f,top=-1.19f,bottom=1.11f;
    assert(eyeGlobals(source,l,el,left,right,top,bottom));assert(eyeGlobals(source,r,er,-right,-left,top,bottom));
    float sx=2/(right-left),offset=(right+left)/(right-left);
    float near=(xndc(l,8,4,10)+offset)-(xndc(r,8,4,10)-offset);
    float far=(xndc(l,8,4,-8)+offset)-(xndc(r,8,4,-8)-offset);
    assert(std::fabs(near-2*sx*.09f/2)<.00001f);assert(std::fabs(near/far-10)<.001f);
    assert(std::fabs(l[28]-7.91f)<.00001f&&std::fabs(r[28]-8.09f)<.00001f);
    Matrix scopeCamera=identity();scopeCamera.m[0][3]=8;scopeCamera.m[1][3]=4;scopeCamera.m[2][3]=12;
    float scoped[96]{};std::memcpy(scoped,source,sizeof(source));assert(cameraGlobals(source,scoped,scopeCamera,.3125f));
    assert(std::fabs(xndc(scoped,9,4,2)/xndc(source,9,4,2)-4)<.00001f);
    assert(std::fabs(xndc(scoped,8,4,2))<.00001f&&scoped[28]==8&&scoped[29]==4&&scoped[30]==12);
    assert(!cameraGlobals(source,scoped,scopeCamera,0));
    source[16]=4;assert(!eyeGlobals(source,l,el,left,right,top,bottom));
    std::cout<<"Stereo geometry: independent eye positions, asymmetric projection, 10x depth-disparity ratio; invalid camera rejected\n";
}
