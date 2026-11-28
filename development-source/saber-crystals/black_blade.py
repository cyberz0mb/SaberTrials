"""Original rounded black blade geometry in the native MD3 format (no game assets)."""
import math
import struct

MODEL = 'models/st_crystals/black_blade.md3'


def capsule():
    sides = 16
    points, normals, uv = [], [], []
    rings = [(0, 1, 0), (39, 1, 0)]
    for degrees in (15, 30, 45, 60, 75):
        angle = math.radians(degrees)
        rings.append((39+math.sin(angle), math.cos(angle), angle))
    for z, radius, cap in rings:
        for i in range(sides):
            a = i*2*math.pi/sides
            points.append((radius*math.cos(a), radius*math.sin(a), z))
            normals.append((math.cos(cap)*math.cos(a), math.cos(cap)*math.sin(a), math.sin(cap)))
            uv.append((i/sides, z/40))
    bottom, tip = len(points), len(points)+1
    points += [(0, 0, 0), (0, 0, 40)]
    normals += [(0, 0, -1), (0, 0, 1)]
    uv += [(.5, 0), (.5, 1)]
    triangles = []
    # Native MD3 faces have clockwise winding relative to outward normals.
    for ring in range(len(rings)-1):
        for i in range(sides):
            j = (i+1) % sides
            a, b = ring*sides+i, ring*sides+j
            c, d = (ring+1)*sides+j, (ring+1)*sides+i
            triangles += [(a, c, b), (a, d, c)]
    for i in range(sides):
        j = (i+1) % sides
        triangles.append((bottom, i, j))
        triangles.append(((len(rings)-1)*sides+i, tip, (len(rings)-1)*sides+j))
    packed = b''
    for p, n in zip(points, normals):
        latitude = round(math.atan2(n[1], n[0])*255/(2*math.pi)) & 255
        longitude = round(math.acos(max(-1, min(1, n[2])))*255/(2*math.pi)) & 255
        packed += struct.pack('<3hH', *(round(v*64) for v in p), (latitude << 8) | longitude)
    header_size, frame_size, surface_size = 108, 56, 108
    shaders = struct.pack('<64si', b'gfx/st_crystals/blackVolume', 0)
    tri_data = b''.join(struct.pack('<3i', *t) for t in triangles)
    st_data = b''.join(struct.pack('<2f', *v) for v in uv)
    ofs_shaders = surface_size
    ofs_tri = ofs_shaders+len(shaders)
    ofs_st = ofs_tri+len(tri_data)
    ofs_xyz = ofs_st+len(st_data)
    surface_end = ofs_xyz+len(packed)
    surface = struct.pack('<4s64s10i', b'IDP3', b'blade', 0, 1, 1, len(points), len(triangles),
                          ofs_tri, ofs_shaders, ofs_st, ofs_xyz, surface_end)
    frame = struct.pack('<10f16s', -1, -1, 0, 1, 1, 40, 0, 0, 20, math.sqrt(402), b'black_blade')
    surface_offset = header_size+frame_size
    size = surface_offset+surface_end
    header = struct.pack('<4si64s9i', b'IDP3', 15, MODEL.encode(), 0, 1, 0, 1, 0,
                         header_size, surface_offset, surface_offset, size)
    result = header+frame+surface+shaders+tri_data+st_data+packed
    assert len(result) == size
    assert len(points) == 114 and len(triangles) == 224
    assert all(0 <= i < len(points) for t in triangles for i in t)
    # Quantized triangles must remain nondegenerate and face the native side.
    vertices = [tuple(round(v*64)/64 for v in p) for p in points]
    for a, b, c in triangles:
        u = [vertices[b][i]-vertices[a][i] for i in range(3)]
        v = [vertices[c][i]-vertices[a][i] for i in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        n = [sum(normals[k][i] for k in (a,b,c)) for i in range(3)]
        assert sum(x*x for x in cross) > 0
        assert sum(cross[i]*n[i] for i in range(3)) < 0
    return result
