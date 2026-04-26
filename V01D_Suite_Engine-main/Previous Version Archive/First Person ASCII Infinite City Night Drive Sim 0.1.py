#!/usr/bin/env python3
# =============================================================================
#  P H O S   C I T Y   v1.0
#  Built around the Cybervoid_Phos engine (Void Engine v2.0 architecture).
#  All combat / health / weapons / enemies stripped. Pure GFX processing.
#
#  An infinite procedural night-city ASCII raycaster. You drive a wide
#  empty boulevard between stacked highrises. Windows light the canyon.
#  Trees, lamps, parked cars line the curb. Lane stripes recede to the
#  horizon. Ambient audio: HVAC void-hum, wind gusts, distant traffic
#  rumble, structure groans. Everything synthesized live, no files.
#
#  Pure Python 3 + tkinter stdlib only. Zero external dependencies.
#
#  W / ↑          Throttle
#  S / ↓          Brake / reverse
#  A / D / ← / →  Steer
#  SHIFT          Boost
#  M              Toggle music / ambience
#  R              Recenter on road
#  ESC            Quit
# =============================================================================

import tkinter as tk
import math, random, time, sys, os, threading, io, wave, struct, subprocess
import array
from pathlib import Path

VERSION  = "1.0"
W, H     = 140, 44
SR       = 22050
TAU      = math.tau
INV_SR   = 1.0 / SR

# =============================================================================
#  PURE-PYTHON WAV SYNTHESIS  (carried from Void Engine, GFX-related only)
# =============================================================================

def _clamp(x, lo=-1.0, hi=1.0):
    return lo if x < lo else (hi if x > hi else x)

def _soft_clip(x, drive=1.15):
    d = math.tanh(drive)
    return math.tanh(x * drive) / d if d else x

def _exp(t, rate): return math.exp(-t * rate)
def _samples(dur): return int(SR * dur)

def _to_wav(samples):
    """Mono float [-1,1] → 16-bit WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        raw = bytearray()
        for s in samples:
            raw += struct.pack('<h', int(_clamp(s) * 32767))
        w.writeframes(bytes(raw))
    return buf.getvalue()

def _to_wav_stereo(L, R):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        raw = bytearray()
        for l, r in zip(L, R):
            raw += struct.pack('<hh', int(_clamp(l) * 32767), int(_clamp(r) * 32767))
        w.writeframes(bytes(raw))
    return buf.getvalue()

# Async playback — picks system player
_AUDIO_PLAYERS = None
def _detect_player():
    global _AUDIO_PLAYERS
    if _AUDIO_PLAYERS is not None:
        return _AUDIO_PLAYERS
    if sys.platform == 'darwin':
        _AUDIO_PLAYERS = ['afplay']
    elif sys.platform.startswith('win'):
        _AUDIO_PLAYERS = ['winsound']
    else:
        for cand in ('aplay', 'paplay', 'play'):
            try:
                subprocess.run(['which', cand], capture_output=True, check=True)
                _AUDIO_PLAYERS = [cand]
                break
            except Exception:
                continue
        if _AUDIO_PLAYERS is None:
            _AUDIO_PLAYERS = []
    return _AUDIO_PLAYERS

def _play_async(wav_bytes):
    players = _detect_player()
    if not players:
        return
    def _go():
        try:
            if players[0] == 'winsound':
                import winsound
                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY | winsound.SND_ASYNC)
                return
            p = subprocess.Popen(
                [players[0], '-'] if players[0] in ('aplay','paplay','play') else [players[0], '/dev/stdin'],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            p.stdin.write(wav_bytes); p.stdin.close()
        except Exception:
            pass
    threading.Thread(target=_go, daemon=True).start()


# =============================================================================
#  AMBIENT AUDIO — kept from Void Engine, repurposed for empty-city night
# =============================================================================

def synth_traffic_rumble(dur=6.0, seed=None):
    """Distant arterial traffic — a band of low rumble + slow swells."""
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random
    n = _samples(dur)
    out = [0.0] * n
    # Brown noise lowpassed
    last = 0.0
    for i in range(n):
        last = 0.985 * last + (rng.random() - 0.5) * 0.04
        # Slow LFOs for traffic ebb & flow
        t = i * INV_SR
        amp = 0.55 + 0.30 * math.sin(0.21 * t) + 0.18 * math.sin(0.067 * t + 1.3)
        out[i] = last * amp
    # Soft seam fade
    fade = int(SR * 0.08)
    for i in range(fade):
        k = i / fade
        out[i] *= k
        out[-1 - i] *= k
    return _to_wav(out)

def synth_void_hum(seed=None):
    """HVAC plant on the next block — sustained low drone."""
    rng = random.Random(seed) if seed is not None else random
    n = _samples(4.0)
    out = [0.0] * n
    f1 = 47 + rng.uniform(-3, 5)
    f2 = f1 * 1.51
    f3 = f1 * 0.5
    p1 = p2 = p3 = 0.0
    for i in range(n):
        p1 += TAU * f1 * INV_SR
        p2 += TAU * f2 * INV_SR
        p3 += TAU * f3 * INV_SR
        # Slight breathing modulation
        breath = 0.5 + 0.5 * math.sin(0.18 * i * INV_SR)
        s = (math.sin(p1) * 0.42 + math.sin(p2) * 0.12 + math.sin(p3) * 0.36) * (0.6 + 0.4 * breath)
        out[i] = s * 0.45
    fade = int(SR * 0.15)
    for i in range(fade):
        k = i / fade
        out[i] *= k; out[-1 - i] *= k
    return _to_wav(out)

def synth_wind_gust(seed=None):
    """Wind through the canyon — filtered noise with envelope."""
    rng = random.Random(seed) if seed is not None else random
    dur = rng.uniform(2.5, 5.0)
    n = _samples(dur)
    out = [0.0] * n
    last = 0.0
    last2 = 0.0
    for i in range(n):
        # Two-pole lowpass on noise
        nz = rng.uniform(-1, 1)
        last = 0.9 * last + 0.1 * nz
        last2 = 0.92 * last2 + 0.08 * last
        t = i / n
        # Gust shape: rising swell, plateau, fall
        env = math.sin(t * math.pi) ** 1.4
        out[i] = last2 * env * 0.55
    return _to_wav(out)

def synth_structure_groan(seed=None):
    """Rebar settling — slow detuned sine pair with a creak transient."""
    rng = random.Random(seed) if seed is not None else random
    dur = rng.uniform(1.6, 3.4)
    n = _samples(dur)
    out = [0.0] * n
    f1 = rng.uniform(72, 140)
    f2 = f1 * rng.uniform(1.005, 1.02)
    p1 = p2 = 0.0
    for i in range(n):
        p1 += TAU * f1 * INV_SR
        p2 += TAU * f2 * INV_SR
        t = i / n
        env = (1 - t) * (t * 4) if t < 0.25 else (1 - t) * 1.0
        creak = 0.0
        # Soft creak transients
        if rng.random() < 0.0007:
            creak = rng.uniform(-0.4, 0.4)
        s = (math.sin(p1) * 0.35 + math.sin(p2) * 0.30) * env + creak * env
        out[i] = s * 0.5
    return _to_wav(out)

def synth_distant_horn(seed=None):
    """A car horn many blocks away — short, doppler-fade."""
    rng = random.Random(seed) if seed is not None else random
    dur = rng.uniform(0.4, 0.9)
    n = _samples(dur)
    out = [0.0] * n
    f = rng.uniform(330, 430)
    p1 = p2 = 0.0
    f2 = f * 1.5
    for i in range(n):
        p1 += TAU * f * INV_SR
        p2 += TAU * f2 * INV_SR
        t = i / n
        env = (1 - abs(2 * t - 1)) ** 1.6
        s = (math.sin(p1) * 0.5 + math.sin(p2) * 0.3) * env * 0.18  # already very distant
        out[i] = s
    return _to_wav(out)

def synth_lamp_buzz(seed=None):
    """Sodium lamp 60Hz buzz."""
    rng = random.Random(seed) if seed is not None else random
    dur = rng.uniform(0.6, 1.4)
    n = _samples(dur)
    out = [0.0] * n
    p1 = p2 = p3 = 0.0
    for i in range(n):
        p1 += TAU * 60 * INV_SR
        p2 += TAU * 120 * INV_SR
        p3 += TAU * 180 * INV_SR
        t = i / n
        env = math.sin(t * math.pi) ** 0.8
        # Gritty buzz
        s = math.sin(p1) * 0.18 + (math.sin(p2) + math.sin(p3)) * 0.08
        s = _soft_clip(s * 2.5, 1.4) * 0.20 * env
        out[i] = s
    return _to_wav(out)


# =============================================================================
#  ENGINE / TIRE AUDIO — continuous PCM stream piped to one player subprocess
#
#  Architecture: keep a single aplay/play/paplay subprocess open and write raw
#  signed-16 little-endian PCM to its stdin in 50 ms chunks. Phase is carried
#  across chunks so output is glitch-free. Each chunk is synthesized using
#  the CURRENT camera state (rpm, throttle, speed, steer), which gives ~50 ms
#  audio latency to player input — fast enough to feel responsive.
#
#  The engine voice mixes seven layers across the full audio band:
#    sub          0.5 × crank        ground rumble (≤ 60 Hz at speed)
#    crank        crank fundamental  body
#    firing       2 × crank          4-cyl 4-stroke combustion pulse, peaky
#    h2           4 × crank          mid harmonic
#    h4           8 × crank          upper mid
#    h8           16 × crank         high
#    h16          32 × crank         intake/exhaust whine
#  Plus lumpy timbre modulation, throttle-scaled grit noise, and tanh
#  soft-clipping that drives harder under load — that's the ROAR.
#
#  Tire layer adds two-pole-lowpassed brown noise (road roar, scaled to
#  speed) plus a high-passed scrub when steering at speed.
# =============================================================================

# ----- AMBIENT MUSIC -----
# A natural-minor (Aeolian) progression: i — VI — III — VII (Am — F — C — G).
# Bass and pad notes are expressed as semitones from A2 (110 Hz).
# Every full cycle of the progression we randomly transpose the whole
# thing into a related key, which is what gives it the "infinite never
# repeats" quality without ever hitting a dissonance.
A2_HZ           = 110.0
MUSIC_BPM       = 50.0
MUSIC_BEAT_DUR  = 60.0 / MUSIC_BPM           # 1.2 seconds per beat
MUSIC_CHORD_DUR = MUSIC_BEAT_DUR * 8.0       # 9.6 seconds per chord

PROGRESSION = [
    {'bass': -12, 'pads': [ 0,  3,  7, 12]},   # Am
    {'bass': -16, 'pads': [-4,  0,  4,  8]},   # F
    {'bass':  -9, 'pads': [ 3,  7, 10, 15]},   # C
    {'bass': -14, 'pads': [ 2,  5, 10, 14]},   # G
]
# Transpositions (in semitones) the progression can shift to between
# cycles — all chosen to stay in the modal family of A minor / C major.
MUSIC_TRANSPOSITIONS = [-7, -5, -3, 0, 0, 2, 3, 5, 7]
# A minor pentatonic across two-and-a-half octaves above A2 — melody never
# misses against any chord in the progression.
PENTATONIC_SEMIS = [12, 15, 17, 19, 22, 24, 27, 29, 31]


def synth_music_stereo(n, phase):
    """
    Generate (out_L, out_R) lists of n stereo music samples in [-1, 1].

    State lives in the shared `phase` dict so the music continues across
    chunk boundaries without phase clicks. Voices fade in over each
    chord's first 2 seconds and fade out over its last 1.5 seconds, so
    chord changes are seamless instead of stepped. Pad voices alternate
    hard left/right for stereo width. Bass and melody sit center. A
    ping-pong delay (slightly different L vs R times) gives spatial bloom.
    """
    inv_sr = INV_SR
    sin = math.sin
    TAU_LOCAL = TAU

    # ---- One-time init ----
    if not phase.get('m_init'):
        phase['m_init']         = True
        phase['m_chord_idx']    = 0
        phase['m_chord_t']      = 0.0
        phase['m_chord_count']  = 0
        phase['m_transpose']    = 0
        phase['m_pad_p']        = [0.0, 0.0, 0.0, 0.0]
        phase['m_pad_p2']       = [0.0, 0.0, 0.0, 0.0]
        phase['m_bass_p']       = 0.0
        phase['m_sub_p']        = 0.0
        phase['m_lfo_p']        = 0.0
        phase['m_filter_L']     = 0.0
        phase['m_filter_R']     = 0.0
        # Stereo ping-pong delay buffers — different lengths for asymmetry
        delay_L = int(SR * 0.34)             # 340 ms left
        delay_R = int(SR * 0.27)             # 270 ms right
        phase['m_delay_L']      = [0.0] * delay_L
        phase['m_delay_R']      = [0.0] * delay_R
        phase['m_delay_iL']     = 0
        phase['m_delay_iR']     = 0
        phase['m_mel_p']        = 0.0
        phase['m_mel_freq']     = 0.0
        phase['m_mel_env']      = 0.0
        phase['m_mel_pan']      = 0.5    # 0.0 = full L, 1.0 = full R
        phase['m_mel_next']     = 6.0    # don't trigger a melody for 6 sec
        phase['m_t']            = 0.0
        phase['m_rng']          = random.Random()

    rng = phase['m_rng']

    # ---- Compute current chord frequencies ----
    chord = PROGRESSION[phase['m_chord_idx']]
    transp = phase['m_transpose']
    bass_freq = A2_HZ * (2.0 ** ((chord['bass'] + transp) / 12.0))
    pad_freqs = [A2_HZ * (2.0 ** ((s + transp) / 12.0)) for s in chord['pads']]

    d_pads  = [TAU_LOCAL * f * inv_sr for f in pad_freqs]
    d_pads2 = [TAU_LOCAL * f * 1.005 * inv_sr for f in pad_freqs]   # detune partner
    d_bass  = TAU_LOCAL * bass_freq * inv_sr
    d_sub   = TAU_LOCAL * bass_freq * 0.5 * inv_sr
    d_lfo   = TAU_LOCAL * 0.07 * inv_sr   # very slow filter sweep

    # Local references (tight loop)
    p_pads   = phase['m_pad_p']
    p_pads2  = phase['m_pad_p2']
    p_bass   = phase['m_bass_p']
    p_sub    = phase['m_sub_p']
    p_lfo    = phase['m_lfo_p']
    fL       = phase['m_filter_L']
    fR       = phase['m_filter_R']
    dL       = phase['m_delay_L']
    dR       = phase['m_delay_R']
    iL       = phase['m_delay_iL']
    iR       = phase['m_delay_iR']
    nL       = len(dL)
    nR       = len(dR)
    p_mel    = phase['m_mel_p']
    mel_freq = phase['m_mel_freq']
    mel_env  = phase['m_mel_env']
    mel_pan  = phase['m_mel_pan']
    chord_t0 = phase['m_chord_t']

    d_mel = TAU_LOCAL * mel_freq * inv_sr if mel_freq > 0 else 0.0

    out_L = [0.0] * n
    out_R = [0.0] * n

    for i in range(n):
        # Pad envelope across the chord
        ct = chord_t0 + i * inv_sr
        if ct < 2.0:
            pad_amp = ct * 0.5
        elif ct > MUSIC_CHORD_DUR - 1.5:
            pad_amp = (MUSIC_CHORD_DUR - ct) * (1.0 / 1.5)
            if pad_amp < 0.0: pad_amp = 0.0
        else:
            pad_amp = 1.0

        # Pads: voices 0&2 on the left, voices 1&3 on the right
        L_pad = (sin(p_pads[0]) * 0.45 + sin(p_pads2[0]) * 0.30
               + sin(p_pads[2]) * 0.45 + sin(p_pads2[2]) * 0.30) * 0.10 * pad_amp
        R_pad = (sin(p_pads[1]) * 0.45 + sin(p_pads2[1]) * 0.30
               + sin(p_pads[3]) * 0.45 + sin(p_pads2[3]) * 0.30) * 0.10 * pad_amp
        for j in range(4):
            p_pads[j]  += d_pads[j]
            p_pads2[j] += d_pads2[j]

        # Bass — sine + sub-octave, center-panned, gentle tremolo on amplitude
        bass = (sin(p_bass) * 0.50 + sin(p_sub) * 0.32) * 0.18 * pad_amp
        p_bass += d_bass
        p_sub  += d_sub

        # Melody — sparse music-box voice, pan set per-note
        mel_sample = 0.0
        if mel_env > 0.0001:
            mel_sample = (sin(p_mel) * 0.55 + sin(p_mel * 2.0) * 0.18) * mel_env
            p_mel += d_mel
            mel_env *= 0.99996   # ~3 sec to half-amplitude

        L_dry = L_pad + bass + mel_sample * (1.0 - mel_pan)
        R_dry = R_pad + bass + mel_sample * mel_pan

        # Slow lowpass filter modulated by the LFO (opens/closes the timbre)
        cutoff = 0.030 + 0.030 * sin(p_lfo)
        fL += cutoff * (L_dry - fL)
        fR += cutoff * (R_dry - fR)
        p_lfo += d_lfo

        # Ping-pong delay: L feeds into R's buffer, R feeds into L's buffer
        delayed_L = dL[iL]
        delayed_R = dR[iR]
        dL[iL] = fL + delayed_R * 0.36
        dR[iR] = fR + delayed_L * 0.36
        iL += 1
        if iL >= nL: iL = 0
        iR += 1
        if iR >= nR: iR = 0

        out_L[i] = fL * 0.80 + delayed_L * 0.45
        out_R[i] = fR * 0.80 + delayed_R * 0.45

    # Wrap phases
    phase['m_pad_p']     = p_pads
    phase['m_pad_p2']    = p_pads2
    phase['m_bass_p']    = p_bass % TAU_LOCAL
    phase['m_sub_p']     = p_sub  % TAU_LOCAL
    phase['m_lfo_p']     = p_lfo  % TAU_LOCAL
    phase['m_filter_L']  = fL
    phase['m_filter_R']  = fR
    phase['m_delay_iL']  = iL
    phase['m_delay_iR']  = iR
    phase['m_mel_p']     = p_mel
    phase['m_mel_freq']  = mel_freq
    phase['m_mel_env']   = mel_env

    chord_t_end = chord_t0 + n * inv_sr
    phase['m_t'] = phase['m_t'] + n * inv_sr

    # Chord change?
    if chord_t_end >= MUSIC_CHORD_DUR:
        chord_t_end -= MUSIC_CHORD_DUR
        phase['m_chord_idx']   = (phase['m_chord_idx'] + 1) % len(PROGRESSION)
        phase['m_chord_count'] = phase['m_chord_count'] + 1
        # Every full cycle (4 chords), pick a new key transposition
        if phase['m_chord_count'] % 4 == 0:
            phase['m_transpose'] = rng.choice(MUSIC_TRANSPOSITIONS)
    phase['m_chord_t'] = chord_t_end

    # Trigger a new melody note?
    if phase['m_t'] >= phase['m_mel_next']:
        if rng.random() < 0.72:
            pent = rng.choice(PENTATONIC_SEMIS)
            new_freq = A2_HZ * (2.0 ** ((pent + transp) / 12.0))
            phase['m_mel_freq'] = new_freq
            phase['m_mel_env']  = 0.55
            phase['m_mel_p']    = 0.0
            phase['m_mel_pan']  = rng.uniform(0.15, 0.85)
        # Schedule the next melody slot — wide variance keeps it from
        # feeling rhythmic.
        phase['m_mel_next'] = phase['m_t'] + rng.uniform(2.5, 7.0)

    return out_L, out_R


# =============================================================================

def synth_audio_chunk(rpm, throttle, brake, speed_frac, steer, n, phase):
    """
    Synthesize n samples of engine + tire audio. Returns a list of floats
    in [-1, 1]. The `phase` dict is mutated in place to carry phase
    continuity across calls — never reset it between chunks or you get
    audible discontinuities.
    """
    out = [0.0] * n

    # Engine frequencies
    f_crank = max(12.0, rpm / 60.0)            # Hz
    f_fire  = f_crank * 2.0                    # 4-cyl, 4-stroke fires twice per rev
    inv_sr  = INV_SR

    d_sub   = TAU * f_crank * 0.5  * inv_sr    # sub-octave
    d_crank = TAU * f_crank        * inv_sr
    d_fire  = TAU * f_fire         * inv_sr
    d_h2    = TAU * f_fire * 2.0   * inv_sr
    d_h4    = TAU * f_fire * 4.0   * inv_sr
    d_h8    = TAU * f_fire * 8.0   * inv_sr
    d_h16   = TAU * f_fire * 16.0  * inv_sr
    d_lump  = TAU * 5.7            * inv_sr    # lumpiness LFO

    p_sub   = phase.get('sub',   0.0)
    p_crank = phase.get('crank', 0.0)
    p_fire  = phase.get('fire',  0.0)
    p_h2    = phase.get('h2',    0.0)
    p_h4    = phase.get('h4',    0.0)
    p_h8    = phase.get('h8',    0.0)
    p_h16   = phase.get('h16',   0.0)
    p_lump  = phase.get('lump',  0.0)

    # How throttle/speed shape the timbre:
    #   - More throttle    → more upper harmonics (brightness, ROAR)
    #   - More speed       → more sub/bass weight
    #   - More throttle    → more soft-clip drive (grit)
    spectral = 0.32 + 0.68 * throttle
    bass_amp = 0.55 + 0.30 * speed_frac
    drive    = 1.10 + throttle * 1.25 + speed_frac * 0.40
    # Engine-brake / coast: if no throttle and moving fast, dampen highs
    if throttle < 0.05 and speed_frac > 0.2:
        spectral *= 0.55
        drive    *= 0.85

    # Tire layer state (two-pole lowpass on noise + a one-pole highpass scrub)
    rng = phase.get('rng')
    if rng is None:
        rng = random.Random()
        phase['rng'] = rng
    t_lp1   = phase.get('t_lp1', 0.0)
    t_lp2   = phase.get('t_lp2', 0.0)
    t_hp_x1 = phase.get('t_hp_x1', 0.0)
    t_hp_y1 = phase.get('t_hp_y1', 0.0)

    sin   = math.sin
    tanh  = math.tanh
    rand  = rng.random
    norm_drive = tanh(drive)
    if norm_drive == 0.0: norm_drive = 1.0

    abs_steer = abs(steer)
    scrub_active = (abs_steer > 0.18 and speed_frac > 0.2)

    # Pre-compute master volume — louder under throttle and at speed
    master = 0.32 + 0.20 * speed_frac + 0.18 * throttle

    for i in range(n):
        # Engine voices
        sf = sin(p_fire)
        # Asymmetric peaky firing (sin³ added gives the cylinder thump)
        firing = sf + 0.45 * sf * sf * sf
        lump_mod = 1.0 + 0.10 * sin(p_lump)

        engine = (
            sin(p_sub)   * 0.50 * bass_amp +
            sin(p_crank) * 0.34 * bass_amp +
            firing       * 0.55 * (0.55 + 0.45 * throttle) +
            sin(p_h2)    * 0.30 * spectral +
            sin(p_h4)    * 0.20 * spectral +
            sin(p_h8)    * 0.12 * spectral +
            sin(p_h16)   * 0.06 * spectral
        ) * lump_mod

        # Throttle grit
        if throttle > 0.25:
            engine += (rand() * 2.0 - 1.0) * 0.05 * throttle

        # Soft-clip — saturating tanh produces the harmonic explosion that
        # SOUNDS like an engine roaring under load.
        engine = tanh(engine * drive) / norm_drive

        # Tire layer — brown-ish road roar
        nz = rand() * 2.0 - 1.0
        t_lp1 = 0.92 * t_lp1 + 0.08 * nz
        t_lp2 = 0.85 * t_lp2 + 0.15 * t_lp1
        roar = t_lp2 * 0.55 * speed_frac

        # Tire scrub when steering at speed — high-pass differential of noise
        scrub = 0.0
        if scrub_active:
            x_in = nz
            # one-pole highpass: y = a*(y_prev + x - x_prev)
            t_hp_y1 = 0.78 * (t_hp_y1 + x_in - t_hp_x1)
            t_hp_x1 = x_in
            scrub = t_hp_y1 * 0.35 * abs_steer * speed_frac

        # Brake squeal — if hard braking at speed, add high-end hiss
        if brake > 0.5 and speed_frac > 0.25:
            squeal = (rand() * 2.0 - 1.0 - 0.6 * t_lp1) * 0.12 * brake * speed_frac
        else:
            squeal = 0.0

        s = (engine * 0.95 + roar + scrub + squeal) * master
        out[i] = s if -1.0 < s < 1.0 else (1.0 if s >= 1.0 else -1.0)

        # Advance phases
        p_sub   += d_sub
        p_crank += d_crank
        p_fire  += d_fire
        p_h2    += d_h2
        p_h4    += d_h4
        p_h8    += d_h8
        p_h16   += d_h16
        p_lump  += d_lump

    # Wrap phases to keep the floats from drifting toward big numbers
    phase['sub']   = p_sub   % TAU
    phase['crank'] = p_crank % TAU
    phase['fire']  = p_fire  % TAU
    phase['h2']    = p_h2    % TAU
    phase['h4']    = p_h4    % TAU
    phase['h8']    = p_h8    % TAU
    phase['h16']   = p_h16   % TAU
    phase['lump']  = p_lump  % TAU
    phase['t_lp1'] = t_lp1
    phase['t_lp2'] = t_lp2
    phase['t_hp_x1'] = t_hp_x1
    phase['t_hp_y1'] = t_hp_y1

    return out


class EngineEngine:
    """Continuous PCM streamed to a single audio-player subprocess.
    Synthesizes engine + tire audio in 50 ms chunks at the current camera
    state, never restarts, never gaps."""

    CHUNK_DUR = 0.050   # 50 ms = 20 Hz update rate, ~50 ms latency

    def __init__(self, state_provider):
        self.get_state = state_provider
        self._stop = threading.Event()
        self._enabled = True
        self._proc = None
        self._mode = 'none'

    def _open_streaming_proc(self):
        """Try a list of candidate audio streamers. Returns first one whose
        subprocess accepts a probe write AND stays alive afterwards."""
        candidates = [
            ['aplay', '-f', 'S16_LE', '-r', str(SR), '-c', '1', '-q'],
            ['pacat', '--playback', '--rate', str(SR), '--channels', '1',
             '--format', 's16le'],
            ['paplay', '--raw', '--rate=' + str(SR),
             '--channels=1', '--format=s16le'],
            ['play', '-q', '-t', 'raw', '-r', str(SR), '-b', '16',
             '-e', 'signed-integer', '-c', '1', '-'],
        ]
        for cmd in candidates:
            try:
                proc = subprocess.Popen(
                    cmd, stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except (FileNotFoundError, OSError):
                continue
            # Probe: write 100 ms of silence, give the backend a moment to
            # fail if there's no PCM device, then verify it's still alive.
            try:
                proc.stdin.write(b'\x00\x00' * (SR // 10))
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                try: proc.kill()
                except Exception: pass
                continue
            time.sleep(0.15)
            if proc.poll() is not None:
                # Backend died (no audio device, perms, etc.) — try next
                continue
            return proc, cmd[0]
        return None, None

    def start(self):
        proc, name = self._open_streaming_proc()
        if proc is None:
            self._mode = 'none'
            print("[engine] no streaming audio backend found "
                  "(aplay/pacat/paplay/play). Engine sound disabled.")
            return
        self._proc = proc
        self._mode = 'stream:' + name
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._stop.set()
        if self._proc:
            try: self._proc.stdin.close()
            except Exception: pass
            try: self._proc.terminate()
            except Exception: pass

    def toggle(self):
        self._enabled = not self._enabled
        return self._enabled

    def _loop(self):
        n = _samples(self.CHUNK_DUR)
        phase = {}
        silence_chunk = b'\x00\x00' * n

        # We pre-pack int16 with array.array for speed
        int_buf = array.array('h', [0] * n)

        while not self._stop.is_set():
            try:
                if not self._enabled:
                    self._proc.stdin.write(silence_chunk)
                    self._proc.stdin.flush()
                    self._stop.wait(self.CHUNK_DUR)
                    continue

                state = self.get_state()
                samples = synth_audio_chunk(
                    rpm        = state['rpm'],
                    throttle   = state['throttle'],
                    brake      = state['brake'],
                    speed_frac = state['speed_frac'],
                    steer      = state['steer'],
                    n          = n,
                    phase      = phase,
                )

                # Pack to int16 LE
                for i in range(n):
                    v = samples[i]
                    if v >  1.0: v =  1.0
                    if v < -1.0: v = -1.0
                    int_buf[i] = int(v * 32767)

                self._proc.stdin.write(int_buf.tobytes())
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                break


# =============================================================================
#  AMBIENT ENGINE — orchestrates the city soundscape (separate from EngineEngine)
# =============================================================================

class AmbientEngine:
    """Always-on city background. Multiple staggered loops."""
    def __init__(self):
        self._stop = threading.Event()
        self._enabled = True
        self._threads = []

    def start(self):
        # Steady bed: traffic rumble + void hum overlap
        self._threads.append(threading.Thread(target=self._bed_loop, daemon=True))
        # Sporadic events: wind, groans, horns, lamp buzzes
        self._threads.append(threading.Thread(target=self._events_loop, daemon=True))
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()

    def toggle(self):
        self._enabled = not self._enabled
        return self._enabled

    def _bed_loop(self):
        # Rebake ahead, play, sleep until next bake
        seed = random.randint(0, 1 << 30)
        while not self._stop.is_set():
            if not self._enabled:
                time.sleep(0.5); continue
            wav_t = synth_traffic_rumble(dur=6.0, seed=seed)
            wav_h = synth_void_hum(seed=seed + 1)
            seed += 7
            _play_async(wav_t)
            time.sleep(0.4)
            _play_async(wav_h)
            time.sleep(5.6)  # let them overlap, they're long

    def _events_loop(self):
        rng = random.Random()
        while not self._stop.is_set():
            if not self._enabled:
                time.sleep(0.5); continue
            wait = rng.uniform(2.5, 6.5)
            self._stop.wait(wait)
            if self._stop.is_set(): break
            roll = rng.random()
            if roll < 0.35:
                _play_async(synth_wind_gust(seed=rng.randint(0, 1<<30)))
            elif roll < 0.60:
                _play_async(synth_structure_groan(seed=rng.randint(0, 1<<30)))
            elif roll < 0.78:
                _play_async(synth_lamp_buzz(seed=rng.randint(0, 1<<30)))
            elif roll < 0.92:
                _play_async(synth_distant_horn(seed=rng.randint(0, 1<<30)))
            # else: silence beat


# =============================================================================
#  CITY MAP ROUTER — infinite procedural grid (carried from Void Engine pattern)
# =============================================================================
#
#  Block layout: streets every BLOCK_STRIDE cells. Streets are STREET_WIDTH cells
#  wide. Building cells store an integer wall-type:
#     1 = brick lowrise        (small windows, dense)
#     2 = concrete tower       (tall narrow windows)
#     3 = glass tower          (full grid, lots lit)
#     4 = office block         (mixed grid)
#  0 = open street (drivable).
# =============================================================================

class CityRouter:
    BLOCK_STRIDE = 12   # full repeat including streets
    STREET_HALF  = 2    # so streets are 2*STREET_HALF wide

    def __init__(self, seed=42):
        self.seed = seed
        self.cache = {}

    def _block_key(self, cx, cy):
        return (cx // self.BLOCK_STRIDE, cy // self.BLOCK_STRIDE)

    def get_cell(self, x, y):
        cx = int(math.floor(x))
        cy = int(math.floor(y))
        # Street test: if cell is within STREET_HALF of a stride line, it's a street
        rx = cx % self.BLOCK_STRIDE
        ry = cy % self.BLOCK_STRIDE
        on_x_street = rx < self.STREET_HALF or rx >= self.BLOCK_STRIDE - self.STREET_HALF
        on_y_street = ry < self.STREET_HALF or ry >= self.BLOCK_STRIDE - self.STREET_HALF
        if on_x_street or on_y_street:
            return 0
        # Building variant — deterministic per block
        bk = (cx // self.BLOCK_STRIDE, cy // self.BLOCK_STRIDE, self.seed)
        h = (hash(bk) & 0x7fffffff)
        # Pick variant per block (whole block same building type, mostly)
        variant = 1 + (h % 4)
        # Slight perturbation per cell so building has interior detail
        return variant

    def is_street(self, x, y):
        return self.get_cell(x, y) == 0

    def is_sidewalk(self, x, y):
        """Cells immediately adjacent to a street, but inside a building block."""
        if self.get_cell(x, y) == 0: return False
        cx = int(math.floor(x)); cy = int(math.floor(y))
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            if self.get_cell(cx+dx, cy+dy) == 0:
                return True
        return False


# =============================================================================
#  WALL TEXTURE — given (variant, u, v) return ASCII char + brightness
#  u: 0..1 horizontal across wall face
#  v: 0..1 vertical (0 = top of slice, 1 = bottom)
# =============================================================================

# Brightness ramp char sets (light → dark).
# We pick from these based on luminance × distance fog.
RAMP_LIGHT  = " .'`,-:;~+*=#%@█"
RAMP_DARK   = " .,:;-+=oOX#%@█"

# Window glyph set
GLYPH_WIN_LIT   = "▣"     # solid lit
GLYPH_WIN_DIM   = "▢"     # dim window
GLYPH_WIN_DARK  = "·"     # dark window
GLYPH_WIN_BLIND = "☰"     # closed blinds
GLYPH_BRICK_H   = "─"
GLYPH_BRICK_V   = "│"
GLYPH_DOOR      = "▮"
GLYPH_DOOR_TOP  = "▬"

def _hashf(*args):
    """Stable float in [0,1) from any args."""
    h = hash(args) & 0xffffffff
    return ((h * 2654435761) & 0xffffffff) / 4294967296.0

def wall_glyph(variant, u, v, world_x, world_y, fog):
    """
    Return (glyph_char, intensity 0..1) for a wall hit point.

    Buildings render as SOLID rectangular masses (█▓▒░ depending on fog)
    with crisp window cutouts punched into them. Lit windows survive fog
    longer than the surrounding wall body, which sells the night-city look.
    """
    # Window grid per variant (cols across × rows up the wall face)
    if variant == 1:        # brick lowrise — squat, mid-density windows
        cols, rows = 5, 9
        lit_chance = 0.30
    elif variant == 2:      # concrete tower — narrow tall openings
        cols, rows = 4, 16
        lit_chance = 0.42
    elif variant == 3:      # glass tower — dense grid, many lit
        cols, rows = 7, 18
        lit_chance = 0.55
    else:                   # office block
        cols, rows = 6, 12
        lit_chance = 0.35

    cu = int(u * cols)
    cv = int(v * rows)
    fu = (u * cols) - cu
    fv = (v * rows) - cv

    # Wider window cell margins so windows take up most of each cell, leaving
    # only a thin solid frame between them — buildings read as glassy blocks.
    in_window = (fu > 0.12 and fu < 0.88 and fv > 0.18 and fv < 0.82)

    # Door at the very bottom row, dead-center column
    is_door_row = (cv == rows - 1)
    door_col = cols // 2
    if is_door_row and cu == door_col and in_window:
        if fv > 0.28:
            return ('▮', max(0.55, 0.88 - fog * 0.4))
        return ('═', max(0.45, 0.75 - fog * 0.4))

    if not in_window:
        # SOLID building body — the squared, defined mass.
        # Distance fog steps the block density char down: █ → ▓ → ▒ → ░
        if fog < 0.22:
            return ('█', max(0.55, 0.95 - fog * 0.5))
        elif fog < 0.48:
            return ('▓', max(0.40, 0.78 - fog * 0.5))
        elif fog < 0.72:
            return ('▒', max(0.22, 0.55 - fog * 0.4))
        else:
            return ('░', max(0.10, 0.32 - fog * 0.3))

    # Window interior — deterministic lit/dark
    rseed = _hashf(world_x, world_y, cu, cv, variant)
    is_lit = rseed < lit_chance
    blinds = (rseed * 17.0) % 1.0 < 0.18

    if is_lit:
        intensity = max(0.55, 0.95 - fog * 0.30)
        if blinds:
            return (GLYPH_WIN_BLIND, intensity * 0.85)
        if (rseed * 13.0) % 1.0 < 0.40:
            return ('▣', intensity)              # solid lit cell
        return ('□', intensity * 0.92)           # outlined lit cell
    else:
        return ('·', max(0.10, 0.30 - fog * 0.3))


# =============================================================================
#  CAMERA / VEHICLE
# =============================================================================

class Camera:
    # Engine RPM model constants
    RPM_IDLE    = 1100.0
    RPM_REDLINE = 6800.0
    N_GEARS     = 6

    def __init__(self, x=6.5, y=6.5, angle=0.0):
        self.x = x; self.y = y
        self.angle = angle
        self.speed = 0.0           # forward velocity (cells/sec, signed)
        self.angular_v = 0.0       # rad/sec
        self.fov = math.pi / 2.6   # ~70°
        self.shake = 0.0           # offroad / hard-brake shake
        self.hp_y = 0.0            # head/cabin pitch from acceleration
        self.gear = 1
        self._idle_phase = 0.0
        self.MAX_FWD = 11.0
        self.MAX_REV = -3.5
        self.ACCEL   = 7.0
        self.BRAKE   = 14.0
        self.DRAG    = 1.6
        self.STEER   = 2.6

    @property
    def rpm(self):
        """Geared RPM curve: cycles through redline as gears change.
        Idle has a small wobble so the engine sounds 'alive' when stopped."""
        sf = max(0.0, self.speed) / self.MAX_FWD
        if sf < 0.0015:
            # Idling — natural breathing
            self._idle_phase += 0.06
            return self.RPM_IDLE + 60.0 * math.sin(self._idle_phase)
        gear = max(1, min(self.N_GEARS, 1 + int(sf * self.N_GEARS)))
        self.gear = gear
        gear_lo = (gear - 1) / self.N_GEARS
        gear_hi = gear / self.N_GEARS
        gear_t = (sf - gear_lo) / max(0.001, (gear_hi - gear_lo))
        return self.RPM_IDLE + (self.RPM_REDLINE - self.RPM_IDLE) * gear_t

    def update(self, dt, throttle, brake, steer, boost):
        # Throttle / brake
        max_fwd = self.MAX_FWD * (1.45 if boost else 1.0)
        if throttle > 0:
            head_room = max(0.0, 1.0 - self.speed / max_fwd) if self.speed > 0 else 1.0
            self.speed += self.ACCEL * throttle * head_room * dt * (1.5 if boost else 1.0)
        if brake > 0:
            if self.speed > 0:
                self.speed -= self.BRAKE * brake * dt
                if self.speed < 0: self.speed = max(self.speed, -0.5)
            else:
                self.speed -= self.ACCEL * 0.5 * brake * dt
                self.speed = max(self.speed, self.MAX_REV)
        if throttle == 0 and brake == 0:
            # Drag
            if self.speed > 0:
                self.speed = max(0.0, self.speed - self.DRAG * dt)
            else:
                self.speed = min(0.0, self.speed + self.DRAG * dt)
        self.speed = max(self.MAX_REV, min(max_fwd, self.speed))

        # Steering — authority drops at high speed
        speed_frac = abs(self.speed) / self.MAX_FWD
        authority = 0.55 + 0.45 * (1.0 - speed_frac * 0.5)
        self.angular_v = steer * self.STEER * authority * (0.4 + 0.6 * speed_frac if abs(self.speed) > 0.2 else 0.0)
        self.angle += self.angular_v * dt

        # Head pitch from acceleration (visual cabin lean)
        target_pitch = -0.15 if (throttle and self.speed > 0.5) else (0.20 if brake and self.speed > 0.5 else 0.0)
        self.hp_y += (target_pitch - self.hp_y) * min(1.0, 6.0 * dt)

    def step(self, dt, router):
        """Integrate position with collision."""
        dx = math.cos(self.angle) * self.speed * dt
        dy = math.sin(self.angle) * self.speed * dt
        # X axis collision
        nx = self.x + dx
        if router.get_cell(nx + (0.18 if dx > 0 else -0.18), self.y) == 0:
            self.x = nx
        else:
            self.shake = min(1.0, self.shake + 0.6)
            self.speed *= 0.4
        # Y axis collision
        ny = self.y + dy
        if router.get_cell(self.x, ny + (0.18 if dy > 0 else -0.18)) == 0:
            self.y = ny
        else:
            self.shake = min(1.0, self.shake + 0.6)
            self.speed *= 0.4
        # Decay shake
        self.shake *= max(0.0, 1.0 - 4.0 * dt)


# =============================================================================
#  (Sprite system removed — pure architectural rendering only.)
# =============================================================================


# =============================================================================
#  RENDERER — DDA raycaster + floor caster, ASCII output (no sprites)
# =============================================================================

# Brightness → glyph (light to dark). Used for distance shading of walls
# when no specific texture override applies.
def shade_char(intensity):
    """intensity 0..1 → ASCII char; high = █, low = space."""
    if intensity <= 0.04: return " "
    if intensity < 0.10:  return "."
    if intensity < 0.18:  return ":"
    if intensity < 0.28:  return "-"
    if intensity < 0.40:  return "+"
    if intensity < 0.55:  return "*"
    if intensity < 0.70:  return "o"
    if intensity < 0.82:  return "X"
    if intensity < 0.92:  return "#"
    return "█"


class Renderer:
    def __init__(self, W, H):
        self.W = W; self.H = H
        # Pre-allocate frame buffer as list of lists of chars
        self.zbuf = [9999.0] * W

    def render(self, cam, router):
        W = self.W; H = self.H
        half_h = H // 2
        # Cabin pitch shifts horizon
        horizon = half_h + int(cam.hp_y * H * 0.2)
        # Shake jitter
        sk = cam.shake
        sx_off = (random.randint(-1, 1) if sk > 0.3 else 0)
        sy_off = (random.randint(-1, 1) if sk > 0.3 else 0)

        buf = [[' '] * W for _ in range(H)]
        zbuf = [9999.0] * W

        # ── SKY (above horizon) ──
        # Phosphor-night gradient: dense stars at the top, fading toward the
        # horizon glow. Stars favor `*`, with `+` and `.` mixing in.
        for y in range(0, max(0, horizon)):
            t = y / max(1, horizon)
            density = 0.060 * (1.0 - t * 0.78)   # ~6% top, ~1% near horizon
            row = buf[y]
            for x in range(W):
                # Stars are stable-ish per (column, row, camera-bin) so they
                # don't strobe wildly while you turn — but they DO drift, the
                # way distant lights drift through your windshield.
                ang_band = (cam.angle + (x - W / 2) * 0.012) % TAU
                h = _hashf(x, y, int(ang_band * 80))
                if h < density:
                    if h < density * 0.25:
                        row[x] = '*'
                    elif h < density * 0.55:
                        row[x] = '+'
                    elif h < density * 0.80:
                        row[x] = '·'
                    else:
                        row[x] = '.'
            # Faint horizon haze
            if horizon > 1 and y == horizon - 1:
                for x in range(W):
                    if buf[y][x] == ' ':
                        buf[y][x] = '.'

        # ── WALL CAST (DDA per column) ──
        for col in range(W):
            cam_x = 2.0 * col / W - 1.0
            ray_a = cam.angle + math.atan(cam_x * math.tan(cam.fov / 2))
            rdx = math.cos(ray_a); rdy = math.sin(ray_a)

            # DDA
            mx = int(math.floor(cam.x))
            my = int(math.floor(cam.y))
            ddx = 1e30 if rdx == 0 else abs(1.0 / rdx)
            ddy = 1e30 if rdy == 0 else abs(1.0 / rdy)
            if rdx < 0:
                step_x = -1; sdx = (cam.x - mx) * ddx
            else:
                step_x =  1; sdx = (mx + 1 - cam.x) * ddx
            if rdy < 0:
                step_y = -1; sdy = (cam.y - my) * ddy
            else:
                step_y =  1; sdy = (my + 1 - cam.y) * ddy

            hit = 0; side = 0; variant = 0
            for _ in range(64):
                if sdx < sdy:
                    sdx += ddx; mx += step_x; side = 0
                else:
                    sdy += ddy; my += step_y; side = 1
                v = router.get_cell(mx, my)
                if v > 0:
                    hit = 1; variant = v; break
            if not hit:
                zbuf[col] = 9999.0
                continue

            if side == 0:
                dist = (sdx - ddx)
                wall_x = cam.y + dist * rdy
            else:
                dist = (sdy - ddy)
                wall_x = cam.x + dist * rdx
            wall_x -= math.floor(wall_x)
            # Fish-eye correction
            corr = dist * math.cos(ray_a - cam.angle)
            if corr < 0.001: corr = 0.001
            zbuf[col] = corr

            line_h = max(1, int(H / corr))
            draw_start = max(0, horizon - line_h // 2)
            draw_end   = min(H - 1, horizon + line_h // 2)

            # Distance fog 0..1
            fog = min(1.0, corr / 22.0)

            # World coords for the hit (used for window-grid hashing so each
            # wall slice is stable per cell — windows don't shimmer as you move)
            world_x = mx; world_y = my

            for y in range(draw_start, draw_end + 1):
                v = (y - (horizon - line_h // 2)) / max(1, line_h)
                v = min(0.999, max(0.0, v))
                glyph, intensity = wall_glyph(variant, wall_x, v, world_x, world_y, fog)
                # Side darkening (cheap fake light: y-side dimmer)
                if side == 1:
                    intensity *= 0.78
                # If the texture returned a specific glyph, draw it directly
                # but only if intensity threshold met given fog
                if intensity < 0.06:
                    continue
                # At extreme fog, replace lit windows with '.' to keep readable
                if fog > 0.85 and glyph in (GLYPH_WIN_LIT, "□", GLYPH_WIN_BLIND):
                    glyph = "·"
                buf[y][col] = glyph

        # ── FLOOR CAST (road surface, lane lines) ──
        # Per-row floor casting from horizon down to bottom of screen
        for y in range(horizon + 1, H):
            p = y - horizon
            # Camera height = 0.5 cells; project floor distance for this row
            row_dist = (0.5 * H) / max(1, p)
            if row_dist > 30.0: continue
            # Compute world step per column using leftmost & rightmost ray
            left_a  = cam.angle - cam.fov / 2
            right_a = cam.angle + cam.fov / 2
            ldx = math.cos(left_a) * row_dist
            ldy = math.sin(left_a) * row_dist
            rdx = math.cos(right_a) * row_dist
            rdy = math.sin(right_a) * row_dist
            sx = (rdx - ldx) / W
            sy = (rdy - ldy) / W
            fx = cam.x + ldx
            fy = cam.y + ldy
            # Brightness with distance
            fog_f = min(1.0, row_dist / 22.0)
            for x in range(W):
                # Are we on a street?
                cellv = router.get_cell(fx, fy)
                if cellv != 0:
                    fx += sx; fy += sy; continue
                # Local coords inside cell
                u = fx - math.floor(fx)
                vv = fy - math.floor(fy)
                stride = router.BLOCK_STRIDE
                rx = int(math.floor(fx)) % stride
                ry = int(math.floor(fy)) % stride

                # Lane stripes:
                #   Streets are 2 cells wide. The center-line runs along the
                #   middle seam between the two street cells (rx in {0,1} side
                #   from the edge or {stride-2, stride-1}).
                # Determine if this is an N-S street (drivable along Y) or E-W.
                is_x_street = (rx < router.STREET_HALF or rx >= stride - router.STREET_HALF)
                is_y_street = (ry < router.STREET_HALF or ry >= stride - router.STREET_HALF)

                ch = ' '
                inten = max(0.05, 0.32 - fog_f * 0.28)

                if is_x_street and is_y_street:
                    # Intersection — crosswalk stripes
                    # Diagonal stripe pattern
                    cw_u = u
                    cw_v = vv
                    if (int(cw_u * 6) + int(cw_v * 6)) % 2 == 0:
                        ch = '─' if int(cw_v * 4) % 2 == 0 else ' '
                        inten = max(0.18, 0.48 - fog_f * 0.4)
                    else:
                        # Asphalt grit
                        h = _hashf(int(fx*8), int(fy*8))
                        if h < 0.05:
                            ch = '.'
                elif is_x_street:
                    # N-S street: lane stripes along Y axis
                    # Center-line: at rx == STREET_HALF-1 with u near 1.0, OR rx==stride-STREET_HALF with u near 0.0
                    # Simpler: distance from the line between the two street-cells
                    if rx == router.STREET_HALF - 1:
                        # right edge of this cell is the center line of the street
                        if u > 0.92:
                            # dashed — only paint when vv segment is even
                            seg = int(fy * 0.6) % 2
                            if seg == 0:
                                ch = '|'
                                inten = max(0.40, 0.85 - fog_f * 0.5)
                    elif rx == stride - router.STREET_HALF:
                        if u < 0.08:
                            seg = int(fy * 0.6) % 2
                            if seg == 0:
                                ch = '|'
                                inten = max(0.40, 0.85 - fog_f * 0.5)
                    # Curb edges (outer boundaries of street)
                    if rx == 0 and u < 0.10:
                        ch = '│'
                        inten = max(0.30, 0.60 - fog_f * 0.4)
                    if rx == stride - 1 and u > 0.90:
                        ch = '│'
                        inten = max(0.30, 0.60 - fog_f * 0.4)
                    # Faint asphalt grain
                    if ch == ' ':
                        h = _hashf(int(fx*7), int(fy*7), "asph")
                        if h < 0.04:
                            ch = '.'
                elif is_y_street:
                    # E-W street: lane stripes along X axis
                    if ry == router.STREET_HALF - 1:
                        if vv > 0.92:
                            seg = int(fx * 0.6) % 2
                            if seg == 0:
                                ch = '-'
                                inten = max(0.40, 0.85 - fog_f * 0.5)
                    elif ry == stride - router.STREET_HALF:
                        if vv < 0.08:
                            seg = int(fx * 0.6) % 2
                            if seg == 0:
                                ch = '-'
                                inten = max(0.40, 0.85 - fog_f * 0.5)
                    if ry == 0 and vv < 0.10:
                        ch = '─'
                        inten = max(0.30, 0.60 - fog_f * 0.4)
                    if ry == stride - 1 and vv > 0.90:
                        ch = '─'
                        inten = max(0.30, 0.60 - fog_f * 0.4)
                    if ch == ' ':
                        h = _hashf(int(fx*7), int(fy*7), "asph")
                        if h < 0.04:
                            ch = '.'

                if ch != ' ' and buf[y][x] == ' ':
                    buf[y][x] = ch
                fx += sx; fy += sy

        # ── Apply shake jitter (off-road bumps) ──
        if sk > 0.3 and (sx_off or sy_off):
            new_buf = [[' '] * W for _ in range(H)]
            for y in range(H):
                for x in range(W):
                    nx = x + sx_off; ny = y + sy_off
                    if 0 <= nx < W and 0 <= ny < H:
                        new_buf[ny][nx] = buf[y][x]
            buf = new_buf

        return buf


# =============================================================================
#  HUD — minimal: speed, heading, position
# =============================================================================

def render_hud(buf, cam, fps):
    W = len(buf[0]); H = len(buf)
    # Speed in km/h-ish
    kph = abs(cam.speed) * 18
    spd_str  = f"  SPD {int(kph):3d} km/h"
    head_deg = (math.degrees(cam.angle) % 360 + 360) % 360
    head_str = f"  HDG {int(head_deg):03d}°"
    pos_str  = f"  X {int(cam.x):+05d}  Y {int(cam.y):+05d}"
    fps_str  = f"  {int(fps):3d} fps  "

    # Top bar
    title = "PHOS CITY · v" + VERSION
    line  = title + " " * (W - len(title) - len(fps_str)) + fps_str
    for x in range(min(W, len(line))):
        buf[0][x] = line[x]
    # Bottom bar
    bot = spd_str + head_str + pos_str
    bot = bot + " " * (W - len(bot))
    bot = bot[:W]
    for x in range(W):
        buf[H - 1][x] = bot[x]

    # Speed bar (under top)
    bar_w = 32
    fill = int(bar_w * min(1.0, abs(cam.speed) / cam.MAX_FWD))
    for i in range(bar_w):
        buf[1][2 + i] = '█' if i < fill else '░'
    # Center reticle (very faint)
    cx = W // 2; cy = H // 2
    if buf[cy][cx] == ' ': buf[cy][cx] = '·'


# =============================================================================
#  INPUT
# =============================================================================

class Input:
    def __init__(self, root):
        self.keys = set()
        root.bind('<KeyPress>',   lambda e: self.keys.add(e.keysym.lower()))
        root.bind('<KeyRelease>', lambda e: self.keys.discard(e.keysym.lower()))
        root.focus_set()

    def held(self, *names):
        return any(n in self.keys for n in names)


# =============================================================================
#  GAME — purely GFX processing loop
# =============================================================================

class PhosCity:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PHOS CITY")
        self.root.configure(bg="black")
        self.root.geometry(f"{W*8 + 20}x{H*16 + 20}")
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        # Phosphor white on black, monospace
        self.lbl = tk.Label(
            self.root, text="", font=("Courier New", 11),
            fg="#E8E8E8", bg="black", justify="left", anchor="nw"
        )
        self.lbl.pack(fill="both", expand=True)

        self.input = Input(self.root)
        self.root.bind("<Escape>", lambda e: self.quit())
        self.root.bind("m",        lambda e: self._toggle_audio())
        self.root.bind("M",        lambda e: self._toggle_audio())
        self.root.bind("r",        lambda e: self._respawn())
        self.root.bind("R",        lambda e: self._respawn())

        seed = random.randint(0, 1 << 30)
        self.router = CityRouter(seed=seed)
        # Spawn the camera at the center of an N-S street, facing +Y (down street)
        # Find the nearest street cell to (0,0)
        cx, cy = self._find_street_spawn()
        self.cam = Camera(x=cx, y=cy, angle=math.pi / 2)  # facing +y
        self.renderer = Renderer(W, H)

        # Last-input snapshot, read by the audio thread (separate thread).
        # Floats are written atomically in CPython so no lock needed for these.
        self._last_throttle = 0.0
        self._last_brake    = 0.0
        self._last_steer    = 0.0

        self.engine = EngineEngine(state_provider=self._audio_state)
        self.engine.start()

        self.ambient = AmbientEngine()
        self.ambient.start()

        self.running = True
        self._last = time.time()
        self._fps = 30.0
        self._fps_smooth = 30.0

    def _audio_state(self):
        sf = max(0.0, abs(self.cam.speed) / self.cam.MAX_FWD)
        return {
            'rpm':        self.cam.rpm,
            'throttle':   self._last_throttle,
            'brake':      self._last_brake,
            'speed_frac': sf,
            'steer':      self._last_steer,
        }

    def _find_street_spawn(self):
        # Search outward from origin
        for r in range(0, 30):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if abs(dx) != r and abs(dy) != r and r > 0: continue
                    if self.router.get_cell(dx, dy) == 0:
                        return (dx + 0.5, dy + 0.5)
        return (0.5, 0.5)

    def _respawn(self):
        cx, cy = self._find_street_spawn()
        self.cam.x = cx; self.cam.y = cy
        self.cam.speed = 0.0
        self.cam.angular_v = 0.0

    def _toggle_audio(self):
        self.ambient.toggle()
        self.engine.toggle()

    def loop(self):
        if not self.running:
            return
        now = time.time()
        dt = min(0.066, now - self._last)
        self._last = now
        if dt > 0:
            inst_fps = 1.0 / dt
            self._fps_smooth = 0.9 * self._fps_smooth + 0.1 * inst_fps

        # Input → controls
        throttle = 1.0 if self.input.held('w', 'up') else 0.0
        brake    = 1.0 if self.input.held('s', 'down') else 0.0
        steer    = 0.0
        if self.input.held('a', 'left'):  steer -= 1.0
        if self.input.held('d', 'right'): steer += 1.0
        boost    = self.input.held('shift_l', 'shift_r', 'shift')

        # Boosted throttle pushes the engine into ROAR territory in the audio
        audio_throttle = throttle * (1.45 if boost and throttle > 0 else 1.0)
        if audio_throttle > 1.0: audio_throttle = 1.0
        self._last_throttle = audio_throttle
        self._last_brake    = brake
        self._last_steer    = steer

        self.cam.update(dt, throttle, brake, steer, boost)
        self.cam.step(dt, self.router)

        # Render
        buf = self.renderer.render(self.cam, self.router)
        render_hud(buf, self.cam, self._fps_smooth)

        # Flatten → tk text
        text = "\n".join("".join(row) for row in buf)
        self.lbl.config(text=text)

        # ~30 fps target (tkinter is the bottleneck regardless)
        self.root.after(33, self.loop)

    def quit(self):
        self.running = False
        try:
            self.engine.stop()
        except Exception:
            pass
        try:
            self.ambient.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.loop()
        self.root.mainloop()


def main():
    print("PHOS CITY — synthesizing city... (first frame can take a moment)")
    g = PhosCity()
    g.run()


if __name__ == "__main__":
    main()


