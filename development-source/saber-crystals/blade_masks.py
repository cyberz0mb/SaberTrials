"""Build small uncompressed TGA masks for the blade's existing line and glow geometry."""
import math
import struct


def texture(width, height, pixel):
    header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, width, height, 32, 40)
    data = bytearray(header)
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixel((x + .5) / width, (y + .5) / height)
            data.extend((b, g, r, a))
    return data


def glow(u, v):
    radius_squared = (2*u - 1)**2 + (2*v - 1)**2
    intensity = round(156 * max(0, math.exp(-3.6 * radius_squared) - math.exp(-3.6)))
    return intensity, intensity, intensity, 255


def smoothstep(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def blade_edge(u, v, taper):
    # The renderer places t=0 at the tip and t=1 at the emitter.
    tip = math.sqrt(max(.002, 1 - (max(0, taper - v) / taper)**2))
    return abs(2*u - 1) / tip


def blade(u, v, black):
    edge = blade_edge(u, v, .075 if black else .105)
    if black:
        alpha = max(0, min(1, (1-edge) * 15))
        rim = max(0, min(1, (edge - .66) * 20))
        return round(210*rim), round(228*rim), round(245*rim), round(255*alpha)
    body = smoothstep((1 - edge) / .68)
    cap = smoothstep(v / .006)
    return (round(200 * body * cap),)*3 + (255,)


def white_center(u, v):
    edge = blade_edge(u, v, .105)
    # Keep the white inside the tapered color band and feather the transition.
    opacity = smoothstep((.53 - edge) / .20) * smoothstep(v / .006)
    return 255, 255, 255, round(255 * opacity)


def thumb(u, v):
    x, y = abs(2*u - 1), abs(2*v - 1)
    border = max(x, y, (x + y) / 1.63)
    alpha = smoothstep((1 - border) / .08)
    if border > .81:
        shade = .97 - .41*v
    else:
        shade = .53 + .39 * (1 - v) + .13 * math.exp(-((v - .27)/.13)**2)
    return (round(255*min(1, shade)),)*3 + (round(255*alpha),)


def facet(u, v):
    # A beveled crystal with a bright top face and angled lower facets.
    x, y = abs(2*u - 1), abs(2*v - 1)
    edge = max(x, y, (x + y) / 1.54)
    alpha = smoothstep((1 - edge) / .09)
    if edge > .82:
        shade = .97 - .47*v
    elif v < .24:
        shade = .93
    elif v > .70 + .16*x:
        shade = .44
    else:
        shade = .76 + .19 * (1 - v) - .20 * x
    return (round(255*shade),)*3 + (round(255*alpha),)


def images():
    return {'glow': texture(64, 64, glow),
            'core': texture(64, 512, lambda u,v: blade(u,v,False)),
            'white-center': texture(64, 512, white_center),
            'black': texture(64, 128, lambda u,v: blade(u,v,True)),
            'thumb': texture(64, 64, thumb),
            'facet': texture(128, 64, facet)}
