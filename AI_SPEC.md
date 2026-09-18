# AI_SPEC — ChessPuzzleBot Complete Reproduction Spec

> **Purpose of this file:** If you hand this repository to ANY AI assistant, it must be
> able to understand, run, and reproduce this bot EXACTLY as it is — with zero
> additional context. Everything is specified below. All UI text in videos is ENGLISH.

## 1. Goal

A fully automated YouTube chess-puzzle channel bot that:
1. Picks validated Lichess puzzles (never re-uploads the same puzzle twice).
2. Renders videos in ONE approved visual style (see §3 — do not deviate).
3. Writes its own title, description, caption, and hashtags (see §6).
4. Uploads on a PERMANENT weekly ramping schedule (see §2).
5. For every long video also uploads 2 Shorts (from the same puzzles) that are
   LINKED to the long video, plus an attractive chess thumbnail.

## 2. Schedule (permanent, config-driven)

Ramping quota from `config.json -> weekly_videos_per_day`, counted from `launch_date`:

| Channel week | Videos per day | Upload slots (evenly spread 08:00–22:00) |
|---|---|---|
| Week 1 | 2 | 08:00, 22:00 |
| Week 2 | 3 | 08:00, 15:00, 22:00 |
| Week 3 | 5 | 08:00, 11:30, 15:00, 18:30, 22:00 |
| Week 4+ (FOREVER) | 8 | every 2h from 08:00 to 22:00 |

- One "batch" = 1 long video + 2 linked Shorts + 1 thumbnail.
- Long video = 5 puzzles × 2 minutes each = **10 minutes total**, one continuous
  music piece, hard cuts between puzzles (no transitions).
- Each Short = 1 puzzle (25 s), its own music, vertical 9:16, description contains
  the link to the full video (`https://youtu.be/<videoId>`).
- Puzzle numbers are GLOBAL and forever increasing: video 1 = Puzzle #1–#5,
  video 2 = #6–#10, ... (stored in `state.json -> next`).

## 3. Visual style (APPROVED — reproduce exactly)

### 3.1 Pieces & colors
- Pieces: official lichess **cburnett** set as transparent PNGs in `assets/pieces/`
  (`wK.png wQ.png wR.png wB.png wN.png wP.png` + black equivalents, 330×330).
  Source: Wikimedia Commons "Chess_xlt45.svg / Chess_xdt45.svg" rendered at 256+ px.
- Board colors: light `#f0d9b5` (240,217,181), dark `#b58863` (181,136,99).
- Background: near-black `(22,21,18)`.
- Text colors: gold `(240,201,135)` for puzzle number, white `(236,234,217)` for
  turn text, muted green `(157,168,143)` for the comment prompt, grey `(185,182,165)`
  for rating.
- Small coordinates (a–h, 1–8) drawn inside the corner squares, lichess-style.

### 3.2 Long video frame (16:9, 1920×1080)
- The board fills the ENTIRE LEFT side, edge-to-edge: 8 squares of 135 px,
  starting at pixel (0,0). Board is 1080×1080. **Nothing of the board may leave
  the frame.**
- Right side is the dark background. Texts centered at x = (1920+1080)/2 = 1500:
  - `Puzzle #<n>` — bold ~92 px, gold, y ≈ 16% of height
  - `Rating: <rating>` — ~39 px grey (below the header)
  - `White to move` / `Black to move` — bold ~56 px white. **CRITICAL RULE: this is
    the SOLVER's side, i.e. the OPPOSITE of the FEN side-to-move.** In the Lichess
    DB the FEN side plays moves[0] = the losing/setup move; the winning solution
    is played by the other side. (FEN '... b' + solution starting after a black
    move => print `White to move`.)
  - `Comment the answer!` — ~48 px green (a bit further down)
- The SOLUTION IS NEVER SHOWN. No arrows, no highlights, no reveal.

### 3.3 Short frame (9:16, 1080×1920)
- Full-width board (8×135 px) placed at y ≈ 30% of height.
- Texts stacked ABOVE the board (Puzzle #n → Rating → turn text) and
  `Comment the answer!` BELOW the board.

### 3.4 Thumbnail (1280×720)
- Board on the left (edge-to-edge), thin golden gradient strip, right side text:
  `PUZZLE #<n>` (big gold), `CAN YOU SOLVE IT?` (white, 2 lines),
  `RATING <r>` (green). High contrast, readable at small sizes.

### 3.5 Fonts
- Windows: `segoeuib.ttf` / `segoeui.ttf` (fallback `arialbd.ttf`).
- Linux (GitHub runner): DejaVuSans-Bold / DejaVuSans.

## 4. Music (4 layers, copyright-free, generated in code)

One continuous piece per long video (10 min); Shorts get their own 25 s piece.
Layers (see `make_video.py -> make_music`):
1. **Warm bass** — chord roots two octaves down, slow swell envelope.
2. **Harp-like arpeggio** — up-down pattern `[0,1,2,3,2,1]` over chord tones,
   plucked exponential decay.
3. **Violin pad** — sustained top/3rd voice with 4.3–5.6 Hz vibrato, slow attack.
4. **Piano melody** — random-walk notes near chord tones every 2 beats,
   decaying harmonics (1st, 2nd, 3rd).
- 6 chord progressions (Am F C G family and friends), random key shift per track
  (-7…+7 semitones), tempo 0.55–0.75 s/beat. 3 s fade-out at the end. Mono 44.1 kHz.
- Never monotone: every track has different key, tempo, melody.

## 5. Pipeline (exact)

```
puzzles.jsonl (100k validated Lichess puzzles, rating 1400–2500, python-chess checked)
   └─ bot.py picks the next N unused puzzles (skips ids in used_puzzles.json
      + ids found in the channel's own past video descriptions)
   └─ make_video.make_video()  -> renders 5 frames (one per puzzle), 120 s each,
      ffmpeg loop → segments → concat, muxes the continuous music  → 16:9 MP4
   └─ make_video.make_thumbnail() -> attractive PNG cover
   └─ upload_youtube.upload()  -> long video (bot-written title/desc/tags)
      upload_youtube.set_thumbnail()
   └─ make_video.make_short() ×2 -> 9:16 MP4s from 2 random puzzles of the batch,
      descriptions contain "Full video with 5 puzzles: https://youtu.be/<id>"
```

## 6. Bot-written copy (templates in bot.py — TITLES / DESC_OPENERS / CAPTIONS / HASHTAG_SETS)

- Title example: `5 Chess Puzzles (1400-2500) 🧠 Can You Solve Them All?`
  (rotates among 4 templates, includes puzzle-number range and rating range)
- Description: opener + `Puzzles #N0–#N1 | Ratings r0–r1` + themes + a line with
  `Puzzles: <lichess ids>` (used later as the anti-duplicate memory) + CTA lines
  (pause & think, comment the answer, subscribe).
- Short description: caption + **link to the full video** + rating/themes + hashtags.
- Hashtags rotate among 3 sets (#chess #chesspuzzle #tactics …).

## 7. Files

| File | Role |
|---|---|
| `bot.py` | Orchestrator: schedule, quota, copywriting, batches, state. Modes: `--once` (immediate), `--cron` (slot-aware, for runners), default (local scheduler loop). |
| `make_video.py` | Frames→MP4 pipeline, music generator, shorts, thumbnail. |
| `board_renderer.py` | The exact approved layouts (16:9, 9:16, thumbnail). |
| `upload_youtube.py` | OAuth upload + thumbnail + channel-history puzzle-id sync. |
| `download_puzzles.py` | Builds `puzzles.jsonl` from the official Lichess DB (`--target N` for small pools). |
| `config.json` | Schedule ramp, timings, puzzle count, rating range. |
| `state.json` | `next` (global puzzle counter), `last_run_date`, `uploaded_today`. |
| `used_puzzles.json` | Local anti-duplicate memory. |
| `assets/pieces/` | cburnett PNGs. `samples/` = approved sample outputs. |
| `.github/workflows/daily.yml` | Runner: every 2 h → `bot.py --cron`; state kept via artifacts. |

## 8. YouTube credentials (no passwords stored)

- OAuth Desktop-app flow (`client_secrets.json`), token cached in `token.pickle`.
- For GitHub Actions: secrets `YT_CLIENT_SECRETS` (raw JSON) and `YT_TOKEN`
  (base64 of token.pickle; create with `certutil -encode token.pickle token.b64`).

## 9. Non-negotiables

1. Never show the puzzle solution in the video — only `Comment the answer!`.
1b. The turn text always shows the SOLVER (winner) = opposite of the FEN side to move.
1c. Only DECISIVE puzzles are used: mate (mateIn1–5) or clear winning advantage
    (advantage/winning/crushing themes) — a puzzle must end in a win or domination.
2. Never re-upload a puzzle (local set + YouTube description-history sync).
3. Keep the approved layout (board fills the left side edge-to-edge; texts right).
4. Keep the ramping quota table of §2 permanent, via config — do not hardcode.
5. All on-screen text in English.
