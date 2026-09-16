# -*- coding: utf-8 -*-
"""Lichess-exact board renderer (official cburnett pieces, brown theme)."""
import os, math
from PIL import Image, ImageDraw, ImageFont

PIECE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "pieces")
def _font(candidates, size):
    """Load a font cross-platform (Windows paths first, then Linux DejaVu)."""
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()

SERIF = ["C:/Windows/Fonts/georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
SANS_B = ["C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
SANS  = ["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

LIGHT = (240, 217, 181)   # lichess brown light  #f0d9b5
DARK  = (181, 136, 99)    # lichess brown dark   #b58863
HLMASK = (255, 213, 79, 96)
ARROW  = (155, 199, 0, 128)

def parse_fen(fen):
    board = {}
    for r, row in enumerate(fen.split()[0].split("/")):
        c = 0
        for ch in row:
            if ch.isdigit(): c += int(ch)
            else:
                board[(c, 7-r)] = ch; c += 1
    return board

def piece_img(p, S):
    im = Image.open(os.path.join(PIECE_DIR, ("w" if p.isupper() else "b") + p.upper() + ".png")).convert("RGBA")
    return im.resize((S, S), Image.LANCZOS)

def sq_xy(sq, S, ox, oy):
    f = ord(sq[0]) - 97; r = int(sq[1]) - 1
    return ox + f*S, oy + (7-r)*S

def draw_arrow(layer, a, b, S, ox, oy):
    d = ImageDraw.Draw(layer)
    x1,y1 = sq_xy(a,S,ox,oy); x2,y2 = sq_xy(b,S,ox,oy)
    cx, cy = x1+S/2, y1+S/2; dx, dy = x2+S/2, y2+S/2
    ang = math.atan2(dy-cy, dx-cx)
    w = S*0.22
    sx, sy = cx + S*0.18*math.cos(ang), cy + S*0.18*math.sin(ang)
    ex, ey = dx - w*0.75*math.cos(ang), dy - w*0.75*math.sin(ang)
    d.line([sx,sy,ex,ey], fill=ARROW, width=int(w))
    hw = w*1.4
    for s in (-1, 1):
        d.polygon([(ex,ey),
                   (ex + hw*math.cos(ang + s*0.42), ey + hw*math.sin(ang + s*0.42)),
                   (ex + hw*0.4*math.cos(ang), ey + hw*0.4*math.sin(ang))], fill=ARROW)

def render_board(fen, size=1440, title=None, top2=None, foot=None, foot2=None,
                 last=None, sol=None):
    S = size // 8
    pad_top = int(size*0.22) if title else int(size*0.06)
    pad_bot = int(size*0.22) if foot else int(size*0.06)
    pad = int(size*0.05)
    W = size + 2*pad
    H = size + pad_top + pad_bot
    oy = pad_top; ox = pad
    img = Image.new("RGBA", (W, H), (36, 37, 38, 255))
    board = parse_fen(fen)
    for r in range(8):
        for c in range(8):
            x, y = ox + c*S, oy + (7-r)*S
            img.paste(Image.new("RGBA",(S,S), LIGHT if (c+r)%2==0 else DARK), (x,y))
    if last:
        hl = Image.new("RGBA", (W, H), (0,0,0,0)); hd = ImageDraw.Draw(hl)
        for sq in last:
            x, y = sq_xy(sq, S, ox, oy)
            hd.rectangle([x, y, x+S, y+S], fill=HLMASK)
        img = Image.alpha_composite(img, hl)
    if sol and len(sol) == 2:
        al = Image.new("RGBA", (W, H), (0,0,0,0))
        draw_arrow(al, sol[0], sol[1], S, ox, oy)
        img = Image.alpha_composite(img, al)
    for (c, r), p in board.items():
        x, y = ox + c*S, oy + (7-r)*S
        img.alpha_composite(piece_img(p, S), (x, y))
    d = ImageDraw.Draw(img)
    fs = max(18, int(S*0.20))
    fnt = _font(SERIF, fs)
    for i in range(8):
        x, y = ox + i*S, oy + 7*S
        d.text((x + S - fs*0.35, y + S - fs*0.35), chr(97+i), font=fnt,
               anchor="rs", fill=LIGHT if i % 2 == 1 else DARK)
        x, y = ox, oy + (7-i)*S
        d.text((x + fs*0.35, y + fs*0.3), str(i+1), font=fnt,
               anchor="ls", fill=LIGHT if i % 2 == 0 else DARK)
    overlay = img.convert("RGBA")
    od = ImageDraw.Draw(overlay)
    def band(text, cy, fh, font_key):
        if not text: return
        # auto-shrink font until text fits inside canvas with margins
        maxw = W * 0.92
        fnt = _font(font_key, fh)
        while od.textlength(text, font=fnt) > maxw and fh > 20:
            fh = int(fh * 0.92)
            fnt = _font(font_key, fh)
        tw = od.textlength(text, font=fnt)
        bx0 = W//2 - tw/2 - fh*0.45; bx1 = W//2 + tw/2 + fh*0.45
        by0 = cy - fh*0.75; by1 = cy + fh*0.75
        od.rounded_rectangle([bx0, by0, bx1, by1], radius=int(fh*0.35), fill=(12, 12, 16, 225))
        d.text((W//2, cy), text, font=fnt, anchor="mm", fill=(255,255,255))
    if title:
        band(title, int(pad_top*0.30), int(size*0.115), SANS_B)
    if top2:
        fh2 = int(size*0.062)
        tf2 = _font(SANS, fh2)
        while od.textlength(top2, font=tf2) > W * 0.9 and fh2 > 20:
            fh2 = int(fh2 * 0.92)
            tf2 = _font(SANS, fh2)
        od.rounded_rectangle([W*0.05, int(pad_top*0.62) - int(fh2*0.85), W*0.95,
                              int(pad_top*0.62) + int(fh2*0.85)],
                             radius=int(size*0.03), fill=(12, 12, 16, 200))
        d.text((W//2, int(pad_top*0.62)), top2, font=tf2, anchor="mm", fill=(255, 205, 60))
    if foot:
        band(foot, H - int(pad_bot*0.60), int(size*0.060), SANS_B)
    if foot2:
        band(foot2, H - int(pad_bot*0.20), int(size*0.048), SANS)
    return Image.alpha_composite(overlay, Image.new("RGBA", overlay.size, (0,0,0,0))).convert("RGB")

