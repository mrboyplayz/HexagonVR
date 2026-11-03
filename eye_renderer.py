"""Explicit offscreen eye projection. No scene depth is invented from a flat image."""
import ctypes
import numpy as np

class EyeRenderer:
    def __init__(self,projections,size):
        from OpenGL import GL
        from OpenGL.GL.shaders import compileProgram,compileShader
        self.GL=GL;self.size=None;self.last_size=None
        self.program=compileProgram(compileShader('''#version 330 core
out vec2 uv;
void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.0-1.0,0,1);}
''',GL.GL_VERTEX_SHADER),compileShader('''#version 330 core
in vec2 uv;out vec4 color;
uniform sampler2D source;
uniform mat4 inverseEyeProjection;
uniform vec2 sourceTanHalf;
uniform float viewScale;
void main(){
 vec4 ray=inverseEyeProjection*vec4(uv*2.0-1.0,1.0,1.0);
 vec2 sourceUV=ray.xy*viewScale/(-ray.z*sourceTanHalf)*0.5+0.5;
 if(any(lessThan(sourceUV,vec2(0)))||any(greaterThan(sourceUV,vec2(1))))color=vec4(0,0,0,1);
 else color=texture(source,sourceUV);
}
''',GL.GL_FRAGMENT_SHADER))
        self.vao=GL.glGenVertexArrays(1);self.fbo=GL.glGenFramebuffers(1)
        self.source=self.new_texture();self.textures=[self.new_texture() for _ in projections]
        self.inverses=[np.asarray(np.linalg.inv(p),dtype=np.float32) for p in projections]
        self.resize(size)
    def resize(self,size):
        size=tuple(int(x)for x in size)
        G=self.GL;limit=int(G.glGetIntegerv(G.GL_MAX_TEXTURE_SIZE))
        if len(size)!=2 or min(size)<64 or max(size)>limit:raise ValueError('Eye resolution exceeds the graphics device limits')
        if self.size==size:return
        for tex in self.textures:
            G.glBindTexture(G.GL_TEXTURE_2D,tex);G.glTexImage2D(G.GL_TEXTURE_2D,0,G.GL_RGBA8,*size,0,G.GL_RGBA,G.GL_UNSIGNED_BYTE,None)
        self.size=size
    def new_texture(self):
        G=self.GL;tex=int(G.glGenTextures(1));G.glBindTexture(G.GL_TEXTURE_2D,tex)
        for parameter in (G.GL_TEXTURE_MIN_FILTER,G.GL_TEXTURE_MAG_FILTER):G.glTexParameteri(G.GL_TEXTURE_2D,parameter,G.GL_LINEAR)
        for parameter in (G.GL_TEXTURE_WRAP_S,G.GL_TEXTURE_WRAP_T):G.glTexParameteri(G.GL_TEXTURE_2D,parameter,G.GL_CLAMP_TO_EDGE)
        return tex
    def render(self,bgra,vertical_fov,view_scale=1):
        G=self.GL;h,w=bgra.shape[:2]
        G.glActiveTexture(G.GL_TEXTURE0);G.glBindTexture(G.GL_TEXTURE_2D,self.source)
        G.glPixelStorei(G.GL_UNPACK_ALIGNMENT,1)
        if self.last_size!=(w,h):
            G.glTexImage2D(G.GL_TEXTURE_2D,0,G.GL_RGBA8,w,h,0,G.GL_BGRA,G.GL_UNSIGNED_BYTE,bgra);self.last_size=(w,h)
        else:G.glTexSubImage2D(G.GL_TEXTURE_2D,0,0,0,w,h,G.GL_BGRA,G.GL_UNSIGNED_BYTE,bgra)
        ty=np.tan(np.radians(vertical_fov/2))
        G.glUseProgram(self.program);G.glBindVertexArray(self.vao)
        G.glUniform1i(G.glGetUniformLocation(self.program,'source'),0)
        G.glUniform2f(G.glGetUniformLocation(self.program,'sourceTanHalf'),ty*w/h,ty)
        G.glUniform1f(G.glGetUniformLocation(self.program,'viewScale'),view_scale)
        G.glBindFramebuffer(G.GL_FRAMEBUFFER,self.fbo);G.glViewport(0,0,*self.size)
        for tex,matrix in zip(self.textures,self.inverses):
            G.glFramebufferTexture2D(G.GL_FRAMEBUFFER,G.GL_COLOR_ATTACHMENT0,G.GL_TEXTURE_2D,tex,0)
            if G.glCheckFramebufferStatus(G.GL_FRAMEBUFFER)!=G.GL_FRAMEBUFFER_COMPLETE:raise RuntimeError('Incomplete eye framebuffer')
            G.glUniformMatrix4fv(G.glGetUniformLocation(self.program,'inverseEyeProjection'),1,G.GL_TRUE,matrix)
            G.glDrawArrays(G.GL_TRIANGLES,0,3)
        G.glBindFramebuffer(G.GL_FRAMEBUFFER,0);G.glFlush()
        return self.textures
