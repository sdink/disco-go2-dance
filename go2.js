// Go2 Dance — TurboWarp extension. Talks to bridge.py on http://localhost:8765.
(function (Scratch) {
  'use strict';

  const BRIDGE = 'http://localhost:8765';
  let bpm = 84;
  let firstBeat = 0.5; // seconds from clock start to beat 1
  let clockStart = null; // performance.now() when the clock started

  const send = (params) => {
    const q = new URLSearchParams(params).toString();
    fetch(`${BRIDGE}/cmd?${q}`).catch((e) => console.warn('Go2 bridge not reachable', e));
  };
  const beatSecs = () => 60 / Math.max(1, bpm);

  class Go2Dance {
    getInfo() {
      return {
        id: 'go2dance',
        name: 'Go2 Dance',
        color1: '#e0457b',
        color2: '#c23366',
        blocks: [
          { blockType: Scratch.BlockType.LABEL, text: 'Timing' },
          {
            opcode: 'startClock',
            blockType: Scratch.BlockType.COMMAND,
            text: 'start beat clock at [BPM] bpm, beat 1 at [OFFSET] sec',
            arguments: {
              BPM: { type: Scratch.ArgumentType.NUMBER, defaultValue: 84 },
              OFFSET: { type: Scratch.ArgumentType.NUMBER, defaultValue: 0.5 },
            },
          },
          {
            opcode: 'waitBeat',
            blockType: Scratch.BlockType.COMMAND,
            text: 'wait until beat [BEAT]',
            arguments: { BEAT: { type: Scratch.ArgumentType.NUMBER, defaultValue: 1 } },
          },
          { opcode: 'currentBeat', blockType: Scratch.BlockType.REPORTER, text: 'current beat' },
          { blockType: Scratch.BlockType.LABEL, text: 'Moves' },
          {
            opcode: 'trick',
            blockType: Scratch.BlockType.COMMAND,
            text: 'do trick [TRICK]',
            arguments: { TRICK: { type: Scratch.ArgumentType.STRING, menu: 'tricks', defaultValue: 'Hello' } },
          },
          {
            opcode: 'flip',
            blockType: Scratch.BlockType.COMMAND,
            text: 'flip [DIR]',
            arguments: { DIR: { type: Scratch.ArgumentType.STRING, menu: 'flips', defaultValue: 'left' } },
          },
          {
            opcode: 'tilt',
            blockType: Scratch.BlockType.COMMAND,
            text: 'tilt body: lean [ROLL]° nod [PITCH]° twist [YAW]°',
            arguments: {
              ROLL: { type: Scratch.ArgumentType.NUMBER, defaultValue: 15 },
              PITCH: { type: Scratch.ArgumentType.NUMBER, defaultValue: 0 },
              YAW: { type: Scratch.ArgumentType.NUMBER, defaultValue: 0 },
            },
          },
          { opcode: 'level', blockType: Scratch.BlockType.COMMAND, text: 'level body' },
          {
            opcode: 'walk',
            blockType: Scratch.BlockType.COMMAND,
            text: 'walk forward [X] sideways [Y] turn [Z] for [BEATS] beats',
            arguments: {
              X: { type: Scratch.ArgumentType.NUMBER, defaultValue: 0 },
              Y: { type: Scratch.ArgumentType.NUMBER, defaultValue: 0 },
              Z: { type: Scratch.ArgumentType.NUMBER, defaultValue: 1 },
              BEATS: { type: Scratch.ArgumentType.NUMBER, defaultValue: 4 },
            },
          },
          { blockType: Scratch.BlockType.LABEL, text: 'Safety' },
          { opcode: 'stop', blockType: Scratch.BlockType.COMMAND, text: 'STOP robot' },
          { opcode: 'connected', blockType: Scratch.BlockType.BOOLEAN, text: 'robot connected?' },
        ],
        menus: {
          tricks: {
            acceptReporters: false,
            items: ['Hello', 'Stretch', 'Heart', 'Dance1', 'Dance2', 'Sit', 'RiseSit',
              'Scrape', 'Content', 'FrontJump', 'FrontPounce', 'StandUp', 'StandDown'],
          },
          flips: { acceptReporters: false, items: ['left', 'back', 'front'] },
        },
      };
    }

    startClock(args) {
      bpm = Scratch.Cast.toNumber(args.BPM);
      firstBeat = Scratch.Cast.toNumber(args.OFFSET);
      clockStart = performance.now();
    }

    waitBeat(args) {
      if (clockStart === null) return;
      const target = clockStart + (firstBeat + (Scratch.Cast.toNumber(args.BEAT) - 1) * beatSecs()) * 1000;
      const ms = target - performance.now();
      if (ms <= 0) return;
      return new Promise((resolve) => setTimeout(resolve, ms));
    }

    currentBeat() {
      if (clockStart === null) return 0;
      const secs = (performance.now() - clockStart) / 1000;
      return Math.floor((secs - firstBeat) / beatSecs()) + 1;
    }

    trick(args) { send({ c: 'trick', name: args.TRICK }); }
    flip(args) { send({ c: 'flip', dir: args.DIR }); }
    tilt(args) {
      send({ c: 'tilt', roll: Scratch.Cast.toNumber(args.ROLL),
        pitch: Scratch.Cast.toNumber(args.PITCH), yaw: Scratch.Cast.toNumber(args.YAW) });
    }
    level() { send({ c: 'level' }); }
    walk(args) {
      send({ c: 'move', x: Scratch.Cast.toNumber(args.X), y: Scratch.Cast.toNumber(args.Y),
        z: Scratch.Cast.toNumber(args.Z), secs: Scratch.Cast.toNumber(args.BEATS) * beatSecs() });
    }
    stop() { send({ c: 'stop' }); }

    async connected() {
      try {
        const r = await fetch(`${BRIDGE}/status`);
        return (await r.json()).connected === true;
      } catch (e) {
        return false;
      }
    }
  }

  Scratch.extensions.register(new Go2Dance());
})(Scratch);
