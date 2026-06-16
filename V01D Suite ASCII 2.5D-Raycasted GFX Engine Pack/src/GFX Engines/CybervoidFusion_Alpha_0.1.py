#!/usr/bin/env python3
# =============================================================================
#  V O I D   E N G I N E   v2.1 — CONFUSION PROTOCOL
#  "THE VOID DEPTHS — DIMENSIONAL ANOMALIES"
#
#  Pure Python 3 + tkinter stdlib ONLY. Zero external dependencies.
#  Single file. Self-contained. Runs forever. Eats itself and grows.
#
#  WASD = move  |  LEFT/RIGHT arrows = turn  |  SPACE/LMB = fire CONFUSION EMITTER
#  V = jump (float up / transformer KLANNNG down — NO BOB AIRBORNE)
#  SHIFT = sprint  |  M = meta-difficulty  |  ESC = quit
#  POWERUPS: > SPEED x2  |  ~ SLOW TIME  |  ! RAPID FIRE  (10s each)
#
#  ARCHITECTURE:
#    • DDA raycaster  — infinite procedural world
#    • Sine-synthesis TTS — announcer voice (no external deps)
#    • WAV PCM audio  — gun CRACK/THWACK, bass drones, ambient pads
#    • Schroeder reverb engine — spatial SFX with wall-proximity detection
#    • BassRumbleEngine — always-on sub-bass ground presence (18-42 Hz)
#    • AmbientEngine — generative pads + metal pings, void hums, wind, groans
#    • aplay/afplay/winsound playback via subprocess
#    • Procedural sprite, name, dialogue, scenario generators
#    • Weapon overheat + cooldown system
#    • Adaptive difficulty (meta-improvement loop)
#    • Particle system (sparks, blood, smoke)
#    • Mission system (kill/key/portal)
#    • Minimap + compass HUD
#    • 4 infinite world stages
# =============================================================================

import tkinter as tk
import math, random, time, sys, os, threading, io, wave, struct, subprocess
from pathlib import Path

VERSION  = "2.1.0"
W, H     = 140, 44        # render columns x rows
SR       = 22050           # audio sample rate
TAU      = math.tau
INV_SR   = 1.0 / SR

# =============================================================================
#  ONOMATOPOEIA DATABASE — gun crack / impact words
# =============================================================================
EMITTER_WORDS = [
    "EMIT","PULSE","HUM","FLUX","WAVE","RESONANCE","PHASE SHIFT","SCATTER",
    "RIPPLE","BLUR","DISTORT","WARP","CONFUSE","DAZE","MUDDLE","BEFUDDLE",
]
HIT_WORDS  = ["SPLAT","THUD","CHUNK","SQUELCH","REND","GORE","IMPACT","CLEAVE"]
KILL_WORDS = ["TERMINATED","OBLITERATED","VAPORIZED","ERASED","NULLIFIED",
              "DISPATCHED","ELIMINATED","PURGED","ANNIHILATED","DELETED"]
LAND_WORDS = ["K-KLANNNG","THOOM","KRAKOOOM","WHUMPH","B-DONNNG","CRANNNG","CHONK","SKHRRRANG","SLAMM","GRRRONK","KAHCHUNNK","BRANNNG","DOOMPH","KRASSH","GONNNG"]
MEDITATION_MESSAGES = [
    "Thank you",
    "I'm finally free",
    "I feel pure peace",
    "I find stillness",
    "We see what's been missing",
    "[entering meditative state]",
]

# =============================================================================
#  PURE-PYTHON WAV SYNTHESIS ENGINE (zero deps, stdlib only)
# =============================================================================

def _clamp(x, lo=-1.0, hi=1.0):
    return lo if x < lo else (hi if x > hi else x)

def _soft_clip(x, drive=1.15):
    d = math.tanh(drive)
    return math.tanh(x * drive) / d if d else x

def _exp(t, rate): return math.exp(-t * rate)

def _samples(dur): return int(SR * dur)

def _to_wav(samples):
    """Convert float list [-1,1] to 16-bit mono WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        raw = bytearray()
        for s in samples:
            v = int(_clamp(s) * 32767)
            raw += struct.pack('<h', v)
        w.writeframes(bytes(raw))
    return buf.getvalue()

def _to_wav_stereo(L, R):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        raw = bytearray()
        for l, r in zip(L, R):
            raw += struct.pack('<hh', int(_clamp(l)*32767), int(_clamp(r)*32767))
        w.writeframes(bytes(raw))
    return buf.getvalue()

def _play_async(wav_bytes):
    """Fire-and-forget audio playback via system player."""
    def _go():
        try:
            p = sys.platform
            if p == 'darwin':
                proc = subprocess.Popen(['afplay','-'], stdin=subprocess.PIPE,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc.communicate(wav_bytes)
            elif 'linux' in p:
                proc = subprocess.Popen(
                    ['aplay','-q','-r',str(SR),'-f','S16_LE','-c','1','-'],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc.communicate(wav_bytes)
            else:
                import tempfile, winsound
                fd, nm = tempfile.mkstemp('.wav')
                os.close(fd)
                open(nm,'wb').write(wav_bytes)
                winsound.PlaySound(nm, winsound.SND_FILENAME)
                os.unlink(nm)
        except Exception:
            pass
    threading.Thread(target=_go, daemon=True).start()

# =============================================================================
#  REVERB + SPATIAL AUDIO ENGINE  (pure Python, zero deps)
#  Schroeder allpass + comb reverb, distance attenuation, echo delay
# =============================================================================

def _apply_reverb(samples, room=0.55, damp=0.4, wet=0.32, pre_delay_ms=12.0):
    """
    Schroeder-style reverb: 4 comb filters + 2 allpass.
    room  : 0.0 (dead) – 1.0 (huge hall)
    damp  : 0.0 (bright) – 1.0 (dark/muffled)
    wet   : dry/wet mix (0 = dry, 1 = full wet)
    pre_delay_ms : pre-delay in milliseconds (simulates distance to first reflection)
    """
    n = len(samples)
    if n == 0 or wet <= 0:
        return samples

    # Comb filter delays (prime-ish sample offsets, scaled by room)
    comb_delays = [int(SR * d * (0.6 + room * 0.4))
                   for d in [0.0297, 0.0371, 0.0411, 0.0437]]
    comb_feeds  = [0.805 + room * 0.14] * 4
    damp_f      = damp * 0.4           # LP coefficient

    # Allpass delays
    ap_delays = [int(SR * d) for d in [0.0050, 0.0017]]

    # Pre-delay buffer
    pre_n   = max(1, int(SR * pre_delay_ms * 0.001))
    pre_buf = [0.0] * pre_n
    pre_idx = 0

    # Comb buffers
    cb = [[0.0] * max(1, d) for d in comb_delays]
    ci = [0] * 4
    lp = [0.0] * 4   # LP state per comb

    # Allpass buffers
    ab = [[0.0] * max(1, d) for d in ap_delays]
    ai = [0, 0]

    out = [0.0] * n
    for i in range(n):
        # pre-delay
        x = pre_buf[pre_idx]
        pre_buf[pre_idx] = samples[i]
        pre_idx = (pre_idx + 1) % pre_n

        # 4 parallel comb filters
        rev = 0.0
        for k in range(4):
            d  = comb_delays[k]
            fb = comb_feeds[k]
            buf= cb[k]; idx= ci[k]
            y  = buf[idx]
            # LP damping
            lp[k] = y * (1 - damp_f) + lp[k] * damp_f
            buf[idx] = x + lp[k] * fb
            ci[k] = (idx + 1) % d
            rev  += y
        rev *= 0.25

        # 2 series allpass
        for k in range(2):
            d   = ap_delays[k]
            buf = ab[k]; idx = ai[k]
            bv  = buf[idx]
            buf[idx] = rev + bv * 0.5
            ai[k] = (idx + 1) % d
            rev  = bv - rev * 0.5

        out[i] = _clamp(samples[i] * (1.0 - wet) + rev * wet)
    return out

def _apply_echo(samples, delay_ms=180.0, feedback=0.38, wet=0.28):
    """Simple tape-echo delay."""
    n = len(samples)
    delay_smp = max(1, int(SR * delay_ms * 0.001))
    buf = [0.0] * delay_smp
    idx = 0
    out = [0.0] * n
    for i in range(n):
        d = buf[idx]
        buf[idx] = _clamp(samples[i] + d * feedback)
        idx = (idx + 1) % delay_smp
        out[i] = _clamp(samples[i] * (1.0 - wet) + d * wet)
    return out

def _wav_to_samples(wav_bytes):
    """Decode mono 16-bit WAV bytes → float list."""
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, 'rb') as w:
        raw = w.readframes(w.getnframes())
    return [struct.unpack_from('<h', raw, i*2)[0] / 32767.0
            for i in range(len(raw)//2)]

def _samples_to_wav(samples):
    return _to_wav(samples)

def apply_spatial_sfx(wav_bytes, dist=1.0, wall_proximity=0.0):
    """
    Apply distance attenuation + context-aware reverb to a WAV.
    dist          : distance to source (world units, 1-20)
    wall_proximity: 0.0=open / 1.0=tight enclosed space
    Returns new WAV bytes with reverb/echo baked in.
    """
    smp = _wav_to_samples(wav_bytes)
    if not smp:
        return wav_bytes

    # Distance attenuation
    atten = min(1.0, 1.0 / max(0.3, dist * 0.18))

    # Room parameters from wall proximity
    room  = 0.25 + wall_proximity * 0.65     # 0.25 open → 0.90 enclosed
    damp  = 0.55 - wall_proximity * 0.20     # brighter in open spaces
    wet   = 0.18 + wall_proximity * 0.38     # more wet when enclosed
    pre_d = max(2.0, (1.0 - wall_proximity) * 22.0 + dist * 4.0)  # ms

    smp = [s * atten for s in smp]
    smp = _apply_reverb(smp, room=room, damp=damp, wet=wet, pre_delay_ms=pre_d)

    # Echo tail for large open spaces (outdoor/wastes feel)
    if wall_proximity < 0.3:
        echo_wet = (0.3 - wall_proximity) * 0.6
        smp = _apply_echo(smp, delay_ms=220.0, feedback=0.30, wet=echo_wet)

    return _samples_to_wav(smp)


def synth_gun_crack():
    """Emitter: High-pitched sweeping whoosh in repeating bursts."""
    n = _samples(0.15)  # Short burst duration
    out = []
    rng = random.Random(random.randint(0, 9999))
    
    for i in range(n):
        t = i * INV_SR
        
        # FREQUENCY SWEEP: High-pitched whoosh
        # Sweep from 1200 Hz down to 600 Hz (fast downward sweep)
        start_freq = 1200.0
        end_freq = 600.0
        sweep_freq = start_freq + (end_freq - start_freq) * (t / 0.15)
        
        # Main tone: Sweeping frequency
        whoosh = math.sin(TAU * sweep_freq * t) * 0.7
        
        # Harmonic layers for richness
        harmonic1 = math.sin(TAU * sweep_freq * 0.5 * t) * 0.2  # Sub-harmonic
        harmonic2 = math.sin(TAU * sweep_freq * 1.5 * t) * 0.15  # Upper harmonic
        
        # Envelope: Sharp attack, smooth decay
        envelope = 1.0 - (t / 0.15)  # Linear fade out
        
        # Combine all elements
        signal = whoosh + harmonic1 + harmonic2
        
        # Apply envelope
        final = signal * envelope * 0.5
        
        out.append(_clamp(final))
    
    return _to_wav(out)



def synth_hit():
    """Wet thud on enemy impact."""
    n   = _samples(0.18)
    out = []
    rng = random.Random(42)
    for i in range(n):
        t   = i * INV_SR
        low = math.sin(TAU * 80.0 * t) * _exp(t, 28.0)
        mid = math.sin(TAU * 340.0 * t) * _exp(t, 45.0) * 0.4
        nz  = (rng.random()*2-1) * _exp(t, 35.0) * 0.5
        out.append(_soft_clip(low + mid + nz, 1.2))
    return _to_wav(out)

def synth_kill():
    """Satisfying kill - low boom + hi sparkle."""
    n   = _samples(0.35)
    out = []
    for i in range(n):
        t   = i * INV_SR
        boom = math.sin(TAU*(45+100*_exp(t,14))*t)*_exp(t,7.0)
        snap = math.sin(TAU*1200*t)*_exp(t,40)*0.3
        out.append(_soft_clip(boom + snap, 1.25))
    return _to_wav(out)

def synth_overheat():
    """Emitter overload: deep void resonance with harmonic decay."""
    n   = _samples(0.6)
    out = []
    for i in range(n):
        t   = i * INV_SR
        
        # Main static hum - low frequency drone
        hum_freq = 55 + 25 * math.sin(TAU * 0.5 * t)  # Modulating 55-80 Hz
        hum = math.sin(TAU * hum_freq * t) * 0.4
        
        # Static/noise layer
        static = (random.random() * 2 - 1) * 0.3 * (1 - t/0.6)
        
        # Ocean waves - multiple sine waves at different frequencies
        wave1 = math.sin(TAU * 0.8 * t) * 0.15  # Slow wave motion
        wave2 = math.sin(TAU * 1.3 * t) * 0.1   # Secondary wave
        wave3 = math.sin(TAU * 2.1 * t) * 0.08  # Tertiary ripple
        
        # Combine with envelope
        amplitude = 1.0 - (t / 0.6) ** 0.5  # Fade out
        v = (hum + static + wave1 + wave2 + wave3) * amplitude * 0.7
        
        out.append(_clamp(v))
    return _to_wav(out)

def synth_portal():
    """Portal whoosh sweep."""
    n   = _samples(0.8)
    out = []
    for i in range(n):
        t  = i * INV_SR
        f  = 80 + 400 * math.sin(TAU * 0.8 * t)
        v  = math.sin(TAU * f * t) * _exp(t, 2.5) * 0.5
        v += math.sin(TAU * f * 2 * t) * _exp(t, 4.0) * 0.25
        v += (random.random()*2-1) * 0.08
        out.append(_clamp(v * 0.7))
    return _to_wav(out)

def synth_step():
    """Footstep thud."""
    n   = _samples(0.14)
    out = []
    for i in range(n):
        t   = i * INV_SR
        f   = 65 + 120 * _exp(t, 28)
        v   = math.sin(TAU * f * t) * _exp(t, 18)
        v  += (random.random()*2-1) * _exp(t, 50) * 0.3
        out.append(_clamp(v * 0.6))
    return _to_wav(out)

def synth_land_clank():
    """Heavy transformer-style metal landing impact — clanking, ground-shaking."""
    n   = _samples(0.9)
    out = []
    rng = random.Random(77)
    for i in range(n):
        t = i * INV_SR
        # Deep sub-bass ground thud — earth shaking
        thud  = math.sin(TAU * (38 + 60*_exp(t, 12)) * t) * _exp(t, 4.5) * 0.9
        # Metal clank — high transient metallic ring
        clank = math.sin(TAU * 820 * t) * _exp(t, 28) * 0.55
        clank2= math.sin(TAU * 1640 * t) * _exp(t, 42) * 0.28
        # Heavy gear/chassis resonance
        mech  = math.sin(TAU * 210 * t) * _exp(t, 14) * 0.42
        mech2 = math.sin(TAU * 310 * t) * _exp(t, 20) * 0.22
        # Debris rattle
        rattle= (rng.random()*2-1) * _exp(t, 18) * 0.32
        # Secondary bounce clank (transformer weight settling)
        t2    = max(0, t - 0.18)
        bounce= math.sin(TAU * 560 * t2) * _exp(t2, 35) * 0.30 * (1.0 if t >= 0.18 else 0.0)
        raw   = thud + clank + clank2 + mech + mech2 + rattle + bounce
        out.append(_soft_clip(raw * 1.5, 1.4))
    return _to_wav(out)

def synth_jump_whoosh():
    """Short rising whoosh on jump launch — air-displacement burst."""
    n   = _samples(0.28)
    out = []
    rng = random.Random(13)
    for i in range(n):
        t   = i * INV_SR
        prog = t / 0.28                     # 0→1 over clip duration
        # Rising frequency sweep: 80 Hz → 420 Hz
        freq = 80.0 + 340.0 * prog
        phase_acc = TAU * freq * t
        tone  = math.sin(phase_acc) * (1.0 - prog) * 0.45
        # White noise burst, heavy at transient, fades fast
        noise = (rng.random()*2-1) * _exp(t, 14.0) * 0.55
        # Sub thump at launch moment
        thump = math.sin(TAU * 55 * t) * _exp(t, 22.0) * 0.6
        raw   = tone + noise + thump
        out.append(_soft_clip(raw * 1.3, 1.2))
    return _to_wav(out)


def synth_death():
    """Player death — descending moan."""
    n   = _samples(1.2)
    out = []
    for i in range(n):
        t   = i * INV_SR
        f   = 220 * (1 - 0.6*(t/1.2))
        v   = math.sin(TAU * f * t) * _exp(t, 2.0) * 0.5
        v  += math.sin(TAU * f*1.5 * t) * _exp(t, 3.0) * 0.25
        v  += (random.random()*2-1) * _exp(t, 8) * 0.15
        out.append(_clamp(v))
    return _to_wav(out)

# ── BASS DRONE ENGINE ──────────────────────────────────────────────────────
def synth_bass_drone(dur=8.0, seed=None):
    """Long low rumbling bass drone with slow LFO modulation — stereo."""
    rng = random.Random(seed or random.randint(0, 99999))
    n   = _samples(dur)
    L   = [0.0] * n
    R   = [0.0] * n

    root = rng.uniform(28, 52)   # very low root freq
    harmonics = [
        (1.0,   0.55, rng.uniform(0.03,0.12)),
        (2.0,   0.28, rng.uniform(0.05,0.18)),
        (3.0,   0.12, rng.uniform(0.07,0.22)),
        (0.5,   0.35, rng.uniform(0.02,0.07)),   # sub-octave
        (1.498, 0.08, rng.uniform(0.04,0.15)),   # fifth
    ]

    lfo_rate = rng.uniform(0.04, 0.14)
    lfo_depth = rng.uniform(0.12, 0.38)
    lfo_phase = rng.uniform(0, TAU)

    # fade in/out
    fade_s = int(SR * min(2.0, dur*0.18))
    fade_e = int(SR * min(2.0, dur*0.18))

    for i in range(n):
        t   = i * INV_SR
        lfo = 1.0 + lfo_depth * math.sin(lfo_rate * TAU * t + lfo_phase)
        # brown noise undertow
        nz  = rng.gauss(0, 0.012)
        s   = 0.0
        for harm, amp, detune in harmonics:
            f = root * harm * (1 + detune * math.sin(TAU * lfo_rate * 0.37 * t))
            s += math.sin(TAU * f * t) * amp
        s   = _soft_clip(s * lfo * 0.28 + nz, 1.08)
        # stereo width
        pan = math.sin(TAU * 0.07 * t) * 0.3
        L[i] = s * (0.7 + pan)
        R[i] = s * (0.7 - pan)

    # apply fade envelope
    for i in range(min(fade_s, n)):
        f = i / fade_s
        L[i] *= f; R[i] *= f
    for i in range(max(0, n - fade_e), n):
        f = (n - 1 - i) / max(fade_e, 1)
        L[i] *= f; R[i] *= f

    return _to_wav_stereo(L, R)

def synth_ambient_pad(dur=10.0, seed=None, mode="dungeon"):
    """Floating ambient pad — layered sines with slow evolution."""
    rng  = random.Random(seed or random.randint(0, 99999))
    n    = _samples(dur)
    out  = [0.0] * n

    # Mode-dependent root
    roots = {"dungeon": 55, "wastes": 41, "arena": 73, "sanctum": 49}
    root  = roots.get(mode, 55) * rng.uniform(0.96, 1.04)

    # 5-7 floating voices
    voices = []
    for _ in range(rng.randint(5, 7)):
        interval = rng.choice([1.0, 1.1892, 1.3348, 1.4983, 1.6818, 2.0, 0.5])
        freq     = root * interval * rng.uniform(0.98, 1.02)
        amp      = rng.uniform(0.04, 0.11)
        phase    = rng.uniform(0, TAU)
        lfo_r    = rng.uniform(0.02, 0.09)
        lfo_d    = rng.uniform(0.08, 0.28)
        voices.append((freq, amp, phase, lfo_r, lfo_d))

    fade_s = int(SR * min(3.0, dur*0.2))
    fade_e = int(SR * min(3.0, dur*0.2))

    for i in range(n):
        t = i * INV_SR
        s = 0.0
        for freq, amp, ph0, lfo_r, lfo_d in voices:
            lfo = 1.0 + lfo_d * math.sin(TAU * lfo_r * t)
            s  += math.sin(TAU * freq * t + ph0) * amp * lfo
        out[i] = _soft_clip(s, 1.05)

    for i in range(min(fade_s, n)):
        out[i] *= i / fade_s
    for i in range(max(0, n-fade_e), n):
        out[i] *= (n - 1 - i) / max(fade_e, 1)

    return _to_wav(out)

# ── SINE-SYNTH TTS ANNOUNCER v3 ─────────────────────────────────────────────
#   Intelligible English formant voice. Pure math, zero deps.
#   Uses: glottal pulse source (sawtooth+noise) → three formant resonators
#   + proper diphone table, pitch contour, coarticulation blending.
# ─────────────────────────────────────────────────────────────────────────────

# Formant table: (F1, F2, F3, voiced, dur_ms)
# Vowels — IPA-accurate formant centers
_PH = {
    'aa':(800,1200,2600,True, 95),  # "sta-Y"    STAY
    'ae':(660,1700,2500,True, 90),  # "ALERT"    æ
    'ah':(700,1200,2600,True, 85),  # schwa/uh
    'ay':(390,2000,2800,True,100),  # "stAY"
    'eh':(530,1840,2480,True, 80),  # "alErt"    ɛ
    'er':(490, 900,2200,True, 90),  # "alERt"    rhotacized
    'ih':(390,1990,2550,True, 70),  # "alIve"    ɪ
    'iy':(270,2290,3010,True, 75),  # "alIVE" ee
    'ow':(570, 840,2410,True, 90),  # "ALERT" ow
    'uw':(300, 870,2240,True, 80),  # "ALErt" oo
    # Consonants voiced
    'b' :(200, 800,2200,True, 55),
    'd' :(300,1700,2600,True, 55),
    'dh':(280,1400,2200,True, 60),  # "the"
    'g' :(200,1000,2200,True, 55),
    'l' :(360,1100,2800,True, 65),
    'm' :(280,1000,2200,True, 70),
    'n' :(280,1500,2500,True, 65),
    'r' :(430, 980,1500,True, 70),
    'v' :(240,3800,6000,True, 60),  # voiced fricative
    'w' :(290, 610,2150,True, 65),
    'y' :(260,2100,3000,True, 55),
    'z' :(240,4200,7000,True, 60),
    # Consonants unvoiced
    'f' :(  0,4000,6500,False,55),
    'h' :(  0,1200,3500,False,50),
    'k' :(  0,1200,2600,False,50),
    'p' :(  0, 800,1800,False,45),
    's' :(  0,4500,7200,False,65),
    'sh':(  0,2400,4800,False,65),
    't' :(  0,1600,3200,False,50),
    'th':(  0,1600,6000,False,55),
    # Silence
    'sil':(0,  0,  0,False,45),
}

# Diphone pronunciation dict — key words the game actually says
_WORD_PHONES = {
    'STAY':   ['s','t','ay'],
    'ALERT':  ['ae','l','er','t'],
    'ALIVE':  ['ah','l','ay','v'],
    'STAY,':  ['s','t','ay','sil'],
    'ALERT,': ['ae','l','er','t','sil'],
    'STAY.':  ['s','t','ay'],
    'ALERT.': ['ae','l','er','t'],
    'ALIVE.': ['ah','l','ay','v'],
    # fallback word fragments from other TTS calls
    'GOOD':   ['g','uw','d'],
    'LUCK':   ['l','ah','k'],
    'YOU':    ['y','uw'],
    'WILL':   ['w','ih','l'],
    'NEED':   ['n','iy','d'],
    'IT':     ['ih','t'],
    'READY':  ['r','eh','d','iy'],
    'WEAPON': ['w','eh','p','ah','n'],
    'JAMMED': ['dh','ae','m','d'],
    'COOL':   ['k','uw','l'],
    'DOWN':   ['d','aw','n'],
    'KEY':    ['k','iy'],
    'FIND':   ['f','ay','n','d'],
    'PORTAL': ['p','ow','r','t','ah','l'],
    'KILL':   ['k','ih','l'],
    'REACH':  ['r','iy','ch'],
    'SPEED':  ['s','p','iy','d'],
    'BOOST':  ['b','uw','s','t'],
    'SLOW':   ['s','l','ow'],
    'TIME':   ['t','ay','m'],
    'RAPID':  ['r','ae','p','ih','d'],
    'FIRE':   ['f','ay','r'],
    'RESPAWNED':['r','ih','s','p','ow','n','d'],
    'TRY':    ['t','r','ay'],
    'AGAIN':  ['ah','g','eh','n'],
}

def _word_to_phones(word):
    w = word.upper().rstrip('.,!?')
    if w in _WORD_PHONES: return _WORD_PHONES[w]
    # Naive grapheme fallback — still intelligible for short words
    phones = []
    i = 0
    s = w.lower()
    while i < len(s):
        c = s[i]
        two = s[i:i+2]
        if two in ('sh','th','dh','ng','ch'):
            phones.append(two); i += 2
        elif c in 'aeiou':
            phones.append({'a':'ae','e':'eh','i':'ih','o':'ow','u':'uw'}.get(c,'ah'))
            i += 1
        elif c in _PH:
            phones.append(c); i += 1
        else:
            i += 1
    return phones if phones else ['sil']

def _glottal_source(t, pitch_hz, phase_acc, rng, voiced):
    """Glottal source: sawtooth for voiced, bandpass noise for unvoiced."""
    if not voiced:
        return rng.gauss(0, 0.8)
    # Sawtooth with slight asymmetry (Rosenberg pulse approximation)
    p = (phase_acc * pitch_hz / SR) % 1.0
    saw = 2.0 * p - 1.0
    # Soften the return edge
    if p > 0.85: saw *= (1.0 - p) / 0.15
    return saw

def _resonator(x, freq, bw, state):
    """Single-pole resonator (bandpass). state=[y1,y2]."""
    if freq <= 0: return 0.0
    r  = math.exp(-math.pi * bw * INV_SR)
    c  = 2 * r * math.cos(TAU * freq * INV_SR)
    y  = x + c * state[0] - r * r * state[1]
    state[1] = state[0]; state[0] = y
    return y * (1.0 - r)

def synth_tts_phrase(text, speed=1.0, pitch_scale=1.0):
    """
    Intelligible English TTS. Glottal source → F1/F2/F3 resonators.
    Falling pitch contour. Coarticulation blending between phonemes.
    Zero external dependencies.
    """
    if not text: return b''
    rng   = random.Random(hash(text) & 0xFFFFFFFF)
    words = text.upper().split()
    nw    = len(words)
    out   = []

    # Base pitch: 135 Hz for better clarity, reduced breathiness
    base_pitch = 135.0 * pitch_scale
    sil_samp   = max(1, int(SR * 0.05 / speed))  # 50ms inter-word gap for clarity

    for wi, word in enumerate(words):
        phones = _word_to_phones(word)
        np_    = len(phones)
        # Sentence-level pitch contour: start high, fall to base over sentence
        sent_prog = wi / max(1, nw - 1)
        word_pitch = base_pitch * (1.14 - 0.20 * sent_prog)

        for pi, ph in enumerate(phones):
            rec = _PH.get(ph, _PH['ah'])
            f1, f2, f3, voiced, dur_ms = rec
            f1 *= pitch_scale; f2 *= pitch_scale; f3 *= pitch_scale
            # Stress: first vowel of word slightly longer + higher pitch
            dur = dur_ms / 1000.0 / speed
            if pi == 0 and voiced: dur *= 1.18; word_pitch *= 1.06
            n = max(3, int(SR * dur))

            # Resonator states
            st1=[0.0,0.0]; st2=[0.0,0.0]; st3=[0.0,0.0]
            # BW: slightly narrower for more precise formants
            bw1 = 75.0; bw2 = 110.0; bw3 = 150.0
            phase_acc = 0.0

            # Lookahead blend target (coarticulation): blend toward next phoneme F2
            next_rec = _PH.get(phones[pi+1], rec) if pi+1 < np_ else rec
            nf2 = next_rec[1] * pitch_scale

            for i in range(n):
                t = i * INV_SR
                prog = i / max(1, n - 1)
                # Amplitude envelope: sharper attack, smoother decay for clarity
                env = (math.sin(math.pi * prog) ** 0.5) * (1.0 - prog * 0.15)

                # Coarticulate F2: blend toward next phoneme in latter half
                blend_f2 = f2 + (nf2 - f2) * max(0, (prog - 0.5) * 2.0)

                # Pitch micro-variation: reduced jitter for clearer tone
                jitter   = 1.0 + rng.gauss(0, 0.006)
                vibrato  = 1.0 + 0.015 * math.sin(TAU * 5.2 * t)
                pitch    = word_pitch * jitter * vibrato

                # Glottal source
                phase_acc += pitch
                src = _glottal_source(t, pitch, phase_acc, rng, voiced)

                # Three formant resonators with adjusted balance for clarity
                r1 = _resonator(src, f1,       bw1, st1) * 0.65 if f1 > 0 else 0.0
                r2 = _resonator(src, blend_f2,  bw2, st2) * 0.32 if f2 > 0 else 0.0
                r3 = _resonator(src, f3,        bw3, st3) * 0.14 if f3 > 0 else 0.0

                # Reduced aspiration noise for clearer voice
                asp  = rng.gauss(0, 0.04) * (0.3 if not voiced else 0.06)

                v = _soft_clip((r1 + r2 + r3 + asp) * env * 0.78, 1.08)
                out.append(_clamp(v))

        # Inter-word silence
        out.extend([0.0] * sil_samp)

    # Master limiter pass — prevent clipping, keep presence
    peak = max(abs(s) for s in out) if out else 1.0
    if peak > 0.88: norm = 0.88 / peak
    else: norm = 1.0
    return _to_wav([s * norm for s in out])

# =============================================================================
#  PROCEDURAL GENERATORS
# =============================================================================

_SYLLABLES = ['ZEN','VOR','KHAL','DRX','MOR','TAN','BEL','KEL','SOR',
              'NEX','VAL','GOR','PYR','ALK','TOR','SEK','MAR','DEL',
              'OHN','WUL','HEX','FEL','JAX','KRON','SYL','AZT','ORC']
_SUFFIXES  = ['ITES','AN','ORC','EX','IAN','OR','AX','EL','US','IS','ON']

def gen_enemy_name():
    """Procedural enemy name from syllable recombination."""
    rng = random.Random()
    s1  = rng.choice(_SYLLABLES)
    s2  = rng.choice(_SYLLABLES)
    suf = rng.choice(_SUFFIXES)
    return f"{s1}{s2}{suf}"[:12]

def gen_mission_dialogue(mtype, target=5):
    """Procedural mission announcement text."""
    kill_phrases = [
        f"Eliminate {target} hostiles. Weapons free.",
        f"Target count: {target}. Begin your assault.",
        f"Kill quota: {target}. Show no mercy.",
        f"Dispatch {target} enemies. The void demands it.",
        f"Neutralize {target} threats. Move out.",
    ]
    key_phrases = [
        "Locate the KEY. The portal waits.",
        "Find the KEY or remain here forever.",
        "The KEY is near. Retrieve it.",
        "Seek the KEY marked on your map.",
        "Acquire the KEY. Then use the portal.",
    ]
    portal_phrases = [
        "Reach the PORTAL. Advance.",
        "Step through the PORTAL. Now.",
        "Find the PORTAL. Time is irrelevant here.",
        "The PORTAL opens. Enter it.",
        "Cross the threshold. PORTAL awaits.",
    ]
    rng = random.Random()
    if mtype == "kill":    return rng.choice(kill_phrases)
    if mtype == "find_key": return rng.choice(key_phrases)
    return rng.choice(portal_phrases)

def gen_scenario_flavour():
    """Random atmospheric scenario text for HUD."""
    scenarios = [
        "SIGNAL LOST — PROCEEDING ON INSTINCT",
        "REALITY SUBSTRATE: UNSTABLE",
        "DIMENSIONAL FOLD DETECTED AHEAD",
        "HEAT DEATH IN SECTOR 7 — CONTINUE",
        "RECURSIVE LOOP DETECTED — IGNORE",
        "VOID ENTITIES: AWAKE",
        "CAUSALITY: OPTIONAL",
        "ENTROPY INCREASING — AS EXPECTED",
        "TIMELINE: CORRUPTED — PROCEED",
        "ANOMALY CLUSTER: SECTOR UNKNOWN",
        "OBSERVER EFFECT: ACTIVE",
        "NULL SPACE INCURSION IN PROGRESS",
        "CONSCIOUSNESS: EXPENDABLE",
        "PROBABILITY FIELD: COLLAPSED",
        "QUANTUM DECOHERENCE: ACCEPTABLE LOSS",
    ]
    return random.choice(scenarios)

def gen_death_quote():
    """What the announcer says when player dies."""
    quotes = [
        "OUCH","You died. Expected.","OUCH — back to start.",
        "Mortality achieved. OUCH.","You have been terminated. OUCH.",
        "OUCH. The void reclaims you.","Death confirmed. OUCH.",
        "Respawning. OUCH.","Critical failure. OUCH.",
        "OUCH — that's gonna leave a mark.",
    ]
    return random.choice(quotes)

def gen_kill_flavour():
    """Random kill line."""
    rng = random.Random()
    w   = rng.choice(KILL_WORDS)
    n   = gen_enemy_name()
    return f"{n} {w}"

# =============================================================================
#  PROCEDURAL SPRITE GENERATOR — unique per-enemy, seeded by entity id
# =============================================================================
# Base frame pools — eyes, torsos, legs, arms per archetype
_EYE_POOL  = ['(o o)','(@ @)','(x x)','(* *)','(> <)','(# #)','[o_o]','<o-o>','(0 0)','(^ ^)']
_HEAD_POOL = ['ZZZ','DDD','GGG','///','###','XXX','|||','<<<','>>>','~~~']
_TORSO_L   = ['<|','[|','\\|','{|','(|','=|','!|','?|']
_TORSO_R   = ['|>','|]','|/',"|}",'|)','|=','|!','|?']
_LEG_POOL  = ['/ \\ ','|_| ','\\|/ ','/_\\ ','/=\\ ','(_) ','||| ','\\=/ ']
_ARM_L     = ['/','\\','|','<','{','[']
_ARM_R     = ['\\','/','|','>','}',']']
_FRAME_CHARS = '#@$%&*+=~-|.:^'
_CORPSE    = ['  x x  ','  |||  ','  ---  ','       ']

def gen_sprite(seed):
    """Procedurally generate a unique 4-row enemy sprite from seed int."""
    r = random.Random(seed)
    eye   = r.choice(_EYE_POOL)
    head  = r.choice(_HEAD_POOL)
    al,ar = r.choice(_ARM_L), r.choice(_ARM_R)
    tl,tr = r.choice(_TORSO_L), r.choice(_TORSO_R)
    leg   = r.choice(_LEG_POOL)
    fc    = r.choice(_FRAME_CHARS)
    w = 8
    row0 = f' {fc}{head}{fc} '[:w].ljust(w)
    row1 = f'  {eye}  '[:w].ljust(w)
    row2 = f' {al}{tl[1:]}{tr[:-1]}{ar} '[:w].ljust(w)
    row3 = f'  {leg}  '[:w].ljust(w)
    return [row0, row1, row2, row3]

# Per-enemy sprite cache — keyed by entity id, generated once on first sight
_SPRITE_CACHE = {}

def get_sprite(char, flash=False, eid=None):
    if char == '%': rows = _CORPSE
    else:
        key = eid if eid is not None else id(char)
        if key not in _SPRITE_CACHE:
            _SPRITE_CACHE[key] = gen_sprite(key ^ (ord(char)*7919))
        rows = _SPRITE_CACHE[key]
    if flash: return [' *' + r[2:] for r in rows]
    return rows

# =============================================================================
#  POWERUP SPAWNER
# =============================================================================
class PowerupSpawner:
    def __init__(self): self.items = []   # list of [x, y, type, frame_timer]
    def spawn_near(self, cx, cy, router):
        for _ in range(40):
            a = random.uniform(0, 6.2832); r = random.uniform(3, 10)
            x = cx + math.cos(a)*r; y = cy + math.sin(a)*r
            if router.get_cell(x, y) == 0:
                t = random.choice(POWERUP_TYPES)
                self.items.append([x, y, t, 900])
                return
    def update(self):
        self.items = [[x,y,t,f-1] for x,y,t,f in self.items if f > 0]
    def check_pickup(self, px, py):
        for item in self.items:
            if math.hypot(item[0]-px, item[1]-py) < 1.1:
                self.items.remove(item)
                return item[2]
        return None
    def draw(self, buf, cam, zbuf, W, H):
        for x, y, t, _ in self.items:
            dx = x - cam.pos.x; dy = y - cam.pos.y
            inv = cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y
            if abs(inv) < 1e-9: continue
            inv = 1.0/inv
            tX = inv*(cam.dir.y*dx - cam.dir.x*dy)
            tY = inv*(-cam.plane.y*dx + cam.plane.x*dy)
            if tY < 0.3: continue
            sx = int(W/2*(1 + tX/tY))
            sz = max(1, abs(int(H/tY)))
            x0 = max(0, sx-sz//4); x1 = min(W-1, sx+sz//4)
            y0 = max(0, H//2-sz//2); y1 = min(H-1, H//2+sz//2)
            zidx = max(0, min(W-1, sx))
            if tY < zbuf[zidx]:
                g = POWERUP_GLYPHS.get(t, '?')
                for by in range(y0, y1):
                    for bx in range(x0, x1):
                        if 0<=bx<W and 0<=by<H: buf[by][bx] = g

# =============================================================================
#  MATH
# =============================================================================

class V2:
    __slots__ = ('x','y')
    def __init__(self, x=0., y=0.): self.x=float(x); self.y=float(y)
    def __add__(self, o): return V2(self.x+o.x, self.y+o.y)
    def __sub__(self, o): return V2(self.x-o.x, self.y-o.y)
    def __mul__(self, s): return V2(self.x*s, self.y*s)
    def dot(self, o): return self.x*o.x + self.y*o.y
    def length(self): return math.sqrt(self.x*self.x + self.y*self.y)
    def norm(self):
        l = self.length()
        return V2(self.x/l, self.y/l) if l > 1e-9 else V2()
    def copy(self): return V2(self.x, self.y)

# =============================================================================
#  INPUT
# =============================================================================

class Input:
    def __init__(self, root):
        self.keys = set(); self.mouse = False; self.mx = 0; self.my = 0
        root.bind("<KeyPress>",   lambda e: self.keys.add(e.keysym.lower()))
        root.bind("<KeyRelease>", lambda e: self.keys.discard(e.keysym.lower()))
        root.bind("<Escape>",     lambda e: root.destroy())
        root.bind("<Button-1>",   lambda e: setattr(self,'mouse',True))
        root.bind("<ButtonRelease-1>", lambda e: setattr(self,'mouse',False))
        root.bind("<Motion>",     lambda e: (setattr(self,'mx',e.x), setattr(self,'my',e.y)))
    def held(self, k): return k in self.keys
    def firing(self): return self.mouse or 'space' in self.keys

# =============================================================================
#  CAMERA
# =============================================================================

class Camera:
    def __init__(self, x=4.5, y=4.5):
        self.pos = V2(x, y)
        self.dir = V2(-1., 0.)
        self.plane = V2(0., 0.66)
        self.pitch = 0.; self.bob = 0.; self.bob_phase = 0.
        self.health = 100; self.max_health = 100
        # jump state
        self.jump_vel    = 0.0
        self.jump_off    = 0.0   # only used to lower floor visually
        self.jumping     = False
        self.landed      = False
        # screen shake
        self.shake_amp   = 0.0   # current shake amplitude (pitch units)
        self.shake_frames = 0    # frames remaining
    def rotate(self, spd):
        c, s = math.cos(spd), math.sin(spd)
        dx, dy = self.dir.x, self.dir.y
        self.dir.x  = dx*c - dy*s; self.dir.y  = dx*s + dy*c
        px, py = self.plane.x, self.plane.y
        self.plane.x = px*c - py*s; self.plane.y = px*s + py*c
    def step_bob(self, moving):
        if moving:
            self.bob_phase += 0.18
            self.bob = math.sin(self.bob_phase) * 2.0
        else: self.bob *= 0.85
    def land_shake(self, intensity=6.0):
        """Trigger screen shake on landing."""
        self.shake_amp    = intensity
        self.shake_frames = 14
    def update_shake(self):
        """Returns shake offset this frame, decays over time."""
        if self.shake_frames <= 0:
            self.shake_amp = 0.0
            return 0.0
        self.shake_frames -= 1
        decay = self.shake_frames / 14.0
        offset = (random.random() * 2.0 - 1.0) * self.shake_amp * decay
        self.shake_amp *= 0.78
        return offset
    def jump(self):
        """Initiate a slow floaty moon-jump."""
        if not self.jumping:
            self.jump_vel = 2.8
            self.jumping  = True
            self.landed   = False
    def update_jump(self):
        """Call each frame. Returns True on landing frame."""
        if not self.jumping:
            self.landed = False
            return False
        gravity = 0.055 if self.jump_vel > 0 else 0.0932
        self.jump_vel -= gravity
        self.jump_off += self.jump_vel
        if self.jump_off <= 0.0 and self.jump_vel < 0:
            self.jump_off = 0.0
            self.jump_vel = 0.0
            self.jumping  = False
            self.landed   = True
            return True
        self.landed = False
        return False

# =============================================================================
#  MAP STAGES — infinite procedural worlds
# =============================================================================

EMPTY=0; WALL=1; PIL=2; POR=3; DOOR=4; KEY=6

class StageVoidDepths:
    name = "THE VOID DEPTHS"
    _cache = {}
    def get_cell(self, x, y):
        ix, iy = int(x), int(y)
        k = (ix, iy)
        if k in self._cache: return self._cache[k]
        h = (ix*2971 ^ iy*1489 ^ (ix+iy)*7) & 0xFFFF
        if h < 8000:  v = WALL
        elif h > 63000: v = PIL
        elif (ix%32==16) and (iy%32==16): v = POR
        else: v = EMPTY
        self._cache[k] = v; return v

class StageDungeon:
    name = "INFINITE DUNGEON"
    def __init__(self, seed=42):
        self._cache = {}; self._seed = seed
        r = random.Random(seed)
        self._rooms = [(r.randint(-80,80), r.randint(-80,80),
                        r.randint(3,9), r.randint(3,9)) for _ in range(400)]
    def get_cell(self, x, y):
        ix, iy = int(x), int(y); k = (ix,iy)
        if k in self._cache: return self._cache[k]
        v = self._compute(ix, iy)
        if len(self._cache) > 6000: self._cache.clear()
        self._cache[k] = v; return v
    def _compute(self, ix, iy):
        for rx,ry,rw,rh in self._rooms:
            if rx<=ix<rx+rw and ry<=iy<ry+rh:
                if ix==rx or ix==rx+rw-1 or iy==ry or iy==ry+rh-1: return WALL
                return EMPTY
        if ix%16==0 or iy%16==0: return EMPTY
        if ix%8==0 and iy%8==0: return POR
        h = (ix*3571 ^ iy*2011) & 0xFFFF
        return WALL if h < 22000 else EMPTY

class StageArena:
    name = "THE ARENA"
    SIZE = 30
    _cache = {}
    def get_cell(self, x, y):
        ix, iy = int(x), int(y); s = self.SIZE
        if ix<=0 or iy<=0 or ix>=s or iy>=s: return WALL
        if ix%6==3 and iy%6==3: return PIL
        if ix==s//2 and iy==s//2: return POR
        return EMPTY

class StageSanctum:
    name = "INNER SANCTUM"
    _cache = {}
    def get_cell(self, x, y):
        ix, iy = int(x), int(y)
        if abs(ix)>40 or abs(iy)>40: return WALL
        if ix%10==0 or iy%10==0: return EMPTY
        if ix%10 in (1,9) or iy%10 in (1,9): return WALL
        if (ix%10==5 and iy%10 in (1,9)) or (iy%10==5 and ix%10 in (1,9)): return DOOR
        if ix%30==15 and iy%30==15: return POR
        return EMPTY

STAGE_ORDER = [StageVoidDepths, StageDungeon, StageArena, StageSanctum]

class MapRouter:
    def __init__(self):
        self._idx = 0
        self._stages = [S() if S != StageDungeon else S(seed=random.randint(1,9999))
                        for S in STAGE_ORDER]
        self.stage = self._stages[0]
        self.trans_timer = 0; self.trans_msg = ""
        self._cache = {}   # shared key injection cache
    def get_cell(self, x, y):
        k = (int(x), int(y))
        if k in self._cache: return self._cache[k]
        return self.stage.get_cell(x, y)
    def inject(self, x, y, val):
        self._cache[(int(x), int(y))] = val
    def advance(self, cam, spawn_cb):
        self._idx = (self._idx+1) % len(self._stages)
        self.stage = self._stages[self._idx]
        self._cache.clear()
        cam.pos = V2(4.5, 4.5); cam.pitch = 0
        self.trans_timer = 90
        self.trans_msg = f">> ENTERING: {self.stage.name} <<"
        spawn_cb()

# =============================================================================
#  ENTITIES
# =============================================================================

ENEMY_CHARS  = ['Z','D','G','S','B','M']
ENEMY_HP     = {'Z':17,'D':17,'G':17,'S':17,'B':17,'M':17}
ENEMY_SPEED  = {'Z':0.020,'D':0.015,'G':0.035,'S':0.010,'B':0.025,'M':0.020}
ENEMY_DMG    = {'Z':8,'D':5,'G':10,'S':4,'B':12,'M':7}

# =============================================================================
#  POWERUP SYSTEM
# =============================================================================
POWERUP_TYPES  = ['SPEED_BOOST','SLOW_TIME','RAPID_FIRE']
POWERUP_GLYPHS = {'SPEED_BOOST':'>','SLOW_TIME':'~','RAPID_FIRE':'!'}
POWERUP_LABELS = {
    'SPEED_BOOST': 'SPEED BOOST',
    'SLOW_TIME':   'SLOW TIME',
    'RAPID_FIRE':  'RAPID FIRE',
}
POWERUP_DURATION = 620   # ~10s at 62fps

class Entity:
    __slots__ = ('x','y','char','hp','speed','dmg','state','flash','dead_timer','attack_cd','eid','confusion','wander_direction','wander_timer','pacified','pacify_timer','wander_scale','wander_noise_timer','vibration_intensity','vibration_timer','shake_intensity','shake_timer','shake_frequency','message_text','message_timer','newly_pacified','stillness_timer')
    def __init__(self, x, y, char='Z'):
        self.x=float(x); self.y=float(y); self.char=char
        self.hp=ENEMY_HP.get(char,3); self.speed=ENEMY_SPEED.get(char,0.02)
        self.dmg=ENEMY_DMG.get(char,8); self.state='IDLE'
        self.flash=0; self.dead_timer=0; self.attack_cd=0
        self.eid = random.randint(1, 0xFFFFFF)  # unique sprite seed
        self.confusion = 0  # Confusion counter - keeps enemy wandering
        self.wander_direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)])  # Cardinal direction
        self.wander_timer = 0  # Timer for direction changes
        self.pacified = False  # Permanently peaceful after 10 seconds of confusion
        self.pacify_timer = 0  # 10 second timer until permanent pacification
        self.wander_scale = 1.0  # Procedural movement scale
        self.wander_noise_timer = random.uniform(0, 100)  # Noise-based timer for organic movement
        self.vibration_intensity = 0.0  # Vibration/rattle effect intensity
        self.vibration_timer = 0  # Vibration duration
        self.shake_intensity = 0.0  # Frequency shake intensity (confused state)
        self.shake_timer = 0.0  # Frequency shake timer (for wave phase)
        self.shake_frequency = random.uniform(0.08, 0.15)  # Random shake frequency per enemy
        self.message_text = ""  # Text to display above NPC
        self.message_timer = 0  # Timer for message display (frames)
        self.newly_pacified = False  # Flag to trigger announcer on first pacification
        self.stillness_timer = 0  # Timer for 15 second stillness period before wandering
    def alive(self): return self.state != 'DEAD'
    def update(self, cam, router):
        if self.state == 'DEAD': self.dead_timer -= 1; return
        
        # VIBRATION/RATTLE EFFECT: Apply slight position wobble
        if self.vibration_intensity > 0:
            self.vibration_timer += 1
            if self.vibration_timer > 8:  # Vibrate for ~8 frames
                self.vibration_intensity = 0
                self.vibration_timer = 0
            else:
                # Apply slight random wobble (rattling effect)
                wobble_x = random.uniform(-self.vibration_intensity, self.vibration_intensity)
                wobble_y = random.uniform(-self.vibration_intensity, self.vibration_intensity)
                temp_x = self.x + wobble_x
                temp_y = self.y + wobble_y
                # Only wobble if valid
                if router.get_cell(temp_x, self.y) == EMPTY: self.x = temp_x
                if router.get_cell(self.x, temp_y) == EMPTY: self.y = temp_y
        
        # LAYER 1: EMERGENCY CHECK - attack_cd impossibly high
        if self.attack_cd >= 9999:
            self.state = 'CONFUSED'; self.dmg = 0; return
        
        # LAYER 2: TRIPLE CHECK - confusion or pacified
        if self.confusion > 0 or self.pacified: self.dmg = 0; self.attack_cd = 9999
        
        # Decay confusion counter
        if self.confusion > 0: self.confusion = max(0, self.confusion - 1)
        
        # Count down pacify timer
        if self.pacify_timer > 0:
            self.pacify_timer -= 1
            if self.pacify_timer == 0: 
                self.pacified = True
                self.confusion = 0
                self.dmg = 0
                # After initial stillness message expires, enter enlightened confusion state
                # Set confusion to infinite (we'll handle it separately in pacified state)
                # Reset wander parameters for enlightened confusion movement
                self.wander_direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
                self.wander_timer = 0
                self.wander_scale = 1.0
                self.wander_noise_timer = random.uniform(0, 100)
                self.shake_frequency = random.uniform(0.08, 0.15)
        
        # LAYER 3: PRE-CONFUSION CHECK
        if self.confusion > 0 or self.pacified: self.dmg = 0; self.attack_cd = 9999
        
        dx = cam.pos.x - self.x; dy = cam.pos.y - self.y
        d  = math.hypot(dx, dy)
        
        # If confused, handle stillness period then wander
        if self.confusion > 0:
            self.state = 'CONFUSED'
            self.dmg = 0  # LAYER 4
            self.attack_cd = 9999  # LAYER 5
            
            # Decrement stillness timer
            if self.stillness_timer > 0:
                self.stillness_timer -= 1
                # During stillness period: stay completely still, just do visual effects
                # FREQUENCY SHAKE: Gentle shake during stillness (showing they're affected)
                self.shake_intensity = 0.15  # Reduced intensity during stillness
                self.shake_timer += self.shake_frequency * 0.5  # Slower oscillation
                
                if self.flash > 0: self.flash -= 1
                else: self.flash = random.randint(1, 3)
                
                # LAYER 6: PRE-RETURN ZERO
                self.dmg = 0; self.attack_cd = 9999; return
            
            # After stillness period: wander freely
            # RANDOMIZED PROCEDURAL MOVEMENT
            self.wander_noise_timer += random.uniform(0.08, 0.35)  # Variable increment
            
            # Speed varies with sine wave + random multiplier
            procedural_multiplier = random.uniform(0.7, 1.3)  # Random speed variation
            self.wander_scale = (0.5 + 0.5 * math.sin(self.wander_noise_timer * 0.05)) * procedural_multiplier
            self.wander_scale = max(0.3, min(1.8, self.wander_scale))  # Clamp 0.3-1.8x
            
            # Direction change with randomized intervals
            random_direction_duration = random.randint(10, 40)  # Variable timing per direction
            self.wander_timer += 1
            if self.wander_timer > random_direction_duration:
                self.wander_timer = 0
                # Random chance to pause instead of moving
                if random.random() < 0.25:  # 25% chance to pause
                    self.wander_direction = (0, 0)
                else:
                    self.wander_direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
            
            dx_move, dy_move = self.wander_direction
            movement = self.speed * self.wander_scale
            nx = self.x + dx_move * movement; ny = self.y + dy_move * movement
            
            if router.get_cell(nx, self.y) == EMPTY: self.x = nx
            if router.get_cell(self.x, ny) == EMPTY: self.y = ny
            
            # FREQUENCY SHAKE: Respond to whoosh sweep (fast shake when confused)
            self.shake_intensity = 0.25  # High intensity shake when confused
            self.shake_timer += self.shake_frequency  # Fast oscillation
            
            # Apply sine wave shake based on timer
            shake_x = math.sin(self.shake_timer * TAU) * self.shake_intensity * random.uniform(0.8, 1.2)
            shake_y = math.cos(self.shake_timer * TAU) * self.shake_intensity * random.uniform(0.8, 1.2)
            
            shake_x_pos = self.x + shake_x
            shake_y_pos = self.y + shake_y
            
            if router.get_cell(shake_x_pos, self.y) == EMPTY: self.x = shake_x_pos
            if router.get_cell(self.x, shake_y_pos) == EMPTY: self.y = shake_y_pos
            
            if self.flash > 0: self.flash -= 1
            else: self.flash = random.randint(1, 3)
            
            # LAYER 6: PRE-RETURN ZERO
            self.dmg = 0; self.attack_cd = 9999; return
        
        # If pacified, enter enlightened confusion state with 10% speed movement
        if self.pacified:
            self.state = 'IDLE'
            self.confusion = 0
            self.dmg = 0  # LAYER 7
            self.attack_cd = 9999  # LAYER 8
            
            # === MESSAGE TIMER MANAGEMENT (REDUNDANT) ===
            # Decrement message timer EVERY FRAME during pacified state
            if self.message_timer > 0:
                self.message_timer -= 1
            
            # Guard: prevent negative timer
            if self.message_timer < 0:
                self.message_timer = 0
            
            # === FORCE MESSAGE DISAPPEARANCE ===
            # If message_timer reaches 0, CLEAR message text immediately
            if self.message_timer == 0:
                self.message_text = ""  # FORCE CLEAR
            
            # === STAY STILL WHILE MESSAGE DISPLAYS (REDUNDANT CHECK) ===
            # Only stay still if message_timer is EXPLICITLY > 0
            if self.message_timer > 0:
                # During message display: stay completely still
                if self.flash > 0: self.flash -= 1
                # LAYER 9: Pacified exit
                self.dmg = 0; self.attack_cd = 9999; return
            
            # === EXPLICIT MESSAGE DISAPPEARANCE CHECK (REDUNDANT) ===
            # Double-check message is gone before wandering
            if self.message_timer <= 0:
                # FORCE message_text to be empty
                self.message_text = ""
            
            # === INFINITE ENLIGHTENED CONFUSION AT 10% SPEED ===
            # (This code ALWAYS executes if we reach here - no other paths)
            
            # RANDOMIZED PROCEDURAL MOVEMENT at 10% speed
            self.wander_noise_timer += random.uniform(0.08, 0.35) * 0.1  # 10% increment
            
            # Speed varies with sine wave + random multiplier (10% of confused speed)
            procedural_multiplier = random.uniform(0.7, 1.3) * 0.10  # 10% speed multiplier
            self.wander_scale = (0.5 + 0.5 * math.sin(self.wander_noise_timer * 0.05)) * procedural_multiplier
            self.wander_scale = max(0.03, min(0.18, self.wander_scale))  # Clamp to 10% range
            
            # Direction change with randomized intervals
            random_direction_duration = random.randint(10, 40)  # Variable timing per direction
            self.wander_timer += 1
            if self.wander_timer > random_direction_duration:
                self.wander_timer = 0
                # Random chance to pause instead of moving
                if random.random() < 0.25:  # 25% chance to pause
                    self.wander_direction = (0, 0)
                else:
                    self.wander_direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
            
            # MOVE in current direction with procedural scale (10% of confused speed)
            dx_move, dy_move = self.wander_direction
            movement = self.speed * self.wander_scale
            nx = self.x + dx_move * movement
            ny = self.y + dy_move * movement
            
            # Free wandering: only check walls, ignore player
            if router.get_cell(nx, self.y) == EMPTY:
                self.x = nx
            if router.get_cell(self.x, ny) == EMPTY:
                self.y = ny
            
            # FREQUENCY SHAKE: Confused-style shake at 10% intensity
            self.shake_intensity = 0.025  # 10% of 0.25 (confused shake)
            self.shake_timer += self.shake_frequency  # Same oscillation rate
            
            # Apply sine wave shake based on timer
            shake_x = math.sin(self.shake_timer * TAU) * self.shake_intensity * random.uniform(0.8, 1.2)
            shake_y = math.cos(self.shake_timer * TAU) * self.shake_intensity * random.uniform(0.8, 1.2)
            
            shake_x_pos = self.x + shake_x
            shake_y_pos = self.y + shake_y
            
            if router.get_cell(shake_x_pos, self.y) == EMPTY: self.x = shake_x_pos
            if router.get_cell(self.x, shake_y_pos) == EMPTY: self.y = shake_y_pos
            
            if self.flash > 0: self.flash -= 1
            else: self.flash = random.randint(1, 3)
            
            # LAYER 9: Pacified exit
            self.dmg = 0; self.attack_cd = 9999; return
        
        # LAYER 10: FINAL PRE-ATTACK CHECK
        if self.confusion > 0 or self.pacified: self.dmg = 0; self.attack_cd = 9999; return
        
        # Normal AI (only if NOT confused and NOT pacified)
        if d < 14: self.state = 'CHASE'
        if d < 1.1: self.state = 'ATTACK'
        if self.state in ('CHASE','ATTACK') and d > 0.8:
            nx = self.x + dx/d*self.speed; ny = self.y + dy/d*self.speed
            if router.get_cell(nx, self.y) == EMPTY: self.x = nx
            if router.get_cell(self.x, ny) == EMPTY: self.y = ny
        if self.flash > 0: self.flash -= 1
        if self.attack_cd > 0: self.attack_cd -= 1
        
        # ATTACK - with LAYER 11: REDUNDANT ZERO DAMAGE CHECK
        if self.state == 'ATTACK' and self.attack_cd <= 0:
            if self.confusion > 0 or self.pacified: cam.health -= 0  # LAYER 11A
            elif self.dmg <= 0: cam.health -= 0  # LAYER 11B
            else: cam.health -= self.dmg
            self.attack_cd = 45
        
        # LAYER 12: POST-ATTACK ZERO
        if self.confusion > 0 or self.pacified: self.dmg = 0
    def hit(self, dmg=1):
        """Emitter hit - reduces HP, achieves stillness when HP reaches 0. Pacified NPCs are immune."""
        # If already pacified, ignore hits
        if self.pacified:
            return False
        
        # Reduce HP
        self.hp -= dmg
        self.flash = 3  # Brief visual feedback
        
        # If still has HP, just flash but don't achieve stillness yet
        if self.hp > 0:
            return False
        
        # HP reached 0 - achieve stillness!
        # IMMEDIATE protection - block attacks right now
        self.attack_cd = 9999  # Set impossibly high immediately
        self.dmg = 0  # Zero damage immediately
        
        # Set confusion to last full 15 seconds (930 frames at 62fps)
        self.confusion = 930
        
        # Set 15-second stillness period for initial confusion (~930 frames at 62fps)
        # During this time, enemy stays completely still
        self.stillness_timer = 930
        
        # VIBRATION/RATTLE EFFECT: Enemy shakes slightly when hit
        self.vibration_intensity = 0.15  # Wobble intensity
        self.vibration_timer = 0  # Start vibration
        
        # FREQUENCY SHAKE: Initialize shake effect for confused state
        self.shake_intensity = 0.25  # High intensity for confused
        self.shake_timer = 0.0  # Start shake timer
        self.shake_frequency = random.uniform(0.08, 0.15)  # Randomized frequency per hit
        
        # Set 10-second pacify timer (~620 frames at 62fps)
        # After 10 seconds of stillness, they become permanently peaceful NPCs
        self.pacify_timer = 620
        
        # Reset wander parameters for organic movement
        self.wander_direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
        self.wander_timer = 0
        self.wander_scale = 1.0
        self.wander_noise_timer = random.uniform(0, 100)
        
        # Immediately display "Stillness Achieved" message for 10 seconds (~620 frames)
        self.message_text = "Stillness Achieved. Peace and Bliss"
        self.message_timer = 620  # Display for 10 seconds
        self.newly_pacified = True  # Trigger TTS and lower-left text immediately
        
        return False  # Emitter never "kills"
    
    def glyph(self):
        if self.state == 'DEAD': return '%'
        if self.flash > 0: return '*'
        if self.pacified: return 'n'  # Peaceful NPC (lowercase n)
        if self.state == 'CONFUSED': return '?'  # Curious about the sound
        if self.state == 'ATTACK': return '!'  # Show when attacking
        return self.char

# =============================================================================
#  PARTICLES
# =============================================================================

class Particle:
    __slots__ = ('bx','by','char','life','vx','vy')
    def __init__(self, bx, by, char, life):
        self.bx=bx; self.by=by; self.char=char; self.life=life
        self.vx=random.choice([-1,0,0,1]); self.vy=random.choice([-1,0,0,1])

class Particles:
    def __init__(self): self.p = []
    def emit(self, bx, by, kind='spark', count=4):
        cs = {'spark':'*+.','blood':'#@.','smoke':'.,:','gore':'$%#'}.get(kind,'*')
        for _ in range(count):
            self.p.append(Particle(bx+random.randint(-3,3),
                                   by+random.randint(-2,2),
                                   random.choice(cs), random.randint(4,10)))
    def update(self):
        alive = []
        for p in self.p:
            p.life -= 1; p.bx += p.vx; p.by += p.vy
            if p.life > 0: alive.append(p)
        self.p = alive
    def draw(self, buf, W, H):
        for p in self.p:
            if 0 <= int(p.bx) < W and 0 <= int(p.by) < H:
                buf[int(p.by)][int(p.bx)] = p.char

# =============================================================================
#  RENDERER — DDA raycaster + sprite projection
# =============================================================================

RAMP_WALL  = "@#$B%&W8MX*+=-:. "
RAMP_FLOOR = ".,`' "
RAMP_CEIL  = ",-.'` "

class Renderer:
    def __init__(self, W, H): self.W=W; self.H=H

    def render(self, cam, router, entities, particles, hud_cb, pu_spawner=None):
        W, H = self.W, self.H
        buf   = [[' ']*W for _ in range(H)]
        zbuf  = [1e9]*W
        ceil_h = H//2
        # jump_off must NOT touch voff — that tilts the horizon and breaks controls
        # instead encode height as eye_h: walls appear taller when airborne
        eye_h  = max(0.45, 1.0 - cam.jump_off * 0.16)
        voff   = int(cam.pitch + cam.bob + cam.update_shake())

        # ceiling (sparse pattern)
        for y in range(ceil_h):
            idx = min(len(RAMP_CEIL)-1, int(len(RAMP_CEIL)*y/ceil_h))
            c   = RAMP_CEIL[idx]
            if y % 3 == 0:
                for x in range(0, W, 4): buf[y][x] = c

        # DDA raycasting
        for x in range(W):
            camX = 2*x/W - 1
            rDX  = cam.dir.x + cam.plane.x * camX
            rDY  = cam.dir.y + cam.plane.y * camX
            mX, mY = int(cam.pos.x), int(cam.pos.y)
            dDX = abs(1/rDX) if rDX else 1e30
            dDY = abs(1/rDY) if rDY else 1e30
            sX, sDX = (-1, (cam.pos.x-mX)*dDX) if rDX<0 else (1, (mX+1.0-cam.pos.x)*dDX)
            sY, sDY = (-1, (cam.pos.y-mY)*dDY) if rDY<0 else (1, (mY+1.0-cam.pos.y)*dDY)
            hit=side=cell=0; iters=0
            while not hit and iters < 80:
                if sDX < sDY: sDX+=dDX; mX+=sX; side=0
                else:          sDY+=dDY; mY+=sY; side=1
                cell = router.get_cell(mX, mY)
                if cell > 0: hit = 1
                iters += 1
            pwd = ((mX-cam.pos.x+(1-sX)/2)/rDX if side==0
                   else (mY-cam.pos.y+(1-sY)/2)/rDY)
            pwd = max(0.1, pwd); zbuf[x] = pwd
            lineH = int(H / (pwd * eye_h))
            dS    = max(0, -lineH//2 + H//2 + voff)
            dE    = min(H-1, lineH//2 + H//2 + voff)
            dist_idx = min(len(RAMP_WALL)-1, int(pwd*1.5))
            wc = RAMP_WALL[dist_idx]
            if cell == PIL:  wc = 'O'
            elif cell == POR: wc = '@'
            elif cell == DOOR: wc = '+'
            elif cell == KEY:  wc = 'K'
            if side == 1 and wc not in '.,': wc = wc.lower() if wc.isalpha() else ':'
            for y in range(dS, dE): buf[y][x] = wc
            # floor
            for y in range(dE, H):
                fi = min(len(RAMP_FLOOR)-1, int((y-H//2)/(H//2)*(len(RAMP_FLOOR)-1)))
                if (x+y)%4==0: buf[y][x] = RAMP_FLOOR[fi]

        # sprites
        live = [e for e in entities if e.alive() or e.dead_timer > 0]
        for ent in sorted(live, key=lambda e:(cam.pos.x-e.x)**2+(cam.pos.y-e.y)**2, reverse=True):
            self._sprite(buf, zbuf, cam, ent, voff)

        particles.draw(buf, W, H)
        if pu_spawner: pu_spawner.draw(buf, cam, zbuf, W, H)
        hud_cb(buf)
        return "\n".join("".join(r) for r in buf)

    def _sprite(self, buf, zbuf, cam, ent, voff):
        W, H = self.W, self.H
        sX = ent.x - cam.pos.x; sY = ent.y - cam.pos.y
        invD = 1.0/(cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y + 1e-9)
        tX   = invD*(cam.dir.y*sX - cam.dir.x*sY)
        tY   = invD*(-cam.plane.y*sX + cam.plane.x*sY)
        if tY <= 0.1: return
        scrX = int(W/2*(1+tX/tY))
        sH   = max(1, abs(int(H/tY))); sW = max(1, sH//2)
        y1   = max(0, -sH//2+H//2+voff); y2 = min(H-1, sH//2+H//2+voff)
        x1   = max(0, scrX-sW//2);        x2 = min(W-1, scrX+sW//2)
        ch   = ent.glyph()
        # multi-row sprite rendering
        sprite_rows = get_sprite(ent.char if ent.alive() else '%', ent.flash > 0, eid=ent.eid)
        row_span    = max(1, (y2 - y1))
        for sx in range(x1, x2):
            if tY < zbuf[sx]:
                for sy in range(y1, y2):
                    row_idx = int((sy - y1) / max(row_span,1) * len(sprite_rows))
                    row_idx = min(row_idx, len(sprite_rows)-1)
                    col_idx = (sx - x1) % max(1, len(sprite_rows[row_idx]))
                    sc = sprite_rows[row_idx][col_idx]
                    buf[sy][sx] = sc if sc.strip() else ch
        
        # Display "Stillness Achieved" message above NPC head (DEFENSIVE REDUNDANT)
        if ent.message_timer > 0 and ent.message_text and len(ent.message_text) > 0:
            msg = ent.message_text
            msg_len = len(msg)
            msg_y = max(0, y1 - 2)  # 2 lines above sprite
            msg_x = max(0, scrX - msg_len // 2)
            msg_x = min(msg_x, W - msg_len)
            
            # Draw message (always visible, no fade)
            for i, c in enumerate(msg):
                if msg_x + i < W and msg_y < H:
                    buf[msg_y][msg_x + i] = c
        elif ent.message_timer <= 0:
            # FORCE message to be empty if timer is 0 or less
            ent.message_text = ""

# =============================================================================
#  HUD
# =============================================================================

def _compass(dx, dy):
    a = math.degrees(math.atan2(dy, dx)) % 360
    return ["E","NE","N","NW","W","SW","S","SE"][int((a+22.5)/45)%8]

class HUD:
    def __init__(self, W, H): self.W=W; self.H=H; self._stage=None

    def draw(self, buf, cam, heat, overheated, score, kills,
             stage_name, trans_timer, trans_msg, entities,
             mission_text, flavour, frame,
             powerups=None, land_word='', land_timer=0):
        W, H = self.W, self.H
        cx, cy = W//2, H//2
        # crosshair
        sym = 'X' if overheated else '+'
        buf[cy][cx] = sym
        if cx > 1: buf[cy][cx-1] = '-'; buf[cy][cx+1] = '-'
        if cy > 1: buf[cy-1][cx] = '|'; buf[cy+1][cx] = '|'

        # health bar
        hp_frac = max(0, cam.health) / cam.max_health
        hp_bar  = 10
        hp_fill = int(hp_frac * hp_bar)
        hp_sym  = '!' if cam.health <= 20 else '#'
        hp_str  = "[" + hp_sym*hp_fill + ' '*(hp_bar-hp_fill) + "]"
        self._w(buf, 2, H-5, f"HP:{hp_str}{cam.health:3d}")

        # heat bar
        bar   = 10; filled = int(heat/100*bar)
        col   = '!' if heat > 70 else '|'
        gauge = "[" + col*filled + ' '*(bar-filled) + "]"
        sts   = "JAMMED!" if overheated else "READY  "
        self._w(buf, 2, H-4, f"HEAT:{gauge}{sts}")

        # compass + stage name
        cdir = _compass(cam.dir.x, cam.dir.y)
        self._w(buf, W-8, 1, f"[{cdir:>2}]")
        sn = stage_name[:W-4]
        self._w(buf, W//2 - len(sn)//2, 1, sn)

        # mission text
        if mission_text:
            self._w(buf, 2, H-2, mission_text[:W-4])

        # flavour / scenario text (slow-scroll, changes every 300 frames)
        if frame % 300 < 180:
            self._w(buf, 2, H-1, flavour[:W-4])

        # minimap
        mm_w, mm_h = 14, 7
        ox = int(cam.pos.x) - mm_w//2; oy = int(cam.pos.y) - mm_h//2
        for my in range(mm_h):
            for mx in range(mm_w):
                wx = ox+mx; wy = oy+my
                c = 0
                try: c = self._stage.get_cell(wx, wy) if self._stage else 0
                except: pass
                mc = '#' if c > 0 else '.'
                if c == POR: mc = '@'
                if c == KEY: mc = 'K'
                bx = 1+mx; by = 2+my
                if 0<=bx<W and 0<=by<H: buf[by][bx] = mc
        buf[2+mm_h//2][1+mm_w//2] = '@'

        # powerup status bar
        if powerups:
            px_row = H - 7
            bar_str = ''
            if powerups.get('SPEED_BOOST',0) > 0:
                bar_str += f' [>SPEED:{powerups["SPEED_BOOST"]//62+1}s]'
            if powerups.get('SLOW_TIME',0) > 0:
                bar_str += f' [~SLOW:{powerups["SLOW_TIME"]//62+1}s]'
            if powerups.get('RAPID_FIRE',0) > 0:
                bar_str += f' [!RAPID:{powerups["RAPID_FIRE"]//62+1}s]'
            if bar_str:
                self._w(buf, 2, px_row, ('PWR:' + bar_str)[:self.W-4])

        # landing impact word flash
        if land_timer > 0:
            sym = land_word
            sx = self.W//2 - len(sym)//2
            for i, c in enumerate(sym):
                bx = sx+i
                if 0<=bx<self.W and 0<=(self.H//2+4)<self.H:
                    buf[self.H//2+4][bx] = c

        # transition message
        if trans_timer > 0:
            sx = W//2 - len(trans_msg)//2
            for i, c in enumerate(trans_msg):
                bx = sx+i
                if 0<=bx<W: buf[H//2][bx] = c

        # low health flash border
        if cam.health <= 20 and frame % 8 < 4:
            for x in range(W):
                buf[0][x] = '!'; buf[H-1][x] = '!'
            for y in range(H):
                buf[y][0] = '!'; buf[y][W-1] = '!'

    def _w(self, buf, x, y, text):
        for i, c in enumerate(text):
            bx = x+i
            if 0<=bx<self.W and 0<=y<self.H: buf[y][bx] = c

    def set_stage(self, stage): self._stage = stage

# =============================================================================
#  MISSION SYSTEM
# =============================================================================

class Mission:
    def __init__(self): self.active=None; self.done=False
    def generate(self, kills):
        # Mission system disabled - exploration mode only
        self.active = None
        self.done = False
        return ""
    def update(self, kills, portal_entered, key_held):
        # No active missions
        return None

# =============================================================================
#  TTS ANNOUNCER
# =============================================================================

class Announcer:
    def __init__(self):
        self.subtitle = ""; self.timer = 0
        self._q = []
        self._busy = False

    def say(self, text, duration=200, wav_bytes=None):
        self.subtitle = text; self.timer = duration
        if wav_bytes:
            # Pre-baked WAV — play immediately, no synthesis delay
            def _instant(): _play_async(wav_bytes)
            threading.Thread(target=_instant, daemon=True).start()
            return
        self._q.append(text)
        if not self._busy: self._flush()

    def _flush(self):
        if not self._q: self._busy = False; return
        self._busy = True
        text = self._q.pop(0)
        def _go():
            wav = synth_tts_phrase(text, speed=0.88, pitch_scale=0.96)
            _play_async(wav)
            self._flush()
        threading.Thread(target=_go, daemon=True).start()

    def tick(self):
        if self.timer > 0:
            self.timer -= 1
            if self.timer <= 0: self.subtitle = ""

    def get(self): return self.subtitle

# =============================================================================
#  UNIFIED BASS RUMBLE ENGINE
#
#  Frequency stack (harmonically related, all blend naturally):
#    18 Hz — infrasonic pressure pulse  (felt, barely heard)
#    28 Hz — sub-bass thump             (room-shaking low end)
#    35 Hz — deep growl                 (the 'body' of the rumble)
#    42 Hz — bass punch                 (attack transient layer)
#    50 Hz — anchor tone                (audible root, ties everything together)
#    ~100Hz — first harmonic of 50Hz    (adds clarity/presence)
#
#  Layers:
#    BED   — always-on quiet sub loop. Ducked ~40% while player is airborne.
#    SWELL — periodic dominant surges 15-40s apart. Fill the mix completely.
#            Uses the same freq stack but driven much harder, with slow
#            attack/sustain/decay envelope and thick stereo width.
# =============================================================================

# Unified frequency stack — every synth draws from this
_BASS_STACK = [
    (18.0,  0.08),   # infrasonic pulse  — felt not heard, tucked deep
    (28.0,  0.12),   # sub-bass thump    — idle engine core
    (35.0,  0.10),   # deep growl        — barely there
    (42.0,  0.07),   # bass punch        — ghost layer
    (50.0,  0.14),   # anchor tone       — dominant but quiet
    (50.3,  0.06),   # slight detune     — subtle width
    (49.7,  0.06),   # opposite detune   — subtle width
    (100.0, 0.04),   # first harmonic    — harmonic ref only
    (100.6, 0.02),   # detune harmonic   — air
]


def _bass_frame(t, phases, rng, noise_amp=0.025):
    """
    Compute one audio frame from the unified stack.
    phases: list of running phase accumulators (modified in place).
    Returns raw sample before gain/clip.
    """
    s = 0.0
    for k, (freq, amp) in enumerate(_BASS_STACK):
        inc = TAU * freq * INV_SR
        phases[k] = (phases[k] + inc) % TAU
        s += math.sin(phases[k]) * amp
    s += rng.gauss(0, noise_amp)
    return s


def synth_rumble_bed(dur=5.0, seed=None, airborne=False):
    """
    Continuous sub-bass bed.
    airborne=True: overall gain reduced ~40% (quieter while jumping).
    """
    rng    = random.Random(seed or 1)
    n      = _samples(dur)
    L      = [0.0] * n
    R      = [0.0] * n
    phases = [rng.uniform(0, TAU) for _ in _BASS_STACK]

    gain   = 0.035 if airborne else 0.055
    lfo_r  = rng.uniform(0.05, 0.11)
    lfo_d  = rng.uniform(0.10, 0.20)
    pan_r  = rng.uniform(0.022, 0.038)
    fade   = int(SR * 0.28)

    for i in range(n):
        t   = i * INV_SR
        lfo = 1.0 + lfo_d * math.sin(TAU * lfo_r * t)
        s   = _soft_clip(_bass_frame(t, phases, rng, 0.006) * lfo * gain, 1.02)
        pan = math.sin(TAU * pan_r * t) * 0.22
        L[i] = s * (0.70 + pan)
        R[i] = s * (0.70 - pan)

    for i in range(min(fade, n)):
        f = i / fade;             L[i] *= f; R[i] *= f
    for i in range(max(0, n - fade), n):
        f = (n-1-i) / max(fade,1); L[i] *= f; R[i] *= f

    return _to_wav_stereo(L, R)


def synth_rumble_swell(seed=None):
    """
    DOMINANT SWELL EVENT.
    Uses the same unified stack driven much harder.
    Slow attack (2-3s) → full sustain with breathing LFO → slow decay.
    Duration 9-16s. Fills the sound field completely.
    """
    rng    = random.Random(seed or random.randint(0, 99999))
    dur    = rng.uniform(9.0, 16.0)
    n      = _samples(dur)
    L      = [0.0] * n
    R      = [0.0] * n
    phases = [rng.uniform(0, TAU) for _ in _BASS_STACK]

    attack_end  = int(n * 0.22)
    sustain_end = int(n * 0.68)
    lfo_r  = rng.uniform(0.04, 0.08)
    lfo_d  = rng.uniform(0.12, 0.22)
    pan_r  = rng.uniform(0.016, 0.030)

    # Peak gain drives the stack hard — this dominates the mix
    peak_gain = rng.uniform(0.22, 0.32)

    for i in range(n):
        t = i * INV_SR

        if i < attack_end:
            env = (i / max(1, attack_end)) ** 0.55
        elif i < sustain_end:
            prog = (i - attack_end) / max(1, sustain_end - attack_end)
            lfo  = 1.0 + lfo_d * math.sin(TAU * lfo_r * t)
            # Secondary very-slow breath (0.031 Hz)
            breath = 1.0 + 0.08 * math.sin(TAU * 0.031 * t)
            env  = lfo * breath * (0.92 + 0.08 * math.cos(TAU * 0.11 * prog))
        else:
            prog = (i - sustain_end) / max(1, n - sustain_end)
            env  = (1.0 - prog) ** 1.6

        s   = _bass_frame(t, phases, rng, 0.055)
        s   = _soft_clip(s * peak_gain * env, 1.22)
        pan = math.sin(TAU * pan_r * t) * 0.40
        L[i] = _clamp(s * (0.72 + pan))
        R[i] = _clamp(s * (0.72 - pan))

    return _to_wav_stereo(L, R)


class BassRumbleEngine:
    """
    Unified two-layer bass rumble:
      bed    — continuous quiet loop, ducks when player airborne
      swells — periodic dominant surges that fill the sound field
    The bed and swells share the same _BASS_STACK so they blend seamlessly.
    """
    def __init__(self):
        self._stop         = threading.Event()
        self._airborne     = False   # set by Game each frame
        self._bed_thread   = None
        self._swell_thread = None

    def set_airborne(self, val):
        self._airborne = val

    def start(self):
        self._stop.clear()
        self._bed_thread   = threading.Thread(target=self._bed_loop,   daemon=True)
        self._swell_thread = threading.Thread(target=self._swell_loop, daemon=True)
        self._bed_thread.start()
        self._swell_thread.start()

    def stop(self): self._stop.set()

    def _bed_loop(self):
        rng   = random.Random(7)
        # Pre-bake two variants: normal and airborne-ducked
        def bake(s, ab=False):
            return synth_rumble_bed(5.0, seed=s, airborne=ab)
        clips_norm = [bake(rng.randint(0, 9999)) for _ in range(3)]
        clips_air  = [bake(rng.randint(0, 9999), ab=True) for _ in range(3)]
        idx = 0
        while not self._stop.is_set():
            c = clips_air if self._airborne else clips_norm
            _play_async(c[idx % 3])
            idx += 1
            # Re-bake next slot quietly in background
            s = rng.randint(0, 9999)
            pos = idx + 1
            def _rebake(seed, p):
                clips_norm[p % 3] = bake(seed, False)
                clips_air[p % 3]  = bake(seed, True)
            threading.Thread(target=_rebake, args=(s, pos), daemon=True).start()
            self._stop.wait(4.72)   # just under 5s for seamless overlap

    def _swell_loop(self):
        rng = random.Random(13)
        self._stop.wait(rng.uniform(5.0, 10.0))   # staggered startup
        while not self._stop.is_set():
            cluster = rng.randint(1, 3)
            for _ in range(cluster):
                if self._stop.is_set(): break
                seed = rng.randint(0, 99999)
                def _fire(s):
                    _play_async(synth_rumble_swell(seed=s))
                threading.Thread(target=_fire, args=(seed,), daemon=True).start()
                if cluster > 1:
                    self._stop.wait(rng.uniform(2.5, 5.5))
            self._stop.wait(rng.uniform(15.0, 38.0))

# =============================================================================
#  GENERATIVE AMBIENT SFX — procedural atmospheric texture layer
#  Metallic pings, distant moans, wind gusts, void hums, structural groans
# =============================================================================

def synth_metal_ping(seed=None):
    """Distant metallic structural ping/resonance — like a huge beam settling."""
    rng = random.Random(seed or random.randint(0, 99999))
    n   = _samples(rng.uniform(1.2, 2.4))
    out = []
    f1  = rng.uniform(180, 520)
    f2  = f1 * rng.choice([1.5, 2.0, 2.73, 3.14])
    for i in range(n):
        t   = i * INV_SR
        dur = n * INV_SR
        env = math.sin(math.pi * t / dur) ** 0.3   # slow attack, long tail
        v   = math.sin(TAU * f1 * t) * _exp(t, 1.8) * 0.5
        v  += math.sin(TAU * f2 * t) * _exp(t, 3.2) * 0.28
        v  += (rng.random()*2-1) * _exp(t, 12) * 0.06
        out.append(_clamp(v * env * 0.4))
    # Apply hall reverb — these echo off distant walls
    out = _apply_reverb(out, room=0.85, damp=0.25, wet=0.55, pre_delay_ms=35.0)
    return _to_wav(out)

def synth_void_hum(seed=None):
    """Deep void resonance hum — alien, organic, unsettling."""
    rng = random.Random(seed or random.randint(0, 99999))
    n   = _samples(rng.uniform(3.0, 6.0))
    out = []
    root = rng.uniform(55, 110)
    for i in range(n):
        t    = i * INV_SR
        dur  = n * INV_SR
        lfo  = 1.0 + 0.3 * math.sin(TAU * 0.11 * t)
        v    = math.sin(TAU * root * t) * 0.4
        v   += math.sin(TAU * root * 1.511 * t) * 0.18
        v   += math.sin(TAU * root * 0.499 * t) * 0.28
        v   += (rng.random()*2-1) * 0.04
        env  = math.sin(math.pi * t / dur) ** 0.6
        out.append(_clamp(v * lfo * env * 0.35))
    out = _apply_reverb(out, room=0.75, damp=0.5, wet=0.45, pre_delay_ms=20.0)
    return _to_wav(out)

def synth_wind_gust(seed=None):
    """Wind / air movement through structure — bandpass filtered noise."""
    rng = random.Random(seed or random.randint(0, 99999))
    n   = _samples(rng.uniform(1.5, 3.5))
    out = []
    fc  = rng.uniform(400, 1200)   # filter centre
    for i in range(n):
        t   = i * INV_SR
        dur = n * INV_SR
        env = math.sin(math.pi * t / dur) ** 0.8
        nz  = rng.gauss(0, 0.5)
        # crude bandpass: mix with sine near fc
        v   = (nz * 0.7 + math.sin(TAU * fc * t) * 0.3) * env
        out.append(_clamp(v * 0.22))
    out = _apply_echo(out, delay_ms=rng.uniform(80, 200), feedback=0.25, wet=0.20)
    return _to_wav(out)

def synth_structure_groan(seed=None):
    """Low structural groan — like the world itself shifting."""
    rng = random.Random(seed or random.randint(0, 99999))
    n   = _samples(rng.uniform(1.8, 4.0))
    out = []
    f   = rng.uniform(42, 90)
    for i in range(n):
        t   = i * INV_SR
        dur = n * INV_SR
        sweep = f * (1.0 + 0.18 * math.sin(TAU * 0.22 * t))
        env   = math.sin(math.pi * t / dur) ** 0.5
        v     = math.sin(TAU * sweep * t) * 0.55
        v    += math.sin(TAU * sweep * 2.02 * t) * 0.18
        v    += (rng.random()*2-1) * 0.08
        out.append(_soft_clip(v * env * 0.38, 1.1))
    out = _apply_reverb(out, room=0.70, damp=0.60, wet=0.40, pre_delay_ms=15.0)
    return _to_wav(out)

# =============================================================================
#  AMBIENT AUDIO ENGINE — continuous bass drones + pads + generative SFX
# =============================================================================

class AmbientEngine:
    def __init__(self):
        self._stop  = threading.Event()
        self._mode  = "dungeon"
        self._thread = None
        self._sfx_thread = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._sfx_thread = threading.Thread(target=self._sfx_loop, daemon=True)
        self._sfx_thread.start()

    def stop(self): self._stop.set()

    def set_mode(self, stage_name):
        n = stage_name.lower()
        if "waste"   in n: self._mode = "wastes"
        elif "dungeon" in n: self._mode = "dungeon"
        elif "arena"   in n: self._mode = "arena"
        else:                self._mode = "sanctum"

    def _loop(self):
        """Infinite layered drone + pad loop with reverb baked in."""
        rng   = random.Random()
        while not self._stop.is_set():
            dur  = rng.uniform(8.0, 18.0)
            seed = rng.randint(0, 99999)
            mode = self._mode
            def _play_drone(d, s):
                raw = synth_bass_drone(d, seed=s)
                # Decode stereo, apply subtle reverb to each channel
                buf = io.BytesIO(raw)
                with wave.open(buf, 'rb') as w:
                    frames = w.readframes(w.getnframes())
                    nc = w.getnchannels()
                n_smp = len(frames) // (2 * nc)
                L = [struct.unpack_from('<h', frames, i*4)[0]/32767.0   for i in range(n_smp)]
                R = [struct.unpack_from('<h', frames, i*4+2)[0]/32767.0 for i in range(n_smp)]
                # Light hall reverb on drone
                L = _apply_reverb(L, room=0.62, damp=0.55, wet=0.22, pre_delay_ms=8.0)
                R = _apply_reverb(R, room=0.65, damp=0.52, wet=0.22, pre_delay_ms=11.0)
                rev_wav = _to_wav_stereo(L, R)
                _play_async(rev_wav)
            threading.Thread(target=_play_drone, args=(dur, seed), daemon=True).start()

            # Occasional ambient pad with reverb
            if rng.random() < 0.60:
                pad_seed = rng.randint(0, 99999)
                pad_dur  = rng.uniform(10.0, 20.0)
                def _play_pad(d, s, m):
                    raw = synth_ambient_pad(d, seed=s, mode=m)
                    smp = _wav_to_samples(raw)
                    # Longer room reverb on pads — very washy/atmospheric
                    smp = _apply_reverb(smp, room=0.80, damp=0.38, wet=0.38, pre_delay_ms=18.0)
                    _play_async(_samples_to_wav(smp))
                threading.Thread(target=_play_pad, args=(pad_dur, pad_seed, mode), daemon=True).start()

            sleep_t = rng.uniform(6.0, 14.0)
            self._stop.wait(sleep_t)

    def _sfx_loop(self):
        """
        Generative atmospheric SFX thread.
        Fires random ambient sounds — metal pings, void hums, wind gusts,
        structural groans — on sparse random timings.
        These create the illusion of a living, breathing environment.
        """
        rng = random.Random()
        # SFX catalogue: (generator_fn, base_interval_range, probability)
        catalogue = [
            (synth_metal_ping,       (8.0,  22.0), 0.55),
            (synth_void_hum,         (12.0, 30.0), 0.45),
            (synth_wind_gust,        (15.0, 35.0), 0.40),
            (synth_structure_groan,  (20.0, 45.0), 0.35),
        ]
        # Stagger initial delays so nothing fires at once
        next_times = [rng.uniform(3.0, cat[1][0]) for cat in catalogue]

        while not self._stop.is_set():
            now = time.time()
            sleep_min = 2.0
            for idx, (fn, (lo, hi), prob) in enumerate(catalogue):
                if now >= next_times[idx]:
                    if rng.random() < prob:
                        seed = rng.randint(0, 99999)
                        def _fire(f, s):
                            _play_async(f(seed=s))
                        threading.Thread(target=_fire, args=(fn, seed), daemon=True).start()
                    next_times[idx] = now + rng.uniform(lo, hi)
                gap = next_times[idx] - now
                if gap < sleep_min:
                    sleep_min = gap
            self._stop.wait(max(0.5, sleep_min))

# =============================================================================
#  SOUND CACHE — pre-generate all SFX at startup
# =============================================================================

class SFX:
    def __init__(self, root):
        self._root  = root
        self._cache = {}          # raw WAV bytes
        self._spatial = {}        # (name, dist_bucket, wp_bucket) -> processed WAV bytes
        self._cd    = {}
        self._gen_thread = threading.Thread(target=self._preload, daemon=True)
        self._gen_thread.start()

    def _preload(self):
        """Generate all SFX in background at startup."""
        self._cache['gun']      = synth_gun_crack()
        self._cache['hit']      = synth_hit()
        self._cache['kill']     = synth_kill()
        self._cache['overheat'] = synth_overheat()
        self._cache['portal']   = synth_portal()
        self._cache['step']     = synth_step()
        self._cache['land']     = synth_land_clank()
        self._cache['jump']     = synth_jump_whoosh()
        self._cache['death']    = synth_death()
        # Pre-bake spawn alerts — must be ready before first spawn
        self._cache['alert_1']  = synth_tts_phrase("Stay alert.", speed=0.88, pitch_scale=0.96)
        self._cache['alert_2']  = synth_tts_phrase("Stay alive.", speed=0.88, pitch_scale=0.96)

    def _get_spatial(self, name, wav, dist, wall_prox):
        """
        Return spatially-processed WAV — baked into cache keyed on
        quantised (name, dist_bucket, wp_bucket) so repeated identical
        spatial contexts reuse the pre-baked result instantly.
        Baking happens in this thread (called from a daemon thread already).
        """
        # Quantise to 4 distance buckets and 4 room buckets
        db = min(3, int(dist / 5.0))          # 0-4, 5-9, 10-14, 15+
        wb = min(3, int(wall_prox * 4.0))     # 0.0-0.24, 0.25-0.49 …
        key = (name, db, wb)
        if key in self._spatial:
            return self._spatial[key]
        # Bake
        processed = apply_spatial_sfx(wav, dist=max(1.0, db*5.0 + 2.5),
                                       wall_proximity=wb / 3.0)
        # Limit cache size to avoid memory bloat
        if len(self._spatial) > 120:
            # Evict oldest ~half
            keys = list(self._spatial.keys())
            for k in keys[:60]:
                del self._spatial[k]
        self._spatial[key] = processed
        return processed

    def play(self, name, cd=0.08, dist=1.0, wall_prox=0.5):
        """
        Play SFX with optional spatial processing.
        dist       : world-distance to source (1=nearby, 20=far)
        wall_prox  : 0=open space, 1=tight enclosed corridor
        All processing is async — main loop never blocks.
        """
        now = time.time()
        if now - self._cd.get(name, 0) < cd: return
        self._cd[name] = now
        wav = self._cache.get(name)
        if not wav:
            self._root.bell(); return
        # Fire-and-forget spatial thread
        def _spatial_play(w, d, wp):
            if d > 1.5 or wp > 0.15:
                w = self._get_spatial(name, w, d, wp)
            _play_async(w)
        threading.Thread(target=_spatial_play, args=(wav, dist, wall_prox), daemon=True).start()

# =============================================================================
#  GAME — the whole thing
# =============================================================================

class Game:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"VOID ENGINE v{VERSION}")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="black")

        # Monospace ASCII canvas
        self.lbl = tk.Label(self.root, text="", font=("Courier New", 9),
                            fg="#E8E8E8", bg="black", justify="left", anchor="nw")
        self.lbl.pack(expand=True, fill="both")

        self.inp    = Input(self.root)
        self.cam    = Camera()
        self.router = MapRouter()
        self.ren    = Renderer(W, H)
        self.hud    = HUD(W, H)
        self.sfx    = SFX(self.root)
        self.parts  = Particles()
        self.tts    = Announcer()
        self.music  = AmbientEngine()
        self.rumble = BassRumbleEngine()
        self.mission = Mission()

        self.heat      = 0.0
        self.overheated = False
        self.score     = 0
        self.kills     = 0
        self.tracers   = []
        self.entities  = []
        self.key_held  = False
        self.mission_text = ""
        self.flavour   = gen_scenario_flavour()
        self._frame    = 0
        self._step_cd  = 0
        self._dead     = False
        self._dead_timer = 0
        self._respawn_timer = 0
        self._land_word  = ''
        self._land_timer = 0
        self._stillness_timer = 0  # Timer for displaying "STILLNESS ACHIEVED"
        self._stillness_announced = False  # Track if we've announced stillness globally
        self._powerups   = {'SPEED_BOOST':0,'SLOW_TIME':0,'RAPID_FIRE':0}
        self._slow_pitch = 1.0   # real-time pitch factor for slow-time
        self.pu_spawner  = PowerupSpawner()

        # Startup sequence
        self.hud.set_stage(self.router.stage)
        self._spawn_entities()
        self.music.start()
        self.rumble.start()
        self.music.set_mode(self.router.stage.name)

        # Announce on startup (slight delay for audio to load)
        def _do_startup_alert():
            wav = self.sfx._cache.get('alert_1') or self.sfx._cache.get('alert_2')
            if wav: self.tts.say("Stay alert.", 180, wav_bytes=wav)
            else:   self.tts.say("Stay alert.", 180)
        self.root.after(1800, _do_startup_alert)

        self.root.after(16, self.loop)

    def _wall_proximity(self):
        """
        Sample 8 rays around player to estimate enclosure (0=open, 1=enclosed).
        Uses cached router calls — very fast.
        """
        cam = self.cam; router = self.router
        hits = 0; total = 8
        for i in range(total):
            a  = TAU * i / total
            dx = math.cos(a); dy = math.sin(a)
            for r in range(1, 6):
                cx = cam.pos.x + dx * r
                cy = cam.pos.y + dy * r
                if router.get_cell(cx, cy) != EMPTY:
                    hits += 1
                    break
        return hits / total   # 0.0 = open field, 1.0 = completely surrounded

    # ── SPAWN ──────────────────────────────────────────────────────────────
    def _spawn_entities(self):
        self.entities.clear()
        stage  = self.router.stage
        count  = 14 if isinstance(stage, StageArena) else 7
        for i in range(count):
            ang  = random.uniform(0, TAU)
            dist = random.uniform(4, 16)
            x    = self.cam.pos.x + math.cos(ang)*dist
            y    = self.cam.pos.y + math.sin(ang)*dist
            c    = random.choice(ENEMY_CHARS)
            self.entities.append(Entity(x, y, c))
        # mission
        desc = self.mission.generate(self.kills)
        self.mission_text = desc
        self.tts.say(desc)
        self.key_held = False
        self.flavour  = gen_scenario_flavour()
        # place key if needed
        if self.mission.active and self.mission.active[0] == "find_key":
            self._place_key()
        # spawn alert TTS
        def _sa_say():
            pick = random.randint(1,2)
            wav  = self.sfx._cache.get(f'alert_{pick}')
            msg  = "Stay alert." if pick==1 else "Stay alive."
            if wav: self.tts.say(msg, 140, wav_bytes=wav)
            else:   self.tts.say(msg, 140)
        self.root.after(500, _sa_say)
        # spawn a powerup nearby
        def _pu_spawn(cx=self.cam.pos.x, cy=self.cam.pos.y):
            self.pu_spawner.spawn_near(cx, cy, self.router)
        self.root.after(600, _pu_spawn)

    def _place_key(self):
        for _ in range(200):
            ang = random.uniform(0, TAU)
            r   = random.uniform(6, 14)
            x   = self.cam.pos.x + math.cos(ang)*r
            y   = self.cam.pos.y + math.sin(ang)*r
            if self.router.get_cell(x, y) == EMPTY:
                self.router.inject(x, y, KEY)
                return

    # ── SHOOTING ───────────────────────────────────────────────────────────
    def _check_shoot(self):
        cam = self.cam
        best = None; best_dist = 999
        for e in self.entities:
            if not e.alive(): continue
            # Skip pacified NPCs - Emitter does nothing to them once still
            if e.pacified: continue
            dx = e.x - cam.pos.x; dy = e.y - cam.pos.y
            d  = math.hypot(dx, dy)
            if d < 0.5 or d > 20: continue
            dot = cam.dir.x*(dx/d) + cam.dir.y*(dy/d)
            if dot > 0.96 and d < best_dist:
                best = e; best_dist = d
        if best:
            killed = best.hit(1)
            invD   = 1.0/(cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y+1e-9)
            dx = best.x - cam.pos.x; dy = best.y - cam.pos.y
            _best_dist = math.hypot(dx, dy)
            tY = invD*(-cam.plane.y*dx + cam.plane.x*dy)
            if tY > 0:
                tX = invD*(cam.dir.y*dx - cam.dir.x*dy)
                sx = int(W/2*(1+tX/tY)); sy = H//2
                self.parts.emit(sx, sy, 'spark', 5)
                _wp = getattr(self, '_wall_prox', 0.5)
                if killed:
                    self.parts.emit(sx, sy, 'blood', 10)
                    self.parts.emit(sx, sy, 'gore', 4)
                    self.kills += 1
                    self.score += 100
                    self.sfx.play('kill', 0.05, dist=_best_dist, wall_prox=_wp)
                    if random.random() < 0.35:
                        self.tts.say(gen_kill_flavour(), 90)
                else:
                    self.sfx.play('hit', 0.05, dist=_best_dist, wall_prox=_wp)

    # ── UPDATE ─────────────────────────────────────────────────────────────
    def update(self):
        self._frame += 1
        inp = self.inp; cam = self.cam; router = self.router

        # Cache spatial context once per frame (cheap: 8 short ray marches)
        if self._frame % 4 == 0:   # update every 4 frames (~15Hz) — plenty fast
            self._wall_prox = self._wall_proximity()
        wp = getattr(self, '_wall_prox', 0.5)

        # death state
        if self._dead:
            self._dead_timer -= 1
            if self._dead_timer <= 0:
                # respawn
                cam.health  = cam.max_health
                cam.pos     = V2(4.5, 4.5)
                self.heat   = 0; self.overheated = False
                self._dead  = False
                self._spawn_entities()
                _pick2 = random.randint(1,2)
                _wav2  = self.sfx._cache.get(f'alert_{_pick2}')
                _msg2  = "Stay alert." if _pick2==1 else "Stay alive."
                if _wav2: self.tts.say(_msg2, 160, wav_bytes=_wav2)
                else:     self.tts.say(_msg2, 160)
            return

        # check player death
        if cam.health <= 0 and not self._dead:
            self._dead = True; self._dead_timer = 120
            self.sfx.play('death', 0.0, dist=1.0, wall_prox=wp)
            self.tts.say(gen_death_quote())
            self.score = max(0, self.score - 200)
            return

        # movement
        _pu = self._powerups
        base_spd = 0.18 if (inp.held('shift') or inp.held('shift_l')) else 0.12
        spd = base_spd * (2.0 if _pu['SPEED_BOOST'] > 0 else 1.0)
        # slow-time: halve all entity speeds visually + self speed
        _slow = _pu['SLOW_TIME'] > 0
        if _slow: spd *= 0.4
        nx, ny = cam.pos.x, cam.pos.y; moving = False
        if inp.held('w'):     nx += cam.dir.x*spd;  ny += cam.dir.y*spd;  moving=True
        if inp.held('s'):     nx -= cam.dir.x*spd;  ny -= cam.dir.y*spd;  moving=True
        if inp.held('a'):     nx -= cam.dir.y*spd;  ny += cam.dir.x*spd;  moving=True
        if inp.held('d'):     nx += cam.dir.y*spd;  ny -= cam.dir.x*spd;  moving=True
        if router.get_cell(nx, cam.pos.y) == EMPTY: cam.pos.x = nx
        if router.get_cell(cam.pos.x, ny) == EMPTY: cam.pos.y = ny
        # Bob only when grounded — airborne = weightless float
        if not cam.jumping: cam.step_bob(moving)
        else: cam.bob *= 0.85  # bleed off residual bob smoothly

        # jump (V key) — edge-triggered
        v_now = inp.held('v')
        if v_now and not getattr(self, '_v_prev', False):
            cam.jump(); self.sfx.play('jump', 0.0, dist=1.0, wall_prox=wp)
            self._step_cd = 30
        self._v_prev = v_now
        landed = cam.update_jump()
        self.rumble.set_airborne(cam.jumping)
        if landed:
            cam.land_shake(6.0); self.sfx.play('land', 0.0, dist=1.0, wall_prox=wp)
            self._land_word = random.choice(LAND_WORDS); self._land_timer = 28
            self._v_prev = True   # force re-press required — no accidental re-jump

        # footstep — grounded only
        if moving and not cam.jumping:
            self._step_cd -= 1
            if self._step_cd <= 0:
                self.sfx.play('step', 0.0, dist=1.0, wall_prox=wp); self._step_cd = 22

        # look
        rot = 0.062
        if inp.held('left'):  cam.rotate(rot)
        if inp.held('right'): cam.rotate(-rot)
        if inp.held('up'):    cam.pitch = min(14, cam.pitch+3)
        if inp.held('down'):  cam.pitch = max(-14, cam.pitch-3)
        if not (inp.held('up') or inp.held('down')): cam.pitch *= 0.88

        # weapon heat system
        if inp.firing() and not self.overheated:
            _rf_mult = 0.35 if self._powerups['RAPID_FIRE'] > 0 else 1.0
            self.heat = min(100, self.heat + 3.8 * _rf_mult)
            if self.heat >= 100:
                self.overheated = True
                self.sfx.play('overheat', 0.4, dist=1.0, wall_prox=wp)
                self.tts.say("Emitter jammed! Cool down.", 120)
            else:
                self.tracers.append([W//2, H//2, 14])
                self._check_shoot()
                self.sfx.play('gun', 0.07, dist=1.0, wall_prox=wp)
        else:
            self.heat = max(0, self.heat - 2.2)
            if self.heat <= 0 and self.overheated:
                self.overheated = False
                self.tts.say("Emitter ready.", 80)

        # tracer decay
        self.tracers = [t for t in self.tracers if t[2]>0]
        for t in self.tracers: t[2] -= 2

        # entities
        _slow_active = self._powerups['SLOW_TIME'] > 0
        _spd_mult = 0.25 if _slow_active else 1.0
        for e in self.entities:
            e.speed = ENEMY_SPEED.get(e.char, 0.02) * _spd_mult
            e.update(cam, router)
        
        # Check for newly pacified entities and announce via TTS (only once globally)
        any_newly_pacified = any(e.newly_pacified for e in self.entities)
        if any_newly_pacified and not self._stillness_announced:
            self.tts.say("Stillness Achieved. Peace and Bliss.", 150)
            self._stillness_timer = 180  # Show "STILLNESS ACHIEVED" in HUD for ~3 seconds
            # Display in lower-left text area
            self._land_word = "Stillness Achieved. Peace and Bliss"
            self._land_timer = 180  # Show for 3 seconds
            self._stillness_announced = True  # Mark as announced globally
        
        # Clear newly_pacified flags
        for e in self.entities:
            if e.newly_pacified:
                e.newly_pacified = False  # Clear flag
        
        self.entities = [e for e in self.entities
                         if not (e.state=='DEAD' and e.dead_timer<=0)]

        # INFINITE ENEMY POPULATION — keep 8-12 alive at all times,
        # trickle in new enemies from a distance so it never feels empty
        # but never swarms the player.
        alive_count = sum(1 for e in self.entities if e.alive())
        TARGET_MIN = 7
        TARGET_MAX = 11
        # Spawn up to 2 new enemies per check, but only every 40 frames
        if self._frame % 40 == 0 and alive_count < TARGET_MAX:
            to_spawn = min(2, TARGET_MIN - alive_count + 1)
            for _ in range(max(0, to_spawn)):
                # spawn far enough away to not instantly aggro
                ang  = random.uniform(0, TAU)
                dist = random.uniform(14, 22)
                sx   = cam.pos.x + math.cos(ang)*dist
                sy   = cam.pos.y + math.sin(ang)*dist
                if router.get_cell(sx, sy) == EMPTY:
                    self.entities.append(Entity(sx, sy, random.choice(ENEMY_CHARS)))

        # powerup pickup check
        picked = self.pu_spawner.check_pickup(cam.pos.x, cam.pos.y)
        if picked:
            self._powerups[picked] = POWERUP_DURATION
            label = POWERUP_LABELS[picked]
            self.tts.say(label, 140)
            self._land_word = label; self._land_timer = 55

        # tick powerup timers
        self.pu_spawner.update()
        for k in self._powerups:
            if self._powerups[k] > 0: self._powerups[k] -= 1

        # land word decay
        if self._land_timer > 0: self._land_timer -= 1
        
        # stillness achieved display
        if self._stillness_timer > 0:
            self._stillness_timer -= 1
            self.flavour = "STILLNESS ACHIEVED"
        elif self._stillness_timer == 0 and self.flavour == "STILLNESS ACHIEVED":
            # Reset to random scenario when timer expires
            self.flavour = gen_scenario_flavour()

        # Full wave respawn only when truly empty (failsafe)
        if alive_count == 0 and len(self.entities) == 0:
            self._spawn_entities()

        # portal check
        portal_entered = False
        if self._frame % 10 == 0:
            cx, cy = int(cam.pos.x), int(cam.pos.y)
            if router.get_cell(cx, cy) == POR:
                if (self.mission.active and
                    self.mission.active[0] == "find_key" and not self.key_held):
                    self.tts.say("Portal locked. Find the key first.")
                else:
                    portal_entered = True
                    self.sfx.play('portal', 0.0, dist=1.0, wall_prox=wp)
                    self.score += 500
                    router.advance(cam, self._spawn_entities)
                    self.hud.set_stage(router.stage)
                    self.music.set_mode(router.stage.name)

        # key pickup
        if not self.key_held:
            kx, ky = int(cam.pos.x), int(cam.pos.y)
            if router.get_cell(kx, ky) == KEY:
                self.key_held = True
                self.score += 200
                self.tts.say("Key acquired. Find the portal.")
                router.inject(kx, ky, EMPTY)

        # mission update
        result = self.mission.update(self.kills, portal_entered, self.key_held)
        if result:
            self.score += 100 * (self.mission.active[1] if self.mission.active else 0)
            self.tts.say(result)
            self.mission_text = "Mission complete! New orders incoming..."
            self.root.after(2200, self._next_mission)

        # rare reality rift
        if random.random() < 0.00025:
            cam.pos = V2(random.uniform(2,12), random.uniform(2,12))
            router.trans_timer = 50
            router.trans_msg   = "** REALITY RIFT **"
            self.tts.say("Reality rift detected.", 100)

        # transition timer
        if router.trans_timer > 0: router.trans_timer -= 1

        # meta difficulty (M key)
        if inp.held('m') and not hasattr(self,'_meta_lock'):
            self._meta_improve()
            self._meta_lock = True
        elif not inp.held('m') and hasattr(self,'_meta_lock'):
            del self._meta_lock

        self.parts.update()
        self.tts.tick()

    def _next_mission(self):
        self.router._idx = (self.router._idx+1) % len(self.router._stages)
        self.router.stage = self.router._stages[self.router._idx]
        self.cam.pos = V2(4.5, 4.5); self.cam.pitch = 0
        self.hud.set_stage(self.router.stage)
        self._spawn_entities()
        self.key_held  = False
        self.mission_text = self.mission.active[2] if self.mission.active else "New orders"

    def _meta_improve(self):
        rate = self.kills / max(1, self._frame//60)
        if rate > 1.8:
            for k in ENEMY_SPEED: ENEMY_SPEED[k] = min(0.048, ENEMY_SPEED[k]*1.06)
            for k in ENEMY_DMG:   ENEMY_DMG[k]   = min(20, ENEMY_DMG[k]+1)
            self.tts.say("Difficulty raised. They're faster now.")
        else:
            for k in ENEMY_SPEED: ENEMY_SPEED[k] = max(0.008, ENEMY_SPEED[k]*0.94)
            self.tts.say("Difficulty lowered. Regain composure.")
        self._spawn_entities()

    # ── HUD CALLBACK ───────────────────────────────────────────────────────
    def _hud_cb(self, buf):
        # tracer beams
        for t in self.tracers:
            bx, by, life = t
            for dy in range(min(life, H-by)):
                ry = by+dy; jitter = random.randint(-1,1); bxj = bx+jitter
                if 0<=bxj<W and 0<=ry<H: buf[ry][bxj] = '|'

        self.hud.draw(buf, self.cam, self.heat, self.overheated,
                      self.score, self.kills,
                      self.router.stage.name,
                      self.router.trans_timer, self.router.trans_msg,
                      self.entities, self.mission_text,
                      self.flavour, self._frame,
                      powerups=self._powerups,
                      land_word=self._land_word,
                      land_timer=self._land_timer)
        # draw world powerup glyphs
        # powerup glyphs drawn inside renderer with real zbuf

        # TTS subtitle
        sub = self.tts.get()
        if sub:
            y = H-6
            self._banner(buf, sub, y, W)

        # death screen overlay
        if self._dead:
            msg = ">>> YOU HAVE DIED <<< RESPAWNING..."
            self._banner(buf, msg, H//2, W)

    def _banner(self, buf, msg, y, W):
        sx = max(0, W//2 - len(msg)//2)
        for i, c in enumerate(msg):
            bx = sx+i
            if 0<=bx<W and 0<=y<H: buf[y][bx] = c

    # ── MAIN LOOP ──────────────────────────────────────────────────────────
    def loop(self):
        self.update()
        frame = self.ren.render(self.cam, self.router, self.entities,
                                self.parts, self._hud_cb, self.pu_spawner)
        self.lbl.config(text=frame)
        # Adaptive frame pacing: target 60fps, fallback to 30fps
        elapsed = time.time() - getattr(self, '_last_t', time.time())
        self._last_t = time.time()
        delay = max(16, min(33, int(elapsed * 1000 * 0.9 + 16 * 0.1)))
        self.root.after(delay, self.loop)

# =============================================================================
#  ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    g = Game()
    g.root.mainloop()


