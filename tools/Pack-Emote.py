"""Package a frame range from a JKA-compatible GLA as one Saber Trials emote."""
from argparse import ArgumentParser
from pathlib import Path
import re
import struct
from zipfile import ZIP_DEFLATED, ZipFile
from zlib import crc32

GLA = 'models/players/_humanoid/_humanoid.gla'


def read_gla(path):
    if path.suffix.lower() == '.pk3':
        with ZipFile(path) as archive:
            return archive.read(GLA)
    return path.read_bytes()


def package(path, output, emote_id, label, first, frames, fps):
    if not re.fullmatch(r'[a-z0-9_-]{1,20}', emote_id):
        raise ValueError('Use a stable lowercase ID of up to 20 characters.')
    if not re.fullmatch(r'[ -~]{1,40}', label) or any(c in label for c in '";\\'):
        raise ValueError('Use a plain-text label of up to 40 printable ASCII characters.')
    data = read_gla(path)
    if len(data) < 100 or data[:8] != b'2LGA\x06\0\0\0':
        raise ValueError('Expected a version 6 JKA GLA.')
    count, index, bones, pool, _, size = struct.unpack_from('<6I',data,76)
    if bones != 53 or index < 312 or pool != index+count*bones*3 or size != len(data):
        raise ValueError('Expected the canonical 53-bone JKA humanoid skeleton.')
    if first < 0 or first+frames > count or not 2 <= frames <= 240 or not 10 <= fps <= 60:
        raise ValueError('Use an in-range clip with 2–240 frames at 10–60 FPS.')
    signature = crc32(data[100:index])
    poses = bytearray()
    for position in range(index+first*bones*3,index+(first+frames)*bones*3,3):
        start = pool+14*int.from_bytes(data[position:position+3],'little')
        if start+14 > size:
            raise ValueError('The GLA contains an invalid pose index.')
        poses.extend(data[start:start+14])
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        archive.writestr('emote.txt',f'STEMOTE1 {emote_id} {frames} {fps} {signature:08x}\t{label}\n')
        archive.writestr('poses.bin',poses)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--id',required=True)
    parser.add_argument('--label',required=True)
    parser.add_argument('--first',type=int,required=True)
    parser.add_argument('--frames',type=int,required=True)
    parser.add_argument('--fps',type=int,required=True)
    args = parser.parse_args()
    package(args.source,args.output,args.id,args.label,args.first,args.frames,args.fps)
