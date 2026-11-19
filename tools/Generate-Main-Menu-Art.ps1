param([Parameter(Mandatory=$true)][string]$Layout,[Parameter(Mandatory=$true)][string]$Output,[switch]$OmitTitleDivider,[switch]$FrameOnly)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
[IO.Directory]::CreateDirectory($Output) | Out-Null
$design=Get-Content -LiteralPath $Layout -Raw | ConvertFrom-Json
function New-Canvas([int]$width,[int]$height,[float]$logicalWidth,[float]$logicalHeight) {
 $script:bitmap=[Drawing.Bitmap]::new($width,$height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
 $script:g=[Drawing.Graphics]::FromImage($bitmap)
 $g.SmoothingMode=[Drawing.Drawing2D.SmoothingMode]::AntiAlias
 $g.PixelOffsetMode=[Drawing.Drawing2D.PixelOffsetMode]::HighQuality
 $g.CompositingQuality=[Drawing.Drawing2D.CompositingQuality]::HighQuality
 $g.Clear([Drawing.Color]::Transparent)
 $g.ScaleTransform($width/$logicalWidth,$height/$logicalHeight)
}
function Save-Canvas([string]$name) {
 $bitmap.Save((Join-Path $Output ($name+'.png')),[Drawing.Imaging.ImageFormat]::Png)
 $g.Dispose();$bitmap.Dispose()
}
function Draw-Contour($points,[string]$tone,[bool]$bright=$false) {
 $vertices=[Drawing.PointF[]]@($points | ForEach-Object { [Drawing.PointF]::new([float]$_[0]*2.6125,[float]$_[1]*1.960416667) })
 if($tone -eq 'gold') { $rgb=@(255,194,58) } else { $rgb=@(15,204,255) }
 $layers=if($bright){@(@(20,13),@(11,28),@(5,65),@(2,235),@(.65,255))}else{@(@(14,9),@(7,22),@(3,55),@(1.25,210))}
 foreach($layer in $layers){
  $color=[Drawing.Color]::FromArgb([int]$layer[1],$rgb[0],$rgb[1],$rgb[2])
  if($bright -and $layer[0] -lt 1){$color=[Drawing.Color]::FromArgb(255,220,250,255)}
  $pen=[Drawing.Pen]::new($color,[float]$layer[0]);$pen.LineJoin=[Drawing.Drawing2D.LineJoin]::Round
  $g.DrawLines($pen,$vertices);$pen.Dispose()
 }
}
# Frame art is authored in the reference's 1672x941 space; the native canvas
# stretches it together with the menu. Assets are power-of-two and antialiased.
New-Canvas 2048 2048 1672 941
Draw-Contour $design.outer 'cyan' $true
Draw-Contour $design.inner 'cyan'
Draw-Contour $design.gold_top 'gold' $true
Draw-Contour $design.gold_bottom 'gold'
if(!$OmitTitleDivider) { Draw-Contour $design.divider 'gold' }
Draw-Contour $design.account 'gold'
foreach($corner in @(@(@(6,27),@(18,9),@(32,9)),@(@(608,7),@(620,7),@(634,25)),@(@(634,440),@(634,451),@(621,468),@(609,468)),@(@(35,468),@(23,468),@(6,451),@(6,440)))){
 $vertices=[Drawing.PointF[]]@($corner | ForEach-Object { [Drawing.PointF]::new($_[0]*2.6125,$_[1]*1.960416667) })
 $pen=[Drawing.Pen]::new([Drawing.Color]::FromArgb(235,12,155,216),5);$g.DrawLines($pen,$vertices);$pen.Dispose()
}

Save-Canvas 'frame'
if($FrameOnly) { return }
foreach($focus in @($false,$true)){
 New-Canvas 1024 256 (157*2.6125) (52*1.960416667)
 $poly=@(@(6,6),@(135,6),@(151,46),@(6,46),@(6,6))
 $vertices=[Drawing.PointF[]]@($poly | ForEach-Object {[Drawing.PointF]::new($_[0]*2.6125,$_[1]*1.960416667)})
 $path=[Drawing.Drawing2D.GraphicsPath]::new();$path.AddPolygon($vertices)
 $a=if($focus){[Drawing.Color]::FromArgb(235,0,71,102)}else{[Drawing.Color]::FromArgb(205,2,17,29)}
 $b=if($focus){[Drawing.Color]::FromArgb(215,0,33,57)}else{[Drawing.Color]::FromArgb(175,3,16,26)}
 $brush=[Drawing.Drawing2D.LinearGradientBrush]::new([Drawing.PointF]::new(0,0),[Drawing.PointF]::new(0,102),$a,$b)
 $g.FillPath($brush,$path);$brush.Dispose();$path.Dispose()
 Draw-Contour $poly 'cyan' $focus
 Save-Canvas $(if($focus){'button_focus'}else{'button_idle'})
}
foreach($button in $design.buttons){
 New-Canvas 512 128 512 128
 $g.TextRenderingHint=[Drawing.Text.TextRenderingHint]::AntiAliasGridFit
 $font=[Drawing.Font]::new('Arial',100,[Drawing.FontStyle]::Bold -bor [Drawing.FontStyle]::Italic,[Drawing.GraphicsUnit]::Pixel)
 $brush=[Drawing.SolidBrush]::new([Drawing.Color]::White)
 $g.DrawString([string]$button.label,$font,$brush,[Drawing.PointF]::new(8,-1),[Drawing.StringFormat]::GenericTypographic)
 $brush.Dispose();$font.Dispose();Save-Canvas ('label_'+$button.name)
}
New-Canvas 64 64 64 64
for($y=0;$y -lt 64;$y++){for($x=0;$x -lt 64;$x++){
 $r=(($x-31.5)*($x-31.5)+($y-31.5)*($y-31.5))/1024
 $alpha=[int](255*[Math]::Exp(-$r*9))
 $bitmap.SetPixel($x,$y,[Drawing.Color]::FromArgb($alpha,255,255,255))
}}
Save-Canvas 'glow'
# Original vector-style Jedi emblem for the footer.
New-Canvas 256 256 128 128
$pen=[Drawing.Pen]::new([Drawing.Color]::FromArgb(255,49,221,255),4)
$g.DrawEllipse($pen,6,6,116,116);$g.DrawEllipse($pen,12,12,104,104)
$path=[Drawing.Drawing2D.GraphicsPath]::new()
$path.AddBezier(55,104,19,91,17,46,42,20);$path.AddBezier(42,20,27,66,48,80,55,104)
$path.CloseFigure();$path.AddBezier(73,104,109,91,111,46,86,20);$path.AddBezier(86,20,101,66,80,80,73,104);$path.CloseFigure()
$brush=[Drawing.SolidBrush]::new([Drawing.Color]::FromArgb(255,72,224,255));$g.FillPath($brush,$path)
$sword=[Drawing.PointF[]]@([Drawing.PointF]::new(64,13),[Drawing.PointF]::new(59,63),[Drawing.PointF]::new(62,110),[Drawing.PointF]::new(66,110),[Drawing.PointF]::new(69,63))
$g.FillPolygon($brush,$sword);$brush.Dispose();$path.Dispose();$pen.Dispose();Save-Canvas 'emblem'
