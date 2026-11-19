// Original vector HUD artwork following the user's MVP reference, without
// letterbox bars. Rasterized with Windows GDI+; no font software is packaged.
using System;
using System.IO;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Globalization;
using System.Collections.Generic;

public static class MvpArt {
    static Bitmap bitmap;
    static Graphics g;
    static string output;
    static Color cyan = Color.FromArgb(10,225,255), gold = Color.FromArgb(255,203,21);
    // Angular display lettering, with counters separated by '|'. The same
    // outlines serve the headline and the live name/count atlas.
    static Dictionary<char,string> letters = new Dictionary<char,string> {
        {'A',"0,100 28,0 64,0 92,100 67,100 61,76 31,76 25,100|37,54 55,54 46,22"},
        {'B',"0,0 73,0 92,17 92,40 81,50 92,61 92,83 75,100 0,100|24,22 24,40 64,40 68,35 68,26 64,22|24,61 24,78 64,78 68,74 68,65 64,61"},
        {'C',"92,0 20,0 0,20 0,80 20,100 92,100 92,76 30,76 24,70 24,30 30,24 92,24"},
        {'D',"0,0 70,0 92,22 92,78 70,100 0,100|24,24 24,76 59,76 68,67 68,33 59,24"},
        {'E',"0,0 92,0 92,23 24,23 24,39 79,39 79,61 24,61 24,77 92,77 92,100 0,100"},
        {'F',"0,0 92,0 92,24 24,24 24,42 76,42 76,66 24,66 24,100 0,100"},
        {'G',"92,0 20,0 0,20 0,80 20,100 92,100 92,43 49,43 49,65 68,65 68,76 30,76 24,70 24,30 30,24 92,24"},
        {'H',"0,0 24,0 24,38 68,38 68,0 92,0 92,100 68,100 68,62 24,62 24,100 0,100"},
        {'I',"0,0 34,0 34,100 0,100"},
        {'J',"42,0 92,0 92,79 71,100 20,100 0,80 0,61 24,61 24,71 30,77 62,77 68,71 68,24 42,24"},
        {'K',"0,0 24,0 24,39 39,39 64,0 92,0 59,50 92,100 63,100 39,62 24,62 24,100 0,100"},
        {'L',"0,0 24,0 24,76 92,76 92,100 0,100"},
        {'M',"0,100 0,0 24,0 55,36 86,0 110,0 110,100 85,100 85,37 55,70 25,37 25,100"},
        {'N',"0,100 0,0 24,0 68,61 68,0 92,0 92,100 68,100 24,39 24,100"},
        {'O',"20,0 72,0 92,20 92,80 72,100 20,100 0,80 0,20|30,24 24,30 24,70 30,76 62,76 68,70 68,30 62,24"},
        {'P',"0,100 0,0 73,0 92,19 92,50 73,69 24,69 24,100|24,24 24,45 62,45 68,39 68,30 62,24"},
        {'Q',"20,0 72,0 92,20 92,76 79,89 94,100 63,100 55,93 20,93 0,73 0,20|30,24 24,30 24,63 30,69 62,69 68,63 68,30 62,24"},
        {'R',"0,100 0,0 73,0 92,19 92,48 74,65 94,100 65,100 45,66 24,66 24,100|24,24 24,43 62,43 68,37 68,30 62,24"},
        {'S',"92,0 19,0 0,19 0,42 19,61 64,61 68,65 68,73 64,77 0,77 0,100 73,100 92,81 92,58 73,39 28,39 24,35 24,27 28,23 92,23"},
        {'T',"0,0 92,0 92,25 58,25 58,100 34,100 34,25 0,25"},
        {'U',"0,0 24,0 24,70 30,76 62,76 68,70 68,0 92,0 92,80 72,100 20,100 0,80"},
        {'V',"0,0 26,0 46,70 66,0 92,0 62,100 30,100"},
        {'W',"0,0 25,0 40,62 56,0 80,0 96,62 111,0 136,0 110,100 84,100 68,43 52,100 26,100"},
        {'X',"0,0 28,0 46,30 64,0 92,0 61,50 92,100 64,100 46,70 28,100 0,100 31,50"},
        {'Y',"0,0 27,0 46,34 65,0 92,0 58,60 58,100 34,100 34,60"},
        {'Z',"0,0 92,0 92,24 32,76 92,76 92,100 0,100 0,76 60,24 0,24"},
        {'0',"20,0 72,0 92,20 92,80 72,100 20,100 0,80 0,20|30,24 24,30 24,70 30,76 62,76 68,70 68,30 62,24"},
        {'1',"10,20 32,0 58,0 58,76 80,76 80,100 10,100 10,76 32,76 32,27 10,43"},
        {'2',"0,0 72,0 92,20 92,43 24,77 92,77 92,100 0,100 0,64 68,30 68,24 0,24"},
        {'3',"0,0 73,0 92,19 92,40 82,50 92,60 92,81 73,100 0,100 0,76 64,76 68,72 68,65 64,61 25,61 25,39 64,39 68,35 68,28 64,24 0,24"},
        {'4',"0,0 24,0 24,40 62,40 62,0 86,0 86,100 62,100 62,64 0,64"},
        {'5',"0,0 92,0 92,24 24,24 24,39 73,39 92,58 92,81 73,100 0,100 0,76 64,76 68,72 68,67 64,63 0,63"},
        {'6',"20,0 92,0 92,24 30,24 24,30 24,39 73,39 92,58 92,81 73,100 20,100 0,80 0,20|24,63 24,71 30,77 62,77 68,71 68,69 62,63"},
        {'7',"0,0 92,0 92,24 46,100 18,100 63,24 0,24"},
        {'8',"20,0 72,0 92,20 92,39 81,50 92,61 92,80 72,100 20,100 0,80 0,61 11,50 0,39 0,20|30,22 24,28 24,34 30,40 62,40 68,34 68,28 62,22|30,60 24,66 24,72 30,78 62,78 68,72 68,66 62,60"},
        {'9',"20,0 72,0 92,20 92,80 72,100 0,100 0,76 62,76 68,70 68,61 19,61 0,42 0,20|30,23 24,29 24,31 30,37 68,37 68,29 62,23"}
    };
    static PointF[] Points(string s) {
        string[] chunks=s.Split(new char[]{' '},StringSplitOptions.RemoveEmptyEntries);
        PointF[] p=new PointF[chunks.Length];
        for(int i=0;i<p.Length;i++){string[] xy=chunks[i].Split(',');p[i]=new PointF(float.Parse(xy[0],CultureInfo.InvariantCulture),float.Parse(xy[1],CultureInfo.InvariantCulture));}
        return p;
    }
    static void Canvas(int w,int h,float lw,float lh) {
        bitmap=new Bitmap(w,h,PixelFormat.Format32bppArgb);g=Graphics.FromImage(bitmap);
        g.SmoothingMode=SmoothingMode.AntiAlias;g.PixelOffsetMode=PixelOffsetMode.HighQuality;
        g.Clear(Color.Transparent);g.ScaleTransform(w/lw,h/lh);
    }
    static void Save(string name){bitmap.Save(Path.Combine(output,name+".png"),ImageFormat.Png);g.Dispose();bitmap.Dispose();}
    static void Line(string points,Color c,bool bright) {
        float[] widths=bright?new float[]{20,12,7,3,1}:new float[]{12,6,2};
        int[] alphas=bright?new int[]{7,15,35,230,255}:new int[]{10,30,210};
        for(int i=0;i<widths.Length;i++)using(Pen pen=new Pen(Color.FromArgb(alphas[i],i==4?Color.FromArgb(210,251,255):c),widths[i])) {
            pen.LineJoin=LineJoin.Round;g.DrawLines(pen,Points(points));
        }
    }
    static void Panel(string points) {
        using(GraphicsPath p=new GraphicsPath()){p.AddPolygon(Points(points));
            using(LinearGradientBrush b=new LinearGradientBrush(p.GetBounds(),Color.FromArgb(236,0,17,25),Color.FromArgb(220,0,4,9),90))g.FillPath(b,p);
        }
    }
    static GraphicsPath Glyph(char c,out float advance) {
        GraphicsPath p=new GraphicsPath(FillMode.Alternate);c=char.ToUpperInvariant(c);
        if(c==' '){advance=48;return p;}
        if(letters.ContainsKey(c)){foreach(string poly in letters[c].Split('|'))p.AddPolygon(Points(poly));advance=p.GetBounds().Width+12;}
        else {
            using(FontFamily font=new FontFamily("Arial"))p.AddString(c.ToString(),font,(int)FontStyle.Bold,115,new PointF(0,-8),StringFormat.GenericTypographic);
            RectangleF b=p.GetBounds();using(Matrix m=new Matrix()){m.Translate(-b.X,0);p.Transform(m);}advance=b.Width+12;
        }
        return p;
    }
    static void PaintText(GraphicsPath p,bool metallic,Color color) {
        RectangleF b=p.GetBounds();if(b.Width==0)return;
        using(Pen shadow=new Pen(Color.FromArgb(210,0,7,12),3)){shadow.LineJoin=LineJoin.Round;g.DrawPath(shadow,p);}
        if(metallic){
            int[] widths={14,12,10,8,6,4,2}, alphas={5,6,9,14,25,55,140};
            for(int i=0;i<widths.Length;i++)using(Pen pen=new Pen(Color.FromArgb(alphas[i],15,180,235),widths[i])){pen.LineJoin=LineJoin.Round;g.DrawPath(pen,p);}
            using(LinearGradientBrush brush=new LinearGradientBrush(new PointF(0,b.Top),new PointF(0,b.Bottom),Color.White,Color.White)){
                ColorBlend blend=new ColorBlend();blend.Positions=new float[]{0,.42f,.47f,.85f,1};
                blend.Colors=new Color[]{Color.White,Color.FromArgb(223,248,255),Color.FromArgb(170,212,233),Color.FromArgb(235,252,255),Color.FromArgb(127,197,230)};
                brush.InterpolationColors=blend;g.FillPath(brush,p);
            }
            using(Pen pen=new Pen(Color.FromArgb(215,224,250,255),.8f)){pen.LineJoin=LineJoin.Round;g.DrawPath(pen,p);}
        }else using(Brush brush=new SolidBrush(color))g.FillPath(brush,p);
    }
    static void Text(string s,float x,float y,float width,float height,bool metal,Color color,float tracking) {
        using(GraphicsPath all=new GraphicsPath(FillMode.Alternate)){
            float offset=0;
            foreach(char c in s){float advance;using(GraphicsPath p=Glyph(c,out advance)){
                if(p.PointCount>0){using(Matrix m=new Matrix()){m.Translate(offset,0);p.Transform(m);}all.AddPath(p,false);}
            }offset+=advance+tracking;}
            RectangleF b=all.GetBounds();using(Matrix m=new Matrix(width/b.Width,0,0,height/b.Height,x-b.X*width/b.Width,y-b.Y*height/b.Height))all.Transform(m);
            PaintText(all,metal,color);
        }
    }
    static void Plain(string s,float x,float y,float width,float height,bool italic) {
        using(GraphicsPath p=new GraphicsPath())using(FontFamily family=new FontFamily("Arial")){
            p.AddString(s,family,(int)(FontStyle.Bold|(italic?FontStyle.Italic:FontStyle.Regular)),100,new PointF(0,0),StringFormat.GenericTypographic);
            RectangleF b=p.GetBounds();using(Matrix m=new Matrix(width/b.Width,0,0,height/b.Height,x-b.X*width/b.Width,y-b.Y*height/b.Height))p.Transform(m);
            PaintText(p,false,Color.White);
        }
    }
    static void Emblem() {
        using(Pen p=new Pen(cyan,3)){g.DrawEllipse(p,54,23,126,126);g.DrawEllipse(p,61,30,112,112);}
        using(GraphicsPath wings=new GraphicsPath()){
            wings.AddBezier(108,136,55,121,58,70,85,47);wings.AddBezier(85,47,68,89,95,91,108,136);wings.CloseFigure();
            wings.AddBezier(126,136,179,121,176,70,149,47);wings.AddBezier(149,47,166,89,139,91,126,136);wings.CloseFigure();
            using(Brush b=new SolidBrush(cyan))g.FillPath(b,wings);
        }
        using(Brush b=new SolidBrush(cyan))g.FillPolygon(b,Points("117,27 112,99 117,143 122,99"));
        using(Brush b=new SolidBrush(Color.FromArgb(230,250,255)))g.FillPolygon(b,Points("117,81 121,98 133,89 126,104 144,108 126,112 133,128 121,118 117,142 113,118 100,129 108,112 90,108 108,104 100,90 113,98"));
    }
    public static void Generate(string directory,string metrics) {
        output=directory;Directory.CreateDirectory(output);
        Canvas(2048,2048,1672,941);
        Line("17,64 56,24 279,24 292,35 510,35 534,14 1138,14 1163,35 1380,35 1394,24 1615,24 1654,64 1654,870 1609,916 1030,916 1015,927 657,927 642,916 63,916 17,870 17,64",cyan,true);
        Line("30,76 68,36 282,36 294,44 505,44",cyan,false);
        Line("1168,44 1384,44 1395,36 1603,36 1641,76 1641,862 1600,904 1030,904 1014,916 658,916 643,904 71,904 30,862 30,76",cyan,false);
        Save("frame");
        string[] titles={"MATCH MVP","DUEL WINNER","MATCH WINNER","CHAMPION"};
        string[] titleFiles={"title","title_duel","title_match","title_champion"};
        for(int variant=0;variant<titles.Length;variant++){
        Canvas(2048,512,824,160);
        Text("SABER TRIALS",176,28,472,20,false,cyan,22);
        float titleWidth=variant==1 || variant==2 ? 760 : 660;
        Text(titles[variant],(824-titleWidth)/2,62,titleWidth,49,true,Color.White,0);
        Line("24,129 401,129 412,118 424,129 800,129",gold,true);
        Line("90,139 365,139 355,135 90,135",gold,false);
        Line("460,139 736,139 736,135 470,135",gold,false);
        Line("412,118 425,131 412,144 399,131 412,118",gold,true);
        Line("412,125 418,131 412,137 406,131 412,125",gold,false);
        Save(titleFiles[variant]);
        }
        for(int variant=0;variant<2;variant++){
        Canvas(2048,512,920,246);
        string card="9,85 73,10 166,10 192,38 861,38 913,85 837,158 71,158 9,85";
        Panel(card);Line(card,cyan,true);
        string counter="286,145 353,215 583,215 646,145";
        Panel(counter);Line(counter,cyan,true);
        Line("367,227 568,227",gold,true);
        Line("229,132 351,132 366,116 585,116 600,132 752,132",gold,true);
        Line("296,151 637,151",gold,false);
        Line("747,122 875,122",cyan,false);
        Plain(variant==0 ? "K I L L S" : "S C O R E",410,125,127,18,true);
        Emblem();
        using(Brush b=new SolidBrush(Color.FromArgb(0,131,181)))foreach(int offset in new int[]{0,17,34}){
            g.FillPolygon(b,new PointF[]{new PointF(204+offset,99),new PointF(227+offset,75),new PointF(240+offset,75),new PointF(217+offset,99)});
            g.FillPolygon(b,new PointF[]{new PointF(794+offset,99),new PointF(817+offset,75),new PointF(830+offset,75),new PointF(807+offset,99)});
        }
        Save(variant==0 ? "nameplate" : "nameplate_score");
        }
        for(int variant=0;variant<2;variant++){
        Canvas(1024,256,440,86);
        Line("7,9 238,9 263,37 416,37",gold,true);
        using(Pen p=new Pen(Color.White,3)){
            g.DrawRectangle(p,12,23,48,35);g.DrawLine(p,20,23,20,58);g.DrawLine(p,52,23,52,58);
            for(int y=29;y<58;y+=10){g.DrawLine(p,12,y,20,y);g.DrawLine(p,52,y,60,y);}
        }
        using(Brush b=new SolidBrush(Color.White))g.FillPolygon(b,Points("28,29 28,52 45,40"));
        Plain(variant==0 ? "MVP CAM" : "WINNER CAM",88,24,variant==0 ? 130 : 180,22,true);
        Plain("E N D  O F  M A T C H  R E P L A Y",82,56,291,11,true);
        Save(variant==0 ? "caption" : "caption_winner");
        }
        for(int variant=0;variant<2;variant++){
        Canvas(1024,256,420,86);
        Line("5,48 104,48 134,17 405,17",gold,true);
        Plain(variant==0 ? "SKIP REPLAY" : "CONTINUE",147,32,179,22,true);
        Plain("Press Esc/Enter",147,64,179,14,false);
        for(int x=342;x<396;x+=18){
            string shape=String.Format(CultureInfo.InvariantCulture,"{0},27 {1},27 {2},41 {1},56 {0},56 {3},41",x,x+8,x+19,x+11);
            using(Brush b=new SolidBrush(gold))g.FillPolygon(b,Points(shape));
        }
        Save(variant==0 ? "skip" : "continue");
        }
        Canvas(2048,1024,2048,1024);
        List<string> advances=new List<string>();
        for(int c=32;c<=126;c++){
            int i=c-32;float advance;using(GraphicsPath p=Glyph((char)c,out advance)){
                // 128x160 cells: 16px left and 24px top inset. Wide W is
                // scaled to the cell along with its advance to prevent bleed.
                float sx=Math.Min(1,96/Math.Max(1,advance-12));
                using(Matrix m=new Matrix(sx,0,0,1,(i%16)*128+16,(i/16)*160+24))p.Transform(m);
                PaintText(p,true,Color.White);advance=(advance-12)*sx+12;
            }
            advances.Add(advance.ToString("0.000",CultureInfo.InvariantCulture)+"f");
        }
        Save("type");
        File.WriteAllText(metrics,"/* Generated with the matching MVP glyph atlas. */\nstatic const float stMvpHudAdvance[]={"+String.Join(",",advances.ToArray())+"};\n");
    }
}
