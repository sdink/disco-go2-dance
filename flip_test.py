"""Go2 Pro flip test (firmware 1.1.15, robot Wi-Fi hotspot).

Usage:
    .venv/bin/python flip_test.py check        # connect only, robot does not move
    .venv/bin/python flip_test.py hello        # safe test: robot waves
    .venv/bin/python flip_test.py left         # side flip
    .venv/bin/python flip_test.py back         # back flip
    .venv/bin/python flip_test.py front        # front flip

Uses the robot's AES key from aes_key.txt if present (see README.md).
"""
import asyncio
import json
import logging
import os
import sys

from unitree_webrtc_connect.constants import RTC_TOPIC, SPORT_CMD_MCF
from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection, WebRTCConnectionMethod

logging.basicConfig(level=logging.FATAL)

HERE = os.path.dirname(os.path.abspath(__file__))

MOVES = {
    "hello": ("Hello", None),
    "left": ("LeftFlip", {"data": True}),
    "back": ("BackFlip", {"data": True}),
    "front": ("FrontFlip", {"data": True}),
}


def load_key():
    key = os.environ.get("UNITREE_AES_128_KEY")
    if not key:
        path = os.path.join(HERE, "aes_key.txt")
        if os.path.exists(path):
            key = open(path).read().strip()
    if not key:
        print("No AES key found - connecting without one (fine on firmware below 1.1.15).")
        return None
    if len(key) != 32:
        sys.exit("aes_key.txt should hold exactly 32 characters (see README.md).")
    return key


def read_setting(env, filename):
    value = os.environ.get(env)
    path = os.path.join(HERE, filename)
    if not value and os.path.exists(path):
        value = open(path).read().strip()
    return value


def make_connection(key):
    """Use GO2_IP / robot_ip.txt if set; else the robot hotspot (192.168.12.x); else search by serial number."""
    ip = read_setting("GO2_IP", "robot_ip.txt")
    if ip:
        print(f"Connecting to robot at {ip} (same network)...")
        return UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip=ip, aes_128_key=key)
    if os.popen("ipconfig getifaddr en0").read().startswith("192.168.12."):
        print("Connecting through the robot's hotspot...")
        return UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalAP, aes_128_key=key)
    sn = read_setting("GO2_SN", "robot_sn.txt")
    if not sn:
        sys.exit("Robot not found. Put its IP address in robot_ip.txt (see README.md).")
    print(f"Searching this network for robot {sn}...")
    return UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalSTA, serialNumber=sn, aes_128_key=key)


async def sport(conn, name, parameter=None):
    options = {"api_id": SPORT_CMD_MCF[name]}
    if parameter is not None:
        options["parameter"] = parameter
    resp = await conn.datachannel.pub_sub.publish_request_new(RTC_TOPIC["SPORT_MOD"], options)
    code = resp["data"]["header"]["status"]["code"]
    print(f"  {name}: {'ok' if code == 0 else f'robot replied code {code}'}")
    return code


async def main(action):
    conn = make_connection(load_key())
    await conn.connect()

    resp = await conn.datachannel.pub_sub.publish_request_new(
        RTC_TOPIC["MOTION_SWITCHER"], {"api_id": 1001}
    )
    try:
        mode = json.loads(resp["data"]["data"]).get("name")
    except Exception:
        mode = "unknown"
    print(f"Connected. Robot motion mode: {mode}")

    if action == "check":
        await conn.disconnect()
        return

    name, parameter = MOVES[action]
    if action != "hello":
        print("\n*** FLIP: clear at least 3 m in every direction, flat non-slip floor, nobody close. ***")
        if input(f"Type FLIP to do a {name}: ").strip().upper() != "FLIP":
            print("Cancelled.")
            await conn.disconnect()
            return

    await sport(conn, "BalanceStand")
    await asyncio.sleep(2)
    for n in (3, 2, 1):
        print(f"  {n}...")
        await asyncio.sleep(1)
    await sport(conn, name, parameter)
    await asyncio.sleep(6)  # let it land and settle
    await sport(conn, "BalanceStand")
    await asyncio.sleep(1)
    await conn.disconnect()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("check", *MOVES):
        sys.exit(__doc__)
    try:
        asyncio.run(main(sys.argv[1]))
    except KeyboardInterrupt:
        print("\nStopped.")
