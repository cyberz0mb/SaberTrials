/* Fixed, reusable RGBA textures for Unicode chat; never written to disk. */
static image_t *stChatImages[224];
static qhandle_t stChatShaders[224];
static void ST_ChatResetImages() {
    memset(stChatImages,0,sizeof(stChatImages));memset(stChatShaders,0,sizeof(stChatShaders));
}
qhandle_t RE_STChatUpload(int slot,int width,int height,const byte *rgba) {
    if(slot<0 || slot>=224 || width<1 || height<1 || width>1024 || height>1024 || !rgba)return 0;
    R_IssuePendingRenderCommands();
    char name[32];Com_sprintf(name,sizeof(name),"*stchat%d",slot);
    if(!stChatImages[slot]) {
#ifdef ST_CHAT_REND2
        stChatImages[slot]=R_CreateImage(name,(byte *)rgba,width,height,IMGTYPE_COLORALPHA,IMGFLAG_CLAMPTOEDGE|IMGFLAG_MUTABLE|IMGFLAG_NOLIGHTSCALE,GL_RGBA8);
#else
        stChatImages[slot]=R_CreateImage(name,rgba,width,height,GL_RGBA,qfalse,qfalse,qfalse,GL_CLAMP);
#endif
        if(!stChatImages[slot])return 0;
        stChatShaders[slot]=RE_RegisterShaderFromImage(name,(int *)lightmaps2d,(byte *)stylesDefault,stChatImages[slot],qfalse);
    } else {
        image_t *image=stChatImages[slot];
        GL_Bind(image);
        if(image->width!=width || image->height!=height) {
            image->width=width;image->height=height;
#ifdef ST_CHAT_REND2
            image->uploadWidth=width;image->uploadHeight=height;
#endif
            qglTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,width,height,0,GL_RGBA,GL_UNSIGNED_BYTE,rgba);
        } else qglTexSubImage2D(GL_TEXTURE_2D,0,0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,rgba);
        qglTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
        qglTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    }
    return stChatShaders[slot];
}
