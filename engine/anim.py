"""Snortlo 2D animation engine.
Stick-figure characters with jointed limbs, poses, expressions, lip-flap, props, sets
and a camera. Every line of a story carries "stage directions" (written by Claude in the
nightly pipeline); this file turns them into frames. Pure Python + cairo: fast enough
for a 2-core server.
"""
import math, random
import cairocffi as cairo

W, H = 1080, 1920
GROUND = 1180
INKC = (0.105, 0.10, 0.13)
FONT = "Inter"

def lerp(a, b, k): return a + (b - a) * k
def ease(k): k = max(0.0, min(1.0, k)); return k * k * (3 - 2 * k)
def spring(t, k=10.0, w=14.0): return 0.0 if t <= 0 else 1 - math.exp(-k * t) * math.cos(w * t)
def hexc(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

# ---------------------------------------------------------------- poses
# angles in degrees from straight down; positive = towards where the character faces
POSES = {
    "stand":     dict(torso=0, head=0, aF=14, eF=8, aB=-14, eB=-8, lF=7, kF=0, lB=-7, kB=0),
    "talk":      dict(torso=2, head=-4, aF=55, eF=55, aB=-14, eB=-8, lF=7, kF=0, lB=-7, kB=0),
    "point":     dict(torso=3, head=0, aF=92, eF=0, aB=-14, eB=-8, lF=9, kF=0, lB=-7, kB=0),
    "shrug":     dict(torso=-2, head=10, aF=55, eF=95, aB=-55, eB=-95, lF=7, kF=0, lB=-7, kB=0),
    "shocked":   dict(torso=-8, head=-8, aF=150, eF=18, aB=-150, eB=-18, lF=16, kF=0, lB=-16, kB=0),
    "facepalm":  dict(torso=6, head=14, aF=140, eF=128, aB=-14, eB=-8, lF=7, kF=0, lB=-7, kB=0),
    "hips":      dict(torso=0, head=-6, aF=45, eF=-115, aB=-45, eB=115, lF=10, kF=0, lB=-10, kB=0),
    "cross":     dict(torso=-2, head=-6, aF=22, eF=98, aB=30, eB=82, lF=8, kF=0, lB=-8, kB=0),
    "drink":     dict(torso=-6, head=-22, aF=42, eF=152, aB=-20, eB=-30, lF=10, kF=0, lB=-8, kB=0),
    "eat":       dict(torso=0, head=-4, aF=38, eF=150, aB=-14, eB=-8, lF=7, kF=0, lB=-7, kB=0),
    "reach":     dict(torso=8, head=0, aF=82, eF=-8, aB=-20, eB=-10, lF=14, kF=0, lB=-10, kB=0),
    "hold":      dict(torso=0, head=4, aF=32, eF=62, aB=-14, eB=-8, lF=7, kF=0, lB=-7, kB=0),
    "stir":      dict(torso=8, head=10, aF=50, eF=48, aB=-30, eB=-60, lF=9, kF=0, lB=-7, kB=0),
    "celebrate": dict(torso=-4, head=-10, aF=158, eF=12, aB=-158, eB=-12, lF=14, kF=0, lB=-14, kB=0),
    "laugh":     dict(torso=-10, head=-16, aF=22, eF=78, aB=-22, eB=-78, lF=9, kF=0, lB=-9, kB=0),
    "slump":     dict(torso=14, head=24, aF=6, eF=0, aB=-6, eB=0, lF=5, kF=0, lB=-5, kB=0),
    "sneak":     dict(torso=18, head=-6, aF=62, eF=40, aB=-40, eB=40, lF=28, kF=-45, lB=-12, kB=-40),
    "relax":     dict(torso=-4, head=-8, aF=150, eF=150, aB=-150, eB=-150, lF=7, kF=0, lB=-7, kB=0),
    "evil":      dict(torso=4, head=6, aF=40, eF=110, aB=-25, eB=-105, lF=7, kF=0, lB=-7, kB=0),
}
LIMB = dict(torso=190, neck=20, head=56, up=105, low=100, thigh=122, shin=116)

class Char:
    def __init__(self, name, look):
        self.name, self.look = name, look
        self.x, self.facing, self.pose = 540.0, 1, dict(POSES["stand"])

CAST_LOOKS = {
    "me":   dict(hat="#2BB3A3", shirt=None, tie=None, hair=None, skin="#FFFFFF"),
    "boss": dict(hat=None, tie="#E0453A", hair="comb", skin="#FFFFFF"),
    "co1":  dict(hat=None, tie=None, hair="bun", skin="#FFFFFF", tint="#6B6A75"),
    "co2":  dict(hat=None, tie=None, hair="spike", skin="#FFFFFF", tint="#6B6A75"),
    "co3":  dict(hat=None, tie=None, hair="pony", skin="#FFFFFF", tint="#6B6A75"),
}

def joints(p, x, facing, ground=GROUND):
    """Forward kinematics. Returns dict of joint points, feet planted on the ground."""
    r = math.radians
    def seg(o, ang, ln):
        return (o[0] + facing * ln * math.sin(r(ang)), o[1] + ln * math.cos(r(ang)))
    hip = (0.0, 0.0)
    kneeF = seg(hip, p["lF"], LIMB["thigh"]); footF = seg(kneeF, p["lF"] + p["kF"], LIMB["shin"])
    kneeB = seg(hip, p["lB"], LIMB["thigh"]); footB = seg(kneeB, p["lB"] + p["kB"], LIMB["shin"])
    lift = max(footF[1], footB[1])
    sh = (hip[0] + facing * LIMB["torso"] * math.sin(r(p["torso"])), hip[1] - LIMB["torso"] * math.cos(r(p["torso"])))
    neck = (sh[0] + facing * LIMB["neck"] * math.sin(r(p["torso"] + p["head"] * .3)), sh[1] - LIMB["neck"])
    ht = p["torso"] + p["head"]
    head = (neck[0] + facing * LIMB["head"] * math.sin(r(ht)), neck[1] - LIMB["head"] * math.cos(r(ht)))
    elF = seg(sh, p["aF"], LIMB["up"]); hF = seg(elF, p["aF"] + p["eF"], LIMB["low"])
    elB = seg(sh, p["aB"], LIMB["up"]); hB = seg(elB, p["aB"] + p["eB"], LIMB["low"])
    pts = dict(hip=hip, kneeF=kneeF, footF=footF, kneeB=kneeB, footB=footB, sh=sh, neck=neck, head=head,
               elF=elF, hF=hF, elB=elB, hB=hB)
    oy = ground - lift
    return {k: (x + v[0], oy + v[1]) for k, v in pts.items()}

# ---------------------------------------------------------------- drawing helpers
def rrect(c, x, y, w, h, r):
    c.new_path(); c.arc(x + w - r, y + r, r, -math.pi / 2, 0); c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi); c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); c.close_path()

def fill_stroke(c, fill, stroke=INKC, lw=8):
    if fill: c.set_source_rgb(*hexc(fill) if isinstance(fill, str) else fill); c.fill_preserve()
    if stroke: c.set_source_rgb(*stroke); c.set_line_width(lw); c.stroke()
    else: c.new_path()

def line(c, a, b, lw=16, col=INKC):
    c.set_source_rgb(*col); c.set_line_width(lw); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(*a); c.line_to(*b); c.stroke()

def poly(c, pts, lw=16, col=INKC):
    c.set_source_rgb(*col); c.set_line_width(lw); c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.move_to(*pts[0])
    for p in pts[1:]: c.line_to(*p)
    c.stroke()

def text(c, s, x, y, size, col=INKC, weight=cairo.FONT_WEIGHT_BOLD, anchor="c", outline=None):
    c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, weight); c.set_font_size(size)
    xb, yb, tw, th, xa, ya = c.text_extents(s)
    ox = {"c": -tw / 2 - xb, "l": -xb, "r": -tw - xb}[anchor]
    c.move_to(x + ox, y + th / 2 - (th + yb))
    if outline:
        c.text_path(s); c.set_source_rgb(*outline); c.set_line_width(size * .16); c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke_preserve(); c.set_source_rgb(*col); c.fill()
    else:
        c.set_source_rgb(*col); c.show_text(s)
    return tw

# ---------------------------------------------------------------- face
def draw_face(c, hx, hy, facing, face, talk, t, red=0.0):
    off = facing * 14
    ex1, ex2, ey = hx + off - 20, hx + off + 20, hy - 6
    eyes = face.get("eyes", "dot"); mouth = face.get("mouth", "smile")
    blink = (t * 0.7 + hash(face.get("_who", "")) % 7 * .13) % 3.4 < 0.12 and eyes in ("dot", "angry", "worried", "smug")
    c.set_source_rgb(*INKC)
    for i, ex in enumerate((ex1, ex2)):
        if blink or eyes == "closed":
            line(c, (ex - 8, ey), (ex + 8, ey), 6)
        elif eyes == "happy":
            c.set_line_width(6); c.new_path(); c.arc(ex, ey + 6, 9, math.pi * 1.1, math.pi * 1.9); c.stroke()
        elif eyes == "wide":
            c.new_path(); c.arc(ex, ey, 13, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill_preserve()
            c.set_source_rgb(*INKC); c.set_line_width(5); c.stroke()
            c.arc(ex, ey, 5, 0, 2 * math.pi); c.fill()
        elif eyes == "flat":
            line(c, (ex - 10, ey - 2), (ex + 10, ey - 2), 6); c.arc(ex, ey + 3, 4, 0, 2 * math.pi); c.fill()
        else:
            c.new_path(); c.arc(ex, ey, 6.5, 0, 2 * math.pi); c.fill()
        if eyes in ("angry", "smug"):
            s = (1 if i == 0 else -1) * (1 if eyes == "angry" else -0.6)
            line(c, (ex - 11, ey - 22 - 6 * s), (ex + 11, ey - 22 + 6 * s), 6)
        if eyes == "worried":
            s = 1 if i == 0 else -1
            line(c, (ex - 11, ey - 20 + 5 * s), (ex + 11, ey - 20 - 5 * s), 6)
    mx, my = hx + off, hy + 22
    c.set_source_rgb(*INKC); c.set_line_width(6); c.set_line_cap(cairo.LINE_CAP_ROUND)
    if talk > 0.05:
        h = 6 + 22 * min(1, talk)
        c.new_path(); c.save(); c.translate(mx, my + 2); c.scale(1, h / 16); c.arc(0, 0, 16, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(0.35, 0.08, 0.12); c.fill_preserve(); c.set_source_rgb(*INKC); c.stroke()
    elif mouth == "smile":
        c.new_path(); c.arc(mx, my - 8, 16, math.pi * .15, math.pi * .85); c.stroke()
    elif mouth == "grin":
        c.new_path(); c.move_to(mx - 22, my - 4); c.curve_to(mx - 10, my + 18, mx + 10, my + 18, mx + 22, my - 4); c.close_path()
        c.set_source_rgb(1, 1, 1); c.fill_preserve(); c.set_source_rgb(*INKC); c.stroke()
    elif mouth == "frown":
        c.new_path(); c.arc(mx, my + 14, 15, math.pi * 1.2, math.pi * 1.8); c.stroke()
    elif mouth == "o":
        c.new_path(); c.arc(mx, my + 2, 11, 0, 2 * math.pi); c.set_source_rgb(0.35, 0.08, 0.12); c.fill_preserve(); c.set_source_rgb(*INKC); c.stroke()
    elif mouth == "wavy":
        c.new_path(); c.move_to(mx - 20, my)
        for k in range(1, 9): c.line_to(mx - 20 + k * 5, my + (5 if k % 2 else -5) * (1 + .3 * math.sin(t * 20)))
        c.stroke()
    else:  # flat
        line(c, (mx - 14, my), (mx + 14, my), 6)

def draw_char(c, ch, t, talk=0.0, face=None, hold=None, fx=None):
    p = ch.pose; J = joints(p, ch.x + (fx or {}).get("dx", 0), ch.facing, GROUND + (fx or {}).get("dy", 0))
    look = CAST_LOOKS[ch.name]
    col = hexc(look["tint"]) if look.get("tint") else INKC
    # back limbs slightly lighter for depth
    back = tuple(min(1, v + .22) for v in col)
    poly(c, [J["sh"], J["elB"], J["hB"]], 15, back)
    poly(c, [J["hip"], J["kneeB"], J["footB"]], 16, back)
    line(c, J["footB"], (J["footB"][0] + ch.facing * 16, J["footB"][1]), 16, back)
    poly(c, [J["hip"], J["sh"], J["neck"]], 17, col)
    if look.get("tie"):
        a, b = J["neck"], J["sh"]; mx, my = lerp(J["sh"][0], J["hip"][0], .35), lerp(J["sh"][1], J["hip"][1], .35)
        c.new_path(); c.move_to(b[0] - 9, b[1] + 6); c.line_to(b[0] + 9, b[1] + 6); c.line_to(mx + ch.facing * 6, my); c.line_to(mx - 4, my + 8); c.close_path()
        fill_stroke(c, look["tie"], INKC, 4)
    poly(c, [J["hip"], J["kneeF"], J["footF"]], 16, col)
    line(c, J["footF"], (J["footF"][0] + ch.facing * 16, J["footF"][1]), 16, col)
    hx, hy = J["head"]; red = (fx or {}).get("red", 0)
    skin = tuple(lerp(a, b, red) for a, b in zip((1, 1, 1), hexc("#FF6B5A")))
    c.new_path(); c.arc(hx, hy, LIMB["head"], 0, 2 * math.pi); fill_stroke(c, skin, col, 12)
    hair = look.get("hair")
    if hair == "comb":
        c.set_source_rgb(*INKC); c.set_line_width(7)
        for k in range(3):
            c.new_path(); c.arc(hx - ch.facing * 6, hy - 6, LIMB["head"] - 2, math.pi * (1.25 + k * .08), math.pi * (1.55 + k * .08)); c.stroke()
    elif hair == "bun":
        c.new_path(); c.arc(hx - ch.facing * 30, hy - 52, 20, 0, 2 * math.pi); fill_stroke(c, col, col, 4)
    elif hair == "spike":
        for k in range(-2, 3): line(c, (hx + k * 14, hy - 50), (hx + k * 18, hy - 76), 7, col)
    elif hair == "pony":
        poly(c, [(hx - ch.facing * 50, hy - 20), (hx - ch.facing * 78, hy + 10), (hx - ch.facing * 70, hy + 40)], 10, col)
    if look.get("hat"):
        c.new_path(); c.arc(hx, hy - 8, LIMB["head"] + 4, math.pi, 2 * math.pi); c.close_path(); fill_stroke(c, look["hat"], INKC, 8)
        line(c, (hx, hy - 10), (hx + ch.facing * 86, hy - 10), 12, INKC)
    f = dict(face or {}); f["_who"] = ch.name
    draw_face(c, hx, hy, ch.facing, f, talk, t, red)
    if (fx or {}).get("sweat"):
        for k, (ox, oy) in enumerate([(-62, -20), (60, -40), (-50, 30)]):
            yy = hy + oy + ((t * 120 + k * 40) % 60)
            c.new_path(); c.move_to(hx + ox, yy - 14); c.curve_to(hx + ox + 10, yy, hx + ox + 8, yy + 10, hx + ox, yy + 10)
            c.curve_to(hx + ox - 8, yy + 10, hx + ox - 10, yy, hx + ox, yy - 14); fill_stroke(c, "#7FD1FF", INKC, 4)
    if (fx or {}).get("steam"):
        for k in range(3):
            ph = (t * 1.6 + k / 3) % 1; sx = hx + (k - 1) * 40; sy = hy - 70 - ph * 90
            c.new_path(); c.arc(sx + 10 * math.sin(t * 5 + k), sy, 14 + 16 * ph, 0, 2 * math.pi)
            c.set_source_rgba(1, 1, 1, 0.9 * (1 - ph)); c.fill_preserve(); c.set_source_rgba(*INKC, .5 * (1 - ph)); c.set_line_width(4); c.stroke()
    # front arm last so held items sit in front
    poly(c, [J["sh"], J["elF"], J["hF"]], 15, col)
    if hold: draw_prop(c, dict(type=hold), J["hF"][0], J["hF"][1], t, held=True, facing=ch.facing)
    return J

# ---------------------------------------------------------------- props
def lunchbox(c, x, y, s=1.0, label=True):
    c.save(); c.translate(x, y); c.scale(s, s)
    rrect(c, -46, -30, 92, 54, 10); fill_stroke(c, "#FFFFFF", INKC, 6)
    rrect(c, -50, -40, 100, 16, 6); fill_stroke(c, "#4DA3FF", INKC, 6)
    if label:
        rrect(c, -26, -14, 52, 22, 4); fill_stroke(c, "#FFE07A", INKC, 3)
    c.restore()

def draw_prop(c, pr, x, y, t, held=False, facing=1):
    ty = pr["type"]
    if ty == "lunch": lunchbox(c, x + facing * 20, y - 10 if held else y, pr.get("s", 1.0))
    elif ty == "sandwich":
        c.save(); c.translate(x + facing * 14, y - 6)
        c.new_path(); c.move_to(-34, 14); c.line_to(34, 14); c.line_to(0, -34); c.close_path(); fill_stroke(c, "#F2C27B", INKC, 5)
        line(c, (-24, 4), (24, 4), 7, hexc("#6CC24A")); c.restore()
    elif ty == "cup":
        c.save(); c.translate(x + facing * 10, y - 18); c.new_path(); c.move_to(-16, -22); c.line_to(16, -22); c.line_to(12, 22); c.line_to(-12, 22); c.close_path()
        fill_stroke(c, "#DDF3FF", INKC, 5); c.restore()
    elif ty == "paper":
        c.save(); c.translate(x + facing * 30, y - 20); c.rotate(-0.15 * facing); rrect(c, -34, -44, 68, 88, 4); fill_stroke(c, "#FFFFFF", INKC, 5)
        text(c, "WARNING", 0, -24, 15, hexc("#E0453A"), anchor="c")
        for k in range(4): line(c, (-22, -4 + k * 13), (22, -4 + k * 13), 4, (0.6, 0.6, 0.65))
        c.restore()
    elif ty == "spoon":
        line(c, (x, y), (x + facing * 40, y + 60), 8, INKC)
    elif ty == "pot":
        rrect(c, x - 80, y - 70, 160, 80, 16); fill_stroke(c, "#555A66", INKC, 7)
        c.new_path(); c.arc(x, y - 70, 78, math.pi, 2 * math.pi); c.close_path(); c.set_source_rgb(*hexc("#C8321E")); c.fill()
        for k in range(4):  # bubbling chili + steam
            ph = (t * 1.3 + k * .27) % 1
            c.new_path(); c.arc(x - 50 + k * 34, y - 80 - ph * 140, 10 + 14 * ph, 0, 2 * math.pi)
            c.set_source_rgba(1, 1, 1, .8 * (1 - ph)); c.fill()
        for k in range(5):
            fx_ = x - 70 + k * 35; fh = 30 + 14 * math.sin(t * 18 + k * 1.7)
            c.new_path(); c.move_to(fx_ - 14, y + 30); c.curve_to(fx_ - 10, y + 10, fx_, y + 30 - fh, fx_, y + 30 - fh)
            c.curve_to(fx_, y + 30 - fh, fx_ + 10, y + 10, fx_ + 14, y + 30); c.close_path(); c.set_source_rgb(*hexc("#FF8A1F")); c.fill()
    elif ty == "pepper":
        c.save(); c.translate(x, y); c.rotate(.5); c.new_path(); c.move_to(-40, -8); c.curve_to(0, -30, 40, -20, 60, 30); c.curve_to(30, 10, -10, 20, -40, 8); c.close_path()
        fill_stroke(c, "#E0453A", INKC, 6); line(c, (-40, 0), (-60, -16), 8, hexc("#3E9A3A")); c.restore()
    elif ty == "note":
        c.save(); c.translate(x, y); c.rotate(pr.get("rot", -.08)); rrect(c, -110, -80, 220, 160, 6); fill_stroke(c, "#FFF6A8", INKC, 6)
        if pr.get("lines"):
            for k, ln in enumerate(pr["lines"]): text(c, ln, 0, -44 + k * 30, 22, INKC)
        else:
          for k in range(4):  # unreadable scribble: the cliffhanger
            c.new_path(); c.move_to(-80, -40 + k * 28)
            for j in range(16): c.line_to(-80 + j * 10, -40 + k * 28 + 6 * math.sin(j * 1.9 + k))
            c.set_source_rgb(*INKC); c.set_line_width(4); c.stroke()
        c.set_source_rgba(.85, .85, .85, .8); rrect(c, -40, -96, 80, 30, 3); c.fill()
        c.restore()
    elif ty == "bubble":
        s = pr["text"]; c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(44)
        lines_ = wrapc(c, s, 520); bw = max(c.text_extents(l)[2] for l in lines_) + 70; bh = len(lines_) * 58 + 44
        bx, by = x - bw / 2, y - bh
        rrect(c, bx, by, bw, bh, 34); c.move_to(x - 20, y - 2); c.line_to(x + pr.get("tail", 30), y + 44); c.line_to(x + 30, y - 2)
        fill_stroke(c, "#FFFFFF", INKC, 6)
        for i, l in enumerate(lines_): text(c, l, x, by + 46 + i * 58, 44, INKC)

def wrapc(c, s, maxw):
    out, cur = [], ""
    for w in s.split():
        tst = (cur + " " + w).strip()
        if c.text_extents(tst)[2] <= maxw: cur = tst
        else: out.append(cur); cur = w
    return out + [cur]

# ---------------------------------------------------------------- sets
def set_kitchen(c, t, st, dark=False):
    c.set_source_rgb(*hexc("#F6ECDC")); c.paint()
    for k in range(-1080, 2 * W, 90): c.set_source_rgba(0, 0, 0, .025); c.rectangle(k, 0, 45, GROUND); c.fill()
    c.set_source_rgb(*hexc("#D8C3A5")); c.rectangle(-1500, GROUND, W + 3000, H * 2); c.fill()
    line(c, (-1500, GROUND), (W + 1500, GROUND), 8)
    rrect(c, 60, 300, 240, 200, 10); fill_stroke(c, "#BFE6FF", INKC, 8)  # window
    line(c, (180, 300), (180, 500), 6); line(c, (60, 400), (300, 400), 6)
    clock(c, 880, 340, st.get("clock", "12:00"))
    # counter + stove
    rrect(c, 680, 930, 400, 250, 0); fill_stroke(c, "#E9D9BF", INKC, 8)
    rrect(c, 660, 900, 440, 40, 8); fill_stroke(c, "#9B7B5B", INKC, 8)
    for k in range(2): rrect(c, 710 + k * 190, 980, 160, 160, 10); fill_stroke(c, None, INKC, 6)
    fridge(c, 350, 560, st.get("fridge_open", False), st.get("fridge_contents", []), t, st.get("sign"))
    if dark:
        c.set_source_rgba(0.05, 0.05, 0.15, 0.72); c.paint()
        if st.get("fridge_open"):
            pat = cairo.RadialGradient(460, 900, 40, 460, 900, 520); pat.add_color_stop_rgba(0, 1, 0.97, 0.8, .55); pat.add_color_stop_rgba(1, 1, 1, .8, 0)
            c.set_source(pat); c.paint()

def fridge(c, x, y, open_, contents, t, sign=None):
    w, h = 230, GROUND - y
    rrect(c, x, y, w, h, 18); fill_stroke(c, "#FAFAFA", INKC, 8)
    if open_:
        rrect(c, x + 14, y + 14, w - 28, h - 28, 10); fill_stroke(c, "#FFFBE6", INKC, 6)
        for k in range(3): line(c, (x + 20, y + 150 + k * 150), (x + w - 20, y + 150 + k * 150), 6)
        for k, item in enumerate(contents): draw_prop(c, dict(type=item), x + w / 2, y + 130 + k * 150, t)
        c.new_path(); c.move_to(x + w, y); c.line_to(x + w + 90, y + 40); c.line_to(x + w + 90, y + h - 30); c.line_to(x + w, y + h); c.close_path()
        fill_stroke(c, "#EDEDED", INKC, 8)
    else:
        line(c, (x, y + 230), (x + w, y + 230), 6)
        line(c, (x + w - 30, y + 80), (x + w - 30, y + 170), 10); line(c, (x + w - 30, y + 290), (x + w - 30, y + 400), 10)
        if sign:
            rrect(c, x + 20, y + 40, 160, 150, 6); fill_stroke(c, "#FFE07A", INKC, 5)
            for k, ln in enumerate(sign.split("|")): text(c, ln, x + 100, y + 75 + k * 32, 22, hexc("#C8321E") if k == 0 else INKC)
        else:
            rrect(c, x + 40, y + 60, 90, 70, 6); fill_stroke(c, "#FFE07A", INKC, 4)  # sticky note "LABEL YOUR FOOD"
            text(c, "LABEL", x + 85, y + 85, 18); text(c, "IT!", x + 85, y + 108, 18)

def clock(c, x, y, s):
    c.new_path(); c.arc(x, y, 62, 0, 2 * math.pi); fill_stroke(c, "#FFFFFF", INKC, 8)
    text(c, s, x, y, 30)

def set_office(c, t, st):
    c.set_source_rgb(*hexc("#E4EEF3")); c.paint()
    c.set_source_rgb(*hexc("#AFC3CF")); c.rectangle(-1500, GROUND, W + 3000, H * 2); c.fill(); line(c, (-1500, GROUND), (W + 1500, GROUND), 8)
    rrect(c, 90, 330, 520, 300, 12); fill_stroke(c, "#FFFFFF", INKC, 8)  # whiteboard
    wb = st.get("whiteboard")
    if wb:
        for i, l in enumerate(wb.split("|")): text(c, l, 350, 420 + i * 70, 54, hexc("#E0453A"))
    else:
        poly(c, [(140, 580), (240, 520), (330, 550), (460, 430), (560, 460)], 8, hexc("#4DA3FF"))
    if st.get("cooler", True):  # water cooler
        x = 880; rrect(c, x - 60, 860, 120, 320, 10); fill_stroke(c, "#DADFE6", INKC, 8)
        c.new_path(); c.move_to(x - 50, 860); c.curve_to(x - 70, 740, x - 60, 680, x, 680); c.curve_to(x + 60, 680, x + 70, 740, x + 50, 860); c.close_path()
        fill_stroke(c, "#8FD3FF", INKC, 8)
        for k in range(3):
            ph = (t * .7 + k / 3) % 1; c.new_path(); c.arc(x - 20 + k * 20, 840 - ph * 140, 7, 0, 2 * math.pi); c.set_source_rgba(1, 1, 1, .8); c.fill()
    if st.get("table"):
        rrect(c, 180, 1000, 560, 34, 8); fill_stroke(c, "#9B7B5B", INKC, 8)
        line(c, (230, 1034), (230, GROUND), 12); line(c, (690, 1034), (690, GROUND), 12)

def set_desk(c, t, st):
    c.set_source_rgb(*hexc("#EEE7F5")); c.paint()
    c.set_source_rgb(*hexc("#C2B4D3")); c.rectangle(-1500, GROUND, W + 3000, H * 2); c.fill(); line(c, (-1500, GROUND), (W + 1500, GROUND), 8)
    rrect(c, 120, 330, 230, 170, 8); fill_stroke(c, "#FFE9A8", INKC, 8); text(c, "EMPLOYEE", 235, 395, 26); text(c, "OF THE MONTH", 235, 430, 26)
    if st.get("minifridge"):
        x = 760; rrect(c, x, 890, 210, 290, 16); fill_stroke(c, "#FAFAFA", INKC, 8)
        line(c, (x + 180, 940), (x + 180, 1060), 10)
        # padlock
        c.new_path(); c.arc(x + 105, 1000, 30, math.pi, 2 * math.pi); c.set_source_rgb(*INKC); c.set_line_width(12); c.stroke()
        rrect(c, x + 65, 1000, 80, 66, 10); fill_stroke(c, "#FFC83D", INKC, 7)
        sparkle(c, x + 200, 880, t); sparkle(c, x + 20, 940, t + .5)
    if st.get("desk", True):
        rrect(c, 80, 1000, 520, 30, 6); fill_stroke(c, "#9B7B5B", INKC, 8)
        line(c, (120, 1030), (120, GROUND), 12); line(c, (560, 1030), (560, GROUND), 12)
        rrect(c, 230, 830, 220, 150, 10); fill_stroke(c, "#2E3440", INKC, 8); line(c, (340, 980), (340, 1000), 14)

def sparkle(c, x, y, t):
    s = 14 + 8 * math.sin(t * 6); c.set_source_rgb(*hexc("#FFC83D"))
    c.new_path(); c.move_to(x, y - s); c.line_to(x + s * .3, y - s * .3); c.line_to(x + s, y); c.line_to(x + s * .3, y + s * .3)
    c.line_to(x, y + s); c.line_to(x - s * .3, y + s * .3); c.line_to(x - s, y); c.line_to(x - s * .3, y - s * .3); c.close_path(); c.fill()

def set_closeup(c, t, st):
    pat = cairo.RadialGradient(540, 820, 50, 540, 820, 900); pat.add_color_stop_rgb(0, *hexc(st.get("bg1", "#FFF3D6"))); pat.add_color_stop_rgb(1, *hexc(st.get("bg2", "#F2C98A")))
    c.set_source(pat); c.paint()
    for k in range(18):  # speed lines for drama
        a = k / 18 * 2 * math.pi + t * .05
        c.set_source_rgba(1, 1, 1, .35); c.set_line_width(10)
        c.move_to(540 + 380 * math.cos(a), 820 + 380 * math.sin(a)); c.line_to(540 + 1400 * math.cos(a), 820 + 1400 * math.sin(a)); c.stroke()
    what = st.get("show")
    if what == "label":
        lunchbox(c, 540, 860, 5.0, label=False)
        c.save(); c.translate(540, 860); rrect(c, -170, -90, 340, 140, 14); fill_stroke(c, "#FFE07A", INKC, 8)
        text(c, "LUNCH", 0, -40, 62); text(c, "extra spicy. do not eat.", 0, 20, 21, hexc("#C8321E"))
        c.restore()
        k = max(0, min(1, (t - st.get("t0", 0)) / 1.2))
        if k > 0:  # magnifier slides over the tiny text
            mx, my = lerp(900, 560, ease(k)), lerp(1250, 900, ease(k))
            c.new_path(); c.arc(mx, my, 120, 0, 2 * math.pi); c.set_source_rgba(1, 1, 1, .25); c.fill_preserve(); c.set_source_rgb(*INKC); c.set_line_width(14); c.stroke()
            line(c, (mx + 85, my + 85), (mx + 190, my + 190), 26)
            c.save(); c.new_path(); c.arc(mx, my, 108, 0, 2 * math.pi); c.clip()
            text(c, "DO NOT EAT", mx, my - 20, 44, hexc("#C8321E")); text(c, "extra spicy", mx, my + 30, 32, hexc("#C8321E")); c.restore()
    elif what == "pepper":
        c.save(); c.translate(540, 860); c.scale(4.2, 4.2); c.rotate(math.sin(t * 3) * .05)
        draw_prop(c, dict(type="pepper"), 0, 0, t); c.restore()
        for k in range(7):
            fx_ = 300 + k * 80; fh = 160 + 60 * math.sin(t * 14 + k * 1.3)
            c.new_path(); c.move_to(fx_ - 40, 1180); c.curve_to(fx_ - 30, 1100, fx_, 1180 - fh, fx_, 1180 - fh)
            c.curve_to(fx_, 1180 - fh, fx_ + 30, 1100, fx_ + 40, 1180); c.close_path(); c.set_source_rgba(1, .45, .1, .85); c.fill()
    elif what == "notebig":
        c.save(); c.translate(540, 820); c.scale(2.6, 2.6)
        draw_prop(c, dict(type="note", rot=-0.04 + 0.01 * math.sin(t * 2), lines=st.get("note_lines")), 0, 0, t); c.restore()
    elif what == "note":
        lunchbox(c, 540, 900, 5.0, label=False)
        draw_prop(c, dict(type="note", rot=-0.06 + 0.02 * math.sin(t * 2), lines=st.get("note_lines")), 540, 800, t)
    elif what == "text":  # big reaction text, e.g. "3:00 AM" or "???"
        c.save(); c.translate(540, 820); sc = 1 + 0.04 * math.sin(t * 5); c.scale(sc, sc)
        lines = st.get("big", "???").split("|"); c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(170)
        widest = max(c.text_extents(l)[2] for l in lines) * 1.16 + 1  # + outline; shrink long lines to fit ~960 px
        size = 170 * min(1.0, 960 / widest)
        for i, l in enumerate(lines): text(c, l, 0, (i - (len(lines) - 1) / 2) * 190 * size / 170, size, hexc(st.get("color", "#E0453A")), outline=INKC)
        c.restore()
    elif what == "part2":
        draw_prop(c, dict(type="note", rot=-0.1), 540, 760, t)
        c.save(); c.translate(540, 760); c.scale(2.4, 2.4); text(c, "?", 0, 0, 120, hexc("#E0453A"), weight=cairo.FONT_WEIGHT_BOLD, outline=INKC); c.restore()

def _floor(c, wall, floor):
    c.set_source_rgb(*hexc(wall)); c.paint()
    c.set_source_rgb(*hexc(floor)); c.rectangle(-1500, GROUND, W + 3000, H * 2); c.fill(); line(c, (-1500, GROUND), (W + 1500, GROUND), 8)

def _dark(c, glow=None):
    c.set_source_rgba(0.04, 0.04, 0.14, 0.72); c.paint()
    if glow:
        gx, gy, r = glow; pat = cairo.RadialGradient(gx, gy, 20, gx, gy, r)
        pat.add_color_stop_rgba(0, .75, .9, 1, .55); pat.add_color_stop_rgba(1, .75, .9, 1, 0); c.set_source(pat); c.paint()

def set_bedroom(c, t, st):
    """state: dark (bool), phone (bool: blue phone glow on the bed), clock ('3:00')"""
    _floor(c, "#E8E1F7", "#B9A9D6")
    rrect(c, 640, 300, 300, 240, 10); fill_stroke(c, "#1E2A4A" if st.get("dark") else "#BFE6FF", INKC, 8)
    line(c, (790, 300), (790, 540), 6); line(c, (640, 420), (940, 420), 6)
    if st.get("dark"): c.new_path(); c.arc(860, 360, 30, 0, 2 * math.pi); c.set_source_rgb(1, .97, .8); c.fill()
    rrect(c, 60, 960, 560, 120, 18); fill_stroke(c, "#7FB2FF", INKC, 8)       # bed
    rrect(c, 60, 900, 130, 80, 30); fill_stroke(c, "#FFFFFF", INKC, 7)       # pillow
    rrect(c, 40, 860, 40, 320, 8); fill_stroke(c, "#9B7B5B", INKC, 7)
    line(c, (90, 1080), (90, GROUND), 12); line(c, (590, 1080), (590, GROUND), 12)
    rrect(c, 700, 1040, 140, 140, 8); fill_stroke(c, "#9B7B5B", INKC, 7)     # nightstand
    rrect(c, 720, 985, 100, 55, 8); fill_stroke(c, "#2E3440", INKC, 5)
    text(c, st.get("clock", "3:00"), 770, 1013, 30, hexc("#FF5A4E"))
    if st.get("dark"): _dark(c, (340, 900, 420) if st.get("phone") else None)

def set_classroom(c, t, st):
    """state: board ('LINE1|LINE2' on the chalkboard)"""
    _floor(c, "#F6EBD3", "#C9B48E")
    rrect(c, 120, 300, 840, 380, 12); fill_stroke(c, "#2F5D50", INKC, 10)
    for i, l in enumerate(st.get("board", "2 + 2 = ?").split("|")): text(c, l, 540, 400 + i * 90, 70, (0.97, 0.97, 0.95))
    for x in (160, 640):
        rrect(c, x, 1010, 300, 26, 6); fill_stroke(c, "#C98B4F", INKC, 7)
        line(c, (x + 30, 1036), (x + 30, GROUND), 10); line(c, (x + 270, 1036), (x + 270, GROUND), 10)
    clock(c, 960, 230, st.get("clock", "2:59"))

def set_street(c, t, st):
    """state: night (bool)"""
    night = st.get("night")
    c.set_source_rgb(*hexc("#1B2340" if night else "#BFE6FF")); c.paint()
    for i, (x, w_, h_, col) in enumerate([(-200, 300, 600, "#F2B880"), (130, 260, 760, "#A8C686"), (420, 320, 540, "#F28F8F"), (770, 280, 700, "#9BB7E0"), (1070, 300, 620, "#E6C36A")]):
        rrect(c, x, GROUND - 120 - h_, w_, h_, 6); fill_stroke(c, col, INKC, 8)
        for r in range(int(h_ / 140)):
            for q in range(2):
                rrect(c, x + 40 + q * (w_ / 2 - 10), GROUND - 80 - h_ + r * 140, w_ / 2 - 70, 80, 6)
                fill_stroke(c, "#FFE9A0" if night and (r + q + i) % 3 else "#E8F6FF", INKC, 5)
    c.set_source_rgb(*hexc("#9AA0A6")); c.rectangle(-1500, GROUND - 120, W + 3000, 120); c.fill(); line(c, (-1500, GROUND - 120), (W + 1500, GROUND - 120), 8)
    c.set_source_rgb(*hexc("#5A5F66")); c.rectangle(-1500, GROUND, W + 3000, H * 2); c.fill(); line(c, (-1500, GROUND), (W + 1500, GROUND), 8)
    if night: c.set_source_rgba(0.05, 0.05, 0.2, 0.35); c.paint()
    else: c.new_path(); c.arc(960, 180, 70, 0, 2 * math.pi); fill_stroke(c, "#FFD23F", INKC, 6)

def set_living(c, t, st):
    """state: tv ('TEXT' on the TV screen), dark (bool)"""
    _floor(c, "#FBE3D3", "#D9A98A")
    rrect(c, 80, 940, 520, 160, 30); fill_stroke(c, "#E0453A", INKC, 8)       # couch
    rrect(c, 60, 880, 90, 260, 30); fill_stroke(c, "#C93A30", INKC, 8); rrect(c, 530, 880, 90, 260, 30); fill_stroke(c, "#C93A30", INKC, 8)
    rrect(c, 700, 660, 330, 220, 12); fill_stroke(c, "#20242C", INKC, 10)    # TV
    if st.get("tv"):
        for i, l in enumerate(st["tv"].split("|")): text(c, l, 865, 740 + i * 60, 46, (1, 1, 1))
    rrect(c, 760, 880, 210, 300, 8); fill_stroke(c, "#9B7B5B", INKC, 8)
    if st.get("dark"): _dark(c, (865, 770, 520))

SETS = {"kitchen": set_kitchen, "night": lambda c, t, st: set_kitchen(c, t, st, dark=True),
        "office": set_office, "desk": set_desk, "closeup": set_closeup,
        "bedroom": set_bedroom, "classroom": set_classroom, "street": set_street, "living": set_living}
