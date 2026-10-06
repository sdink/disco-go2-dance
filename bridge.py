"""Go2 bridge: keeps one connection to the robot and takes commands from Scratch.

Run:
    .venv/bin/python bridge.py              # real robot
    .venv/bin/python bridge.py --no-flips   # real robot, flips skipped (rehearsal)
    .venv/bin/python bridge.py --dry-run    # no robot, just prints commands

Then in TurboWarp load the extension from http://localhost:8765/go2.js
(or open dance.sb3, which loads it for you).
"""
import argparse
import asyncio
import json
import logging
import math
import os
import random
import time

from aiohttp import web
from unitree_webrtc_connect.constants import RTC_TOPIC, SPORT_CMD_MCF

from flip_test import HERE, load_key, make_connection

logging.basicConfig(level=logging.FATAL)

PORT = 8765
TRICKS = {"Hello", "Stretch", "Heart", "Dance1", "Dance2", "Sit", "RiseSit",
          "Scrape", "Content", "FrontJump", "FrontPounce", "StandUp", "StandDown"}
FLIPS = {"left": "LeftFlip", "back": "BackFlip", "front": "FrontFlip"}
FLIP_SETTLE = 4.0  # seconds after a flip during which other moves are ignored

# Safety limits
MAX_TILT_DEG = 30
MAX_X, MAX_Y, MAX_TURN, MAX_SECS = 0.6, 0.4, 2.0, 5.0


def clamp(v, lim):
    return max(-lim, min(lim, v))


class Robot:
    def __init__(self, dry_run, no_flips):
        self.dry_run = dry_run
        self.no_flips = no_flips
        self.conn = None
        self.move_task = None
        self.busy_until = 0.0
        self.move_ended = 0.0

    async def connect(self):
        if self.dry_run:
            print("DRY RUN: not connecting to the robot.")
            return
        self.conn = make_connection(load_key())
        await self.conn.connect()
        print("Robot connected.")

    @property
    def connected(self):
        return self.dry_run or bool(self.conn and self.conn.isConnected)

    async def call(self, name, parameter=None):
        print(f"  -> {name} {parameter or ''}")
        if self.dry_run:
            return
        options = {"api_id": SPORT_CMD_MCF[name]}
        if parameter is not None:
            options["parameter"] = parameter
        try:
            resp = await asyncio.wait_for(
                self.conn.datachannel.pub_sub.publish_request_new(RTC_TOPIC["SPORT_MOD"], options), 3)
        except asyncio.TimeoutError:
            print(f"     no reply to {name} (connection lost?)")
            return
        code = resp.get("data", {}).get("header", {}).get("status", {}).get("code", -1)
        if code != 0:
            print(f"     robot replied code {code} to {name}")

    def call_no_reply(self, name, parameter):
        if self.dry_run:
            return
        self.conn.datachannel.pub_sub.publish_without_callback(RTC_TOPIC["SPORT_MOD"], {
            "header": {
                "identity": {"id": int(time.time() * 1000) % 2147483648 + random.randint(0, 1000),
                             "api_id": SPORT_CMD_MCF[name]},
                "policy": {"priority": 0, "noreply": True},
            },
            "parameter": json.dumps(parameter),
            "binary": [],
        })

    def cancel_move(self):
        if self.move_task and not self.move_task.done():
            self.move_task.cancel()

    async def _stream_move(self, x, y, z, secs):
        print(f"  -> Move x={x} y={y} turn={z} for {secs}s")
        end = time.monotonic() + secs
        try:
            while time.monotonic() < end:
                self.call_no_reply("Move", {"x": x, "y": y, "z": z})
                await asyncio.sleep(0.1)
        finally:
            self.call_no_reply("Move", {"x": 0, "y": 0, "z": 0})
            self.move_ended = time.monotonic()

    def busy(self):
        if time.monotonic() < self.busy_until:
            print("  (ignored: robot is landing a flip)")
            return True
        return False

    # ---- commands from Scratch ----
    async def trick(self, name):
        if name in TRICKS and not self.busy():
            # Tricks are refused while walking (code 401001), so stop and steady first.
            moving = self.move_task and not self.move_task.done()
            if moving or time.monotonic() - self.move_ended < 1.0:
                self.cancel_move()
                await asyncio.sleep(0.2)
                await self.call("BalanceStand")
                await asyncio.sleep(0.3)
            await self.call(name)

    async def tilt(self, roll, pitch, yaw):
        if self.busy():
            return
        r, p, y = (math.radians(clamp(v, MAX_TILT_DEG)) for v in (roll, pitch, yaw))
        await self.call("Euler", {"x": round(r, 3), "y": round(p, 3), "z": round(y, 3)})

    async def move(self, x, y, z, secs):
        if self.busy():
            return
        self.cancel_move()
        self.move_task = asyncio.create_task(self._stream_move(
            clamp(x, MAX_X), clamp(y, MAX_Y), clamp(z, MAX_TURN), min(max(secs, 0), MAX_SECS)))

    async def flip(self, direction):
        name = FLIPS.get(direction)
        if not name or self.busy():
            return
        if self.no_flips:
            print(f"  (skipped {name}: --no-flips)")
            return
        # Stand still and level before flipping.
        self.cancel_move()
        self.call_no_reply("Move", {"x": 0, "y": 0, "z": 0})
        await self.call("Euler", {"x": 0, "y": 0, "z": 0})
        await self.call("BalanceStand")
        await asyncio.sleep(0.5)
        self.busy_until = time.monotonic() + FLIP_SETTLE
        await self.call(name, {"data": True})

    async def stop(self):
        print("  STOP")
        self.busy_until = 0
        self.cancel_move()
        self.call_no_reply("Move", {"x": 0, "y": 0, "z": 0})
        await self.call("StopMove")
        await self.call("Euler", {"x": 0, "y": 0, "z": 0})
        await self.call("BalanceStand")


def num(q, key, default=0.0):
    try:
        return float(q.get(key, default))
    except ValueError:
        return default


def make_app(robot):
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Private-Network"] = "true"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        return resp

    async def options(request):
        return cors(web.Response())

    async def status(request):
        return cors(web.json_response({"connected": robot.connected}))

    async def cmd(request):
        q = request.query
        c = q.get("c")
        handlers = {
            "trick": lambda: robot.trick(q.get("name", "")),
            "tilt": lambda: robot.tilt(num(q, "roll"), num(q, "pitch"), num(q, "yaw")),
            "level": lambda: robot.tilt(0, 0, 0),
            "move": lambda: robot.move(num(q, "x"), num(q, "y"), num(q, "z"), num(q, "secs", 1)),
            "flip": lambda: robot.flip(q.get("dir", "")),
            "stop": robot.stop,
        }
        if c not in handlers:
            return cors(web.json_response({"ok": False, "error": f"unknown command {c}"}, status=400))
        if not robot.connected:
            return cors(web.json_response({"ok": False, "error": "robot not connected"}, status=503))
        # Fire and forget so Scratch's beat timing is never held up by the robot.
        asyncio.create_task(handlers[c]())
        return cors(web.json_response({"ok": True}))

    async def extension(request):
        return cors(web.FileResponse(os.path.join(HERE, "go2.js"),
                                     headers={"Content-Type": "application/javascript"}))

    async def project(request):
        return cors(web.FileResponse(os.path.join(HERE, "dance.sb3")))

    app = web.Application()
    app.router.add_route("OPTIONS", "/{tail:.*}", options)
    app.router.add_get("/dance.sb3", project)
    app.router.add_get("/status", status)
    app.router.add_get("/cmd", cmd)
    app.router.add_get("/go2.js", extension)
    return app


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="don't connect; print commands only")
    ap.add_argument("--no-flips", action="store_true", help="skip flips (rehearsal)")
    args = ap.parse_args()

    robot = Robot(args.dry_run, args.no_flips)
    await robot.connect()
    runner = web.AppRunner(make_app(robot))
    await runner.setup()
    await web.TCPSite(runner, "localhost", PORT).start()
    print(f"Bridge ready on http://localhost:{PORT}  (extension: http://localhost:{PORT}/go2.js)")
    print("Ctrl+C to quit. Keep the remote in hand.")
    try:
        await asyncio.Event().wait()
    finally:
        if robot.conn:
            await robot.stop()
            await robot.conn.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBridge stopped.")
