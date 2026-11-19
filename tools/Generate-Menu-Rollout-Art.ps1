param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
[IO.Directory]::CreateDirectory($Output)|Out-Null
$bmp=[Drawing.Bitmap]::new(2048,2048,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g=[Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode=[Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.Clear([Drawing.Color]::Transparent)
$g.ScaleTransform(2048/1672,2048/941)
function Stroke($points,$r,$green,$b,[bool]$bright=$false){
 $vertices=[Drawing.PointF[]]@($points|ForEach-Object{[Drawing.PointF]::new($_[0]*2.6125,$_[1]*1.960416667)})
 $layers=if($bright){@(@(15,13),@(7,30),@(3,68),@(1.5,235),@(.65,255))}else{@(@(8,13),@(3,37),@(1.05,170))}
 foreach($l in $layers){
  $color=if($l[0] -lt 1){[Drawing.Color]::FromArgb(255,217,248,255)}else{[Drawing.Color]::FromArgb($l[1],$r,$green,$b)}
  $pen=[Drawing.Pen]::new($color,$l[0]);$pen.LineJoin=[Drawing.Drawing2D.LineJoin]::Round;$g.DrawLines($pen,$vertices);$pen.Dispose()
 }
}
Stroke @(@(3,21),@(17,5),@(623,5),@(637,21),@(637,460),@(623,478),@(17,478),@(3,460),@(3,21)) 12 203 255 $true
Stroke @(@(6,23),@(19,8),@(311,8),@(320,15),@(329,8),@(621,8),@(634,23),@(634,458),@(621,476),@(19,476),@(6,458),@(6,23)) 12 182 240
Stroke @(@(260,8),@(314,8),@(320,13),@(326,8),@(380,8)) 255 194 65 $true
Stroke @(@(23,476),@(162,476),@(169,478),@(232,478)) 255 194 65
Stroke @(@(411,478),@(470,478),@(478,476),@(615,476)) 255 194 65
$bmp.Save((Join-Path $Output 'frame.png'),[Drawing.Imaging.ImageFormat]::Png)
$g.Dispose();$bmp.Dispose()
