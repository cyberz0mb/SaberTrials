"""Deterministic, append-only Ghoul2 ready-stance library. Never installs assets."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HEADER = struct.Struct('<4si64sf6i')
PREFIX = 'models/players/_humanoid/'

def sha(data): return hashlib.sha256(data).hexdigest()

def parse_gla(data):
    if len(data) < HEADER.size: raise ValueError('Truncated GLA header')
    h = list(HEADER.unpack_from(data))
    if h[0] != b'2LGA' or h[1] != 6: raise ValueError('Unsupported GLA version')
    frames, start, bones, pool, skel, end = h[4:]
    if not (0 < frames <= 1000000 and 0 < bones <= 512 and
            100 <= skel < start <= pool < end == len(data) and
            start + frames*bones*3 <= pool and (end-pool) % 14 == 0):
        raise ValueError('Invalid GLA bounds')
    count = (end-pool)//14
    indices = data[start:start+frames*bones*3]
    if any(int.from_bytes(indices[i:i+3], 'little') >= count for i in range(0, len(indices), 3)):
        raise ValueError('Invalid compressed bone index')
    return h

def merge_gla(base, clips):
    """Append (donor bytes, first frame, count); preserve the entire base library."""
    h = parse_gla(base)
    prefix = base[:h[5]]
    frames = bytearray(base[h[5]:h[5]+h[4]*h[6]*3])
    pool = bytearray(base[h[7]:h[9]])
    # Existing indices remain valid, even if the base pool itself has duplicates.
    lookup = {bytes(pool[i:i+14]): i//14 for i in range(0, len(pool), 14)}
    ranges = []
    parsed = {}
    for donor, first, count in clips:
        key = id(donor)
        d = parsed.get(key)
        if d is None: d = parsed[key] = parse_gla(donor)
        if h[6] != d[6] or prefix[100:] != donor[100:d[5]] or h[3] != d[3]:
            raise ValueError('Incompatible skeleton or scale')
        if first < 0 or count <= 0 or first+count > d[4]: raise ValueError('Clip out of bounds')
        ranges.append((h[4], count))
        for pos in range(d[5]+first*d[6]*3, d[5]+(first+count)*d[6]*3, 3):
            index = int.from_bytes(donor[pos:pos+3], 'little')
            value = donor[d[7]+index*14:d[7]+(index+1)*14]
            target = lookup.get(value)
            if target is None:
                target = len(pool)//14
                if target >= 1 << 24: raise ValueError('Compressed bone pool overflow')
                lookup[value] = target
                pool.extend(value)
            frames.extend(target.to_bytes(3, 'little'))
        h[4] += count
    h[7] = len(prefix)+len(frames)
    h[9] = h[7]+len(pool)
    return HEADER.pack(*h)+prefix[100:]+frames+pool, ranges

def rows(data):
    found = {}
    for line in data.decode('latin1').splitlines():
        values = line.split('//')[0].split()
        if len(values) >= 5:
            try: found[values[0]] = tuple(int(v) for v in values[1:5])
            except ValueError: pass
    return found

def build(output, input_root=ROOT/'assets/stance-inputs', base_path=ROOT.parent/'base/japlus_gla_anims.pk3'):
    lock = json.loads((ROOT/'development-source/stances/sources.lock.json').read_text())
    catalog = json.loads((ROOT/'development-source/stances/catalog.json').read_text())
    if sha(base_path.read_bytes()) != lock['base_archive_sha256']:
        raise ValueError('JA+ base archive differs from the frozen source (including cfg/events)')
    with zipfile.ZipFile(base_path) as z:
        base = z.read(PREFIX+'_humanoid.gla')
        cfg = z.read(PREFIX+'animation.cfg')
        events = z.read(PREFIX+'animevents.cfg')
    if sha(base) != lock['base_gla_sha256']:
        raise ValueError('JA+ base GLA changed since assessment')
    sources = {str(base_path): sha(base_path.read_bytes())}
    clips, metadata, cache = [], [], {}
    for item in catalog['stances']:
        path = input_root/item['pack']
        if path not in cache:
            expected = lock['donors'].get(item['pack'])
            data = path.read_bytes()
            if expected != sha(data): raise ValueError('Donor changed since assessment: '+str(path))
            sources[str(path)] = sha(data)
            with zipfile.ZipFile(path) as z:
                if z.testzip(): raise ValueError('Corrupt donor archive')
                donor_cfg = rows(z.read(PREFIX+'animation.cfg'))
                donor = z.read(PREFIX+'_humanoid.gla') if PREFIX+'_humanoid.gla' in z.namelist() else base
            cache[path] = donor, donor_cfg
        donor, donor_cfg = cache[path]
        first, count, loop, fps = donor_cfg[item['source_animation']]
        if [first,count,loop,fps] != item['expected_row']: raise ValueError('Unexpected donor clip')
        clips.append((donor, first, count))
        metadata.append({**item, 'donor_frame': first, 'count': count, 'loop': loop, 'fps': fps})
    combined, ranges = merge_gla(base, clips)
    fnv=2166136261
    for byte in combined:fnv=((fnv^byte)*16777619)&0xffffffff
    additions = '\n// Saber Trials ready poses v1; existing rows above are unchanged.\n'
    for item, (start,count) in zip(metadata, ranges):
        item['frame'] = start
        additions += f"{item['animation']} {start} {count} {item['loop']} {item['fps']}\n"
    files = {PREFIX+'_humanoid.gla': combined, PREFIX+'animation.cfg': cfg+additions.encode(), PREFIX+'animevents.cfg': events}
    manifest = {'version': 1, 'base_frames': parse_gla(base)[4], 'frames': parse_gla(combined)[4],
                'gla_size': len(combined), 'gla_fnv32': fnv,
                'base_cfg_sha256': sha(cfg), 'base_events_sha256': sha(events), 'sources': sources,
                'stances': metadata, 'files': {k:sha(v) for k,v in files.items()}, 'installed': False}
    # Library marker is a compatibility hint, never an anti-cheat attestation.
    files['stances/library-v1.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    files['stances/CREDITS.txt'] = ('Saber Trials stance library\n\n'+catalog['credits']+'\n').encode()
    output.mkdir(parents=True, exist_ok=True)
    package = output/'zz_sabertrials_stances_v1.pk3'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026,10,29,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    manifest['package_sha256'] = sha(package.read_bytes())
    (output/'library.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Built {len(metadata)} isolated ready poses, {manifest["frames"]} frames: {package}')
    return manifest

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=ROOT/'dist/stance-candidate/assets')
    parser.add_argument('--inputs',type=Path,default=ROOT/'assets/stance-inputs')
    parser.add_argument('--base',type=Path,default=ROOT.parent/'base/japlus_gla_anims.pk3')
    args=parser.parse_args();build(args.output,args.inputs,args.base)
