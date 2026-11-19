param([Parameter(Mandatory=$true)][string]$Output,[Parameter(Mandatory=$true)][string]$Metrics)
$ErrorActionPreference='Stop'
# Reuse the established antialiased authoring functions and main-menu artwork.
. "$PSScriptRoot/Generate-Main-Menu-Art.ps1" -Layout "$PSScriptRoot/../development-source/main-menu/layout.json" -Output $Output
function Shape($points,[bool]$focus,[bool]$fill=$true){
 $v=[Drawing.PointF[]]@($points|ForEach-Object{[Drawing.PointF]::new([float]$_[0]*2.6125,[float]$_[1]*1.960416667)})
 $path=[Drawing.Drawing2D.GraphicsPath]::new();$path.AddPolygon($v)
 if($fill){
  $a=if($focus){[Drawing.Color]::FromArgb(238,0,91,124)}else{[Drawing.Color]::FromArgb(215,3,21,32)}
  $b=[Drawing.Color]::FromArgb(212,1,12,21)
  $brush=[Drawing.Drawing2D.LinearGradientBrush]::new([Drawing.PointF]::new(0,0),[Drawing.PointF]::new(0,90),$a,$b)
  $g.FillPath($brush,$path);$brush.Dispose()
 }
 Draw-Contour $points 'cyan' $focus
 # A fine pearly highlight gives the surface a bevel without a second box.
 $pen=[Drawing.Pen]::new([Drawing.Color]::FromArgb($(if($focus){240}else{125}),199,243,255),.7)
 $g.DrawLine($pen,$v[0],$v[1]);$pen.Dispose();$path.Dispose()
}
foreach($kind in @('action','tab','field','panel')){foreach($focus in @($false,$true)){
 New-Canvas 1024 256 (200*2.6125) (48*1.960416667)
 $p=switch($kind){
 'tab' {@(@(12,5),@(194,5),@(183,43),@(1,43),@(12,5))}
 'field' {@(@(5,5),@(191,5),@(195,12),@(195,36),@(191,43),@(5,43),@(1,36),@(1,12),@(5,5))}
 'panel' {@(@(8,5),@(188,5),@(195,16),@(195,34),@(188,43),@(8,43),@(1,34),@(1,16),@(8,5))}
 default {@(@(8,5),@(194,5),@(194,32),@(183,43),@(1,43),@(1,16),@(8,5))}
 }
 if($kind -eq 'panel'){Draw-Contour $p 'gold' $true}else{Shape $p $focus $true}
 Save-Canvas ($kind+$(if($focus){'_focus'}else{'_idle'}))
}}
# One transparent shell; connected content behind the header is never baked in.
New-Canvas 2048 2048 1672 941
$outer=@(@(6,27),@(19,9),@(311,9),@(320,17),@(329,9),@(620,9),@(634,27),@(634,451),@(620,468),@(21,468),@(6,451),@(6,27))
Draw-Contour $outer 'cyan' $true
Draw-Contour @(@(10,31),@(23,14),@(617,14),@(630,31),@(630,448),@(617,463),@(25,463),@(10,448),@(10,31)) 'cyan'
Draw-Contour @(@(244,12),@(315,12),@(320,18),@(325,12),@(390,12)) 'gold' $true
Draw-Contour @(@(28,462),@(234,462),@(240,467)) 'gold'
Draw-Contour @(@(414,467),@(420,462),@(611,462)) 'gold'
Draw-Contour @(@(12,42),@(22,51),@(474,51),@(481,44),@(621,44)) 'cyan'
Draw-Contour @(@(23,141),@(315,141),@(320,135),@(325,141),@(320,147),@(315,141),@(617,141)) 'gold'
Draw-Contour @(@(13,432),@(22,442),@(618,442),@(629,432)) 'cyan'
Save-Canvas 'page_frame'
New-Canvas 1024 128 1024 128
$path=[Drawing.Drawing2D.GraphicsPath]::new()
$family=[Drawing.FontFamily]::new('Arial')
$path.AddString('SABER TRIALS',$family,[int]([Drawing.FontStyle]::Bold -bor [Drawing.FontStyle]::Italic),98,[Drawing.PointF]::new(0,0),[Drawing.StringFormat]::GenericTypographic)
$bounds=$path.GetBounds();$matrix=[Drawing.Drawing2D.Matrix]::new();$matrix.Translate(-$bounds.X,-$bounds.Y);$path.Transform($matrix);$matrix.Dispose()
$bounds=$path.GetBounds();$matrix=[Drawing.Drawing2D.Matrix]::new();$matrix.Scale(1010/$bounds.Width,102/$bounds.Height);$path.Transform($matrix);$matrix.Dispose()
$brush=[Drawing.Drawing2D.LinearGradientBrush]::new([Drawing.PointF]::new(0,0),[Drawing.PointF]::new(0,110),[Drawing.Color]::White,[Drawing.Color]::FromArgb(255,167,206,228))
$g.FillPath($brush,$path);$brush.Dispose();$path.Dispose();$family.Dispose();Save-Canvas 'wordmark'
# Rasterize only glyph coverage; no font software is redistributed.
New-Canvas 1024 1024 1024 1024
$g.TextRenderingHint=[Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$font=[Drawing.Font]::new('Arial',46,[Drawing.FontStyle]::Bold -bor [Drawing.FontStyle]::Italic,[Drawing.GraphicsUnit]::Pixel)
$format=[Drawing.StringFormat]::GenericTypographic.Clone();$format.FormatFlags=$format.FormatFlags -bor [Drawing.StringFormatFlags]::MeasureTrailingSpaces
$white=[Drawing.SolidBrush]::new([Drawing.Color]::White);$advances=@()
for($c=32;$c -le 126;$c++){
 $i=$c-32;$x=($i%16)*64;$y=[Math]::Floor($i/16)*80
 $s=[string][char]$c;$advance=$g.MeasureString($s,$font,1000,$format).Width
 $advances+=([Math]::Round($advance,3).ToString('0.000',[Globalization.CultureInfo]::InvariantCulture)+'f')
 $g.DrawString($s,$font,$white,[Drawing.PointF]::new($x+6,$y),$format)
}
$white.Dispose();$font.Dispose();$format.Dispose();Save-Canvas 'type'
[IO.File]::WriteAllText($Metrics,('// Generated glyph advances for the accompanying atlas.'+"`n"+'static const float richAdvance[]={'+($advances -join ',')+'};'+"`n"))
# Metallic title artwork as one composition: the separator cannot drift away
# from either title line. Geometric letter outlines remain sharp at 4K.
New-Canvas 2048 512 1024 256
$letters=@{
 S=@(@(100,0),@(20,0),@(0,20),@(0,43),@(22,61),@(64,61),@(78,74),@(0,74),@(0,100),@(81,100),@(100,81),@(100,58),@(78,39),@(33,39),@(22,26),@(100,26))
 T=@(@(0,0),@(100,0),@(100,26),@(65,26),@(65,100),@(35,100),@(35,26),@(0,26))
 A=@(@(0,100),@(32,0),@(70,0),@(102,100),@(71,100),@(64,75),@(36,75),@(29,100))
 R=@(@(0,100),@(0,0),@(73,0),@(98,20),@(98,45),@(76,62),@(105,100),@(67,100),@(40,65),@(30,65),@(30,100))
 W=@(@(0,0),@(28,0),@(44,58),@(59,0),@(85,0),@(101,58),@(117,0),@(145,0),@(114,100),@(87,100),@(72,45),@(57,100),@(30,100))
}
$path=[Drawing.Drawing2D.GraphicsPath]::new([Drawing.Drawing2D.FillMode]::Alternate);$offset=22.0
foreach($c in 'STAR WARS'.ToCharArray()){
 if($c -eq ' '){$offset+=45;continue}
 $points=$letters[[string]$c];$v=[Drawing.PointF[]]@($points|ForEach-Object{[Drawing.PointF]::new($offset+$_[0]*.95,9+$_[1])});$path.AddPolygon($v)
 if($c -eq 'A'){$hole=@(@(44,49),@(57,49),@(50,24))}elseif($c -eq 'R'){$hole=@(@(30,24),@(30,43),@(64,43),@(68,38),@(68,28),@(64,24))}else{$hole=$null}
 if($hole){$v=[Drawing.PointF[]]@($hole|ForEach-Object{[Drawing.PointF]::new($offset+$_[0]*.95,9+$_[1])});$path.AddPolygon($v)}
 $offset+=(@{S=100;T=100;A=102;R=105;W=145}[[string]$c]*.95)+8
}
$bounds=$path.GetBounds();$matrix=[Drawing.Drawing2D.Matrix]::new();$matrix.Translate((1024-$bounds.Width)/2-$bounds.X,0);$path.Transform($matrix);$matrix.Dispose()
foreach($layer in @(@(12,18),@(6,30),@(2,110))){$pen=[Drawing.Pen]::new([Drawing.Color]::FromArgb($layer[1],55,164,221),$layer[0]);$g.DrawPath($pen,$path);$pen.Dispose()}
$brush=[Drawing.Drawing2D.LinearGradientBrush]::new([Drawing.PointF]::new(0,8),[Drawing.PointF]::new(0,112),[Drawing.Color]::FromArgb(255,241,252,255),[Drawing.Color]::FromArgb(255,143,196,229))
$g.FillPath($brush,$path);$brush.Dispose();$path.Dispose()
# Soft gold separator with a bright, small diamond centered at x=512.
$points=[Drawing.PointF[]]@([Drawing.PointF]::new(0,145),[Drawing.PointF]::new(499,145),[Drawing.PointF]::new(512,132),[Drawing.PointF]::new(525,145),[Drawing.PointF]::new(512,158),[Drawing.PointF]::new(499,145),[Drawing.PointF]::new(1024,145))
foreach($layer in @(@(14,9),@(7,24),@(3,75),@(1.5,255))){$pen=[Drawing.Pen]::new([Drawing.Color]::FromArgb($layer[1],255,193,59),$layer[0]);$g.DrawLines($pen,$points);$pen.Dispose()}
$family=[Drawing.FontFamily]::new('Arial Black');$path=[Drawing.Drawing2D.GraphicsPath]::new()
$path.AddString('S A B E R   T R I A L S',$family,0,49,[Drawing.PointF]::new(0,0),[Drawing.StringFormat]::GenericTypographic)
$bounds=$path.GetBounds();$matrix=[Drawing.Drawing2D.Matrix]::new();$matrix.Translate(-$bounds.X,-$bounds.Y);$path.Transform($matrix);$matrix.Dispose()
$matrix=[Drawing.Drawing2D.Matrix]::new();$matrix.Scale(948/$bounds.Width,43/$bounds.Height);$path.Transform($matrix);$matrix.Dispose()
$matrix=[Drawing.Drawing2D.Matrix]::new();$matrix.Translate(38,195);$path.Transform($matrix);$matrix.Dispose()
$brush=[Drawing.SolidBrush]::new([Drawing.Color]::FromArgb(255,0,207,245));$g.FillPath($brush,$path)
$family.Dispose();$path.Dispose();$brush.Dispose();Save-Canvas 'logo'
# The main title now owns its separator. Leave no second line/diamond behind it.
New-Canvas 2048 2048 1672 941
Draw-Contour $design.outer 'cyan' $true
Draw-Contour $design.inner 'cyan'
Draw-Contour $design.gold_top 'gold' $true
Draw-Contour $design.gold_bottom 'gold'
Draw-Contour $design.account 'gold'
Save-Canvas 'frame'
