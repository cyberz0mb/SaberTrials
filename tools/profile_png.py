"""Small RGB/RGBA PNG reader for native Profile screenshot regressions."""
import struct,zlib

def portrait_fixture(path):
 # A circle reveals distortion even when the entire menu uses stretched units.
 width=height=128
 rows=[]
 for y in range(height):
  rows.append(b'\0'+b''.join(bytes((10,235,30) if (x-64)**2+(y-64)**2<=24**2 else (210,20,190)) for x in range(width)))
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b''))

def portrait_proportions(path,wide):
 width,height,pixel=read(path)
 # The bright green fixture is unique within the first gallery row.
 left=22 if wide else 147;top=177 if wide else 174
 points=[]
 for y in range(int((top+1)*height/480),int((top+58)*height/480)):
  for x in range(int((left+1)*width/640),int((left+(410 if wide else 285))*width/640)):
   r,g,b=pixel(x,y)
   if g>190 and r<60 and b<80:points.append((x,y))
 assert points,'Missing circle portrait fixture'
 w=max(x for x,y in points)-min(x for x,y in points)+1;h=max(y for x,y in points)-min(y for x,y in points)+1
 assert abs(w-h)<=3,('Portrait circle stretched',w,h,path)

def read(path):
 data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
 position=8;packed=[];width=height=bpp=0
 while position<len(data):
  length=struct.unpack('>I',data[position:position+4])[0];kind=data[position+4:position+8];chunk=data[position+8:position+8+length];position+=length+12
  if kind==b'IHDR':
   width,height,depth,color,_,_,interlace=struct.unpack('>IIBBBBB',chunk)
   assert depth==8 and color in (2,6) and interlace==0;bpp=3 if color==2 else 4
  elif kind==b'IDAT':packed.append(chunk)
 raw=zlib.decompress(b''.join(packed));stride=width*bpp;rows=[];offset=0;previous=bytearray(stride)
 for _ in range(height):
  mode=raw[offset];line=bytearray(raw[offset+1:offset+1+stride]);offset+=stride+1
  for x in range(stride):
   left=line[x-bpp] if x>=bpp else 0;above=previous[x];corner=previous[x-bpp] if x>=bpp else 0
   if mode==1:prediction=left
   elif mode==2:prediction=above
   elif mode==3:prediction=(left+above)//2
   elif mode==4:
    p=left+above-corner;a=abs(p-left);b=abs(p-above);c=abs(p-corner);prediction=left if a<=b and a<=c else above if b<=c else corner
   else:assert mode==0;prediction=0
   line[x]=(line[x]+prediction)&255
  rows.append(line);previous=line
 return width,height,lambda x,y:tuple(rows[y][x*bpp:x*bpp+3])

def clean_background(path):
 width,height,pixel=read(path)
 samples=[pixel(width-10,int(height*f)) for f in (.2,.35,.5,.65,.8)]
 assert all(max(abs(a-b) for a,b in zip(sample,(7,16,25)))<=2 for sample in samples),('A prior menu paints over Profile',samples)
