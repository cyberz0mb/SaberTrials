param([string]$First,[string]$Second,[string]$Third)
Add-Type -TypeDefinition @'
using System;
using System.Drawing;
public static class MvpImageCompare {
    public static double Same(string first,string second) {
        using(var a=new Bitmap(first)) using(var b=new Bitmap(second)) {
            if(a.Width!=b.Width || a.Height!=b.Height)return 0;
            long same=0;
            for(int y=0;y<a.Height;y++)for(int x=0;x<a.Width;x++) {
                var p=a.GetPixel(x,y);var q=b.GetPixel(x,y);
                if(Math.Abs(p.R-q.R)<8 && Math.Abs(p.G-q.G)<8 && Math.Abs(p.B-q.B)<8)++same;
            }
            return (double)same/(a.Width*a.Height);
        }
    }
}
'@ -ReferencedAssemblies System.Drawing
@{stable=[MvpImageCompare]::Same($First,$Second);scoreboard=[MvpImageCompare]::Same($Second,$Third)} | ConvertTo-Json -Compress
