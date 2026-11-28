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

// Real depth-writing black volume. The existing colored blade materials above
// are unchanged; no lighting or additive stage can brighten this black fill.
gfx/st_crystals/blackVolume
{
 nomipmaps
 nopicmip
 surfaceparm nodlight
 sort opaque
 {
  map $whiteimage
  rgbGen const ( 0 0 0 )
  depthWrite
 }
}

// Inverted hull: only the far faces outside the opaque body's silhouette draw.
// Submitted only when White Core is enabled, with a soft outer and thin inner edge.
gfx/st_crystals/blackEdge
{
 nomipmaps
 nopicmip
 cull back
 surfaceparm nodlight
 sort seeThrough
 {
  map $whiteimage
  blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
  rgbGen const ( .84 .92 1 )
  alphaGen entity
  glow
 }
}
