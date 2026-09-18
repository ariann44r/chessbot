# -*- coding: utf-8 -*-
"""Board renderer — lichess-exact (official cburnett pieces, brown theme).

Layouts (approved by the user):
- 16:9 long video: board fills the ENTIRE LEFT side edge-to-edge,
  texts on the RIGHT: "Puzzle #N" -> "White/Black to move" -> "Comment the answer!"
- 9:16 Short: full-width board centered, same texts above and below.
The solution is NEVER drawn on the board.
"""
import os
from PIL import Image, ImageDraw, ImageFont

PIECE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "pieces")
LIGHT = (240, 217, 181)   # lichess brown light  #f0d9b5
DARK  = (181, 136, 99)    # lichess brown dark   #b58863
BG    = (22, 21, 18)      # near-black background
GOLD  = (240, 201, 135)
GREY  = (185, 182, 165)
GREEN = (157, 168, 143)

def _font(name, size):
    paths = (f"C:/Windows/Fonts/{name}.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # GitHub Linux runner
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

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

def turn_text(fen):
    """The SOLVER's turn — the side that plays the winning solution.
    Lichess DB format: the FEN side-to-move plays moves[0], which is the
    opponent's (losing) setup move. The puzzle is solved by the OTHER side.
    So the solver is always the OPPOSITE of the FEN side to move.
    (Example: FEN '... b' + Kxf7 ... means WHITE mates in 2 -> 'White to move'.)"""
    solver = "w" if fen.split()[1] == "b" else "b"
    return "White to move" if solver == "w" else "Black to move"

def _draw_board(img, fen, bx, by, S, with_coords=True):
    d = ImageDraw.Draw(img)
    for r in range(8):
        for c in range(8):
            d.rectangle([bx+c*S, by+(7-r)*S, bx+(c+1)*S-1, by+(8-r)*S-1],
                        fill=LIGHT if (c+r) % 2 == 0 else DARK)
    for (c, r), p in parse_fen(fen).items():
        img.paste(piece_img(p, int(S*0.95)), (int(bx+c*S + S*0.025), int(by+(7-r)*S + S*0.025)),
                  piece_img(p, int(S*0.95)))
    if with_coords:  # small lichess-style coordinates in corner squares
        f = _font("georgiab", max(14, int(S*0.16)))
        for i in range(8):
            x, y = bx+i*S, by+7*S
            d.text((x+S-4, y+S-4), chr(97+i), font=f, anchor="rs",
                   fill=LIGHT if (i+7) % 2 == 0 else DARK)
            d.text((bx+4, by+(7-i)*S+4), str(i+1), font=f,
                   fill=LIGHT if (i+0) % 2 == 0 else DARK)

def _text(img, msg, f, x, y, col, alpha=255):
    if alpha <= 0: return
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((x, y), msg, font=f, fill=tuple(col)+(alpha,), anchor="ma")
    img.paste(Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB"), (0, 0))

# ------------------------------------------------------------------ 16:9
def render_16x9(fen, puzzle_num, W=1920, H=1080, rating=None):
    """Board = full LEFT half (edge-to-edge). Texts on the right side."""
    img = Image.new("RGB", (W, H), BG)
    S = H // 8
    bx, by = 0, 0
    _draw_board(img, fen, bx, by, S)
    tx = (W + 8*S) // 2                      # center of the right area
    f1 = _font("segoeuib", int(H*0.085))      # Puzzle #N
    f2 = _font("segoeuib", int(H*0.052))      # turn
    f3 = _font("segoeui",  int(H*0.045))      # comment
    f4 = _font("segoeui",  int(H*0.036))      # rating
    y = int(H*0.16)
    _text(img, f"Puzzle #{puzzle_num}", f1, tx, y, GOLD)
    y += int(f1.size*1.6)
    if rating:
        _text(img, f"Rating: {rating}", f4, tx, y, GREY); y += int(f4.size*1.9)
    _text(img, turn_text(fen), f2, tx, y, (236, 234, 217)); y += int(f2.size*3.4)
    _text(img, "Comment the answer!", f3, tx, y, GREEN)
    return img

# ------------------------------------------------------------------ 9:16
def render_9x16(fen, puzzle_num, W=1080, H=1920, rating=None):
    """Short: full-width board, texts above and below (approved layout)."""
    img = Image.new("RGB", (W, H), BG)
    S = W // 8
    bx, by = 0, int(H*0.30)
    _draw_board(img, fen, bx, by, S)
    cx = W // 2
    f1 = _font("segoeuib", int(W*0.075))
    f2 = _font("segoeuib", int(W*0.05))
    f3 = _font("segoeui",  int(W*0.045))
    f4 = _font("segoeui",  int(W*0.038))
    y = by - int(f1.size*2.6) - int(f2.size*1.8)
    _text(img, f"Puzzle #{puzzle_num}", f1, cx, y, GOLD)
    y += int(f1.size*1.45)
    if rating:
        _text(img, f"Rating: {rating}", f4, cx, y, GREY); y += int(f4.size*1.7)
    _text(img, turn_text(fen), f2, cx, y, (236, 234, 217))
    _text(img, "Comment the answer!", f3, cx, by + 8*S + int(f3.size*1.2), GREEN)
    return img

# ------------------------------------------------------------------ thumbnail
THUMB_STYLES = [
    # (hook lines, accent color, gradient background) — هر بار متفاوت
    (["99% FAIL",   "THIS PUZZLE!"], (255, 209, 66),  [(18, 18, 24), (46, 26, 10)]),
    (["IMPOSSIBLE?", "TRY IT!"],     (255, 84, 84),   [(26, 10, 10), (10, 18, 26)]),
    (["ONLY 1%",    "CAN SOLVE!"],   (66, 255, 170),  [(8, 22, 16), (16, 30, 40)]),
    (["CAN YOU",    "SURVIVE?"],     (120, 180, 255), [(10, 10, 28), (24, 10, 40)]),
    (["BEWARE:",    "ONLY 1 MOVE!"],  (255, 140, 60),  [(30, 16, 6), (40, 30, 10)]),
    (["GENIUS",     "TEST ♟"],       (212, 175, 55),  [(14, 14, 18), (44, 34, 12)]),
]

def render_thumbnail(fen, puzzle_num, rating=None, W=1280, H=720, variant=0):
    """Attractive, always-different chess thumbnail (style varies per upload)."""
    hook, accent, grad = THUMB_STYLES[variant % len(THUMB_STYLES)]
    img = Image.new("RGB", (W, H), grad[0])
    d = ImageDraw.Draw(img)
    for y in range(H):                     # full-color gradient background
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(grad[0][i]*(1-t)+grad[1][i]*t) for i in range(3)))
    S = H // 8
    d.rectangle([-6, -6, 8*S+6, H+6], fill=tuple(max(0, c-8) for c in grad[0]))
    _draw_board(img, fen, 0, 0, S, with_coords=False)
    d.rectangle([0, 0, 8*S-1, H-1], outline=accent, width=6)
    tx = (W + 8*S) // 2
    _text(img, f"PUZZLE #{puzzle_num}", _font("segoeuib", int(H*0.115)), tx, int(H*0.13), accent)
    _text(img, hook[0], _font("segoeuib", int(H*0.085)), tx, int(H*0.38), (245, 243, 235))
    _text(img, hook[1], _font("segoeuib", int(H*0.085)), tx, int(H*0.52), (245, 243, 235))
    _text(img, (f"RATING {rating}" if rating else "DAILY PUZZLE"), _font("segoeuib", int(H*0.058)), tx, int(H*0.70), accent)
    _text(img, "ANSWER PINNED 💬", _font("segoeuib", int(H*0.045)), tx, int(H*0.82), (160, 160, 150))
    return img

# Backwards-compatible alias (old callers)
def render_board(fen, **kw):
    return render_16x9(fen, kw.get("puzzle_num", 1))
