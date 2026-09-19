# -*- coding: utf-8 -*-
"""Download the OFFICIAL Lichess puzzle DB and build a validated 100k pool.

ACCURATE SIDE-TO-MOVE:
  Lichess format: FEN = position BEFORE the opponent's setup move;
  Moves = [opponent move, solver move, opponent reply, ...].
  The position the viewer must SOLVE is FEN + Moves[0], and the side to move
  there — computed with python-chess — is the SOLVER.
  We therefore store:
    fen   = position AFTER the opponent's setup move (what the viewer sees)
    stm   = 'w' or 'b' — the solver's side, machine-verified
    moves = the solver's solution line ONLY (setup move dropped)
  board_renderer.turn_text then uses this directly (no flipping, no guessing).
"""
import csv, io, json, os, sys, urllib.request

URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"

DECISIVE_THEMES = ("mate", "mateIn1", "mateIn2", "mateIn3", "mateIn4", "mateIn5",
                   "advantage", "winning", "crushing", "equality")
TARGET = int(sys.argv[sys.argv.index("--target") + 1]) if "--target" in sys.argv else int(os.environ.get("PUZZLE_TARGET", 100000))
RATING_MIN, RATING_MAX = 1400, 2500
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzles.jsonl")

def log(*a, **kw): print(*a, flush=True, **kw)

def download(dest):
    log("Downloading Lichess puzzle database (~300 MB, official & free)...")
    req = urllib.request.Request(URL, headers={"User-Agent": "ChessPuzzleBot/1.0"})
    done = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk: break
            f.write(chunk); done += len(chunk)
            log(f"\r  {done/1e6:.0f} MB", end="")
    log("\nDownload complete.")

def build_record(fen, moves, themes):
    """Validate with python-chess and return the record, or None."""
    import chess
    if len(moves) < 3: return None               # setup move + solver move + reply minimum
    try:
        board = chess.Board(fen)
        setup = chess.Move.from_uci(moves[0])
        if setup not in board.legal_moves: return None
        board.push(setup)                        # -> position the SOLVER faces
        stm = "w" if board.turn == chess.WHITE else "b"   # machine-verified side to move
        sol = moves[1:]
        for u in sol:
            m = chess.Move.from_uci(u)
            if m not in board.legal_moves: return None
            board.push(m)
        if "mate" in themes and not board.is_checkmate(): return None
        display = chess.Board(fen); display.push(setup)
        return {"id": None, "fen": display.fen(), "moves": sol,
                "stm": stm, "rating": None, "themes": themes}
    except Exception:
        return None

def main():
    import chess  # fail fast if missing
    import zstandard
    zpath = os.path.join(os.path.dirname(OUT), "lichess_db_puzzle.csv.zst")
    if not os.path.exists(zpath): download(zpath)
    kept, seen = 0, set()
    with open(zpath, "rb") as fz, open(OUT, "w", encoding="utf-8") as out:
        z = zstandard.ZstdDecompressor().stream_reader(fz, read_size=4 << 20)
        reader = csv.reader(io.TextIOWrapper(z, encoding="utf-8"))
        idx = {n: i for i, n in enumerate(next(reader))}
        for row in reader:
            if kept >= TARGET: break
            rating = int(row[idx["Rating"]]); rd = int(row[idx["RatingDeviation"]])
            pop = int(row[idx["Popularity"]])
            if not (RATING_MIN <= rating <= RATING_MAX and rd < 100 and pop >= 90): continue
            if not any(t in row[idx["Themes"]] for t in DECISIVE_THEMES): continue
            pid = row[idx["PuzzleId"]]
            if pid in seen: continue
            rec = build_record(row[idx["FEN"]], row[idx["Moves"]].split(), row[idx["Themes"]])
            if rec is None: continue
            rec["id"], rec["rating"] = pid, rating
            seen.add(pid)
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            kept += 1
            if kept % 5000 == 0: log(f"  {kept} puzzles validated & saved")
    log(f"DONE: {kept} puzzles saved to {OUT}")
    if kept < TARGET:
        log(f"WARNING: only {kept} reached; rerun after a newer DB release or relax filters.")

if __name__ == "__main__":
    main()
