/* Windows Unicode shaping and rasterization; no chat files or network access. */
#ifndef ST_CHAT_RASTER_H
#define ST_CHAT_RASTER_H
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <dwrite_3.h>
#include <d2d1.h>
#include <wincodec.h>
#include <wrl/client.h>
#include <algorithm>
#include <cmath>
#include <string>
#include <vector>
#include "st_utf8.h"
#include "st_translation_languages.h"
#pragma comment(lib,"dwrite.lib")
#pragma comment(lib,"d2d1.lib")
#pragma comment(lib,"windowscodecs.lib")
#pragma comment(lib,"ole32.lib")
namespace stchat {
using Microsoft::WRL::ComPtr;
struct Bitmap {int width=0,height=0,lines=0;float row=0,inkWidth=0;std::vector<unsigned char> rgba;};
struct ColorSpan {UINT32 start,length;int color;};
class Rasterizer {
    ComPtr<IDWriteFactory3> write;
    ComPtr<ID2D1Factory> draw;
    ComPtr<IWICImagingFactory> imaging;
    ComPtr<IDWriteFontCollection1> collection;
    ComPtr<IDWriteFontFallback> fallback;
    bool initialized=false,available=false;
public:
    bool init(const std::wstring& folder) {
        if(initialized)return available;
        initialized=true;
        CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
        if(FAILED(DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED,__uuidof(IDWriteFactory3),
            reinterpret_cast<IUnknown**>(write.GetAddressOf()))) ||
           FAILED(D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED,draw.GetAddressOf())) ||
           FAILED(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(imaging.GetAddressOf()))))return false;
        ComPtr<IDWriteFontSetBuilder> builder;
        if(FAILED(write->CreateFontSetBuilder(&builder)))return false;
        const wchar_t *files[]={L"NotoSans-Regular.ttf",L"NotoSansArabic-Regular.ttf",L"NotoSansDevanagari-Regular.ttf",
            L"NotoSansCJKjp-Regular.otf",L"NotoSansCJKsc-Regular.otf",L"NotoSansCJKtc-Regular.otf",L"NotoSansCJKkr-Regular.otf"};
        for(const wchar_t *file:files) {
            ComPtr<IDWriteFontFaceReference> reference;
            if(FAILED(write->CreateFontFaceReference((folder+L"\\"+file).c_str(),nullptr,0,DWRITE_FONT_SIMULATIONS_NONE,&reference)) ||
               FAILED(builder->AddFontFaceReference(reference.Get())))return false;
        }
        ComPtr<IDWriteFontSet> fontSet;
        if(FAILED(builder->CreateFontSet(&fontSet)) || FAILED(write->CreateFontCollectionFromFontSet(fontSet.Get(),&collection)))return false;
        ComPtr<IDWriteFontFallbackBuilder> fb;
        if(FAILED(write->CreateFontFallbackBuilder(&fb)))return false;
        auto mapping=[&](UINT32 first,UINT32 last,const wchar_t *family,const wchar_t *locale=nullptr) {
            DWRITE_UNICODE_RANGE range={first,last};const wchar_t *names[]={family};
            return SUCCEEDED(fb->AddMapping(&range,1,names,1,collection.Get(),locale));
        };
        if(!mapping(0x600,0x8ff,L"Noto Sans Arabic") || !mapping(0xfb50,0xfeff,L"Noto Sans Arabic") ||
           !mapping(0x900,0x97f,L"Noto Sans Devanagari") || !mapping(0xa8e0,0xa8ff,L"Noto Sans Devanagari") ||
           !mapping(0x1100,0x11ff,L"Noto Sans CJK KR") || !mapping(0x3130,0x318f,L"Noto Sans CJK KR") ||
           !mapping(0xac00,0xd7af,L"Noto Sans CJK KR") || !mapping(0x3040,0x30ff,L"Noto Sans CJK JP") ||
           !mapping(0x31f0,0x31ff,L"Noto Sans CJK JP"))return false;
        for(auto locale:{L"ja-JP",L"ko-KR",L"zh-TW",L"zh-CN"}) {
            const wchar_t *family=locale[0]=='j'?L"Noto Sans CJK JP":locale[0]=='k'?L"Noto Sans CJK KR":
                locale[3]=='T'?L"Noto Sans CJK TC":L"Noto Sans CJK SC";
            if(!mapping(0x2e80,0x303f,family,locale) || !mapping(0x3400,0x9fff,family,locale) ||
               !mapping(0xf900,0xfaff,family,locale) || !mapping(0xff00,0xffef,family,locale))return false;
        }
        if(!mapping(0x2e80,0x303f,L"Noto Sans CJK SC") || !mapping(0x3400,0x9fff,L"Noto Sans CJK SC") ||
           !mapping(0xf900,0xfaff,L"Noto Sans CJK SC") || !mapping(0xff00,0xffef,L"Noto Sans CJK SC") ||
           FAILED(fb->CreateFontFallback(&fallback)))return false;
        available=true;return true;
    }

    bool render(const char *input,int width,float fontSize,float row,int language,Bitmap& bitmap,
                bool menu=false,bool measureOnly=false) {
        if(!available || !input || strlen(input)>4095 || width<8 || width>1024 || fontSize<6 || fontSize>64 || row<fontSize || row>80)return false;
        char normalized[12288];ST_UTF8Sanitize(input,normalized,sizeof(normalized));
        std::wstring text;std::vector<ColorSpan> spans;
        int color=7;UINT32 spanStart=0;bool arabic=false,japanese=false,korean=false,arabicRun=false;
        for(const char *p=normalized;*p;) {
            if(p[0]=='^'&&p[1]>='0'&&p[1]<='9') {
                if(text.size()>spanStart)spans.push_back({spanStart,(UINT32)text.size()-spanStart,color});
                color=p[1]-'0';spanStart=(UINT32)text.size();p+=2;continue;
            }
            int n;unsigned cp=ST_UTF8Read(p,&n);p+=n;
            if(cp<32&&cp!='\n')continue;
            if((cp>=0x202a&&cp<=0x202e)||(cp>=0x2066&&cp<=0x2069))continue;
            // Trusted isolates keep Arabic sentence punctuation with its body
            // after an LTR sender/tag. User-supplied bidi controls remain stripped.
            if(cp=='\n'&&arabicRun){text+=(wchar_t)0x2069;arabicRun=false;}
            if(cp>=0x600&&cp<=0x8ff&&!arabicRun){text+=(wchar_t)0x2067;arabicRun=true;}
            arabic|=cp>=0x600&&cp<=0x8ff;japanese|=cp>=0x3040&&cp<=0x30ff;korean|=cp>=0xac00&&cp<=0xd7af;
            if(cp>0xffff){cp-=0x10000;text+=(wchar_t)(0xd800+(cp>>10));text+=(wchar_t)(0xdc00+(cp&1023));}
            else text+=(wchar_t)cp;
        }
        if(text.empty())return false;
        if(arabicRun)text+=(wchar_t)0x2069;
        spans.push_back({spanStart,(UINT32)text.size()-spanStart,color});
        std::wstring locale;
        const char *loc=ST_LanguageLocale(language);
        while(*loc)locale+=(wchar_t)*loc++;
        if(language<=0){if(japanese)locale=L"ja-JP";else if(korean)locale=L"ko-KR";else if(arabic)locale=L"ar-SA";}
        ComPtr<IDWriteTextFormat> format;
        if(FAILED(write->CreateTextFormat(L"Noto Sans",collection.Get(),menu?DWRITE_FONT_WEIGHT_SEMI_BOLD:DWRITE_FONT_WEIGHT_NORMAL,DWRITE_FONT_STYLE_NORMAL,
            DWRITE_FONT_STRETCH_NORMAL,fontSize,locale.c_str(),&format)))return false;
        // Chat starts with a sender/tag. Let bidi shaping order the Arabic run,
        // retaining the position of a preceding Latin sender and original line.
        bool rtl=false;
        for(wchar_t cp:text) {
            if((cp>=L'A'&&cp<=L'Z')||(cp>=L'a'&&cp<=L'z'))break;
            if(cp>=0x600&&cp<=0x8ff){rtl=true;break;}
            if(cp>=0x900)break;
        }
        if(rtl&&text.find(L'\n')==std::wstring::npos) {
            format->SetReadingDirection(DWRITE_READING_DIRECTION_RIGHT_TO_LEFT);
            if(menu)format->SetTextAlignment(DWRITE_TEXT_ALIGNMENT_TRAILING);
        }
        format->SetWordWrapping(menu?DWRITE_WORD_WRAPPING_NO_WRAP:DWRITE_WORD_WRAPPING_WRAP);
        format->SetLineSpacing(DWRITE_LINE_SPACING_METHOD_UNIFORM,row,row*.80f);
        ComPtr<IDWriteTextLayout> layout;
        if(FAILED(write->CreateTextLayout(text.data(),(UINT32)text.size(),format.Get(),(float)width-4,row*16,&layout)))return false;
        ComPtr<IDWriteTextLayout2> layout2;
        if(FAILED(layout.As(&layout2)) || FAILED(layout2->SetFontFallback(fallback.Get())))return false;
        DWRITE_TEXT_METRICS metrics={};if(FAILED(layout->GetMetrics(&metrics)))return false;
        bitmap.inkWidth=metrics.widthIncludingTrailingWhitespace;
        if(measureOnly)return true;
        if(menu)width=std::min(width,std::max(8,(int)std::ceil(bitmap.inkWidth)+4));
        bitmap.lines=std::min(16,(int)metrics.lineCount);bitmap.row=row;
        // The classic renderer requires power-of-two image dimensions.
        auto power2=[](int n){int result=1;while(result<n&&result<1024)result*=2;return result;};
        bitmap.width=power2(width);bitmap.height=power2((int)std::ceil(row*bitmap.lines)+4);
        ComPtr<IWICBitmap> surface;
        if(FAILED(imaging->CreateBitmap(bitmap.width,bitmap.height,GUID_WICPixelFormat32bppPBGRA,WICBitmapCacheOnLoad,&surface)))return false;
        ComPtr<ID2D1RenderTarget> target;
        auto props=D2D1::RenderTargetProperties(D2D1_RENDER_TARGET_TYPE_SOFTWARE,
            D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM,D2D1_ALPHA_MODE_PREMULTIPLIED),96,96);
        if(FAILED(draw->CreateWicBitmapRenderTarget(surface.Get(),props,&target)))return false;
        target->SetTextAntialiasMode(D2D1_TEXT_ANTIALIAS_MODE_GRAYSCALE);
        static const float colors[10][3]={{0,0,0},{1,0,0},{0,1,0},{1,1,0},{.2f,.4f,1},{0,1,1},{1,0,1},{1,1,1},{1,.5f,0},{.5f,.5f,.5f}};
        ComPtr<ID2D1SolidColorBrush> brushes[10];
        for(int i=0;i<10;++i)if(FAILED(target->CreateSolidColorBrush(D2D1::ColorF(colors[i][0],colors[i][1],colors[i][2]),&brushes[i])))return false;
        for(const auto& span:spans)layout->SetDrawingEffect(brushes[span.color].Get(),{span.start,span.length});
        target->BeginDraw();target->Clear(D2D1::ColorF(0,0,0,0));
        target->DrawTextLayout(D2D1::Point2F(2,1),layout.Get(),brushes[7].Get(),D2D1_DRAW_TEXT_OPTIONS_CLIP);
        if(FAILED(target->EndDraw()))return false;
        ComPtr<IWICBitmapLock> locked;WICRect rect={0,0,bitmap.width,bitmap.height};
        if(FAILED(surface->Lock(&rect,WICBitmapLockRead,&locked)))return false;
        UINT stride=0,size=0;BYTE *pixels=nullptr;
        if(FAILED(locked->GetStride(&stride)) || FAILED(locked->GetDataPointer(&size,&pixels)))return false;
        bitmap.rgba.resize((size_t)bitmap.width*bitmap.height*4);
        for(int y=0;y<bitmap.height;++y)for(int x=0;x<bitmap.width;++x){
            const BYTE *p=pixels+y*stride+x*4;BYTE *q=&bitmap.rgba[((size_t)y*bitmap.width+x)*4];
            q[3]=p[3];for(int c=0;c<3;++c)q[c]=p[3]?(BYTE)std::min(255,(int)p[2-c]*255/p[3]):0;
        }
        return true;
    }
};
}
#endif
#endif
