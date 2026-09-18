# -*- coding: utf-8 -*-
"""Download Lichess puzzle DB and build a validated 100,000-puzzle pool (rating 1400-2500).
Only DECISIVE puzzles are kept: mate or clear winning advantage (see DECISIVE_THEMES).
The solver side is the OPPOSITE of the FEN side to move (Lichess format)."""
import csv, io, json, os, sys, urllib.request

URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"  # official current format

# A puzzle counts as decisive if its themes contain one of these
DECISIVE_THEMES = ("mate", "mateIn1", "mateIn2", "mateIn3", "mateIn4", "mateIn5",
                   "advantage", "winning", "crushing", "equality")
# Target puzzle-pool size: env var (GitHub runner) or CLI arg or default.
TARGET = int(sys.argv[sys.argv.index("--target") + 1]) if "--target" in sys.argv else int(os.environ.get("PUZZLE_TARGET", 100000))
RATING_MIN, RATING_MAX = 1400, 2500
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzles.jsonl")

def log(*a, **kw): print(*a, flush=True, **kw)

def download(dest):
    log("Downloading Lichess puzzle database (~300 MB, official & free, .zst format)...")
    req = urllib.request.Request(URL, headers={"User-Agent": "ChessPuzzleBot/1.0"})
    done = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk: break
            f.write(chunk); done += len(chunk)
            log(f"\r  {done/1e6:.0f} MB", end="")
    log("\nDownload complete.")

def decisive(themes):
    """Mate or a clear advantage/win only — the puzzle must matter (win or dominate)."""
    return any(t in themes for t in DECISIVE_THEMES)

def validate(fen, moves_str, themes=""):
    """STRICT solution check with python-chess. A puzzle is kept ONLY if:
       1. it HAS a solution (non-empty moves),
       2. every move of the line is legal from the position,
       3. mate-themed puzzles REALLY end in checkmate.
    Source is the OFFICIAL Lichess puzzle database only — nothing else."""
    try:
        import chess
        moves = moves_str.split()
        if not moves: return False            # no solution -> reject
        board = chess.Board(fen)
        for mv in moves:                       # every move must be legal
            m = chess.Move.from_uci(mv)
            if m not in board.legal_moves: return False
            board.push(m)
        if "mate" in themes:                   # mate puzzles must end in checkmate
            return board.is_checkmate()
        return True                            # legal, complete solution line
    except Exception:
        return False

def main():
    import chess  # fail fast if missing
    zpath = os.path.join(os.path.dirname(OUT), "lichess_db_puzzle.csv.zst")
    if not os.path.exists(zpath): download(zpath)
    kept = 0
    seen = set()
    import zstandard
    with open(zpath, "rb") as fz, open(OUT, "w", encoding="utf-8") as out:
        z = zstandard.ZstdDecompressor().stream_reader(fz, read_size=4 << 20)
        reader = csv.reader(io.TextIOWrapper(z, encoding="utf-8"))
        header = next(reader)
        idx = {n: i for i, n in enumerate(header)}
        for row in reader:
            if kept >= TARGET: break
            rating = int(row[idx["Rating"]]); rd = int(row[idx["RatingDeviation"]])
            pop = int(row[idx["Popularity"]])
            if not (RATING_MIN <= rating <= RATING_MAX and rd < 100 and pop >= 90):
                continue
            if not decisive(row[idx["Themes"]]):   # mate / winning advantage only
                continue
            pid, fen, moves = row[idx["PuzzleId"]], row[idx["FEN"]], row[idx["Moves"]]
            themes = row[idx["Themes"]]
            if pid in seen: continue
            if not validate(fen, moves, themes): continue
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
