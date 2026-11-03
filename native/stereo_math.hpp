#pragma once
#include <cmath>
#include <cstring>
namespace stereo {
struct Matrix {float m[4][4]{};};
inline Matrix identity(){Matrix x;for(int i=0;i<4;++i)x.m[i][i]=1;return x;}
inline Matrix multiply(const Matrix&a,const Matrix&b){Matrix c;for(int i=0;i<4;++i)for(int j=0;j<4;++j)for(int k=0;k<4;++k)c.m[i][j]+=a.m[i][k]*b.m[k][j];return c;}
inline Matrix rigidInverse(const Matrix&a){Matrix b=identity();for(int i=0;i<3;++i)for(int j=0;j<3;++j)b.m[i][j]=a.m[j][i];for(int i=0;i<3;++i)for(int j=0;j<3;++j)b.m[i][3]-=b.m[i][j]*a.m[j][3];return b;}
inline bool eyeGlobals(const float* source,float* output,const Matrix& eyeToHead,float left,float right,float top,float bottom){
    if(!(right>left&&bottom>top))return false;
    Matrix original;std::memcpy(&original,source,64);Matrix view=identity();
    for(int i=0;i<3;++i){
        float length=0;for(int j=0;j<3;++j){view.m[i][j]=source[16+i*4+j];length+=view.m[i][j]*view.m[i][j];view.m[i][3]-=view.m[i][j]*source[28+j];}
        if(std::fabs(length-1)>.03f)return false;
    }
    Matrix projection=multiply(original,rigidInverse(view));
    if(std::fabs(projection.m[3][2]+1)>.02f||std::fabs(projection.m[3][3])>.02f||projection.m[0][0]<=0||projection.m[1][1]<=0)return false;
    float error=0;for(int i=0;i<3;++i)error+=std::fabs(projection.m[3][i]-(i==2?-1.f:0.f));if(error>.02f)return false;
    Matrix eyeView=multiply(rigidInverse(eyeToHead),view),eyeProjection{};
    eyeProjection.m[0][0]=2/(right-left);eyeProjection.m[0][2]=(right+left)/(right-left);
    eyeProjection.m[1][1]=2/(bottom-top);eyeProjection.m[1][2]=(bottom+top)/(bottom-top);
    eyeProjection.m[2][2]=projection.m[2][2];eyeProjection.m[2][3]=projection.m[2][3];eyeProjection.m[3][2]=-1;
    Matrix vp=multiply(eyeProjection,eyeView);std::memcpy(output,&vp,64);
    for(int i=0;i<3;++i)for(int j=0;j<3;++j)output[16+i*4+j]=eyeView.m[i][j];
    Matrix worldEye=rigidInverse(eyeView);for(int j=0;j<3;++j)output[28+j]=worldEye.m[j][3];
    return true;
}
}
