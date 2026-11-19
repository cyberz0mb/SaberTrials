"""Generate sealed, deterministic Q3Map2 inputs for map support testing."""

import argparse
from pathlib import Path
import struct


def brush(lo, hi, shader="st_maptest/caulk", top=None, detail=False):
    x, y, z = lo
    X, Y, Z = hi
    a, b, c, d = (x, y, z), (X, y, z), (X, Y, z), (x, Y, z)
    e, f, g, h = (x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)
    faces = ((a, b, c), (e, h, g), (a, e, f), (d, c, g), (a, d, h), (b, f, g))
    lines = ["{"]
    for i, points in enumerate(faces):
        coords = " ".join("( %d %d %d )" % point for point in points)
        material = (top or shader) if i == 1 else shader
        lines.append(f"{coords} {material} 0 0 0 0.5 0.5 {134217728 if detail else 0} 0 0")
    return "\n".join((*lines, "}"))


def room(x, width, depth, z=0):
    thickness = 16
    xmin, xmax = x - width // 2, x + width // 2
    ymin, ymax = -depth // 2, depth // 2
    return [
        brush((xmin, ymin, z - thickness), (xmax, ymax, z), top="st_maptest/grid"),
        brush((xmin, ymin, z + 256), (xmax, ymax, z + 256 + thickness)),
        brush((xmin - thickness, ymin, z - thickness), (xmin, ymax, z + 272)),
        brush((xmax, ymin, z - thickness), (xmax + thickness, ymax, z + 272)),
        brush((xmin - thickness, ymin - thickness, z - thickness), (xmax + thickness, ymin, z + 272)),
        brush((xmin - thickness, ymax, z - thickness), (xmax + thickness, ymax + thickness, z + 272)),
    ]


def patch(x, z=0):
    # Ramp with a curved crest, fully outside the classic coordinate range on the far map.
    rows = []
    for y in (-64, 0, 64):
        points = [f"( {x + dx} {y} {z + dz} {s} {y / 64} )"
                  for s, (dx, dz) in enumerate(((96, 1), (160, 40), (224, 16)))]
        rows.append("( " + " ".join(points) + " )")
    return "\n".join(("{", "patchDef2", "{", "st_maptest/grid",
                      "( 3 3 0 0 0 )", "(", *rows, ")", "}", "}"))


def entity(classname, origin, **keys):
    return "\n".join(("{", f'"classname" "{classname}"', f'"origin" "{origin}"',
                      *(f'"{key}" "{value}"' for key, value in keys.items()), "}"))


def generate(output):
    output.mkdir(parents=True, exist_ok=True)
    shaders = output / "shaders"
    shaders.mkdir(exist_ok=True)
    (shaders / "st_maptest.shader").write_text(
        """textures/st_maptest/caulk
{
    surfaceparm nodraw
    surfaceparm nolightmap
}
textures/st_maptest/grid
{
    q3map_vertexLight
    {
        map textures/st_maptest/grid.tga
        rgbGen identity
    }
}
""", encoding="ascii")
    texture = output / "textures/st_maptest"
    texture.mkdir(parents=True, exist_ok=True)
    header = bytes((0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16, 0, 16, 0, 24, 32))
    pixels = bytes(channel for y in range(16) for x in range(16)
                   for channel in ((70, 100, 150) if (x // 8 + y // 8) % 2 else (36, 52, 80)))
    (texture / "grid.tga").write_bytes(header + pixels)
    for name, places in (
        ("st_classic", [(0, 0)]),
        ("st_far", [(-130768, -130768), (130768, 130768)]),
    ):
        geometry = [shape for x, z in places for shape in (*room(x, 576, 512, z), patch(x, z))]
        entities = []
        for i, (x, z) in enumerate(places):
            entities.append(entity("info_player_deathmatch", f"{x} 0 {z + 64}"))
            entities.append(entity("info_player_deathmatch", f"{x + 48} 0 {z + 64}"))
            if len(places) > 1:
                entities.append(entity("misc_teleporter_dest", f"{x} 96 {z + 64}",
                                       targetname=f"arrival{i}"))
                volume = brush((x - 48, -208, z), (x + 48, -144, z + 96), "st_maptest/caulk")
                entities.append("\n".join(("{", '"classname" "trigger_teleport"',
                                           f'"target" "arrival{1 - i}"', volume, "}")))
        write_map(output / f"{name}.map", geometry, entities)

    # Detail brushes avoid making tens of thousands of structural PVS splits.
    geometry = room(0, 12672, 12672)
    for j in range(184):
        for i in range(184):
            x, y = (i - 92) * 64, (j - 92) * 64
            geometry.append(brush((x, y, 8), (x + 16, y + 16, 24), "st_maptest/grid", detail=True))
    write_map(output / "st_dense.map", geometry, [
        entity("info_player_deathmatch", "36 36 64"),
        entity("info_player_deathmatch", "36 100 64"),
    ])


def write_map(path, geometry, entities):
    path.write_text("\n".join(("{", '"classname" "worldspawn"', '"gridsize" "512 512 512"',
                               '"_blocksize" "8192 8192 8192"', '"distanceCull" "32768"',
                               *geometry, "}", *entities, "")), encoding="ascii")


def expand_indices(source, destination):
    """Give every dense fixture surface its own index range for the index stress test."""
    data = bytearray(source.read_bytes())
    if data[:8] != b"RBSP\x02\x00\x00\x00":
        raise ValueError("The dense index fixture requires a compiled RBSP 2 file")
    index_lump, surface_lump = 8 + 11 * 8, 8 + 13 * 8
    index_offset, index_length = struct.unpack_from("<ii", data, index_lump)
    surface_offset, surface_length = struct.unpack_from("<ii", data, surface_lump)
    expanded = bytearray()
    for surface in range(surface_offset, surface_offset + surface_length, 148):
        first, count = struct.unpack_from("<ii", data, surface + 20)
        if first < 0 or count < 0 or first + count > index_length // 4:
            raise ValueError("Invalid source surface index range")
        struct.pack_into("<i", data, surface + 20, len(expanded) // 4)
        expanded.extend(data[index_offset + 4 * first:index_offset + 4 * (first + count)])
    data.extend(bytes((-len(data)) % 4))
    struct.pack_into("<ii", data, index_lump, len(data), len(expanded))
    data.extend(expanded)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / source.name).write_bytes(data)
    print(f"Dense fixture now has {len(expanded) // 4:,} stored indices.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expand-indices", type=Path)
    args = parser.parse_args()
    if args.expand_indices:
        expand_indices(args.expand_indices, args.output)
    else:
        generate(args.output)
