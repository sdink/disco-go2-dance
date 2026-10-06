"""Estimate a song's tempo (BPM) and when its first beat lands.

    .venv/bin/python find_tempo.py song.mp3

Copy the numbers into BPM and FIRST_BEAT in make_project.py. Needs ffmpeg.
"""
import subprocess
import sys

import numpy as np

SR, HOP, N = 11025, 256, 1024


def onset_envelope(path):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(x, N)[::HOP] * np.hanning(N)
    spec = np.log1p(10 * np.abs(np.fft.rfft(frames, axis=1)))
    flux = np.concatenate([[0], np.maximum(0, np.diff(spec, axis=0)).sum(1)])
    return np.maximum(flux - np.convolve(flux, np.ones(16) / 16, "same"), 0)


def main(path):
    o = onset_envelope(path)
    fps = SR / HOP
    seg = o[: int(fps * 90)]
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    bpms = np.arange(60, 180, 0.5)
    scores = [sum(np.interp(fps * 60 / b * k, np.arange(len(ac)), ac) for k in (1, 2, 4)) for b in bpms]
    bpm = float(bpms[int(np.argmax(scores))])
    period = fps * 60 / bpm
    phase = max(range(int(period)),
                key=lambda p: o[np.round(np.arange(p, len(o) - 1, period)).astype(int)].sum())
    print(f"BPM = {bpm:g}")
    print(f"FIRST_BEAT = {phase / fps:.2f}")
    print("(If the dance feels twice as fast or slow as the music, halve or double BPM.)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
