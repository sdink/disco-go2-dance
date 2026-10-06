"""Play the dance straight from the terminal (no Scratch/browser needed).

    .venv/bin/python play_dance.py --no-flips   # rehearsal
    .venv/bin/python play_dance.py              # full dance with the flip

Uses the same DANCE list as make_project.py. Ctrl+C = stop (robot levels and balances).
Stop bridge.py first: the robot accepts one connection at a time.
"""
import argparse
import asyncio
import os
import subprocess
import time

from bridge import Robot
from flip_test import HERE
from make_project import BPM, DANCE, FIRST_BEAT

SONG = os.path.join(HERE, "song_short.mp3")


async def run(robot):
    beat_secs = 60 / BPM
    music = subprocess.Popen(["afplay", SONG])
    start = time.monotonic()
    try:
        for beat, kind, arg in DANCE:
            delay = start + FIRST_BEAT + (beat - 1) * beat_secs - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            if kind == "say":
                print(f"[beat {beat}] {arg}")
            elif kind == "tilt":
                asyncio.create_task(robot.tilt(*arg))
            elif kind == "level":
                asyncio.create_task(robot.tilt(0, 0, 0))
            elif kind == "trick":
                asyncio.create_task(robot.trick(arg))
            elif kind == "flip":
                asyncio.create_task(robot.flip(arg))
            elif kind == "walk":
                x, y, z, beats = arg
                asyncio.create_task(robot.move(x, y, z, beats * beat_secs))
        await asyncio.sleep(4 * beat_secs)
    finally:
        music.terminate()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-flips", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    robot = Robot(args.dry_run, args.no_flips)
    await robot.connect()
    print("\nStarting in 3 seconds. Ctrl+C = STOP.")
    await asyncio.sleep(3)
    try:
        await run(robot)
        print("Done!")
    finally:
        if robot.conn:
            await robot.stop()
            await asyncio.sleep(0.5)
            await robot.conn.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
