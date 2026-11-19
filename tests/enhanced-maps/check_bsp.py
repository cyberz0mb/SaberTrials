"""Exercise the production validator on stock archives and corrupt copies."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile


def lump(data, index):
    return struct.unpack_from("<ii", data, 8 + index * 8)


def change(data, offset, fmt, value):
    copy = bytearray(data)
    struct.pack_into(fmt, copy, offset, value)
    return copy


def check(checker, archives):
    with tempfile.TemporaryDirectory(dir=checker.parent) as tmp:
        stage = Path(tmp)
        files = []
        for pkg in archives:
            with zipfile.ZipFile(pkg) as archive:
                for name in archive.namelist():
                    if name.lower().endswith(".bsp"):
                        destination = stage / f"{len(files):03d}-{Path(name).name}"
                        destination.write_bytes(archive.read(name))
                        files.append(destination)
        if not files:
            raise ValueError("No BSP files found")
        for start in range(0, len(files), 24):
            subprocess.run([checker, *files[start:start + 24]], check=True)

        data = max(files, key=lambda p: p.stat().st_size).read_bytes()
        excessive_surfaces = bytearray(data)
        surface_lump = 13
        stride = 148
        excessive_surfaces.extend(bytes((-len(excessive_surfaces)) % 4))
        new_offset = len(excessive_surfaces)
        new_size = (262144 + 1) * stride
        excessive_surfaces.extend(bytes(new_size))
        struct.pack_into("<ii", excessive_surfaces, 8 + surface_lump * 8, new_offset, new_size)
        repeated_indices = bytearray(data)
        repeated_indices.extend(bytes((-len(repeated_indices)) % 4))
        index_offset = len(repeated_indices)
        index_count = 5997
        repeated_indices.extend(bytes(index_count * 4))
        struct.pack_into("<ii", repeated_indices, 8 + 11 * 8, index_offset, index_count * 4)
        offset, length = lump(data, surface_lump)
        for surface in range(offset, offset + length, stride):
            kind = struct.unpack_from("<i", data, surface + 8)[0]
            struct.pack_into("<ii", repeated_indices, surface + 20, 0,
                             index_count if kind in (1, 3) else 0)
        corruptions = {
            "short": (data[:100], "file length"),
            "signature": (change(data, 0, "<4s", b"IBSP"), "signature"),
            "version": (change(data, 4, "<i", 999), "unsupported RBSP version"),
            "negative_lump": (change(data, 8, "<i", -1), "lump offset"),
            "oversized_lump": (change(data, 12, "<i", 0x7fffffff), "lump offset"),
            "surface_capacity": (excessive_surfaces, "supported capacity"),
            "referenced_index_capacity": (repeated_indices, "surface references exceed"),
            "unterminated_entities": (change(data, sum(lump(data, 0)) - 1, "<B", 1), "unterminated"),
            "cyclic_node": (change(data, lump(data, 3)[0] + 4, "<i", 0), "node tree"),
            "invalid_node_leaf": (change(data, lump(data, 3)[0] + 4, "<i", -0x80000000), "node leaf"),
            "invalid_leaf_surface": (change(data, lump(data, 5)[0], "<i", -1), "leaf surface"),
            "invalid_model": (change(data, lump(data, 7)[0] + 24, "<i", 0x7fffffff), "model geometry"),
            "invalid_brush": (change(data, lump(data, 8)[0] + 4, "<i", 1), "brush geometry"),
            "nan_vertex": (change(data, lump(data, 10)[0], "<f", float("nan")), "draw vertex"),
            "out_of_world": (change(data, lump(data, 10)[0], "<f", 131073), "draw vertex"),
            "index": (change(data, lump(data, 11)[0], "<i", -1), "vertex index"),
            "vis_stride": (change(data, lump(data, 16)[0] + 4, "<i", 0x7fffffff), "visibility dimensions"),
            "lightgrid": (change(data, lump(data, 17)[0], "<H", 65535), "light grid index"),
        }
        for name, (bad, message) in corruptions.items():
            path = stage / (name + ".bsp")
            path.write_bytes(bad)
            result = subprocess.run([checker, path], capture_output=True, text=True)
            if result.returncode != 1 or message not in result.stderr:
                raise AssertionError(f"{name}: {result.returncode} {result.stderr}")
        print(f"Validated {len(files)} BSP files and rejected {len(corruptions)} malformed cases.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checker", type=Path)
    parser.add_argument("archives", type=Path, nargs="+")
    args = parser.parse_args()
    check(args.checker, args.archives)
