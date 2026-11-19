/* Preserve the approved panel and Western font; shape other scripts as whole lines. */
static qboolean ST_ChatLegacyText(const char *utf8,char *legacy,int capacity) {
    int used=0;
    while(*utf8 && used<capacity-1){int n;unsigned cp=ST_UTF8Read(utf8,&n);
        if(cp>255)return qfalse;legacy[used++]=(char)cp;utf8+=n;
    }
    legacy[used]=0;return qtrue;
}
static void CG_ChatBox_DrawStrings(void) {
    if(cg_chatBox.integer<=0 || cg.chatPanelMode==ST_CHAT_COLLAPSED)return;
    const qboolean expanded=cg.chatPanelMode==ST_CHAT_EXPANDED;
    const stChatLayout_t layout=ST_ChatLayout(st_chatSize.value,st_chatWidth.value,st_chatHeight.value,st_chatOpacity.value);
    const float s=layout.size,fontScale=.65f*s,stampScale=.47f*s;
    const float x=10,padding=12*s,stampColumn=32*s;
    const float bottom=cg.scoreBoardShowing?474:Com_Clampi(190,400,cg_chatBoxHeight.integer+33);
    const float height=Q_min(layout.height,bottom-25*s),y=bottom-height;
    typedef struct {int slot,line;float row;const char *stamp;stChatLine_t text;} displayLine_t;
    displayLine_t lines[ST_CHAT_MAX_LINES];int total=0;
    for(int i=0;i<MAX_CHATBOX_ITEMS;++i) {
        int slot=(cg.chatItemActive+i)%MAX_CHATBOX_ITEMS;
        const chatBoxItem_t *chat=&cg.chatItems[slot];
        if(!chat->string[0] || (!expanded&&chat->time<=cg.time))continue;
        char display[4096],utf8[4096],legacy[4096];
        ST_UTF8Sanitize(STTR_ChatText(chat,display,sizeof(display)),utf8,sizeof(utf8));
        if(ST_ChatLegacyText(utf8,legacy,sizeof(legacy))) {
            stChatLine_t wrapped[ST_CHAT_MAX_LINES];
            int count=ST_ChatWrap(legacy,wrapped,layout.width-2*padding-stampColumn,fontScale);
            for(int j=0;j<count;++j,++total){displayLine_t *line=&lines[total%ST_CHAT_MAX_LINES];
                line->slot=-1;line->line=0;line->row=16*s;line->stamp=j?NULL:chat->stamp;
                Q_strncpyz(line->text,wrapped[j],sizeof(line->text));
            }
        } else {
            stChatLayoutRequest_t request={slot,utf8,layout.width-2*padding-stampColumn,11*s,18*s,
                chat->translated[0]?chat->translationTarget:0};
            stChatLayoutResult_t result;
            if(trap->ST_ChatLayout(&request,&result)) {
                for(int j=0;j<result.lines;++j,++total){displayLine_t *line=&lines[total%ST_CHAT_MAX_LINES];
                    line->slot=slot;line->line=j;line->row=18*s;line->stamp=j?NULL:chat->stamp;line->text[0]=0;
                }
            } else {
                displayLine_t *line=&lines[total++%ST_CHAT_MAX_LINES];line->slot=-1;line->line=0;
                line->row=16*s;line->stamp=chat->stamp;
                Q_strncpyz(line->text,"Chat font unavailable. Restore the translator font files.",sizeof(line->text));
            }
        }
    }
    if(!total&&!expanded)return;
    ST_ChatDrawFrame(ST_ChatPic,st_hudMedia.chatFill,st_hudMedia.chatFrame,x,y,layout.width,height,s,s,layout.opacity);
    const float headerAspect=ST_HudAspect();
    ST_ChatPic(x,y-11*s,102*s*headerAspect,26*s,0,0,1,1,st_hudMedia.chatHeader,NULL);
    ST_HudText(x/headerAspect+32*s,y-5*s,8*s,"CHAT",st_hudWhite);
    vec4_t timeColor={.51f,.77f,.89f,1};float textY=y+13*s;
    int count=0;float used=0;
    while(count<Q_min(total,ST_CHAT_MAX_LINES)) {
        float row=lines[(total-1-count)%ST_CHAT_MAX_LINES].row;
        if(used+row>height-20*s)break;used+=row;++count;
    }
    if(!count)CG_Text_Paint(x+padding,textY,fontScale,timeColor,"No recent messages",0,0,ITEM_TEXTSTYLE_OUTLINED,FONT_SMALL2);
    for(int i=0;i<count;++i){const displayLine_t *line=&lines[(total-count+i)%ST_CHAT_MAX_LINES];
        if(line->stamp){CG_Text_Paint(x+padding,textY+2*s,stampScale,timeColor,line->stamp,0,0,ITEM_TEXTSTYLE_OUTLINED,FONT_SMALL2);
            CG_FillRect(x+padding+stampColumn-6*s,textY,.4f*s,10*s,timeColor);}
        if(line->slot>=0)trap->ST_ChatDraw(line->slot,x+padding+stampColumn,textY,line->line,1);
        else CG_Text_Paint(x+padding+stampColumn,textY,fontScale,colorWhite,line->text,0,0,ITEM_TEXTSTYLE_OUTLINED,FONT_SMALL2);
        textY+=line->row;
    }
}
