# -*- coding: utf-8 -*-
"""Download Lichess puzzle DB and build a validated 2,000,000-puzzle pool (rating 1400-2500)."""
import bz2, csv, io, json, os, sys, urllib.request

URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
TARGET = 2000000
RATING_MIN, RATING_MAX = 1400, 2500
# فیلترهای کیفیت را کمی باز کردیم تا به ۲ میلیون پازل برسیم
RD_MAX, POP_MIN = 150, 75
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzles.jsonl")

def log(*a): print(*a, flush=True)

def download(dest):
    log("Downloading Lichess puzzle database (~700 MB, official & free)...")
    req = urllib.request.Request(URL, headers={"User-Agent": "ChessPuzzleBot/1.0"})
    done = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk: break
            f.write(chunk); done += len(chunk)
            print(f"\r  {done/1e6:.0f} MB", end="", flush=True)
    log("\nDownload complete.")

def validate(fen, moves_str):
    """Check the FEN + solution moves are legal using python-chess."""
    try:
        import chess
        board = chess.Board(fen)
        for mv in moves_str.split():
            m = chess.Move.from_uci(mv)
            if m not in board.legal_moves: return False
            board.push(m)
        return True
    except Exception:
        return False

def main():
    import chess  # fail fast if missing
    zpath = os.path.join(os.path.dirname(OUT), "lichess_db_puzzle.csv.zst")
    if not os.path.exists(zpath): download(zpath)
    kept = 0
    seen = set()
    import zstandard
    dctx = zstandard.ZstdDecompressor()
    with open(OUT, "w", encoding="utf-8") as out, \
         open(zpath, "rb") as fh, dctx.stream_reader(fh) as zr, \
         io.TextIOWrapper(zr, encoding="utf-8") as z:
        reader = csv.reader(z)
        header = next(reader)
        idx = {n: i for i, n in enumerate(header)}
        for row in reader:
            if kept >= TARGET: break
            rating = int(row[idx["Rating"]]); rd = int(row[idx["RatingDeviation"]])
            pop = int(row[idx["Popularity"]])
            if not (RATING_MIN <= rating <= RATING_MAX and rd < RD_MAX and pop >= POP_MIN):
                continue
            pid, fen, moves = row[idx["PuzzleId"]], row[idx["FEN"]], row[idx["Moves"]]
            if pid in seen: continue
            if not validate(fen, moves): continue
            seen.add(pid)
            out.write(json.dumps({"id": pid, "fen": fen, "moves": moves.split(),
                                  "rating": rating,
                                  "themes": row[idx["Themes"]]},
                                 ensure_ascii=False) + "\n")
            kept += 1
            if kept % 5000 == 0: log(f"  {kept} puzzles validated & saved")
    log(f"DONE: {kept} puzzles saved to puzzles.jsonl")
    if kept < TARGET:
        log(f"WARNING: only {kept} reached; rerun after a newer DB release or relax filters in config.")

if __name__ == "__main__":
    main()
