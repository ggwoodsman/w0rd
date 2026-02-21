/**
 * SoundEngine — Procedural audio via Web Audio API
 * 
 * Vegas-slot-machine-inspired: bright chimes, satisfying clicks,
 * resonant hums, reward cascades. All synthesized — no audio files needed.
 */

let ctx = null;
let masterGain = null;
let compressor = null;
let reverbNode = null;
let _muted = false;
let _volume = 0.35;

function getCtx() {
  if (ctx && ctx.state !== 'closed') return ctx;
  ctx = new (window.AudioContext || window.webkitAudioContext)();
  
  // Master chain: compressor → gain → destination
  compressor = ctx.createDynamicsCompressor();
  compressor.threshold.value = -24;
  compressor.knee.value = 12;
  compressor.ratio.value = 4;
  compressor.attack.value = 0.003;
  compressor.release.value = 0.15;
  
  masterGain = ctx.createGain();
  masterGain.gain.value = _volume;
  
  // Simple convolver-free reverb using feedback delay
  reverbNode = createReverb(ctx);
  
  compressor.connect(masterGain);
  reverbNode.connect(masterGain);
  masterGain.connect(ctx.destination);
  
  return ctx;
}

function createReverb(audioCtx) {
  const convolver = audioCtx.createGain();
  // We'll use a delay-based pseudo-reverb for simplicity
  const delay = audioCtx.createDelay(0.5);
  delay.delayTime.value = 0.08;
  const feedback = audioCtx.createGain();
  feedback.gain.value = 0.3;
  const filter = audioCtx.createBiquadFilter();
  filter.type = 'lowpass';
  filter.frequency.value = 3000;
  
  convolver.connect(delay);
  delay.connect(filter);
  filter.connect(feedback);
  feedback.connect(delay);
  delay.connect(convolver);
  
  return convolver;
}

function now() { return getCtx().currentTime; }

function playNote(freq, duration, type = 'sine', gainVal = 0.15, opts = {}) {
  if (_muted) return;
  const c = getCtx();
  const t = now();
  
  const osc = c.createOscillator();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t);
  if (opts.freqEnd) {
    osc.frequency.exponentialRampToValueAtTime(opts.freqEnd, t + duration);
  }
  if (opts.vibrato) {
    const lfo = c.createOscillator();
    const lfoGain = c.createGain();
    lfo.frequency.value = opts.vibrato;
    lfoGain.gain.value = freq * 0.02;
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);
    lfo.start(t);
    lfo.stop(t + duration);
  }
  
  const gain = c.createGain();
  const attack = opts.attack || 0.005;
  const release = opts.release || duration * 0.4;
  gain.gain.setValueAtTime(0, t);
  gain.gain.linearRampToValueAtTime(gainVal, t + attack);
  gain.gain.setValueAtTime(gainVal, t + duration - release);
  gain.gain.exponentialRampToValueAtTime(0.001, t + duration);
  
  osc.connect(gain);
  
  // Route to dry + wet
  gain.connect(compressor);
  if (opts.reverb !== false) {
    const wet = c.createGain();
    wet.gain.value = opts.reverbMix || 0.2;
    gain.connect(wet);
    wet.connect(reverbNode);
  }
  
  osc.start(t + (opts.delay || 0));
  osc.stop(t + duration + (opts.delay || 0));
}

function playNoise(duration, gainVal = 0.05, opts = {}) {
  if (_muted) return;
  const c = getCtx();
  const t = now();
  
  const bufferSize = c.sampleRate * duration;
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
  
  source.start(t + (opts.delay || 0));
}

// ═══════════════════════════════════════════════════════════════
// PUBLIC SOUND EFFECTS
// ═══════════════════════════════════════════════════════════════

/** Bright ascending chime — seed planted */
export function sfxPlant() {
  const base = 523.25; // C5
  playNote(base, 0.3, 'sine', 0.12, { attack: 0.002, reverbMix: 0.4 });
  playNote(base * 1.25, 0.25, 'sine', 0.10, { delay: 0.08, attack: 0.002, reverbMix: 0.4 });
  playNote(base * 1.5, 0.35, 'sine', 0.12, { delay: 0.16, attack: 0.002, reverbMix: 0.5 });
  playNote(base * 2, 0.5, 'sine', 0.08, { delay: 0.24, attack: 0.002, reverbMix: 0.6 });
  playNoise(0.08, 0.03, { filterType: 'highpass', filterFreq: 8000 });
}

/** Warm resonant cascade — harvest reward (slot machine jackpot feel) */
export function sfxHarvest() {
  const notes = [523.25, 659.25, 783.99, 1046.5, 1318.5, 1568.0];
  notes.forEach((f, i) => {
    playNote(f, 0.4 - i * 0.03, 'sine', 0.10 + i * 0.01, {
      delay: i * 0.06,
      attack: 0.002,
      reverbMix: 0.3 + i * 0.1,
    });
    // Harmonic shimmer
    playNote(f * 2, 0.2, 'sine', 0.04, {
      delay: i * 0.06 + 0.02,
      reverbMix: 0.5,
    });
  });
  // Sparkle noise burst
  playNoise(0.15, 0.04, { filterType: 'highpass', filterFreq: 6000, delay: 0.1 });
  playNoise(0.1, 0.03, { filterType: 'highpass', filterFreq: 10000, delay: 0.3 });
}

/** Low thud + descending tone — compost */
export function sfxCompost() {
  playNote(110, 0.4, 'sine', 0.15, { freqEnd: 55, release: 0.3 });
  playNote(165, 0.2, 'triangle', 0.06, { delay: 0.05, freqEnd: 82 });
  playNoise(0.12, 0.05, { filterType: 'lowpass', filterFreq: 400, filterQ: 2 });
}

/** Ethereal whoosh + high bell — dream generated */
export function sfxDream() {
  playNoise(0.6, 0.03, { filterType: 'bandpass', filterFreq: 1200, filterQ: 3 });
  playNote(880, 0.8, 'sine', 0.06, { delay: 0.1, vibrato: 4, reverbMix: 0.7 });
  playNote(1320, 0.6, 'sine', 0.04, { delay: 0.2, vibrato: 5, reverbMix: 0.8 });
  playNote(1760, 0.5, 'sine', 0.03, { delay: 0.35, reverbMix: 0.9 });
}

/** Quick electric zap — node activation / thinking pulse */
export function sfxPulse(freq = 440) {
  playNote(freq, 0.12, 'sawtooth', 0.06, { freqEnd: freq * 1.5, attack: 0.001, release: 0.08 });
  playNote(freq * 0.5, 0.08, 'sine', 0.04, { delay: 0.02 });
  playNoise(0.04, 0.02, { filterType: 'highpass', filterFreq: 5000 });
}

/** Mechanical click + rising tone — agent spawned */
export function sfxAgentSpawn() {
  playNoise(0.03, 0.08, { filterType: 'highpass', filterFreq: 4000 });
  playNote(330, 0.15, 'square', 0.05, { freqEnd: 660, delay: 0.03 });
  playNote(660, 0.2, 'sine', 0.08, { delay: 0.1, reverbMix: 0.4 });
  playNote(990, 0.15, 'sine', 0.05, { delay: 0.18, reverbMix: 0.5 });
}

/** Completion ding-ding-ding — agent completed (slot machine coins) */
export function sfxAgentComplete() {
  for (let i = 0; i < 5; i++) {
    const f = 1200 + Math.random() * 800;
    playNote(f, 0.08, 'sine', 0.06 + Math.random() * 0.03, {
      delay: i * 0.07 + Math.random() * 0.02,
      reverbMix: 0.3,
    });
  }
  playNote(1568, 0.3, 'sine', 0.08, { delay: 0.35, reverbMix: 0.5 });
}

/** Season change — sweeping pad transition */
export function sfxSeasonChange() {
  playNote(220, 1.5, 'sine', 0.08, { vibrato: 2, reverbMix: 0.8, release: 1.2 });
  playNote(330, 1.2, 'sine', 0.06, { delay: 0.2, vibrato: 2.5, reverbMix: 0.8, release: 1.0 });
  playNote(440, 1.0, 'sine', 0.05, { delay: 0.5, vibrato: 3, reverbMix: 0.9, release: 0.8 });
  playNoise(1.0, 0.02, { filterType: 'bandpass', filterFreq: 800, filterQ: 0.5, delay: 0.1 });
}

/** Soft click — UI interaction */
export function sfxClick() {
  playNote(800, 0.04, 'sine', 0.06, { attack: 0.001, release: 0.03 });
  playNoise(0.02, 0.02, { filterType: 'highpass', filterFreq: 6000 });
}

/** Shockwave whomp — big event emphasis */
export function sfxShockwave() {
  playNote(80, 0.3, 'sine', 0.18, { freqEnd: 40, release: 0.25 });
  playNote(160, 0.15, 'triangle', 0.08, { freqEnd: 60 });
  playNoise(0.2, 0.06, { filterType: 'lowpass', filterFreq: 600, filterQ: 3 });
}

// ═══════════════════════════════════════════════════════════════
// AMBIENT DRONE (per-season)
// ═══════════════════════════════════════════════════════════════

let _ambientOscs = [];
let _ambientGain = null;

export function startAmbient(season = 'spring') {
  stopAmbient();
  if (_muted) return;
  const c = getCtx();
  
  const configs = {
    spring:  { freqs: [130.81, 196.00, 261.63], type: 'sine', vol: 0.012, filterFreq: 800 },
    summer:  { freqs: [146.83, 220.00, 293.66], type: 'sine', vol: 0.014, filterFreq: 1000 },
    autumn:  { freqs: [123.47, 185.00, 246.94], type: 'triangle', vol: 0.010, filterFreq: 600 },
    winter:  { freqs: [110.00, 164.81, 220.00], type: 'sine', vol: 0.008, filterFreq: 500 },
  };
  const cfg = configs[season] || configs.spring;
  
  _ambientGain = c.createGain();
  _ambientGain.gain.setValueAtTime(0, now());
  _ambientGain.gain.linearRampToValueAtTime(cfg.vol, now() + 3);
  
  const filter = c.createBiquadFilter();
  filter.type = 'lowpass';
  filter.frequency.value = cfg.filterFreq;
  filter.Q.value = 0.5;
  
  _ambientGain.connect(filter);
  filter.connect(compressor);
  
  cfg.freqs.forEach(f => {
    const osc = c.createOscillator();
    osc.type = cfg.type;
    osc.frequency.value = f;
    // Slow detune drift
    const lfo = c.createOscillator();
    lfo.frequency.value = 0.1 + Math.random() * 0.15;
    const lfoGain = c.createGain();
    lfoGain.gain.value = f * 0.003;
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);
    lfo.start();
    
    osc.connect(_ambientGain);
    osc.start();
    _ambientOscs.push(osc, lfo);
  });
}

export function stopAmbient() {
  if (_ambientGain) {
    try { _ambientGain.gain.linearRampToValueAtTime(0, now() + 1); } catch {}
  }
  setTimeout(() => {
    _ambientOscs.forEach(o => { try { o.stop(); } catch {} });
    _ambientOscs = [];
    _ambientGain = null;
  }, 1200);
}

// ═══════════════════════════════════════════════════════════════
// CONTROLS
// ═══════════════════════════════════════════════════════════════

export function setVolume(v) {
  _volume = Math.max(0, Math.min(1, v));
  if (masterGain) masterGain.gain.linearRampToValueAtTime(_volume, now() + 0.05);
}

export function setMuted(m) {
  _muted = m;
  if (m) {
    if (masterGain) masterGain.gain.linearRampToValueAtTime(0, now() + 0.1);
    stopAmbient();
  } else {
    if (masterGain) masterGain.gain.linearRampToValueAtTime(_volume, now() + 0.1);
  }
}

export function isMuted() { return _muted; }

/** Must be called from a user gesture to unlock Web Audio */
export function unlock() {
  const c = getCtx();
  if (c.state === 'suspended') c.resume();
}
