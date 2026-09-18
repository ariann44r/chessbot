# -*- coding: utf-8 -*-
"""Main bot: builds & uploads videos + linked Shorts on a schedule.

Schedule (config.json, defaults):
  - Week 1: 2 videos per day.
  - Each video = 5 puzzles x 2 minutes = 10 minutes total.
  - Each video gets 2 Shorts made from the same puzzles, linked to the video.
  - Each video gets an attractive chess thumbnail.
  - The bot writes its own title, description, caption and hashtags.
  - Puzzle numbers increase automatically (Puzzle #N grows with every video).
"""
import json, os, random, socket, subprocess, sys, time, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_video as mv

CFG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
STATE_F = os.path.join(HERE, "state.json")
PUZZLES_F = os.path.join(HERE, "puzzles.jsonl")

PUZZLES_PER_VIDEO = CFG.get("puzzles_per_video", 5)
SECONDS_PER_PUZZLE = CFG.get("seconds_per_puzzle", 120)   # 2 minutes
SHORTS_PER_VIDEO = CFG.get("shorts_per_video", 2)
SHORT_SECONDS = CFG.get("short_seconds", 25)
LAUNCH_DATE = dt.date.fromisoformat(CFG.get("launch_date", dt.date.today().isoformat()))
WEEKLY_QUOTA = CFG.get("weekly_videos_per_day", {"1": 2, "2": 3, "3": 5, "4": 8, "default": 8})

def videos_per_day():
    """Ramping schedule (permanent):
       week 1 -> 2 videos/day, week 2 -> 3, week 3 -> 5, week 4+ -> 8 forever."""
    week = max(1, (dt.date.today() - LAUNCH_DATE).days // 7 + 1)   # before launch -> week 1
    return int(WEEKLY_QUOTA.get(str(week), WEEKLY_QUOTA.get("default", 8)))

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

def next_puzzles(state, n=PUZZLES_PER_VIDEO):
    """Pick the next UNUSED puzzles (skips any already uploaded)."""
    used = load_used()
    picked = 0
    with open(PUZZLES_F, encoding="utf-8") as f:
        for line in f:
            if picked >= n: break
            pz = json.loads(line)
            if pz["id"] in used: continue
            picked += 1
            yield pz

def schedule_times(n=None):
    """N upload slots evenly spread between first_upload_time and last_upload_time.
    N changes automatically with the weekly ramping schedule."""
    n = n or videos_per_day()
    first = CFG.get("first_upload_time", "08:00")
    last = CFG.get("last_upload_time", "22:00")
    t0 = dt.datetime.strptime(first, "%H:%M")
    t1 = dt.datetime.strptime(last, "%H:%M")
    if n == 1: return [first]
    return [ (t0 + (t1 - t0) * i / (n - 1)).strftime("%H:%M") for i in range(n) ]

# ------------------------- auto copywriting (bot writes its own text) --------------------------
TITLES = [
    "5 Chess Puzzles ({r0}-{r1}) 🧠 Can You Solve Them All?",
    "Daily Chess Puzzles #{n0}-#{n1} ♟️ Level Up Your Tactics!",
    "Chess Training: 5 Puzzles ({r0}-{r1}) 🏆 How Fast Can You Solve?",
    "Improve at Chess: 5 Tactical Puzzles 🔥 Puzzle #{n0}-#{n1}",
]
DESC_OPENERS = [
    "Five hand-picked chess puzzles. The answer of each puzzle is in the pinned comment. "
    "Comment your solution before checking!",
    "Train your chess tactics with 5 fresh puzzles. Try to solve them before reading the "
    "comments — then comment your answer!",
    "Can you find the best move in all 5 positions? Pause the video, think, and comment "
    "your answers!",
]
CAPTIONS = [
    "Which puzzle was the hardest? 🤔 Comment your answers!",
    "How many did you solve? Rate this video 1-5 in the comments!",
    "Tag a friend who loves chess puzzles ♟️",
    "Drop your answers in the comments — best solution gets pinned!",
]
HASHTAG_SETS = [
    ["#chess", "#chesspuzzle", "#tactics", "#puzzle", "#chessbrah"],
    ["#chess", "#chesstactics", "#dailypuzzle", "#improve", "#strategy"],
    ["#chess", "#puzzleoftheday", "#chesslover", "#tactics", "#blitz"],
]

def gen_copy(puzzles, n0, n1):
    """The bot generates title, description, caption and hashtags itself."""
    rng = random.Random(f"copy{n0}")
    r0, r1 = puzzles[0]["rating"], puzzles[-1]["rating"]
    title = rng.choice(TITLES).format(r0=r0, r1=r1, n0=n0, n1=n1)
    themes = sorted({t for pz in puzzles for t in pz.get("themes", "").split(" ") if t})[:4]
    desc = (rng.choice(DESC_OPENERS)
            + f"\n\nPuzzles #{n0}-#{n1} | Ratings {r0}-{r1}"
            + (f"\nThemes: {', '.join(themes)}" if themes else "")
            + "\n\n⏱ 2 minutes per puzzle — pause and think!"
            + "\n💬 Comment the answer for every puzzle you solve!"
            + "\n🔔 Subscribe & Follow for daily chess puzzles ♟️"
            + f"\n\nPuzzles: {','.join(p['id'] for p in puzzles)}")
    return title, desc, rng.choice(CAPTIONS), rng.choice(HASHTAG_SETS)

# ------------------------- one batch = 1 video + 2 linked shorts -------------------------
def run_one_batch(batch_no):
    state = load_state()
    ff = mv.get_ffmpeg()
    # Stateless-safe numbering: on fresh runners state.json is empty, but the
    # used-puzzle memory is synced from YouTube — continue numbering from there.
    used_now = load_used()
    if state["next"] < len(used_now):
        state["next"] = len(used_now)
    puzzles = list(next_puzzles(state))
    if len(puzzles) < PUZZLES_PER_VIDEO:
        log("Puzzle pool exhausted! Run download_puzzles.py again."); return False
    n0 = state["next"] + 1                 # global puzzle numbering
    n1 = state["next"] + len(puzzles)
    tag = time.strftime("%Y%m%d_%H%M%S")
    seg = SECONDS_PER_PUZZLE
    total_min = seg*len(puzzles)/60
    log(f"Building video {batch_no}: {len(puzzles)} puzzles x {seg/60:.0f} min = {total_min:.0f} min ...")
    video = mv.make_video(puzzles, os.path.join(HERE, "out"), tag, seg=seg, ff=ff, start_num=n0)
    thumb = mv.make_thumbnail(puzzles, os.path.join(HERE, "out"), tag, n0)
    log("Video ready:", os.path.basename(video))
    log("Waiting for internet (if offline, retries every 60s)...")
    while not online(): time.sleep(60)
    log("Online. Uploading...")
    import upload_youtube as uy
    title, desc, caption, tags = gen_copy(puzzles, n0, n1)
    vid = uy.upload(video, title, desc, ["chess", "chess puzzle", "chess tactics", "puzzle", "daily puzzle"])
    uy.set_thumbnail(vid, thumb)
    link = f"https://youtu.be/{vid}"
    log("Upload DONE ✅ setting thumbnail...")
    log(f"Video link: {link}")
    log(f"Now making {SHORTS_PER_VIDEO} Shorts (from the same puzzles, linked to the video)...")
    rng = random.Random(tag)
    shorts_pz = rng.sample(puzzles, SHORTS_PER_VIDEO)
    for i, pz in enumerate(shorts_pz, 1):
        pnum = n0 + puzzles.index(pz)
        s = mv.make_short(pz, pnum, os.path.join(HERE, "out"), tag, i, ff=ff, seg=SHORT_SECONDS)
        while not online(): time.sleep(60)
        uy.upload(s,
                  f"Chess Puzzle #{pnum} (Rating {pz['rating']}) ♟️ #shorts",
                  f"{caption}\n"
                  f"Full video with 5 puzzles: {link}\n"
                  f"Rating {pz['rating']}. Themes: {pz.get('themes', '')}\n"
                  f"Comment the answer! 🤔\n#chess #shorts #puzzle #chesstactics",
                  ["chess", "chessshorts", "puzzle", "chesspuzzle", "shorts", "chesstactics"],
                  is_short=True)
        os.remove(s)
        log(f"  Short {i}/{SHORTS_PER_VIDEO} uploaded & linked to the video.")
    os.remove(video); os.remove(thumb)
    state["next"] += len(puzzles)
    state["uploaded_today"] += 1
    save_state(state)
    used = load_used() | {p["id"] for p in puzzles}
    save_used(used)   # local anti-duplicate memory
    log("BATCH DONE ✅ (1 video + %d linked Shorts)." % SHORTS_PER_VIDEO)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, "✅ آپلود کامل شد!\n\n1 ویدیو + 2 شورت لینک‌شده منتشر شد.",
            "ChessPuzzleBot", 0x40)
    except Exception:
        pass
    return True

def main():
    if "--cron" in sys.argv:      # GitHub runner mode: upload ONLY if a slot is due
        sync_with_youtube()
        state = load_state()
        now = dt.datetime.now()
        today = dt.date.today().isoformat()
        if state.get("last_run_date") != today:
            state["last_run_date"] = today; state["uploaded_today"] = 0; save_state(state)
        quota = videos_per_day()
        # Stateless-safe daily count: on GitHub runners state.json doesn't persist,
        # so count today's main-video uploads straight from YouTube, falling back to state.
        done = state["uploaded_today"]
        try:
            import upload_youtube as uy
            done = uy.count_today_uploads(uy.get_service())
        except Exception as e:
            log("YouTube count unavailable, falling back to state:", e)
        slots = sorted(schedule_times(quota))
        passed = len([s for s in slots if now >= dt.datetime.strptime(f"{today} {s}", "%Y-%m-%d %H:%M")])
        if done >= quota:
            log(f"Daily quota reached ({done}/{quota}). Nothing to do."); return
        if done >= passed:
            log("No upload slot due yet. Nothing to do."); return
        log(f"--cron: slot due ({done}/{quota} done, {passed} slots passed). Uploading...")
        try:
            run_one_batch(done + 1)
        except Exception as e:
            log("ERROR:", e)
        return
    if "--once" in sys.argv:   # one immediate batch (quota-limited), then exit
        if not online():
            log("No internet — cannot upload now."); return
        sync_with_youtube()
        state = load_state()
        today = dt.date.today().isoformat()
        if state.get("last_run_date") != today:
            state["last_run_date"] = today; state["uploaded_today"] = 0; save_state(state)
        quota = videos_per_day()
        # count today's uploads from YouTube so the ramp quota is honored even
        # if this mode is triggered many times a day (stateless-safe)
        done = state["uploaded_today"]
        try:
            import upload_youtube as uy
            done = uy.count_today_uploads(uy.get_service())
        except Exception as e:
            log("YouTube count unavailable, falling back to state:", e)
        if done >= quota:
            log(f"Daily quota reached ({done}/{quota}). Nothing to do."); return
        log(f"Once mode: uploading batch {done + 1}/{quota} (1 video + {SHORTS_PER_VIDEO} Shorts) ...")
        try:
            run_one_batch(done + 1)
        except Exception as e:
            log("ERROR:", e)
        return
    log("ChessPuzzleBot started. Press Ctrl+C or close this window to STOP.")
    sync_with_youtube()
    log("========================================================")
    log("READY ✅  everything is set up and connected to YouTube.")
    log(f"  - Week {((dt.date.today() - LAUNCH_DATE).days // 7 + 1)} quota: {videos_per_day()} videos/day at {', '.join(schedule_times())}")
    log(f"    (ramp: week1=2, week2=3, week3=5, week4+ = 8 per day, permanent)")
    log(f"  - Each video: {PUZZLES_PER_VIDEO} puzzles x {SECONDS_PER_PUZZLE/60:.0f} min = "
        f"{PUZZLES_PER_VIDEO*SECONDS_PER_PUZZLE/60:.0f} min + {SHORTS_PER_VIDEO} linked Shorts + thumbnail")
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
        quota = videos_per_day()          # weekly ramp: 2 -> 3 -> 5 -> 8 (permanent)
        slots = sorted(schedule_times(quota))
        if state["uploaded_today"] >= quota:
            log(f"Daily quota reached ({state['uploaded_today']}/{quota}). Sleeping until tomorrow 00:05...")
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
