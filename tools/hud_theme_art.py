"""Generate Saber Trials combat HUD art. Text and values are drawn by cgame."""
from pathlib import Path
import argparse
from math import cos, pi, sin

from PIL import Image, ImageDraw, ImageFilter, ImageFont


SUPERSAMPLE = 6
CYAN = (13, 208, 255)
GOLD = (255, 179, 28)


def points(path):
    return [(round(x * SUPERSAMPLE), round(y * SUPERSAMPLE)) for x, y in path]


def outline(size, paths, width):
    mask = Image.new('L', size)
    draw = ImageDraw.Draw(mask)
    for path in paths:
        draw.line(points(path), fill=255, width=max(1, round(width * SUPERSAMPLE)), joint='curve')
    return mask


def tint(mask, rgb, opacity=1):
    result = Image.new('RGBA', mask.size, rgb)
    result.putalpha(mask.point(lambda value: round(value * opacity)))
    return result


def light(image, paths, color, width, opacity=1):
    mask = outline(image.size, paths, width)
    image.alpha_composite(tint(mask.filter(ImageFilter.GaussianBlur(2 * SUPERSAMPLE)), color, .86 * opacity))
    image.alpha_composite(tint(mask.filter(ImageFilter.GaussianBlur(.62 * SUPERSAMPLE)), color, .56 * opacity))
    image.alpha_composite(tint(mask, color, opacity))
    glint = tuple(round(channel * .6 + 255 * .4) for channel in color)
    image.alpha_composite(tint(outline(image.size, paths, width * .35), glint, opacity * .8))


def panel(out, name, dimensions, path, inset, accent, detail):
    size = tuple(round(n * SUPERSAMPLE) for n in dimensions)
    mask = Image.new('L', size)
    ImageDraw.Draw(mask).polygon(points(path), fill=255)
    fill = Image.new('RGBA', size)
    draw = ImageDraw.Draw(fill)
    for y in range(size[1]):
        height = y / size[1]
        shade = max(0, 1 - height * 3) * 8 + max(0, (height - .8) * 5) * 5
        draw.line((0, y, size[0], y), fill=(3, round(12 + shade), round(23 + shade * 1.7), 255))
    fill.putalpha(mask)
    fill.resize((512, 256 if dimensions[1] > 30 else 128), Image.Resampling.LANCZOS).save(out / f'{name}_fill.png')
    trim = Image.new('RGBA', size)
    light(trim, [path + path[:1]], CYAN, .85)
    light(trim, inset, (29, 114, 151), .52, .75)
    light(trim, accent, GOLD, .76)
    light(trim, detail, CYAN, .90, .92)
    trim.resize((512, 256 if dimensions[1] > 30 else 128), Image.Resampling.LANCZOS).save(out / f'{name}.png')


def panels(out):
    panel(out, 'health_frame', (186, 29),
          [(6, 16), (17, 5), (76, 5), (81, 9), (164, 9), (181, 25), (17, 25)],
          [[(12, 16), (19, 8), (75, 8), (79, 11), (163, 11), (175, 22), (18, 22), (12, 16)]],
          [[(29, 2.8), (76, 2.8), (81, 6.7), (111, 6.7)]],
          [[(15, 12), (11, 16), (15, 20)], [(111, 9), (151, 9)]])
    panel(out, 'armor_frame', (186, 29),
          [(6, 12), (17, 3), (166, 3), (181, 3), (164, 23), (17, 23)],
          [[(12, 12), (19, 6), (175, 6), (162, 20), (19, 20), (12, 12)]],
          [[(9, 9), (4.5, 12), (17, 26), (126, 26)]],
          [[(170, 9), (163, 16), (154, 16)], [(174, 6), (169, 11)]])
    panel(out, 'weapon_frame', (148, 55),
          [(5, 43), (32, 6), (130, 6), (142, 18), (120, 49), (12, 49)],
          [[(9, 43), (33, 9), (129, 9), (138, 18), (118, 46), (13, 46), (9, 43)]],
          [[(63, 3.5), (125, 3.5)], [(29, 52), (121, 52), (135, 34), (132, 31)],
           [(59, 17), (59, 40)]],
          [[(16, 38), (12, 43), (21, 43)], [(130, 13), (135, 18), (129, 25)]])
    panel(out, 'score_frame', (128, 29),
          [(5, 16), (21, 4), (124, 4), (124, 9), (109, 25), (14, 25)],
          [[(9, 16), (22, 7), (121, 7)], [(16, 22), (107, 22), (117, 11)]],
          [[(25, 25), (99, 25)], [(65, 10), (62, 19)]],
          [[(23, 4), (48, 4)]])
    panel(out, 'team_frame', (128, 29),
          [(5, 16), (21, 4), (124, 4), (124, 9), (109, 25), (14, 25)],
          [[(9, 16), (22, 7), (121, 7)], [(16, 22), (107, 22), (117, 11)]],
          [[(25, 25), (99, 25)]],
          [[(23, 4), (48, 4)]])


def chat_panel(out):
    panel(out, 'chat_frame', (270, 90),
          [(4, 16), (15, 5), (255, 5), (266, 16), (266, 77), (256, 86), (13, 86), (4, 77)],
          [[(7, 18), (17, 9), (253, 9), (263, 18), (263, 75), (254, 82), (15, 82), (7, 75)]],
          [[(7, 25), (7, 18), (16, 10), (59, 10)], [(206, 7.5), (239, 7.5)],
           [(231, 84), (236, 81), (255, 81)]],
          [[(18, 85.5), (106, 85.5)], [(84, 5.5), (153, 5.5)]])
    header = Image.new('RGBA', (102 * SUPERSAMPLE, 28 * SUPERSAMPLE))
    shape = [(3, 23), (3, 14), (14, 3), (78, 3), (89, 14), (89, 23)]
    ImageDraw.Draw(header).polygon(points(shape), fill=(5, 26, 43, 245))
    light(header, [shape], CYAN, 1.05)
    light(header, [[(6, 23), (86, 23)]], (27, 108, 143), .55)
    light(header, [[(85, 7), (92, 14)], [(90, 7), (97, 14)], [(95, 7), (102, 14)]], GOLD, 1.05)
    light(header, [[(16, 8), (24, 8), (26, 10), (26, 16), (24, 18), (19, 18),
                    (16, 20), (16, 17), (14, 16), (14, 10), (16, 8)],
                   [(17, 13), (18, 13)], [(20, 13), (21, 13)], [(23, 13), (24, 13)]], CYAN, .64)
    header.resize((512, 128), Image.Resampling.LANCZOS).save(out/'chat_header.png')


def bars(out):
    size = (512, 64)
    track = Image.new('RGBA', size)
    draw = ImageDraw.Draw(track)
    draw.polygon([(2, 50), (31, 14), (509, 14), (480, 50)], fill=(5, 32, 51, 211))
    draw.line([(4, 50), (480, 50)], fill=(72, 130, 154, 132), width=3)
    track.save(out / 'meter_track.png')
    for name, color in [('health', (255, 41, 81)), ('armor', (18, 166, 255))]:
        mask = Image.new('L', size)
        ImageDraw.Draw(mask).polygon([(4, 44), (31, 20), (495, 20), (508, 32), (496, 44)], fill=255)
        art = tint(mask.filter(ImageFilter.GaussianBlur(8)), color, .9)
        art.alpha_composite(tint(mask, color))
        highlight = Image.new('L', size)
        ImageDraw.Draw(highlight).polygon([(10, 40), (35, 24), (492, 24), (501, 32), (492, 40)], fill=225)
        art.alpha_composite(tint(highlight, tuple(round(c * .42 + 255 * .58) for c in color)))
        art.save(out / f'meter_{name}.png')


def icons(out):
    hilt = [[(10, 6), (20, 6), (19, 9), (17, 11), (18, 13), (18, 24),
             (16, 26), (14, 26), (12, 24), (12, 13), (13, 11), (11, 9), (10, 6)],
            [(11, 9), (19, 9)], [(12, 17), (18, 17)], [(12, 21), (18, 21)]]
    def crossed(angle):
        c, s = cos(angle), sin(angle)
        return [[(15 + .87*((x-15)*c-(y-15)*s), 15 + .87*((x-15)*s+(y-15)*c))
                 for x,y in line] for line in hilt]

    paths = {
        'health_mark': [[(12, 4), (18, 4), (18, 12), (26, 12), (26, 18), (18, 18),
                         (18, 26), (12, 26), (12, 18), (4, 18), (4, 12), (12, 12), (12, 4)]],
        'armor_mark': [[(15, 4), (26, 8), (24, 19), (20, 24), (15, 27), (10, 24),
                        (6, 19), (4, 8), (15, 4)],
                       [(15, 8), (21, 10), (20, 18), (15, 23), (10, 18), (9, 10), (15, 8)]],
        'saber_mark': hilt,
        'staff_mark': [[(9, 2), (21, 2), (21, 5), (17, 8), (17, 22), (21, 25),
                        (21, 28), (9, 28), (9, 25), (13, 22), (13, 8), (9, 5), (9, 2)],
                       [(9, 5), (21, 5)], [(9, 25), (21, 25)],
                       [(13, 12), (17, 12)], [(13, 18), (17, 18)]],
        'dual_mark': crossed(-pi/4) + crossed(pi/4),
        'ammo_mark': [[(6, 25), (6, 10), (9, 5), (12, 10), (12, 25), (6, 25)],
                      [(18, 25), (18, 10), (21, 5), (24, 10), (24, 25), (18, 25)],
                      [(6, 21), (12, 21)], [(18, 21), (24, 21)]],
        'reticle': [[(15, 3), (15, 10)], [(15, 20), (15, 27)], [(3, 15), (10, 15)], [(20, 15), (27, 15)]],
    }
    for name, lines in paths.items():
        mask = outline((30 * SUPERSAMPLE,) * 2, lines, 1.5)
        shadow = mask.filter(ImageFilter.GaussianBlur(1.3 * SUPERSAMPLE))
        art = tint(shadow, (255, 255, 255), .76)
        art.alpha_composite(tint(mask, (255, 255, 255)))
        art.resize((128, 128), Image.Resampling.LANCZOS).save(out / f'{name}.png')


def letters(out):
    font = ImageFont.truetype('arialbi.ttf', 52)
    atlas = Image.new('RGBA', (512, 256))
    for i, char in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-/:+?.core'):
        x0, y0, x1, y1 = font.getbbox(char)
        mask = Image.new('L', (x1 - x0 + 2, y1 - y0 + 2))
        ImageDraw.Draw(mask).text((1 - x0, 1 - y0), char, font=font, fill=255)
        height = 29 if char.islower() else 13 if char in '-+.' else 39
        width = min(24, round(mask.width * height / mask.height))
        glyph = tint(mask.resize((width, height), Image.Resampling.LANCZOS), (255, 255, 255))
        x = (i % 16) * 32 + 4 + (24 - width) // 2
        y = (i // 16) * 64 + (27 if char in '-+' else 49 - height)
        atlas.alpha_composite(glyph, (x, y))
    atlas.save(out / 'letters.png')


def generate(out):
    out.mkdir(parents=True, exist_ok=True)
    panels(out)
    chat_panel(out)
    bars(out)
    icons(out)
    letters(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    generate(parser.parse_args().output)
