"""Builds dance.sb3: the song plus the Go2 dance as Scratch blocks.

    .venv/bin/python make_project.py

Edit DANCE below to change the choreography, then re-run.
"""
import hashlib
import json
import os
import subprocess
import zipfile

from flip_test import HERE

SONG_SRC = os.environ.get("GO2_SONG", os.path.join(HERE, "song.mp3"))  # your music file
SONG_SECS = 51          # trim the song for a short dance...
FADE_SECS = 3           # ...with a fade-out at the end
BPM = 84                # tempo of your song
FIRST_BEAT = 0.51       # seconds until the first beat of your song

# (beat, block, args). Beats count from 1; four beats per bar.
# tilt = (lean/roll, nod/pitch, twist/yaw) in degrees.
DANCE = [
    (1,  "say", "Waking up"),
    (1,  "tilt", (0, 0, 20)),       # look left
    (3,  "tilt", (0, 0, -20)),      # look right
    (5,  "tilt", (0, 15, 0)),       # nod
    (7,  "level", None),
    (9,  "say", "Sway"),
    *[(b, "tilt", (15 if b % 2 else -15, 0, 0)) for b in range(9, 17)],
    (16.5, "level", None),
    (17, "say", "Hello!"),
    (17, "trick", "Hello"),
    (23, "level", None),
    (25, "say", "Groove"),
    *[(b, "tilt", (12 if b % 2 else -12, 10, 0)) for b in range(25, 33)],
    (32.5, "level", None),
    (33, "say", "Look around"),
    (33, "walk", (0, 0, 1.0, 4)),   # turn left for 4 beats
    (37, "walk", (0, 0, -1.0, 3.5)),  # turn back (ends early so Stretch is accepted)
    (41, "say", "Stretch"),
    (41, "trick", "Stretch"),
    (49, "say", "Get ready..."),
    (49, "tilt", (8, 0, 0)),
    (50, "tilt", (-8, 0, 0)),
    (51, "level", None),
    (53, "say", "FLIP!"),
    (53, "flip", "left"),
    (61, "say", "Heart"),
    (61, "trick", "Heart"),
    (65, "say", "Bow"),
    (65, "tilt", (0, 20, 0)),
    (67, "level", None),
    (67, "say", "Thank you!"),
]

DOG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="160" height="110" viewBox="0 0 160 110">
<rect x="30" y="30" width="90" height="38" rx="16" fill="#3a3f47"/>
<rect x="108" y="18" width="40" height="30" rx="10" fill="#3a3f47"/>
<circle cx="136" cy="30" r="5" fill="#e0457b"/>
<rect x="38" y="62" width="12" height="40" rx="6" fill="#2a2e34"/>
<rect x="58" y="62" width="12" height="40" rx="6" fill="#2a2e34"/>
<rect x="88" y="62" width="12" height="40" rx="6" fill="#2a2e34"/>
<rect x="104" y="62" width="12" height="40" rx="6" fill="#2a2e34"/>
<text x="62" y="54" font-family="sans-serif" font-size="14" fill="#fff">Disco</text>
</svg>"""

STAGE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
<rect width="480" height="360" fill="#1b1530"/>
<circle cx="240" cy="40" r="26" fill="#f6d365"/>
<rect y="280" width="480" height="80" fill="#2c2350"/>
</svg>"""


class Blocks:
    def __init__(self):
        self.blocks = {}
        self.n = 0

    def new_id(self):
        self.n += 1
        return f"b{self.n}"

    def add(self, opcode, inputs=None, fields=None, parent=None, top=None, shadow=False, mutation=None):
        bid = self.new_id()
        b = {"opcode": opcode, "next": None, "parent": parent, "inputs": inputs or {},
             "fields": fields or {}, "shadow": shadow, "topLevel": top is not None}
        if top:
            b["x"], b["y"] = top
        if mutation:
            b["mutation"] = mutation
        self.blocks[bid] = b
        return bid

    def chain(self, hat_opcode, pos, steps, hat_fields=None):
        """steps: list of (opcode, inputs, fields, extra) where extra may add shadow children."""
        hat = self.add(hat_opcode, fields=hat_fields, top=pos)
        prev = hat
        for opcode, inputs, fields, *rest in steps:
            bid = self.add(opcode, inputs, fields, parent=prev,
                           mutation=rest[0] if rest else None)
            self.blocks[prev]["next"] = bid
            for v in (inputs or {}).values():  # re-parent shadow menu blocks
                if isinstance(v[1], str):
                    self.blocks[v[1]]["parent"] = bid
            prev = bid
        return hat


def num(v):
    return [1, [4, str(v)]]


def text(v):
    return [1, [10, str(v)]]


def dance_steps(blocks, sound_name):
    menu = blocks.add("sound_sounds_menu", fields={"SOUND_MENU": [sound_name, None]}, shadow=True)
    steps = [
        ("go2dance_level", {}, {}),
        ("sound_play", {"SOUND_MENU": [1, menu]}, {}),
        ("go2dance_startClock", {"BPM": num(BPM), "OFFSET": num(FIRST_BEAT)}, {}),
    ]
    last_beat = None
    for beat, kind, arg in DANCE:
        if beat != last_beat:
            steps.append(("go2dance_waitBeat", {"BEAT": num(beat)}, {}))
            last_beat = beat
        if kind == "say":
            steps.append(("looks_say", {"MESSAGE": text(arg)}, {}))
        elif kind == "tilt":
            r, p, y = arg
            steps.append(("go2dance_tilt", {"ROLL": num(r), "PITCH": num(p), "YAW": num(y)}, {}))
        elif kind == "level":
            steps.append(("go2dance_level", {}, {}))
        elif kind == "trick":
            steps.append(("go2dance_trick", {}, {"TRICK": [arg, None]}))
        elif kind == "flip":
            steps.append(("go2dance_flip", {}, {"DIR": [arg, None]}))
        elif kind == "walk":
            x, y, z, beats = arg
            steps.append(("go2dance_walk", {"X": num(x), "Y": num(y), "Z": num(z), "BEATS": num(beats)}, {}))
    steps.append(("go2dance_waitBeat", {"BEAT": num(last_beat + 4)}, {}))
    steps.append(("sound_stopallsounds", {}, {}))
    return steps


def build():
    # Trimmed, faded song.
    song = os.path.join(HERE, "song_short.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SONG_SRC, "-t", str(SONG_SECS),
                    "-af", f"afade=t=out:st={SONG_SECS - FADE_SECS}:d={FADE_SECS}",
                    "-ar", "44100", "-b:a", "192k", song], check=True)
    song_bytes = open(song, "rb").read()
    song_md5 = hashlib.md5(song_bytes).hexdigest()
    dog = DOG_SVG.encode()
    dog_md5 = hashlib.md5(dog).hexdigest()
    stage = STAGE_SVG.encode()
    stage_md5 = hashlib.md5(stage).hexdigest()

    sprite_blocks = Blocks()
    sprite_blocks.chain("event_whenflagclicked", (40, 40), dance_steps(sprite_blocks, "song"))
    sprite_blocks.chain("event_whenkeypressed", (520, 40), [
        ("go2dance_stop", {}, {}),
        ("sound_stopallsounds", {}, {}),
        ("control_stop", {}, {"STOP_OPTION": ["all", None]},
         {"tagName": "mutation", "children": [], "hasnext": "false"}),
    ], hat_fields={"KEY_OPTION": ["space", None]})

    project = {
        "targets": [
            {
                "isStage": True, "name": "Stage", "variables": {}, "lists": {}, "broadcasts": {},
                "blocks": {}, "comments": {}, "currentCostume": 0,
                "costumes": [{"name": "backdrop", "assetId": stage_md5, "md5ext": f"{stage_md5}.svg",
                              "dataFormat": "svg", "rotationCenterX": 240, "rotationCenterY": 180}],
                "sounds": [], "volume": 100, "layerOrder": 0, "tempo": BPM,
                "videoTransparency": 50, "videoState": "on", "textToSpeechLanguage": None,
            },
            {
                "isStage": False, "name": "Disco", "variables": {}, "lists": {}, "broadcasts": {},
                "blocks": sprite_blocks.blocks, "comments": {}, "currentCostume": 0,
                "costumes": [{"name": "Disco", "assetId": dog_md5, "md5ext": f"{dog_md5}.svg",
                              "dataFormat": "svg", "rotationCenterX": 80, "rotationCenterY": 55}],
                "sounds": [{"name": "song", "assetId": song_md5, "md5ext": f"{song_md5}.mp3",
                            "dataFormat": "mp3", "rate": 44100, "sampleCount": 44100 * SONG_SECS}],
                "volume": 100, "layerOrder": 1, "visible": True, "x": -40, "y": -40, "size": 120,
                "direction": 90, "draggable": False, "rotationStyle": "all around",
            },
        ],
        "monitors": [],
        "extensions": ["go2dance"],
        "extensionURLs": {"go2dance": "http://localhost:8765/go2.js"},
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "go2_dance/make_project.py"},
    }

    out = os.path.join(HERE, "dance.sb3")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(project))
        z.writestr(f"{song_md5}.mp3", song_bytes)
        z.writestr(f"{dog_md5}.svg", dog)
        z.writestr(f"{stage_md5}.svg", stage)
    print(f"Wrote {out}  ({len(DANCE)} moves, ~{FIRST_BEAT + (DANCE[-1][0] + 3) * 60 / BPM:.0f}s)")


if __name__ == "__main__":
    build()
