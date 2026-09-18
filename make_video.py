# -*- coding: utf-8 -*-
"""Generate music (copyright-free, randomized per track), long video, shorts & thumbnails.
Video style (approved): board fills the whole left side, texts on the right.
Long video: 5 puzzles x 2 minutes = 10 minutes. Shorts: 9:16, 2 per video.
The solution is NEVER shown."""
import os, math, wave, struct, json, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board_renderer as br

def get_ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

# ---------------- music: rich, layered, always different --------------------
# Chord progressions (MIDI) chosen for a calm, warm, non-monotonous feel.
PROGRESSIONS = [
    [[57,60,64,69],[53,57,60,65],[48,52,55,60],[55,59,62,67]],   # Am F C G
    [[62,65,69,72],[57,60,64,67],[53,57,60,65],[55,59,62,66]],   # Dm-ish
    [[52,55,59,62],[57,60,64,67],[50,53,57,60],[48,52,55,59]],
    [[60,64,67,71],[65,69,72,76],[62,65,69,72],[67,71,74,77]],   # C bright
    [[45,52,57,60],[41,48,53,57],[43,50,55,59],[48,55,60,64]],   # low warm
    [[58,62,65,70],[51,55,58,63],[56,60,63,68],[53,57,60,65]],
]
ARPEGGIO_STEPS = [0, 1, 2, 3, 2, 1]   # gentle up-down arpeggio pattern

def _f(n): return 440.0 * 2**((n - 69) / 12.0)

def make_music(path, seconds=600, sr=44100, rng=None):
    """One continuous calm piece for the WHOLE video with 4 layers:
       1. warm bass (root notes, soft)      2. slow arpeggio (harp-like)
       3. singing pad with vibrato          4. sparse piano melody (random walk)
    Each video gets its own key, progression, tempo and melody."""
    rng = rng or random.Random()
    key = rng.choice([-7,-5,-3,-2,0,2,3,5,7])
    prog = [[n+key for n in ch] for ch in rng.choice(PROGRESSIONS)]
    beat = rng.uniform(0.55, 0.75)                # calm tempo
    steps_per_chord = 8
    chord_sec = steps_per_chord*beat
    total = int(seconds*sr)
    samples = [0.0]*total
    n_chords = int(math.ceil(seconds/chord_sec))

    # 1) warm bass: root of each chord, one octave down, slow swell
    for ci in range(n_chords):
        t0 = int(ci*chord_sec*sr)
        root = prog[ci % len(prog)][0] - 24
        fr = _f(root)
        seg = min(int(chord_sec*sr), total-t0)
        for j in range(seg):
            t = j/sr
            env = min(1, t/1.5)*min(1, (seg/sr - t)/1.5)
            samples[t0+j] += 0.16*env*(math.sin(2*math.pi*fr*t)
                                       + 0.3*math.sin(2*math.pi*2*fr*t)*0.5)

    # 2) slow harp-like arpeggio over the chord tones
    step_i = 0
    for t0s in [i*beat for i in range(int(seconds/beat))]:
        ci = int(t0s/chord_sec)
        chord = prog[ci % len(prog)]
        note = chord[ARPEGGIO_STEPS[step_i % len(ARPEGGIO_STEPS)]] + 12*0
        step_i += 1
        start = int(t0s*sr)
        dur = int(min(1.4, rng.uniform(0.9, 1.4))*sr)
        fr = _f(note)
        for j in range(min(dur, total-start)):
            t = j/sr
            env = math.exp(-2.2*t)*min(1, t/0.01)
            samples[start+j] += 0.09*env*(math.sin(2*math.pi*fr*t)
                                         + 0.35*math.sin(2*math.pi*2.02*fr*t)*math.exp(-3*t))

    # 3) singing pad (violin-ish, top voice, vibrato, slow attack)
    vib_hz, vib_amt = rng.uniform(4.3, 5.6), 0.0045
    for ci in range(n_chords):
        chord = prog[ci % len(prog)]
        t0 = int(ci*chord_sec*sr)
        seg = min(int(chord_sec*sr), total-t0)
        # alternate between 3rd / top voice to avoid repetition
        note = chord[(ci + (1 if ci % 2 else 0)) % 4] - 12
        fr = _f(note)
        for j in range(seg):
            t = j/sr
            env = min(1, t/1.6)*min(1, (seg/sr - t)/2.0)
            vib = 1 + vib_amt*math.sin(2*math.pi*vib_hz*t)
            samples[t0+j] += 0.05*env*(math.sin(2*math.pi*fr*vib*t)
                                      + 0.25*math.sin(2*math.pi*2.001*fr*t))

    # 4) sparse piano melody: random walk near chord tones, ~ every 2 beats
    last_note = prog[0][3] + 12
    for k in range(int(seconds/(2*beat))):
        ci = int(k*2*beat/chord_sec)
        chord = prog[ci % len(prog)]
        step = rng.choice([-2, -1, -1, 0, 1, 1, 2])
        last_note = max(chord[0]+12, min(chord[3]+24, last_note + step))
        start = int(k*2*beat*sr)
        dur = int(rng.uniform(1.4, 2.2)*sr)
        fr = _f(last_note)
        for j in range(min(dur, total-start)):
            t = j/sr
            env = math.exp(-1.5*t)*min(1, t/0.008)
            samples[start+j] += 0.11*env*(math.sin(2*math.pi*fr*t)
                + 0.5*math.sin(2*math.pi*2*fr*t)*math.exp(-2.5*t)
                + 0.22*math.sin(2*math.pi*3*fr*t)*math.exp(-5*t))

    # gentle master fade-out at the very end
    fade = int(3*sr)
    for j in range(fade):
        samples[total-fade+j] *= j/fade

    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s))*32000)) for s in samples))

# ---------------- frames ----------------------------------------------------------
def board_frame(pz, puzzle_num, out_dir, tag, w, h, vertical=False):
    """Render one still frame in the approved layout (no solution shown)."""
    q = os.path.join(out_dir, f"{tag}_p{puzzle_num}.png")
    img = (br.render_9x16(pz["fen"], puzzle_num, W=w, H=h, rating=pz.get("rating")) if vertical
           else br.render_16x9(pz["fen"], puzzle_num, W=w, H=h, rating=pz.get("rating")))
    img.save(q)
    return q

# ---------------- videos ----------------------------------------------------------
def make_video(puzzles, out_dir, tag, seg=120, ff=None, start_num=1):
    """5 puzzles x seg seconds (default 2 min each = 10 min) -> 16:9 long video.
    Static frames, hard cuts, ONE continuous music piece."""
    os.makedirs(out_dir, exist_ok=True)
    W, H = 1920, 1080
    total = seg*len(puzzles)
    music = os.path.join(out_dir, f"{tag}_music.wav")
    make_music(music, seconds=total, rng=random.Random(tag))
    parts = []
    for i, pz in enumerate(puzzles, 1):
        frame = board_frame(pz, start_num + i - 1, out_dir, tag, W, H)
        out = os.path.join(out_dir, f"{tag}_seg{i}.mp4")
        subprocess.run([ff, "-y", "-loop","1","-t",str(seg),"-i",frame,
            "-f","lavfi","-t",str(seg),"-i","anullsrc=r=44100:cl=stereo",
            "-filter_complex", f"[0:v]scale={W}:{H},fps=25[v]",
            "-map","[v]","-map","1:a","-t",str(seg),"-c:v","libx264","-preset","veryfast",
            "-pix_fmt","yuv420p","-c:a","aac","-shortest", out],
            check=True, capture_output=True)
        os.remove(frame)
        parts.append(out)
    lst = os.path.join(out_dir, f"{tag}_list.txt")
    with open(lst, "w") as f:
        for p in parts: f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")
    final = os.path.join(out_dir, f"{tag}_video.mp4")
    subprocess.run([ff, "-y","-f","concat","-safe","0","-i",lst,"-i",music,
        "-map","0:v","-map","1:a",
        "-af","afade=t=out:st={:.1f}:d=3".format(total-3),
        "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
        "-c:a","aac","-shortest", final],
        check=True, capture_output=True)
    for p in parts: os.remove(p)
    os.remove(lst); os.remove(music)
    return final

def make_short(pz, puzzle_num, out_dir, tag, i, ff=None, seg=25):
    """One puzzle -> vertical Short (9:16), static frame, its own random music."""
    os.makedirs(out_dir, exist_ok=True)
    sw, sh = 1080, 1920
    frame = board_frame(pz, puzzle_num, out_dir, f"{tag}s", sw, sh, vertical=True)
    music = os.path.join(out_dir, f"{tag}_sm{i}.wav")
    make_music(music, seconds=seg, rng=random.Random(f"{tag}short{i}"))
    final = os.path.join(out_dir, f"{tag}_short{i}.mp4")
    subprocess.run([ff, "-y","-loop","1","-t",str(seg),"-i",frame,"-i",music,
        "-filter_complex", f"[0:v]scale={sw}:{sh},fps=25[v]",
        "-map","[v]","-map","1:a","-t",str(seg),"-c:v","libx264","-preset","veryfast",
        "-pix_fmt","yuv420p","-c:a","aac","-shortest", final],
        check=True, capture_output=True)
    os.remove(frame); os.remove(music)
    return final

def make_thumbnail(puzzles, out_dir, tag, puzzle_num):
    """Attractive chess thumbnail for the main video."""
    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(f"{tag}thumb")
    pz = rng.choice(puzzles)                 # a random puzzle of this batch as cover
    path = os.path.join(out_dir, f"{tag}_thumb.png")
    # هر بار استایل/رنگ/متن تامنیل متفاوت
    br.render_thumbnail(pz["fen"], puzzle_num, rating=pz.get("rating"), variant=rng.randrange(6)).save(path)
    return path

if __name__ == "__main__":
    ff = get_ffmpeg()
    demo = json.loads(open(os.path.join(HERE, "puzzles.jsonl"), encoding="utf-8").readline())
    demo = [dict(demo)] * 2
    v = make_video(demo, os.path.join(HERE, "out"), "test", seg=10, ff=ff)
    s = make_short(demo[0], 1, os.path.join(HERE, "out"), "test", 1, ff=ff, seg=10)
    t = make_thumbnail(demo, os.path.join(HERE, "out"), "test", 1)
    print("OK:", v, "|", s, "|", t)
