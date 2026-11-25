"""Regenerate the optional high-DPI JKA glyph atlases from the shipped Noto font."""
from pathlib import Path
from struct import Struct
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
GLYPH = Struct("<hhhhiffff")
HEADER = Struct("<hhhhhh")


def build_variant(data, name, level, factor, output):
    offset = 256 * GLYPH.size
    point, height, ascent, descent, unused, padding = HEADER.unpack_from(data, offset)
    if not height:  # Same legacy header correction as OpenJK's font loader.
        height = point
        descent = int(point / 10 + 2.5)
        ascent = height - descent
    font = ImageFont.truetype(str(ROOT / "client/translator/fonts/NotoSans-Regular.ttf"), point * factor * 2)
    atlas = Image.new("L", (512 if factor == 2 else 2048, 2048))
    metrics = bytearray()
    x = y = 2
    line_height = 0
    for code in range(256):
        w, h, advance, bearing, baseline, *_ = GLYPH.unpack_from(data, code * GLYPH.size)
        w, h = w * factor, h * factor
        if x + w + 2 > atlas.width:
            x, y, line_height = 2, y + line_height + 4, 0
        if y + h + 2 > atlas.height:
            raise ValueError(f"{name} exceeds atlas bounds")
        char = bytes([code]).decode("cp1252", errors="replace")
        if w and h and code >= 33 and char.isprintable():
            weight = max(1, point * factor // 32)
            x0, y0, x1, y1 = font.getbbox(char, stroke_width=weight)
            glyph = Image.new("L", (x1 - x0, y1 - y0))
            ImageDraw.Draw(glyph).text((-x0, -y0), char, font=font, fill=255,
                                       stroke_width=weight, stroke_fill=255)
            if glyph.getbbox():
                # Keep stock glyph positions, advances and baselines at every DPI.
                # Retain a fraction of a glyph unit as the original atlas gutter.
                inset = max(1, factor // 2)
                left = max(inset, -bearing * factor)
                right = min(w - inset, (advance - bearing) * factor - inset)
                if right <= left:
                    left, right = inset, max(inset + 1, w - inset)
                glyph = glyph.crop(glyph.getbbox()).resize(
                    (right - left, max(1, h - 2 * inset)), Image.Resampling.LANCZOS)
                atlas.paste(glyph, (x + left, y + inset))
        metrics.extend(GLYPH.pack(w, h, advance * factor, bearing * factor, baseline * factor,
                                  x / atlas.width, y / atlas.height,
                                  (x + w) / atlas.width, (y + h) / atlas.height))
        x += w + 4
        line_height = max(h, line_height)
    used_height = 1 << (y + line_height + 1).bit_length()
    for index in range(256):
        w,h,advance,bearing,baseline,s,t,s2,t2 = GLYPH.unpack_from(metrics, index * GLYPH.size)
        GLYPH.pack_into(metrics, index * GLYPH.size, w,h,advance,bearing,baseline,s,
                        t * atlas.height / used_height,s2,t2 * atlas.height / used_height)
    atlas = atlas.crop((0, 0, atlas.width, used_height))
    metrics.extend(HEADER.pack(point * factor, height * factor, ascent * factor, descent * factor, unused, padding))
    rgba = Image.new("RGBA", atlas.size, (255, 255, 255, 0))
    rgba.putalpha(atlas)
    stem = output / f"{name}_sharp{level}"
    rgba.save(stem.with_suffix(".png"), optimize=True)
    stem.with_suffix(".fontdat").write_bytes(metrics)


if __name__ == "__main__":
    output = ROOT / "assets/hud-fonts"
    output.mkdir(exist_ok=True)
    with ZipFile(ROOT.parent / "base/assets1.pk3") as retail:
        for name in ("ergoec", "arialnb"):
            for level, factor in enumerate((2, 6), 1):
                build_variant(retail.read(f"fonts/{name}.fontdat"), name, level, factor, output)
