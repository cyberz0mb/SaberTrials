"""Build TFFA uniform textures from a local Jedi Academy installation (Pillow and NumPy)."""
import argparse
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PALETTE = {
    "red": (.81, .25, .23), "blue": (.24, .43, .81), "green": (.25, .70, .35),
    "yellow": (.83, .72, .27), "white": (.84, .85, .86), "black": (.35, .36, .38),
    "orange": (.88, .50, .23), "purple": (.64, .34, .77),
}
PACKAGE = "zzzzzzz_sabertrials_stock_team_skins.pk3"


def stem(path):
    return str(PurePosixPath(path).with_suffix(""))


def skin_map(data):
    result = {}
    for line in data.decode("latin1").splitlines():
        fields = line.partition("//")[0].split(",", 1)
        if len(fields) == 2:
            surface, material = (s.strip().lower() for s in fields)
            result[surface] = material
    return result


class StockSkins:
    def __init__(self, base, output):
        self.sources = {}
        self.archives = []
        for i in range(4):
            archive = ZipFile(base / f"assets{i}.pk3")
            self.archives.append(archive)
            self.sources.update((n.lower(), (archive, n)) for n in archive.namelist())
        self.output = output
        self.shaders = {}
        self.generated_shaders = []
        self.models = {}
        self.coverage = {}
        for path in self.sources:
            if path.startswith("shaders/") and path.endswith(".shader"):
                text = self.read(path).decode("latin1")
                text = re.sub(r"/\*.*?\*/|//[^\r\n]*", "", text, flags=re.S)
                for match in re.finditer(r'(?im)^\s*(models/players/[^\s{}]+)\s*(\{(?:[^{}]|\{[^{}]*\})*\})', text):
                    self.shaders[stem(match[1].lower())] = match[2]

    def read(self, path):
        archive, name = self.sources[path]
        return archive.read(name)

    def image(self, path):
        for ext in (".tga", ".jpg", ".png", ".jpeg"):
            key = stem(path) + ext
            if key in self.sources:
                with Image.open(BytesIO(self.read(key))) as im:
                    return im.convert("RGBA")
        raise ValueError(f"Missing stock texture {path}")

    @lru_cache(maxsize=None)
    def materials(self, red, blue, colors):
        source = self.image(red)
        rgba = np.array(source)
        rgb = rgba[:, :, :3].astype(np.float32) / 255
        if blue:
            other = np.asarray(self.image(blue).resize(source.size, Image.Resampling.BILINEAR), dtype=np.float32)[:, :, :3] / 255
            shift = (rgb[:,:,0] - rgb[:,:,2]) - (other[:,:,0] - other[:,:,2])
            mask = np.clip((shift - .03) / .19, 0, 1)
        else:
            # The Jawa has one robe atlas and independent eye and hand materials.
            mask = np.clip((rgb[:,:,0] - rgb[:,:,2] - .015) / .07, 0, 1)
        peak = rgb.max(axis=2)
        level = np.power(peak, .72)
        self.coverage[red] = max(self.coverage.get(red, 0), int((mask > .25).sum()))
        if not mask.any():
            return {color: red for color in colors}
        key = sha256((red + "|" + blue).encode()).hexdigest()[:12]
        result = {}
        for color in colors:
            path = f"models/st_team/{key}_{color}"
            strength = np.array(PALETTE[color], dtype=np.float32)
            tinted = level[:,:,None] * strength
            if color == "black":
                tinted += (.095 * peak**3)[:,:,None]
            out = rgba.copy()
            out[:,:,:3] = np.rint(255*np.clip(rgb + mask[:,:,None]*(tinted-rgb), 0, 1))
            image = Image.fromarray(out)
            buffer = BytesIO()
            opaque = bool((rgba[:,:,3] == 255).all())
            if opaque:
                image.convert("RGB").save(buffer, "JPEG", quality=94, subsampling=0)
            else:
                image.save(buffer, "PNG", compress_level=5)
            ext = ".jpg" if opaque else ".png"
            self.output.writestr(path + ext, buffer.getvalue())
            original = stem(red)
            if original in self.shaders:
                body = re.sub(re.escape(original) + r'(?:\.(?:tga|jpg|png))?(?=\s|$)', path+ext,
                              self.shaders[original], flags=re.I)
                self.generated_shaders.append(f"{path}\n{body}\n")
            result[color] = path
        return result

    def build_model(self, model):
        folder = f"models/players/{model}/"
        if folder+"head_a1.skin" in self.sources:
            self.models[model] = {"method": "stock clothing shaders"}
            return
        has_pair = all(folder+"model_"+c+".skin" in self.sources for c in ("red","blue"))
        if not has_pair and model != "jawa":
            return
        colors = tuple(PALETTE)
        red = skin_map(self.read(folder+("model_red.skin" if has_pair else "model_default.skin")))
        blue = skin_map(self.read(folder+"model_blue.skin")) if has_pair else {}
        default = skin_map(self.read(folder+"model_default.skin"))
        variants = {p[len(folder+"model_"):-5] for p in self.sources if p.startswith(folder+"model_") and p.endswith(".skin")}
        variants -= {"red","blue","menu","siege"}
        skins = 0
        changed = set()
        for variant in sorted(variants):
            outfit = red if variant == "default" else skin_map(self.read(folder+f"model_{variant}.skin"))
            generated = {c:{} for c in colors}
            for surface, mat in outfit.items():
                r, b = red.get(surface), blue.get(surface)
                repl = {}
                if r and r != "*off" and mat != "*off":
                    if has_pair and b and b != "*off" and r != b and mat in (r,default.get(surface)):
                        repl = self.materials(r,b,colors)
                    elif model == "jawa" and stem(mat) == folder+"jawa":
                        repl = self.materials(mat,"",colors)
                if any(v.startswith("models/st_team/") for v in repl.values()):
                    changed.add(surface)
                for c in colors:
                    generated[c][surface] = repl.get(c,mat)
            for c,mapping in generated.items():
                name = f"models/st_team/skins/{model}/{variant}_{c}.skin"
                text = "".join(f"{s},{m}\n" for s,m in mapping.items())
                self.output.writestr(name, text)
                skins+=1
        if not changed:
            raise ValueError(f"No team coloring found for {model}")
        self.models[model] = {"method":"uniform textures", "skins":skins, "surfaces":len(changed)}

    def build(self):
        for path in sorted(self.sources):
            if re.fullmatch(r"models/players/[^/]+/model\.glm",path):
                self.build_model(path.split("/")[2])
        self.output.writestr("shaders/st_team_uniforms.shader","\n".join(self.generated_shaders))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base",type=Path,default=ROOT.parent/"base")
    ap.add_argument("--output",type=Path,default=ROOT/"dist/multiteam-02")
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    target=args.output/PACKAGE
    temporary=target.with_suffix(".pending")
    with ZipFile(temporary,"w",compression=ZIP_DEFLATED,compresslevel=3) as archive:
        skins=StockSkins(args.base,archive)
        try:
            skins.build()
        finally:
            for source in skins.archives:
                source.close()
    with ZipFile(temporary) as archive:
        names=set(archive.namelist())
        assert len(names)==len(archive.namelist()) and archive.testzip() is None
        textures={stem(n) for n in names if n.endswith((".jpg",".png"))}
        for name in (n for n in names if n.endswith(".skin")):
            for material in skin_map(archive.read(name)).values():
                if material.startswith("models/st_team/") and material not in textures:
                    raise ValueError(f"{name} references missing {material}")
    temporary.replace(target)
    report={"models":skins.models, "textures":len(textures),"shader_variants":len(skins.generated_shaders),
            "skin_files":sum(n.endswith(".skin") for n in names)}
    (args.output/"stock-team-inventory.json").write_text(json.dumps(report,indent=2))
    print(f"{len(skins.models)} stock model families, {report['skin_files']} skins, {len(textures)} textures")


if __name__=="__main__":
    main()
