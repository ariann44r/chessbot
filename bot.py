# -*- coding: utf-8 -*-
"""Main bot: builds & uploads 5 videos/day (+5 shorts per video) until stopped.
Runs forever; checks internet before every upload; prints DONE when a batch finishes."""
import json, os, socket, subprocess, sys, time, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_video as mv

CFG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
STATE_F = os.path.join(HERE, "state.json")
PUZZLES_F = os.path.join(HERE, "puzzles.jsonl")

def log(*a): print(f"[{dt.datetime.now():%H:%M:%S}]", *a, flush=True)

def load_state():
    if os.path.exists(STATE_F):
        return json.load(open(STATE_F, encoding="utf-8"))
    return {"next": 0, "last_run_date": None, "uploaded_today": 0}

def save_state(s): json.dump(s, open(STATE_F, "w", encoding="utf-8"))

def online():
    for host in ("8.8.8.8", "1.1.1.1", "youtube.com"):
        try:
            socket.create_connection((host, 53 if host != "youtube.com" else 443), timeout=4)
            return True
        except OSError:
            continue
    return False

USED_F = os.path.join(HERE, "used_puzzles.json")

def load_used():
    if os.path.exists(USED_F):
        return set(json.load(open(USED_F, encoding="utf-8")))
    return set()

def save_used(used):
    json.dump(sorted(used), open(USED_F, "w", encoding="utf-8"))

def sync_with_youtube():
    """Mark puzzles already uploaded (read from YouTube history) as used.
    This is the memory that survives VPS wipes."""
    try:
        import upload_youtube as uy
        yt = uy.get_service()
        remote = uy.get_uploaded_puzzle_ids(yt)
        if remote:
            used = load_used() | remote
            save_used(used)
            log(f"Synced with YouTube: {len(remote)} puzzle ids marked used.")
    except Exception as e:
        log("YouTube history sync skipped:", e)

def next_puzzles(state, n=5):
    """Pick the next UNUSED puzzles (skips any already uploaded, locally tracked)."""
    used = load_used()
    picked = 0
    with open(PUZZLES_F, encoding="utf-8") as f:
        for line in f:
            if picked >= n: break
            pz = json.loads(line)
            if pz["id"] in used: continue
            picked += 1
            yield pz

def schedule_times():
    """Upload slots/day (local time), best-practice spread."""
    return CFG.get("upload_times", ["09:00", "12:00", "15:00", "18:00", "21:00"])

def videos_today():
    """Weekly ramp: week 1 -> 2/day, week 2 -> 4, week 3 -> 8, week 4+ -> 10."""
    ramp = CFG.get("ramp_per_week", [2, 4, 8, 10])
    start = dt.date.fromisoformat(CFG.get("start_date", dt.date.today().isoformat()))
    week = ((dt.date.today() - start).days // 7) + 1
    return ramp[min(max(week, 1), len(ramp)) - 1]

def n_puzzles():
    """Puzzles per video (8 x 15s = 2 minutes)."""
    return int(CFG.get("puzzles_per_video", 5))

def run_one_batch(batch_no):
    state = load_state()
    ff = mv.get_ffmpeg()
    N = n_puzzles()
    puzzles = list(next_puzzles(state, N))
    if len(puzzles) < N:
        log("Puzzle pool exhausted! Run download_puzzles.py again."); return False
    tag = time.strftime("%Y%m%d_%H%M%S")
    seg = int(CFG.get("seconds_per_puzzle", 120))
    log(f"Building video {batch_no} ({len(puzzles)} puzzles, {seg}s each)...")
    video = mv.make_video(puzzles, os.path.join(HERE, "out"), tag, seg=seg, ff=ff)
    log("Video ready:", os.path.basename(video))
    log("Waiting for internet (if offline, retries every 60s)...")
    while not online(): time.sleep(60)
    log("Online. Uploading...")
    import upload_youtube as uy
    r0 = puzzles[0]["rating"]; r4 = puzzles[-1]["rating"]
    title = f"{len(puzzles)} Chess Puzzles (Rating {r0}-{r4}) 🧠 Can You Solve Them All?"
    desc = (f"{len(puzzles)} hand-picked chess puzzles. The answer of each puzzle is in the "
            "pinned comment. Comment your solution before checking!\n"
            "Subscribe & Follow for daily puzzles ♟️\n\n#chess #puzzle #chesspuzzle")
    vid = uy.upload(video, title, desc + f"\nPuzzles: {','.join(p['id'] for p in puzzles)}",
                    ["chess", "chess puzzle", "chess tactics", "lichess", "puzzle"])
    log("Upload DONE ✅ — now making & uploading Shorts (1 per puzzle)...")
    for i, pz in enumerate(puzzles, 1):
        s = mv.make_short(pz, os.path.join(HERE, "out"), tag, i, ff=ff)
        while not online(): time.sleep(60)
        uy.upload(s, f"Chess Puzzle #{i} (Rating {pz['rating']}) ♟️ #shorts",
                  f"Answer in the comments. Rating {pz['rating']}.\n"
                  f"Themes: {pz.get('themes','')}\n"
                  f"▶️ Full puzzle video: https://youtu.be/{vid}\n#chess #shorts #puzzle",
                  ["chess", "chessshorts", "puzzle", "chesspuzzle", "shorts"],
                  is_short=True)
        os.remove(s)
        log(f"  Short {i}/{len(puzzles)} uploaded.")
    os.remove(video)
    state["next"] += len(puzzles)
    state["uploaded_today"] += 1
    save_state(state)
    used = load_used() | {p["id"] for p in puzzles}
    save_used(used)   # local anti-duplicate memory
    log(f"BATCH DONE ✅ (1 video + {len(puzzles)} shorts).")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, "✅ آپلود کامل شد!\n\n1 ویدیو + شورت‌ها منتشر شد.",
            "ChessPuzzleBot", 0x40)
    except Exception:
        pass
    return True

def main():
    if "--ci" in sys.argv:   # GitHub Actions: one batch if daily quota not reached
        if not online():
            log("No internet — skipping."); return
        sync_with_youtube()
        state = load_state()
        today = dt.date.today().isoformat()
        if state.get("last_run_date") != today:
            state["last_run_date"] = today; state["uploaded_today"] = 0; save_state(state)
        quota = videos_today()
        if state["uploaded_today"] >= quota:
            log(f"Daily quota reached ({state['uploaded_today']}/{quota}). Nothing to do."); return
        log(f"Weekly ramp: today's quota = {quota} videos.")
        try:
            run_one_batch(state["uploaded_today"] + 1)
        except Exception as e:
            log("ERROR:", e)
        return
    if "--once" in sys.argv:   # DAZAI: one immediate batch, then exit
        log("DAZAI mode: immediate upload of 1 video + 5 shorts")
        if not online():
            log("No internet — cannot upload now."); return
        sync_with_youtube()
        state = load_state()
        try:
            run_one_batch(state["uploaded_today"] + 1)
        except Exception as e:
            log("ERROR:", e)
        return
    log("ChessPuzzleBot started. Press Ctrl+C or close this window to STOP.")
    sync_with_youtube()
    log("========================================================")
    log("READY ✅  everything is set up and connected to YouTube.")
    log("  - Auto uploads run in THIS window at scheduled times.")
    log("  - For an immediate upload right now: run DAZAI.bat")
    log("  - Keep this window OPEN. Closing it = stopping the bot.")
    log("========================================================")
    if not os.path.exists(PUZZLES_F):
        log("puzzles.jsonl missing — run:  python download_puzzles.py"); return
    state = load_state()
    today = dt.date.today().isoformat()
    if state.get("last_run_date") != today:
        state["last_run_date"] = today; state["uploaded_today"] = 0; save_state(state)
    slots = sorted(schedule_times())
    while True:  # runs until stopped
        state = load_state()
        now = dt.datetime.now()
        today = dt.date.today().isoformat()
        if state.get("last_run_date") != today:
            state["last_run_date"] = today; state["uploaded_today"] = 0; save_state(state)
        if state["uploaded_today"] >= len(slots):
            log(f"Daily quota reached ({len(slots)}/day). Sleeping until tomorrow 00:05...")
            tomorrow = (dt.datetime.combine(dt.date.today() + dt.timedelta(days=1),
                                            dt.time(0, 5)) - now).total_seconds()
            time.sleep(max(60, tomorrow)); continue
        slot = slots[state["uploaded_today"]]
        target = dt.datetime.strptime(f"{dt.date.today()} {slot}", "%Y-%m-%d %H:%M")
        if now < target:
            wait = (target - now).total_seconds()
            log(f"Next upload at {slot} (waiting {wait/60:.0f} min). Checking internet...")
            if online(): log("Internet: connected ✅")
            else: log("Internet: offline — will retry before upload.")
            time.sleep(min(wait, 300)); continue
        try:
            run_one_batch(state["uploaded_today"] + 1)
        except Exception as e:
            log("ERROR:", e, "— retrying in 5 minutes..."); time.sleep(300)

if __name__ == "__main__":
    main()
