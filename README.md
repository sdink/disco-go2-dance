# Disco Go2 Dance

Choreograph a **Unitree Go2 Pro** (no EDU kit needed) to music — from **Scratch** (TurboWarp)
or straight from the terminal. Includes body tilts, sways, turns, built-in tricks
(Hello, Stretch, Heart…) and **flips**, all timed to the beat of a song.

> Unofficial. This talks to the robot over Wi-Fi the same way the Unitree Go app does, using the
> community library [unitree_webrtc_connect](https://github.com/legion1581/unitree_webrtc_connect).
> Flips and jumps are dangerous: clear ~3 m around the robot, use a flat non-slip floor,
> keep people back and keep the remote in hand. Use at your own risk.

Tested on a Go2 Pro, firmware 1.1.15, macOS, Python 3.14.

## Files
| File | What it does |
|---|---|
| `play_dance.py` | Plays the song and runs the dance from the terminal. Simplest way to perform. |
| `make_project.py` | The choreography (`DANCE` list). Builds `dance.sb3`, a Scratch project with the song + dance blocks. |
| `bridge.py` | Helper that stays connected to the robot and takes commands from Scratch. |
| `go2.js` | "Go2 Dance" custom blocks for TurboWarp (beat clock, tricks, flip, tilt, walk, STOP). |
| `flip_test.py` | Single-move tests: `check`, `hello`, `left`, `back`, `front`. |
| `find_tempo.py` | Measures a song's BPM and first beat. |

## Setup (macOS)
```bash
brew install portaudio ffmpeg
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Connect to the robot
1. In the Unitree Go app, connect the robot to the same Wi-Fi as your computer
   (or a phone hotspot both can join). Note the robot's IP address.
2. Save it: `echo 192.168.x.x > robot_ip.txt`
3. **Close the Unitree Go app** — the robot accepts one controller at a time.
4. Test: `.venv/bin/python flip_test.py check` (no movement), then `flip_test.py hello`.

Alternatives: join the robot's own hotspot (detected automatically), or put the serial number in
`robot_sn.txt` to search the network. Firmware ≥ 1.1.15 *may* need a per-robot key: run
`.venv/bin/unitree-fetch-aes-key --email YOU --device-type Go2` and save the 32-character key in
`aes_key.txt`. (Ours came back empty and connected fine without one.)

### Add your song
Put your music file at `song.mp3` (it is not included in this repo), then:
```bash
.venv/bin/python find_tempo.py song.mp3     # copy BPM and FIRST_BEAT into make_project.py
.venv/bin/python make_project.py            # trims the song, builds dance.sb3
```

## Perform
**From the terminal** (recommended):
```bash
.venv/bin/python play_dance.py --no-flips   # rehearsal
.venv/bin/python play_dance.py              # full dance, with the flip
```
Ctrl+C = stop (robot levels and balances).

**From Scratch:**
1. `.venv/bin/python bridge.py --no-flips` (or without `--no-flips`; `--dry-run` = no robot) and leave it running.
2. In Chrome open https://turbowarp.org/editor → File → Load from your computer → `dance.sb3`.
   Allow the custom extension (sandboxed is fine) and, if asked, allow **local network access**
   (or set it under the site settings).
3. Green flag to start; **space bar = emergency stop**.

## The dance
At 84 bpm; beats count from 1, four per bar.

| Beats | Move |
|---|---|
| 1–8 | Wake up: look left, look right, nod |
| 9–16 | Hip sway on every beat |
| 17 | Hello wave |
| 25–32 | Groove: sway with head down |
| 33–40 | Turn left, turn back |
| 41 | Stretch |
| 49–52 | Small sway, then still |
| 53 | **Side flip** |
| 61 | Finger heart |
| 65–67 | Bow |

Edit the `DANCE` list in `make_project.py` to change it — `play_dance.py` and `dance.sb3` both use it.

## What the Go2 Pro can do without EDU
Whole-body moves only: tilt (lean / nod / twist, capped at 30° here), walk, sidestep and turn
(speed-capped), plus the built-in tricks and flips. Individual legs can't be posed. On firmware
1.1.15 the side flip is a **left** flip (there is no right flip); back and front flips also work.
The bridge stands the robot still and level before a flip, and ignores other moves for 4 s after.

## License
MIT — see `LICENSE`.
