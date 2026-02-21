/**
 * SoundEngine — Procedural audio via Web Audio API
 * 
 * One-shot sound effects only. No looping, no feedback loops,
 * no persistent oscillators. Every sound self-terminates.
 */

let ctx = null;
let masterGain = null;
let compressor = null;
let _muted = false;
let _volume = 0.3;
let _unlocked = false;

function _initCtx() {
  if (ctx && ctx.state !== 'closed') return ctx;
  ctx = new (window.AudioContext || window.webkitAudioContext)();
  
  compressor = ctx.createDynamicsCompressor();
  compressor.threshold.value = -18;
  compressor.knee.value = 12;
  compressor.ratio.value = 6;
  compressor.attack.value = 0.003;
  compressor.release.value = 0.15;
  
  masterGain = ctx.createGain();
  masterGain.gain.value = _volume;
  
  compressor.connect(masterGain);
  masterGain.connect(ctx.destination);
  
  return ctx;
}

function getCtx() {
  if (!_unlocked) return null;
  return _initCtx();
}

function now() { return ctx ? ctx.currentTime : 0; }

function playNote(freq, duration, type = 'sine', gainVal = 0.12, opts = {}) {
  if (_muted || !_unlocked) return;
  const c = getCtx();
  if (!c) return;
  const t = now() + (opts.delay || 0);
  
  const osc = c.createOscillator();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t);
  if (opts.freqEnd) {
    osc.frequency.exponentialRampToValueAtTime(opts.freqEnd, t + duration);
  }
  
  const gain = c.createGain();
  const attack = opts.attack || 0.005;
  const release = opts.release || duration * 0.4;
  gain.gain.setValueAtTime(0, t);
  gain.gain.linearRampToValueAtTime(gainVal, t + attack);
  gain.gain.setValueAtTime(gainVal, t + duration - release);
  gain.gain.exponentialRampToValueAtTime(0.001, t + duration);
  
  osc.connect(gain);
  gain.connect(compressor);
  
  osc.start(t);
  osc.stop(t + duration + 0.01);
}

function playNoise(duration, gainVal = 0.04, opts = {}) {
  if (_muted || !_unlocked) return;
  const c = getCtx();
  if (!c) return;
  const t = now() + (opts.delay || 0);
  
  const bufferSize = Math.floor(c.sampleRate * duration);
  const buffer = c.createBuffer(1, bufferSize, c.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;
  
  const source = c.createBufferSource();
  source.buffer = buffer;
  
  const filter = c.createBiquadFilter();
  filter.type = opts.filterType || 'bandpass';
  filter.frequency.value = opts.filterFreq || 2000;
  filter.Q.value = opts.filterQ || 1;
  
  const gain = c.createGain();
  gain.gain.setValueAtTime(0, t);
  gain.gain.linearRampToValueAtTime(gainVal, t + 0.005);
  gain.gain.exponentialRampToValueAtTime(0.001, t + duration);
  
  source.connect(filter);
  filter.connect(gain);
  gain.connect(compressor);
  
  source.start(t);
}

// ═══════════════════════════════════════════════════════════════
// PUBLIC SOUND EFFECTS (all one-shot, self-terminating)
// ═══════════════════════════════════════════════════════════════

/** Bright ascending chime — seed planted */
export function sfxPlant() {
  const base = 523.25;
  playNote(base, 0.25, 'sine', 0.10, { attack: 0.002 });
  playNote(base * 1.25, 0.2, 'sine', 0.08, { delay: 0.07, attack: 0.002 });
  playNote(base * 1.5, 0.25, 'sine', 0.10, { delay: 0.14, attack: 0.002 });
  playNote(base * 2, 0.35, 'sine', 0.07, { delay: 0.21, attack: 0.002 });
  playNoise(0.06, 0.02, { filterType: 'highpass', filterFreq: 8000 });
}

/** Warm resonant cascade — harvest reward */
export function sfxHarvest() {
  const notes = [523.25, 659.25, 783.99, 1046.5, 1318.5];
  notes.forEach((f, i) => {
    playNote(f, 0.3, 'sine', 0.08, { delay: i * 0.06, attack: 0.002 });
  });
  playNoise(0.1, 0.03, { filterType: 'highpass', filterFreq: 6000, delay: 0.1 });
}

/** Low thud + descending tone — compost */
export function sfxCompost() {
  playNote(110, 0.35, 'sine', 0.12, { freqEnd: 55, release: 0.25 });
  playNote(165, 0.15, 'triangle', 0.05, { delay: 0.05, freqEnd: 82 });
  playNoise(0.1, 0.04, { filterType: 'lowpass', filterFreq: 400, filterQ: 2 });
}

/** Ethereal whoosh + high bell — dream */
export function sfxDream() {
  playNoise(0.4, 0.02, { filterType: 'bandpass', filterFreq: 1200, filterQ: 3 });
  playNote(880, 0.5, 'sine', 0.05, { delay: 0.1 });
  playNote(1320, 0.4, 'sine', 0.03, { delay: 0.2 });
}

/** Quick electric zap — node activation */
export function sfxPulse(freq = 440) {
  playNote(freq, 0.1, 'sawtooth', 0.05, { freqEnd: freq * 1.5, attack: 0.001, release: 0.07 });
  playNote(freq * 0.5, 0.06, 'sine', 0.03, { delay: 0.02 });
}

/** Mechanical click + rising tone — agent spawned */
export function sfxAgentSpawn() {
  playNoise(0.02, 0.06, { filterType: 'highpass', filterFreq: 4000 });
  playNote(330, 0.12, 'square', 0.04, { freqEnd: 660, delay: 0.03 });
  playNote(660, 0.15, 'sine', 0.06, { delay: 0.1 });
}

/** Coin ding cascade — agent completed */
export function sfxAgentComplete() {
  for (let i = 0; i < 4; i++) {
    playNote(1200 + i * 200, 0.08, 'sine', 0.05, { delay: i * 0.07 });
  }
  playNote(1568, 0.25, 'sine', 0.06, { delay: 0.3 });
}

/** Sweeping tone — season change */
export function sfxSeasonChange() {
  playNote(220, 1.0, 'sine', 0.06, { release: 0.8 });
  playNote(330, 0.8, 'sine', 0.04, { delay: 0.2, release: 0.6 });
  playNote(440, 0.6, 'sine', 0.03, { delay: 0.5, release: 0.4 });
}

/** Soft click — UI interaction */
export function sfxClick() {
  playNote(800, 0.03, 'sine', 0.05, { attack: 0.001, release: 0.02 });
}

// ═══════════════════════════════════════════════════════════════
// CONTROLS
// ═══════════════════════════════════════════════════════════════

export function setVolume(v) {
  _volume = Math.max(0, Math.min(1, v));
  if (masterGain) masterGain.gain.setValueAtTime(_volume, now());
}

export function setMuted(m) {
  _muted = m;
  if (masterGain) {
    masterGain.gain.setValueAtTime(m ? 0 : _volume, now());
  }
}

export function isMuted() { return _muted; }

const _throttleMap = {};

export function sfxPulseThrottled(freq = 440, key = 'default', cooldownMs = 3000) {
  const t = Date.now();
  if (_throttleMap[key] && t - _throttleMap[key] < cooldownMs) return;
  _throttleMap[key] = t;
  sfxPulse(freq);
}

export function unlock() {
  if (_unlocked && ctx && ctx.state === 'running') return;
  _unlocked = true;
  const c = _initCtx();
  if (c.state === 'suspended') c.resume();
}

export function isUnlocked() { return _unlocked; }

// Stubs for backward compat — these are no-ops now
export function startAmbient() {}
export function stopAmbient() {}
export function isAmbientRunning() { return false; }
