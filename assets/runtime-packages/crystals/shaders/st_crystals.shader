gfx/st_crystals/rgbGlow
{
 nomipmaps
 nopicmip
 cull none
 {
  clampmap gfx/st_crystals/glow.tga
  blendFunc GL_ONE GL_ONE
  glow
  rgbGen exactVertex
 }
}

gfx/st_crystals/rgbCore
{
 nomipmaps
 nopicmip
 cull none
 {
  clampmap gfx/st_crystals/core.tga
  blendFunc GL_ONE GL_ONE
  rgbGen exactVertex
 }
}

gfx/st_crystals/rgbWhiteCore
{
 nomipmaps
 nopicmip
 cull none
 {
  clampmap gfx/st_crystals/core.tga
  blendFunc GL_ONE GL_ONE
  rgbGen exactVertex
 }
 {
  clampmap gfx/st_crystals/white-center.tga
  blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
  rgbGen identity
 }
}

gfx/st_crystals/blackCore
{
 nomipmaps
 nopicmip
 cull none
 sort seeThrough
 {
  clampmap gfx/st_crystals/black.tga
  blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
  rgbGen identity
 }
}
