"""Paint the emote wheel layers at high resolution for both JKA renderers."""
from math import cos, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


SIZE = 1024
CENTER = SIZE / 2
CYAN = (28, 208, 246)
GOLD = (255, 191, 52)


def polar(radius, angle):
    rotation = angle * pi / 180
    return CENTER + sin(rotation) * radius, CENTER - cos(rotation) * radius


def arc(radius, first, last):
    return [polar(radius, first + (last - first) * step / 48) for step in range(49)]


def layer(mask, color, opacity=1):
    image = Image.new('RGBA', mask.size, color)
    image.putalpha(mask.point(lambda value: round(value * opacity)))
    return image


def luminous(image, paths, color, width):
    mask = Image.new('L', image.size)
    draw = ImageDraw.Draw(mask)
    for path in paths:
        draw.line(path, fill=255, width=width, joint='curve')
    image.alpha_composite(layer(mask.filter(ImageFilter.GaussianBlur(9)), color, .65))
    image.alpha_composite(layer(mask.filter(ImageFilter.GaussianBlur(3)), color, .65))
    image.alpha_composite(layer(mask, color, .9))


def sector(mid):
    first, last = mid - 21.9, mid + 21.9
    return arc(451, first, last) + arc(143, last, first)


def render(out):
    out.mkdir(parents=True, exist_ok=True)
    face = Image.new('RGBA', (SIZE, SIZE))
    draw = ImageDraw.Draw(face)
    outlines, glints = [], []
    for slot in range(8):
        mid = 45 * slot
        path = sector(mid)
        draw.polygon(path, fill=(4, 19, 28, 224))
        outlines.append(path + path[:1])
        glints.append(arc(451, mid - 14, mid + 13))
    draw.ellipse((CENTER - 139, CENTER - 139, CENTER + 139, CENTER + 139), fill=(1, 11, 19, 248))
    luminous(face, outlines + [arc(136, 0, 360)], (17, 126, 158), 3)
    luminous(face, glints, CYAN, 5)
    face.save(out / 'emote_face.png')

    for slot in range(8):
        path = sector(45 * slot)
        mask = Image.new('L', face.size)
        ImageDraw.Draw(mask).polygon(path, fill=255)
        highlight = layer(mask, (40, 29, 10), .78)
        bloom = Image.new('L', face.size)
        ImageDraw.Draw(bloom).line(arc(147, 45 * slot - 20, 45 * slot + 20), fill=255, width=22)
        bloom = Image.composite(bloom.filter(ImageFilter.GaussianBlur(35)), Image.new('L', face.size), mask)
        highlight.alpha_composite(layer(bloom, GOLD, .9))
        luminous(highlight, [path + path[:1]], GOLD, 7)
        highlight.save(out / f'emote_focus{slot}.png')

    badge = Image.new('RGBA', (128, 128))
    path = [(28, 16), (100, 16), (119, 44), (119, 84), (100, 112), (28, 112), (9, 84), (9, 44)]
    ImageDraw.Draw(badge).polygon(path, fill=(8, 17, 21, 252))
    luminous(badge, [path + path[:1]], GOLD, 5)
    badge.save(out / 'emote_number.png')

    def pose(name, head, limbs):
        icon = Image.new('RGBA', (128, 128))
        brush = ImageDraw.Draw(icon)
        white = (229, 247, 255, 255)
        for path, width in limbs:
            brush.line(path, fill=white, width=width, joint='curve')
            for x, y in path:
                r = width / 2
                brush.ellipse((x-r,y-r,x+r,y+r), fill=white)
        if head:
            x, y = head
            brush.ellipse((x-10,y-10,x+10,y+10), fill=white)
        icon.save(out / f'emote_{name}.png')

    pose('taunt',(64,24), [([(64,45),(64,77)],25), ([(16,48),(39,55),(64,48),(89,55),(112,48)],10), ([(45,112),(64,74),(83,112)],11)])
    pose('bow',(91,57), [([(45,69),(58,46),(73,48)],23), ([(65,50),(75,76),(85,92)],9), ([(42,69),(37,94),(36,114)],12), ([(48,74),(54,97),(55,113)],10)])
    pose('meditate',(64,28), [([(64,51),(64,78)],23), ([(63,49),(48,65),(42,89)],10), ([(65,49),(80,65),(86,89)],10), ([(48,83),(30,99),(64,103),(98,99),(80,83)],14)])
    pose('flourish',(62,30), [([(63,52),(63,76)],22), ([(20,74),(42,54),(63,51),(83,50),(101,28)],10), ([(42,110),(63,74),(88,105)],10), ([(94,39),(116,10)],6)])
    pose('celebrate',(64,41), [([(64,62),(64,88)],21), ([(22,19),(38,52),(64,62),(90,52),(106,19)],10), ([(49,112),(64,83),(79,112)],10)])
    pose('empty',None,[([(35,64),(93,64)],8), ([(64,35),(64,93)],8)])
    pose('gesture',None,[([(64,18),(83,49),(64,110),(45,49),(64,18)],6), ([(45,49),(83,49)],6)])


if __name__ == '__main__':
    import sys
    render(Path(sys.argv[1]))
