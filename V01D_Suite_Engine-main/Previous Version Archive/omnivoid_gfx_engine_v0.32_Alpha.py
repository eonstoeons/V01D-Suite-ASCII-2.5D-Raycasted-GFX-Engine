#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OMNI VOID ENGINE  —  single-file, zero-dependency, fully offline Python/tkinter.
=================================================================================
All three versions merged into one. Pure stdlib. No pip installs needed.

THREE GFX ENGINES, AUTO-SWAPPING:
  On foot / boarding  ->  CybervoidFusion DDA raycaster (true look left/right)
  In vehicle          ->  Phos City Night Drive renderer (windowed buildings)
  In space            ->  Void Space Sim 6-DOF starfield cosmos

HOW TO MOD THIS FILE (beginner guide):
  - CONFIG section:  change colors, speed, grid size, FPS
  - CONTENT section: add dialogue lines, log entries, artifact glyphs
  - ENEMIES:         change ENEMY_HP / ENEMY_SPD / ENEMY_DMG dicts
  - WORLDS:          add a new Router class (see CityRouter as a template)
  - AUDIO:           tweak _wave() calls in Audio._bake() for new SFX

CONTROLS:
  On foot / boarding:
    WASD              move / strafe
    arrow LEFT/RIGHT  turn left / right
    arrow UP/DOWN     move forward / backward
    PgUp/PgDn         look pitch up / down
    SHIFT  sprint     V  jump
    SPACE/LMB   fire emitter  (confuses -> pacifies, never kills)
    E           interact — enter vehicle, terminal, ship
    F           take off to space
    T           teleport to spaceship (on same planet)
    L           open/close artifact log
  In vehicle:
    W/S          throttle         A/D         steer
    arrow LEFT   look / yaw left  arrow RIGHT look / yaw right
    SHIFT  boost   E  exit
  In space:
    WASD  pitch/yaw   Q/E  roll   arrow-keys  strafe
    SPACE  thrust      B  boost   F  land      G  board enemy ship
  Any mode:
    M  toggle music    R  toggle SFX    ESC  quit
"""

import tkinter as tk
import math, random, time, threading, array, io, wave, subprocess, tempfile

# ================================================================ CONFIG
WORLD_SEED   = 42
GRID_W       = 140
GRID_H       = 44
SPACE_W      = 1100
SPACE_H      = 800
FPS          = 45
SR           = 22050
TAU          = math.tau

BG    = "#000005"
FG    = "#00ff88"
WHITE = "#ffffff"
AMBER = "#ffb000"
GLOW  = "#ffcc00"
RED   = "#ff4444"
DIM   = "#446644"

EMPTY    = 0
WALL     = 1
TERMINAL = 2

CITY    = 0
DUNGEON = 1
WILDS   = 2
MOON    = 3
BIOME_NAMES = {CITY:"PHOS CITY", DUNGEON:"VOID DUNGEON",
               WILDS:"OPEN WILDS", MOON:"MOON SURFACE"}

# ================================================================ CONTENT

ENEMY_CHARS = ['Z','D','G','S','B','M']
ENEMY_HP    = {'Z':17,'D':17,'G':17,'S':17,'B':17,'M':17}
ENEMY_SPD   = {'Z':0.020,'D':0.015,'G':0.035,'S':0.010,'B':0.025,'M':0.020}
ENEMY_DMG   = {'Z':8,'D':5,'G':10,'S':4,'B':12,'M':7}

DIALOGUE = {
    'Z':["Who goes there?","I feel uneasy..","What do you want?","Stay back.","...leave me alone."],
    'D':["You shouldn't be here.","I've been waiting.","The void watches.","Turn back now.","...silence..."],
    'G':["HALT. IDENTIFY.","Authorization code?","Sector locked down.","Move along.","You are trespassing."],
    'S':["...","...hmm.","...you smell odd.","...leave.","...please go."],
    'B':["COME CLOSER.","I WILL BREAK YOU.","FEAR ME.","YOU CANNOT PASS.","WITNESS MY POWER."],
    'M':["The signal is strong today.","Have you seen the light?","All will return to the void.",
         "The pattern repeats.","Convergence is near."],
}

MEDITATE = ["Thank you","I'm finally free","I feel pure peace",
            "I find stillness","[entering meditative state]"]

PU_TYPES  = ['SPEED_BOOST','SLOW_TIME','RAPID_FIRE']
PU_GLYPHS = {'SPEED_BOOST':'>','SLOW_TIME':'~','RAPID_FIRE':'!'}
PU_LABELS = {'SPEED_BOOST':'> SPEED x2','SLOW_TIME':'~ SLOW TIME','RAPID_FIRE':'! RAPID FIRE'}
PU_DUR    = 620

LAND_WORDS = ["K-KLANNNG","THOOM","KRAKOOOM","WHUMPH","B-DONNNG","CRANNNG","CHONK","SKHRRRANG"]

ARTIFACTS = [
    "\u2741","*","#","\u25c6","\u2665","\u25aa","\u00a4","\u263c","\u2318","\u2767",
    "\u269b","\u2042","\u204b","\u2021","\u2623","\u2620","\u2609","\u2604","\u2301","\u2302"
]

LOG_ENTRIES = [
    "Old pond / a frog jumps in / sound of water",
    "Over the wintry / forest, winds howl in rage / with no leaves to blow",
    "An old silent pond / a frog jumps into the pond / splash! Silence again",
    "In the cicada's cry / no sign can foretell / how soon it must die",
    "The light of a candle / is transferred to another candle / spring twilight",
    "The map is not the territory.\nThe territory has no edges.\nYou are the cartographer\nof a land you cannot name.",
    "Between the stars / something breathes.\nNot air. Not light.\nA patience older\nthan the concept of waiting.",
    "The signal repeats.\nThe signal repeats.\nNo one sent it.\nYou are receiving it anyway.",
    "First there was darkness.\nThen there was a question about darkness.\nThe question is still running.",
    "Every door opens\nonto another door.\nThe rooms between\nare where you actually live.",
    "Quantum entanglement: two particles remain connected regardless of distance. Measuring one instantly affects the other.",
    "The Fermi Paradox: given the age and size of the universe, intelligent life should be everywhere. Yet silence.",
    "Entropy always increases. But locally, temporarily, complexity can emerge — you are one such emergence.",
    "The observable universe is 93 billion light-years across. Beyond that: unknown.",
    "Dark matter comprises 27% of the universe yet emits no light and has never been directly observed.",
    "The brain generates consciousness, yet cannot fully model itself modeling itself. Self-reference has a horizon.",
    "Music exists only in time. A note heard is already gone. What you call a melody is a construction of memory.",
    "There are more possible chess games than atoms in the observable universe. Most will never be played.",
    "The mitochondria in your cells have their own separate DNA, remnants of an ancient bacterium never released.",
    "Language shapes thought. The Hopi language has no tense for past or future.",
    "A city is a machine for living in.\nBut the machine has forgotten its purpose.\nNow it just runs.",
    "Every light in every window\nis someone deciding something.\nYou will never know what.",
    "The grid beneath the city\npredates the city.\nThe city is just the grid\nlearning to dream.",
    "Transmission log 447-C: carrier signal intact. Content: unknown. Origin: unknown. Age: unknown.",
    "They built the roads first.\nThen the buildings came\nto crowd around the roads\nlike they were warmth.",
    "Speed is the illusion that distance\ndoes not exist.\nYou are still far from everything.",
    "LOG CORRUPTED\n...\n...\nfragment: '...do not stop the vehicle...'",
    "No map survives contact with the territory.\nNo territory survives contact with time.",
    "You are moving through a place\nthat does not know you are there.\nThis is most places.",
    "The stars are not a ceiling.\nThey are a floor\nyou have not yet learned to walk on.",
    "Sector 7 clearance log: access revoked. Reason: [REDACTED]. Date: [REDACTED].",
    "There is no outside.\nEvery outside\nis just a larger inside\nyou have not mapped yet.",
    "Something followed the vehicle for 3.2 km.\nWhen it stopped, nothing was there.\nThe log ends here.",
    "Archive entry 0091: the last library burned.\nWhat was saved: everything small.\nWhat was lost: the index.",
    "Motion is not progress.\nProgress is not arrival.\nArrival is not the end.",
    "You passed this block before.\nThe block does not remember.\nOnly you remember.\nOnly you.",
    "Broadcast fragment: '...all units return to base...'\nNo base was ever found.\nAll units kept moving.",
    "The void between objects\nis not empty.\nIt is full of the absence\nof everything that was there.",
    "Speed log: maximum recorded 94 mph.\nDriver: unknown.\nDestination: unknown.\nOutcome: pending.",
    "There is a frequency\nbelow hearing\nthat the city emits at night.\nAnimals know it. You feel it.",
    "Every road leads somewhere.\nNot every somewhere\nis worth the road.",
    "Archive node 33: last ping 14 cycles ago.\nContent preserved.\nAccess: open.\nReader count: 1.",
    "The city breathes at 0.08 Hz.\nOne breath per twelve seconds.\nCount the traffic lights.",
    "You are a moving point\nin a static grid.\nThe grid does not move for you.\nYou move for the grid.",
    "Signal decay rate: nominal.\nCarrier integrity: 71%.\nMessage: still transmitting.\nRecipient: still unknown.",
    "Fragment recovered from sector 12:\n'...the engine never stopped...\n...we just stopped hearing it...'",
]

# Procedural log fragment generator — called at runtime for infinite unique entries
_LOG_SUBJECTS  = ["the signal","the grid","the archive","the void","the road","the city","the engine",
                  "the frequency","the last broadcast","sector zero","node 7","the carrier wave",
                  "the pattern","the corridor","the compound","the observer","unit 9","the record"]
_LOG_VERBS     = ["persists","decays","repeats","shifts","expands","contracts","remembers","forgets",
                  "returns","departs","calculates","observes","transmits","receives","collapses","endures"]
_LOG_OBJECTS   = ["without source","beyond the boundary","at unknown intervals","in all directions",
                  "toward no destination","from the beginning","after the signal ends","in silence",
                  "with no recipients","through every wall","across every sector","indefinitely"]
_LOG_CLOSERS   = ["no further data","log ends here","access restricted","content unverified",
                  "origin unknown","timestamp corrupted","classification: open","filed under: void",
                  "cross-reference: none","redundancy confirmed","signal strength: trace"]

def _gen_log_entry(seed):
    """Generate a unique procedural archive log entry from a seed."""
    r = random.Random(seed)
    form = r.randint(0, 4)
    if form == 0:
        return (f"ARCHIVE FRAGMENT {seed & 0xFFFF:04X}:\n"
                f"{r.choice(_LOG_SUBJECTS).title()} {r.choice(_LOG_VERBS)} "
                f"{r.choice(_LOG_OBJECTS)}.\n"
                f"[{r.choice(_LOG_CLOSERS).upper()}]")
    elif form == 1:
        lines = [f"{r.choice(_LOG_SUBJECTS).title()} {r.choice(_LOG_VERBS)}.",
                 f"It {r.choice(_LOG_VERBS)} {r.choice(_LOG_OBJECTS)}.",
                 f"{r.choice(_LOG_CLOSERS).capitalize()}."]
        return "\n".join(lines)
    elif form == 2:
        return (f"Log {seed & 0xFFF:03X} / {r.choice(_LOG_SUBJECTS)} / "
                f"{r.choice(_LOG_VERBS)} / {r.choice(_LOG_OBJECTS)}") 
    elif form == 3:
        n = r.randint(2, 4)
        return "\n".join(f"{r.choice(_LOG_SUBJECTS).title()} {r.choice(_LOG_VERBS)} {r.choice(_LOG_OBJECTS)}."
                         for _ in range(n))
    else:
        return (f"Transmission {seed & 0xFF:02X}-{(seed>>8)&0xFF:02X}:\n"
                f"'{r.choice(_LOG_SUBJECTS)} {r.choice(_LOG_VERBS)} {r.choice(_LOG_OBJECTS)}.'\n"
                f"[{r.choice(_LOG_CLOSERS).upper()}]")

# ================================================================ AUDIO BACKEND DETECTION

def _detect_audio():
    try:
        import winsound
        return "winsound"
    except Exception:
        pass
    for name, probe in (("afplay",["which","afplay"]), ("aplay",["aplay","--version"])):
        try:
            if subprocess.run(probe, capture_output=True).returncode == 0:
                return name
        except Exception:
            pass
    try:
        import ctypes; ctypes.windll.winmm; return "winmm"
    except Exception:
        return None

BACKEND = _detect_audio()

# ================================================================ AUDIO SYNTHESIS HELPERS

_TAU = math.tau
_SN  = 4096
_ST  = [math.sin(_TAU*i/_SN) for i in range(_SN)]
_INV = 1.0 / SR

def _fs(phase):
    q = (phase % _TAU) * (_SN / _TAU)
    i = int(q) & (_SN - 1)
    f = q - int(q)
    return _ST[i] + (_ST[(i+1) & (_SN-1)] - _ST[i]) * f

def _clx(x, lo=-1., hi=1.):
    return lo if x < lo else (hi if x > hi else x)

def _m2f(n):
    return 440. * (2. ** ((n - 69.) / 12.))

class _SVF:
    __slots__ = ("lp","bp","_f","_q")
    def __init__(s, cutoff=1000., res=0.):
        s.lp = s.bp = 0.; s.set(cutoff, res)
    def set(s, cutoff, res=None):
        cutoff = min(max(20., cutoff), SR*.47)
        s._f = 2. * math.sin(math.pi * cutoff * _INV)
        if res is not None: s._q = 1. - min(max(0., res), .97)
    def lp_p(s, x):
        h = x - s.lp - s._q*s.bp; s.bp += s._f*h; s.lp += s._f*s.bp; return s.lp

class _ADSR:
    __slots__ = ("a","d","s","r")
    def __init__(s, attack=.01, decay=.1, sustain=.7, release=.3):
        s.a=max(attack,.001); s.d=max(decay,.001); s.s=sustain; s.r=max(release,.001)
    def get(s, t, dur):
        if t < 0:            return 0.
        if t < s.a:          return t/s.a
        if t < s.a+s.d:      return 1.-(1.-s.s)*((t-s.a)/s.d)
        if t < dur:           return s.s
        rt = t - dur;        return s.s*(1.-rt/s.r) if rt < s.r else 0.

class _Pad:
    def __init__(s, notes, detune=.005):
        s.ph=[]; s.inc=[]; s.lfo=random.uniform(0,_TAU); s.li=_TAU*.16*_INV
        for n in notes:
            f = _m2f(n)
            for d in (-detune, 0., detune):
                s.ph.append(random.uniform(0,_TAU)); s.inc.append(_TAU*f*(1.+d)*_INV)
        s.n = len(s.ph)
    def sample(s, t=0., env=1.):
        s.lfo += s.li; mod = .7 + .3*(.5+.5*_fs(s.lfo)); v = 0.
        for i in range(s.n): s.ph[i] += s.inc[i]; v += _fs(s.ph[i])
        return (v / max(1,s.n)) * mod

class _FM:
    def __init__(s, freq, ratio=2., depth=1.4, feedback=.12):
        s.ci=_TAU*freq*_INV; s.mi=_TAU*freq*ratio*_INV
        s.depth=depth; s.fb=feedback; s.pc=0.; s.pm=0.; s.pv=0.
    def sample(s, t=0., env=1.):
        m = _fs(s.pm + s.pv*s.fb)*s.depth; s.pm += s.mi
        o = _fs(s.pc + m); s.pc += s.ci; s.pv = o; return o

class _Sub:
    def __init__(s, freq, wave="sine", cutoff=2000., res=.2, env_depth=2500.):
        s.ph=random.uniform(0,_TAU); s.inc=_TAU*freq*_INV; s.w=wave
        s.flt=_SVF(cutoff,res); s.env_depth=env_depth; s.base_cutoff=cutoff
    def sample(s, t=0., env=1.):
        s.ph += s.inc; w=s.w
        if   w=="saw": v = 2*(s.ph%_TAU)/_TAU - 1.
        elif w=="tri": p=(s.ph%_TAU)/_TAU; v=4*p-1 if p<.5 else 3-4*p
        else:          v = _fs(s.ph)
        s.flt.set(min(s.base_cutoff + s.env_depth*env, SR*.47))
        return s.flt.lp_p(v)

class _Rev:
    _COMB_DELAYS = (.0226,.0239,.0264,.0274,.03,.0312)
    def __init__(s, size=.9, damp=.45, mix=.3):
        s.cb = [[0.]*max(int(SR*d*size),2) for d in s._COMB_DELAYS]
        s.ci = [0]*6; s.lp = [0.]*6; s.damp=damp; s.mix=mix
    def proc(s, x):
        o = 0.
        for i,b in enumerate(s.cb):
            j = s.ci[i]%len(b); v=b[j]
            s.lp[i] = v*(1.-s.damp) + s.lp[i]*s.damp
            b[j] = x + s.lp[i]*.84; s.ci[i]+=1; o+=v
        return x*(1.-s.mix) + (o/6.)*s.mix

class _Dly:
    def __init__(s, time_s=.4, feedback=.35, mix=.25):
        s.b=[0.]*(int(SR*time_s)+2); s.i=0; s.fb=feedback; s.mix=mix
    def proc(s, x):
        j=s.i%len(s.b); d=s.b[j]; s.b[j]=x+d*s.fb; s.i+=1; return x+d*s.mix

_SCALES = {
    "minor"     :[0,2,3,5,7,8,10],
    "dorian"    :[0,2,3,5,7,9,10],
    "phrygian"  :[0,1,3,5,7,8,10],
    "penta"     :[0,2,4,7,9],
    "whole"     :[0,2,4,6,8,10],
    "lydian"    :[0,2,4,6,7,9,11],
}
_CHORDS = {
    "sus2":[0,2,7],  "min":[0,3,7],  "maj7":[0,4,7,11],
    "min7":[0,3,7,10],"sus4":[0,5,7],"add9":[0,4,7,14],
}

_MUSIC_CFG = {
    "space"       :("whole",  40,["sus2","add9","sus4","min7"],.12,"sine",200,"fm",1.6,.5,.62,.8),
    "PHOS CITY"   :("dorian", 48,["sus2","maj7","min7","sus2"],.26,"tri", 600,"fm",1.05,.38,.44,.4),
    "VOID DUNGEON":("phrygian",43,["min","min7","sus4","min"], .14,"sine",180,"fm",1.5,.65,.6,.65),
    "OPEN WILDS"  :("penta",  48,["sus2","add9","sus4","sus2"],.16,"sine",250,"fm",1.3,.45,.52,.55),
    "MOON SURFACE":("phrygian",45,["sus2"],                   .08,"sine",160,"fm",1.62,.72,.66,1.),
    "ENEMY SHIP"  :("phrygian",41,["min","min7","min","sus4"], .2, "sine",220,"fm",1.4,.6,.58,.6),
}

def _build_scale(root_midi, scale_name, octaves=3):
    pattern = _SCALES.get(scale_name, _SCALES["minor"])
    return [root_midi + o*12 + i
            for o in range(octaves) for i in pattern
            if 0 <= root_midi + o*12 + i <= 127]

def _env_curve(t, total_dur):
    p = t / max(total_dur, 1.)
    if p < .10: return p / .10
    if p < .85: return 1.
    return max(0., 1. - (p-.85)/.15)

def _render_music(mode, duration=11., rng=None):
    rng = rng or random.Random()
    cfg = _MUSIC_CFG.get(mode, _MUSIC_CFG["space"])
    scale_name, root, chord_names, density, bass_wave, bass_cut, _, rsize, rdamp, rmix, dly_t = cfg
    scale  = _build_scale(root, scale_name, 3)
    bscale = _build_scale(root-12, scale_name, 2)
    beat   = 60. / rng.randint(50,72)
    bar    = beat*4
    bars   = max(2, int(duration/bar))
    events = []

    for bn in range(0, bars, 2):
        en = _env_curve(bn*bar, duration)
        if en < .12: continue
        chord_key = chord_names[bn % len(chord_names)]
        root_note = scale[(bn*2) % len(scale)] + 12
        notes     = [root_note + i for i in _CHORDS.get(chord_key, _CHORDS["sus2"])]
        t = bn*bar; d = min(bar*rng.choice([2,4]), max(.5, duration-t))
        events.append((t, d, _Pad(notes, detune=rng.uniform(.003,.007)),
                       .62*(.4+.6*en), _ADSR(rng.uniform(.5,1.5),.6,.8,rng.uniform(1.,2.2))))

    for bn in range(bars):
        en = _env_curve(bn*bar, duration)
        br = bscale[(bn*3) % len(bscale)]
        for step in range(0, 16, rng.choice([3,4])):
            if rng.random() > density*(.4+.6*en): continue
            t = bn*bar + step*beat*.25
            if t >= duration: continue
            events.append((t, beat*rng.choice([.5,1.]),
                           _Sub(_m2f(br), wave=bass_wave, cutoff=bass_cut, res=.15, env_depth=bass_cut*2.),
                           .5, _ADSR(.006,.12,.6,.12)))

    lead_count = 0
    for bn in range(bars):
        if lead_count > 10: break
        en = _env_curve(bn*bar, duration)
        if rng.random() > density*(.3+.7*en): continue
        chord_key = chord_names[bn % len(chord_names)]
        chord_root = scale[(bn*2) % len(scale)] + 12
        for k in range(rng.randint(2,4)):
            t = bn*bar + k*bar/4
            if t >= duration: continue
            note = rng.choice([chord_root+i for i in _CHORDS.get(chord_key,_CHORDS["sus2"])])
            events.append((t, bar/4*.7,
                           _FM(_m2f(note), ratio=rng.choice([1,2,3]),
                               depth=rng.uniform(.6,2.), feedback=.1),
                           .2*(.5+.5*en), _ADSR(.02,.15,.5,.2)))
            lead_count += 1

    if not events:
        events.append((0, duration*.9, _Pad([root+12,root+19,root+24], detune=.004),
                       .6, _ADSR(.5,1.,.85,1.5)))

    reverb = _Rev(rsize, rdamp, rmix)
    delay  = _Dly(dly_t, .4, .4)
    total  = int(duration * SR)
    buf    = array.array('h', [0]*total)
    events.sort(key=lambda e: e[0])
    ptr = 0; active = []
    for i in range(total):
        t = i * _INV
        while ptr < len(events) and events[ptr][0] <= t+.003:
            active.append(events[ptr]); ptr += 1
        s = 0.; keep = []
        for ev in active:
            lt = t - ev[0]
            if lt > ev[1] + ev[4].r + 1.: continue
            keep.append(ev); env = ev[4].get(lt, ev[1])
            if env < .0001: continue
            s += ev[2].sample(lt, env) * env * ev[3]
        active = keep
        s = delay.proc(reverb.proc(s))
        buf[i] = int(_clx(s, -.97, .97) * 27000)
    return _wav_bytes(buf)

def _quick_drone(mode, duration=4.):
    cfg = _MUSIC_CFG.get(mode, _MUSIC_CFG["space"]); root = cfg[1]
    n   = int(SR*duration); buf = array.array('h',[0]*n)
    freqs = [_m2f(root+i) for i in (0,7,12,19)]
    phases= [random.uniform(0,_TAU) for _ in freqs]
    incs  = [_TAU*f*_INV for f in freqs]
    for i in range(n):
        v   = sum(_fs(phases[j])*(.4,.25,.2,.15)[j] for j in range(4))
        for j in range(4): phases[j] += incs[j]
        t   = i*_INV; env = min(t,.5)/.5 * min(1.,(duration-t)/.5)
        buf[i] = int(_clx(v*env*.55,-.97,.97)*27000)
    return _wav_bytes(buf)

class MusicEngine:
    def __init__(self):
        self._run=False; self._mode="space"; self._cache={}
        self._thread=None; self._rng=random.Random()
    def set_mode(self, mode): self._mode=mode
    def start(self):
        if self._run: return
        self._run=True; self._thread=threading.Thread(target=self._loop,daemon=True); self._thread.start()
    def stop(self): self._run=False
    def _get(self, mode):
        if mode not in self._cache:
            try:    self._cache[mode] = _render_music(mode, 11., self._rng)
            except Exception: self._cache[mode] = None
        return self._cache[mode]
    def _loop(self):
        try: _audio_play(_quick_drone(self._mode, 4.)); time.sleep(3.2)
        except Exception: pass
        while self._run:
            try:
                m    = self._mode
                data = self._get(m)
                threading.Thread(target=self._get, args=(m,), daemon=True).start()
                if data and self._run:
                    _audio_play(data)
                    time.sleep(9.8)
                    if self._run:
                        try: _audio_play(_quick_drone(self._mode, 2.5))
                        except Exception: pass
                        time.sleep(0.6)
                else:
                    time.sleep(1.5)
            except Exception: time.sleep(1.5)

# ================================================================ TTS NARRATOR

def _tts_normalise(text):
    for k,v in {"\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',
                "\u2014":" - ","\u2026":"..."}.items():
        text = text.replace(k, v)
    return " ".join(text.split())

class Narrator:
    def __init__(self):
        self._queue=[]; self._run=True; self._backend=None; self._piper=None
        threading.Thread(target=self._detect, daemon=True).start()

    def _detect(self):
        try:
            import piper
            from pathlib import Path
            voices_dir = Path.home()/".local"/"share"/"tts-studio"/"voices"
            model = next(voices_dir.glob("*.onnx"),None) if voices_dir.is_dir() else None
            if model:
                self._piper=piper.PiperVoice.load(str(model)); self._backend="piper"
        except Exception: self._piper=None
        if not self._backend:
            for cmd,probe in (("espeak-ng",["espeak-ng","--version"]),("espeak",["espeak","--version"])):
                try:
                    if subprocess.run(probe,capture_output=True,timeout=2).returncode==0:
                        self._backend=cmd; break
                except Exception: pass
        if not self._backend:
            try:
                if subprocess.run(["which","say"],capture_output=True,timeout=2).returncode==0:
                    self._backend="say"
            except Exception: pass
        if not self._backend and BACKEND in ("winsound","winmm"):
            self._backend="sapi"
        threading.Thread(target=self._worker, daemon=True).start()

    def say(self, text, priority=False):
        if not self._backend: return
        t = _tts_normalise(text)
        if priority: self._queue.insert(0, t)
        elif len(self._queue) < 3: self._queue.append(t)

    def _worker(self):
        while self._run:
            if self._queue:
                t = self._queue.pop(0)
                try:
                    if self._backend=="piper":
                        tf = tempfile.NamedTemporaryFile(suffix=".wav",delete=False)
                        with wave.open(tf.name,"wb") as wf:
                            wf.setnchannels(1); wf.setsampwidth(2)
                            wf.setframerate(self._piper.config.sample_rate)
                            for ch in self._piper.synthesize(t): wf.writeframes(ch.audio_int16_bytes)
                        tf.close(); _audio_play(open(tf.name,"rb").read())
                    elif self._backend in ("espeak","espeak-ng"):
                        subprocess.Popen([self._backend,"-s","145","-a","85",t],
                                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    elif self._backend=="say":
                        subprocess.Popen(["say","-r","165",t],
                                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    elif self._backend=="sapi":
                        ps=('Add-Type -AssemblyName System.Speech;'
                            '(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("%s")'
                            % t.replace('"',"'"))
                        subprocess.Popen(["powershell","-Command",ps],
                                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    time.sleep(.4)
                except Exception: pass
            else: time.sleep(.1)

    def stop(self): self._run=False

# ================================================================ AUDIO PRIMITIVES

def _wave(freq, dur, amp=0.4, kind="sine"):
    n    = int(SR*dur); fade=max(1,int(SR*.05)); out=[]
    for i in range(n):
        t = i/SR
        if   kind=="sine":   v=math.sin(TAU*freq*t)
        elif kind=="saw":    v=2*((freq*t)%1)-1.
        elif kind=="square": v=1. if math.sin(TAU*freq*t)>=0 else -1.
        elif kind=="tri":    p=(freq*t)%1; v=4*p-1 if p<.5 else 3-4*p
        else:                v=random.uniform(-1,1)
        env = min(i, n-i, fade) / fade
        out.append(int(max(-32767, min(32767, v*amp*32767*env))))
    return array.array('h', out)

def _mix(*wave_arrays):
    if not wave_arrays: return array.array('h',[])
    L=max(len(w) for w in wave_arrays); n=len(wave_arrays); out=[]
    for i in range(L):
        s = sum(w[i] for w in wave_arrays if i < len(w))
        out.append(int(max(-32767, min(32767, s/n))))
    return array.array('h', out)

def _wav_bytes(samples):
    b = io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(samples.tobytes())
    return b.getvalue()

def _audio_play(data):
    if not BACKEND or not data: return
    def _go():
        try:
            if BACKEND=="winsound":
                import winsound
                winsound.PlaySound(data, winsound.SND_MEMORY|winsound.SND_ASYNC)
            elif BACKEND in ("aplay","afplay"):
                tf = tempfile.NamedTemporaryFile(suffix=".wav",delete=False)
                tf.write(data); tf.close()
                subprocess.Popen(["aplay","-q",tf.name] if BACKEND=="aplay" else ["afplay",tf.name],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif BACKEND=="winmm":
                import ctypes
                tf = tempfile.NamedTemporaryFile(suffix=".wav",delete=False)
                tf.write(data); tf.close()
                ctypes.windll.winmm.PlaySoundW(tf.name,None,0x00020001)
        except Exception: pass
    threading.Thread(target=_go, daemon=True).start()

# ================================================================ AUDIO ENGINE SFX

def _bake_engine_sounds():
    """
    Build all vehicle engine SFX.

    Architecture:
      Sub-bass fundamental (35-220 Hz) tracks RPM with real harmonic stack.
      Each harmonic is a pure sine — fast and clean.
      SVF low-pass breathes with RPM (higher RPM = brighter, more harmonics audible).
      LFO adds idle flutter (cylinder-firing irregularity simulation).
      Noise floor adds mechanical texture (valve train, belt, exhaust rasp).

    RPM mapping (4-cylinder, ~2 firing events per revolution):
      Idle  ~850 rpm  → fundamental ≈ 28 Hz  (use 38 Hz for audibility)
      Low   ~1500rpm  → fundamental ≈ 50 Hz
      Mid   ~3000rpm  → fundamental ≈ 100 Hz
      High  ~5500rpm  → fundamental ≈ 183 Hz
    """
    c = {}

    # ---- shared low-pass filter state (reset per sound) ----
    def _lpf_proc(x, lp_state, cutoff_hz):
        """One-pole IIR low-pass filter."""
        rc = 1.0 / (TAU * cutoff_hz * (1.0/SR))
        alpha = 1.0 / (1.0 + rc)
        lp_state[0] = lp_state[0] + alpha * (x - lp_state[0])
        return lp_state[0]

    # ----------------------------------------------------------
    # ENGINE IDLE  —  warm rumble, gentle flutter, sub presence
    # ----------------------------------------------------------
    dur = 0.9
    n = int(SR * dur)
    out = []
    lfo_ph = 0.0
    flutter_ph = 0.0
    f0 = 38.0          # fundamental at idle (~850 rpm)
    lp = [0.0]
    for i in range(n):
        t = i / SR
        # Slow LFO: cylinder-firing irregularity (2.8 Hz flutter)
        lfo_ph += TAU * 2.8 / SR
        lfo = 0.88 + 0.12 * math.sin(lfo_ph)
        # Very slow flutter for rough idle feel (0.4 Hz)
        flutter_ph += TAU * 0.4 / SR
        flutter = 0.94 + 0.06 * math.sin(flutter_ph)
        mod = lfo * flutter
        # Harmonic stack (fundamental + 6 harmonics, falling off)
        v  = math.sin(TAU * f0 * t)       * 0.52 * mod    # fundamental
        v += math.sin(TAU * f0*2 * t)     * 0.28 * mod    # 2nd harmonic
        v += math.sin(TAU * f0*3 * t)     * 0.14          # 3rd
        v += math.sin(TAU * f0*4 * t)     * 0.07          # 4th — adds body
        v += math.sin(TAU * f0*5 * t)     * 0.03          # 5th — presence
        v += math.sin(TAU * f0*6 * t)     * 0.015         # 6th — air
        # Mechanical noise: valve train + belt (very quiet broadband)
        v += random.uniform(-1.0, 1.0) * 0.018
        # Gentle exhaust rasp on even harmonics (adds "burble")
        rasp_ph = TAU * f0 * 2.5 * t
        v += math.sin(rasp_ph + math.sin(rasp_ph) * 0.3) * 0.04
        # Low-pass: idle tone is warm, cut above ~600 Hz
        v = _lpf_proc(v, lp, 620.0)
        # Smooth fade in/out
        env = min(i, n-i, int(SR*.06)) / int(SR*.06)
        out.append(int(max(-32767, min(32767, v * 32767 * 0.72 * env))))
    c['engine_idle'] = _wav_bytes(array.array('h', out))

    # ----------------------------------------------------------
    # ENGINE LO  —  1500-2200 rpm band (pulling away from lights)
    # ----------------------------------------------------------
    dur = 0.55
    n = int(SR * dur)
    out = []
    lfo_ph = 0.0
    f0 = 52.0          # ~1500 rpm
    lp = [0.0]
    for i in range(n):
        t = i / SR
        lfo_ph += TAU * 4.5 / SR
        lfo = 0.90 + 0.10 * math.sin(lfo_ph)
        v  = math.sin(TAU * f0 * t)       * 0.55 * lfo
        v += math.sin(TAU * f0*2 * t)     * 0.30 * lfo
        v += math.sin(TAU * f0*3 * t)     * 0.16
        v += math.sin(TAU * f0*4 * t)     * 0.09
        v += math.sin(TAU * f0*5 * t)     * 0.04
        v += random.uniform(-1.0, 1.0) * 0.020
        # Slight exhaust note
        v += math.sin(TAU * f0 * 1.5 * t) * 0.035
        v = _lpf_proc(v, lp, 900.0)
        env = min(i, n-i, int(SR*.04)) / int(SR*.04)
        out.append(int(max(-32767, min(32767, v * 32767 * 0.68 * env))))
    c['engine_lo'] = _wav_bytes(array.array('h', out))

    # ----------------------------------------------------------
    # ENGINE MID  —  2500-3800 rpm band (cruising)
    # ----------------------------------------------------------
    dur = 0.55
    n = int(SR * dur)
    out = []
    lfo_ph = 0.0
    f0 = 95.0          # ~2800 rpm
    lp = [0.0]
    for i in range(n):
        t = i / SR
        lfo_ph += TAU * 7.0 / SR
        lfo = 0.93 + 0.07 * math.sin(lfo_ph)
        v  = math.sin(TAU * f0 * t)       * 0.50 * lfo
        v += math.sin(TAU * f0*2 * t)     * 0.28 * lfo
        v += math.sin(TAU * f0*3 * t)     * 0.18
        v += math.sin(TAU * f0*4 * t)     * 0.10
        v += math.sin(TAU * f0*5 * t)     * 0.05
        v += math.sin(TAU * f0*6 * t)     * 0.02
        v += random.uniform(-1.0, 1.0) * 0.022
        # Mid-range exhaust "blare"
        blare = math.sin(TAU * f0 * 2.0 * t + math.sin(TAU * f0 * 0.5 * t) * 0.5)
        v += blare * 0.06
        v = _lpf_proc(v, lp, 1400.0)
        env = min(i, n-i, int(SR*.04)) / int(SR*.04)
        out.append(int(max(-32767, min(32767, v * 32767 * 0.65 * env))))
    c['engine_md'] = _wav_bytes(array.array('h', out))

    # ----------------------------------------------------------
    # ENGINE HI  —  4500+ rpm band (hard acceleration / redline)
    # ----------------------------------------------------------
    dur = 0.50
    n = int(SR * dur)
    out = []
    lfo_ph = 0.0
    f0 = 155.0         # ~4600 rpm
    lp = [0.0]
    for i in range(n):
        t = i / SR
        lfo_ph += TAU * 11.0 / SR
        lfo = 0.95 + 0.05 * math.sin(lfo_ph)
        v  = math.sin(TAU * f0 * t)       * 0.45 * lfo
        v += math.sin(TAU * f0*2 * t)     * 0.26 * lfo
        v += math.sin(TAU * f0*3 * t)     * 0.18
        v += math.sin(TAU * f0*4 * t)     * 0.12
        v += math.sin(TAU * f0*5 * t)     * 0.07
        v += math.sin(TAU * f0*6 * t)     * 0.04
        v += math.sin(TAU * f0*7 * t)     * 0.02
        v += random.uniform(-1.0, 1.0) * 0.028
        # Exhaust scream at high rpm — inharmonic partial gives "raw" character
        v += math.sin(TAU * f0 * 2.47 * t) * 0.055
        v += math.sin(TAU * f0 * 3.52 * t) * 0.025
        v = _lpf_proc(v, lp, 2800.0)
        env = min(i, n-i, int(SR*.035)) / int(SR*.035)
        out.append(int(max(-32767, min(32767, v * 32767 * 0.62 * env))))
    c['engine_hi'] = _wav_bytes(array.array('h', out))

    # ----------------------------------------------------------
    # ACCELERATION SWEEP  —  RPM climb with harmonic enrichment
    # Starts at idle (38 Hz), sweeps to ~4000 rpm (133 Hz)
    # ----------------------------------------------------------
    dur = 1.1
    n = int(SR * dur)
    out = []
    lp = [0.0]
    phase_acc = 0.0    # continuous phase accumulator (avoids clicks at freq transitions)
    for i in range(n):
        t = i / SR
        prog = t / dur                              # 0 → 1
        # RPM sweep curve: slow start, fast through power band
        curve = prog ** 0.7
        f0 = 38.0 + curve * (148.0 - 38.0)         # 38 Hz → 148 Hz
        phase_acc += TAU * f0 / SR                  # accumulate instantaneous phase
        # Harmonics grow in brightness as RPM climbs
        v  = math.sin(phase_acc)                    * (0.50 + 0.10*curve)
        v += math.sin(phase_acc*2)                  * (0.24 + 0.12*curve)
        v += math.sin(phase_acc*3)                  * (0.12 + 0.10*curve)
        v += math.sin(phase_acc*4)                  * (0.06 + 0.08*curve)
        v += math.sin(phase_acc*5)                  * (0.02 + 0.05*curve)
        v += random.uniform(-1.0, 1.0)              * (0.015 + 0.020*curve)
        # Intake "bark" burst at the top of the sweep
        if prog > 0.88:
            bark = (prog - 0.88) / 0.12
            v += math.sin(phase_acc * 2.5)          * 0.08 * bark
        cutoff = 600.0 + curve * 2400.0
        v = _lpf_proc(v, lp, cutoff)
        # Envelope: immediate on, gentle release at end
        env = min(i, int(SR*.02)) / int(SR*.02) * (1.0 if prog < 0.85 else 1.0 - (prog-0.85)/0.15)
        out.append(int(max(-32767, min(32767, v * 32767 * 0.70 * env))))
    c['accel'] = _wav_bytes(array.array('h', out))

    # ----------------------------------------------------------
    # BRAKE / DECELERATION  —  engine braking rumble + pad squeal
    # RPM falls back down, exhaust pops on lift-off
    # ----------------------------------------------------------
    dur = 0.90
    n = int(SR * dur)
    out = []
    lp = [0.0]
    phase_acc = 0.0
    for i in range(n):
        t = i / SR
        prog = t / dur                              # 0 → 1
        # RPM drops quickly at first, then settles near idle
        curve = 1.0 - (1.0 - prog) ** 0.5          # fast drop, slow tail
        f0 = 148.0 - curve * (148.0 - 38.0)        # 148 Hz → 38 Hz
        phase_acc += TAU * f0 / SR
        v  = math.sin(phase_acc)                    * (0.48 - 0.15*curve)
        v += math.sin(phase_acc*2)                  * (0.26 - 0.10*curve)
        v += math.sin(phase_acc*3)                  * (0.14 - 0.05*curve)
        v += math.sin(phase_acc*4)                  * (0.07)
        v += random.uniform(-1.0, 1.0)              * 0.022
        # Exhaust "pop/crackle" on lift-off (first 15% of sound)
        if prog < 0.15:
            pop_chance = (0.15 - prog) / 0.15
            if random.random() < 0.06 * pop_chance:
                v += random.choice([-1.0, 1.0]) * 0.55 * pop_chance
        # Brake pad squeal — brief mid-freq whine near the end
        if prog > 0.65:
            squeal = (prog - 0.65) / 0.35
            squeal_f = 2800.0 + squeal * 600.0
            v += math.sin(TAU * squeal_f * t) * 0.12 * squeal
        cutoff = 2200.0 - curve * 1600.0
        v = _lpf_proc(v, lp, cutoff)
        env = min(i, int(SR*.015)) / int(SR*.015) * (1.0 if prog < 0.80 else 1.0 - (prog-0.80)/0.20)
        out.append(int(max(-32767, min(32767, v * 32767 * 0.65 * env))))
    c['brake'] = _wav_bytes(array.array('h', out))

    # ----------------------------------------------------------
    # REVERSE  —  low-RPM burble with reverse-gear whine
    # ----------------------------------------------------------
    dur = 0.75
    n = int(SR * dur)
    out = []
    lfo_ph = 0.0
    f0 = 44.0          # low RPM, slightly uneven
    gear_whine_f = 340.0  # reverse-gear geartrain whine
    lp = [0.0]
    for i in range(n):
        t = i / SR
        lfo_ph += TAU * 3.5 / SR
        lfo = 0.87 + 0.13 * math.sin(lfo_ph)       # more flutter in reverse
        v  = math.sin(TAU * f0 * t)       * 0.50 * lfo
        v += math.sin(TAU * f0*2 * t)     * 0.28 * lfo
        v += math.sin(TAU * f0*3 * t)     * 0.13
        v += math.sin(TAU * f0*4 * t)     * 0.06
        v += random.uniform(-1.0, 1.0) * 0.022
        # Geartrain whine at fixed frequency (characteristic reverse sound)
        v += math.sin(TAU * gear_whine_f * t) * 0.10
        v += math.sin(TAU * gear_whine_f * 1.5 * t) * 0.04
        v = _lpf_proc(v, lp, 750.0)
        env = min(i, n-i, int(SR*.05)) / int(SR*.05)
        out.append(int(max(-32767, min(32767, v * 32767 * 0.62 * env))))
    c['reverse'] = _wav_bytes(array.array('h', out))

    # ----------------------------------------------------------
    # BOOST  —  supercharger whine + raw engine scream
    # ----------------------------------------------------------
    n = int(SR * 1.5); out = []
    lp = [0.0]; phase_acc = 0.0
    for i in range(n):
        t = i / SR; prog = t / 1.5
        f0 = 100.0 + prog * 120.0
        phase_acc += TAU * f0 / SR
        v  = math.sin(phase_acc)          * 0.40
        v += math.sin(phase_acc*2)        * 0.24
        v += math.sin(phase_acc*3)        * 0.16
        v += math.sin(phase_acc*5)        * 0.06
        # Supercharger whine: rising inharmonic tone
        sc_f = 1800.0 + prog * 3200.0
        v += math.sin(TAU * sc_f * t)     * 0.18
        v += math.sin(TAU * sc_f * 1.5 * t) * 0.07
        v += random.uniform(-1.0, 1.0)    * 0.030
        v = _lpf_proc(v, lp, 1200.0 + prog * 3000.0)
        env = min(i, int(SR*.03)) / int(SR*.03)
        out.append(int(max(-32767, min(32767, v * 32767 * 0.68 * env))))
    c['boost'] = _wav_bytes(array.array('h', out))

    return c


class Audio:
    """Manages all sound effects and the music engine."""
    def __init__(self):
        self.music_on = self.sfx_on = bool(BACKEND)
        self.sounds   = {}
        self.music    = MusicEngine()
        if BACKEND:
            threading.Thread(target=self._bake, daemon=True).start()

    def _bake(self):
        """Build all SFX on a background thread so startup is instant."""
        c = self.sounds
        try:
            # --- Emitter laser ---
            dur_gun = 0.28; n=int(SR*dur_gun); o=[]
            for i in range(n):
                t = i/SR
                sub_env = math.exp(-t * 18.)
                sub     = math.sin(TAU * 80. * t) * sub_env * 0.9
                sub2    = math.sin(TAU * 160. * t) * math.exp(-t * 28.) * 0.35
                sweep_f = 2200. - t * (2200.-600.) / dur_gun
                sweep   = math.sin(TAU * sweep_f * t) * 0.50
                noise   = random.uniform(-1.,1.) * max(0., 1. - t/0.06) * 0.18
                harm    = math.sin(TAU * sweep_f * 2.1 * t) * 0.10
                env     = min(i, int(SR*.008)) / int(SR*.008) * math.exp(-t * 5.5)
                v       = (sub + sub2 + sweep + noise + harm) * env
                o.append(int(max(-32767, min(32767, v * 32767))))
            c['gun'] = _wav_bytes(array.array('h',o))

            # --- Realistic vehicle engine sounds ---
            c.update(_bake_engine_sounds())

            # --- Misc SFX ---
            c['thruster'] = _wav_bytes(_mix(_wave(60,1,.25,"saw"),_wave(.5,1,.15,"noise")))
            c['whoosh']   = _wav_bytes(_mix(_wave(200,.5,.20,"noise"),_wave(100,.5,.10)))
            c['death']    = _wav_bytes(_mix(_wave(100,.3,.30,"noise"),_wave(50,.3,.20)))
            c['pickup']   = _wav_bytes(_wave(880,.10,.20))
            c['artifact'] = _wav_bytes(_mix(_wave(660,.3,.2,"tri"),_wave(880,.2,.15)))
            c['dialogue'] = _wav_bytes(_wave(440,.12,.18,"tri"))
            c['step']     = _wav_bytes(_wave(80,.06,.15,"noise"))
            c['jump']     = _wav_bytes(_mix(_wave(200,.15,.20,"saw"),_wave(150,.15,.10)))
            c['land']     = _wav_bytes(_mix(_wave(60,.25,.40,"noise"),_wave(40,.25,.30)))
            c['overheat'] = _wav_bytes(_mix(_wave(400,.5,.25,"square"),_wave(200,.5,.15)))
            c['still']    = _wav_bytes(_mix(_wave(440,.4,.25),_wave(550,.6,.15),_wave(330,.8,.10)))
        except Exception: pass

    def play(self, key):
        if self.sfx_on: _audio_play(self.sounds.get(key))

    def toggle_music(self):
        self.music_on = not self.music_on
        if self.music_on: self.music.start()
        else:             self.music.stop()
        return self.music_on

    def toggle_sfx(self):
        self.sfx_on = not self.sfx_on; return self.sfx_on

    def stop(self):
        self.music.stop()

# ================================================================ MATH HELPERS

class V2:
    __slots__ = ('x','y')
    def __init__(self, x=0., y=0.): self.x=float(x); self.y=float(y)
    def copy(self): return V2(self.x, self.y)

class V3:
    __slots__ = ('x','y','z')
    def __init__(self, x=0., y=0., z=0.): self.x,self.y,self.z=float(x),float(y),float(z)
    def __add__(self,o): return V3(self.x+o.x, self.y+o.y, self.z+o.z)
    def __sub__(self,o): return V3(self.x-o.x, self.y-o.y, self.z-o.z)
    def __mul__(self,s): return V3(self.x*s,   self.y*s,   self.z*s)
    def dot(self,o):     return self.x*o.x + self.y*o.y + self.z*o.z
    def length(self):    return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    def normalize(self):
        m=self.length(); return V3(0,0,1) if m<1e-9 else V3(self.x/m,self.y/m,self.z/m)

def vdot(a,b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def vsub(a,b): return [a[0]-b[0],a[1]-b[1],a[2]-b[2]]
def vadd(a,b): return [a[0]+b[0],a[1]+b[1],a[2]+b[2]]
def vmul(v,s): return [v[0]*s,v[1]*s,v[2]*s]
def vnorm(v):
    m=math.sqrt(v[0]**2+v[1]**2+v[2]**2)
    return [v[0]/m,v[1]/m,v[2]/m] if m>1e-9 else [0,0,1]

def rodrigues(v, axis, angle):
    c,s = math.cos(angle), math.sin(angle)
    cross = [axis[1]*v[2]-axis[2]*v[1], axis[2]*v[0]-axis[0]*v[2], axis[0]*v[1]-axis[1]*v[0]]
    d = vdot(axis,v)
    return [v[i]*c + cross[i]*s + axis[i]*d*(1-c) for i in range(3)]

# ================================================================ PHOS CITY WALL TEXTURE

def _pch(*args):
    h = hash(args) & 0xffffffff
    return ((h*2654435761) & 0xffffffff) / 4294967296.0

def _pc_glyph(building_variant, u, v, wall_x, wall_y, fog):
    PC_WIN_LIT   = "\u25a3"
    PC_WIN_DIM   = "\u25a2"
    PC_WIN_DARK  = "\u00b7"
    PC_WIN_BLIND = "\u2630"
    if   building_variant==1: cols,rows,lit_chance = 5,9, .30
    elif building_variant==2: cols,rows,lit_chance = 4,16,.42
    elif building_variant==3: cols,rows,lit_chance = 7,18,.55
    else:                     cols,rows,lit_chance = 6,12,.35
    col_idx  = int(u*cols); row_idx = int(v*rows)
    frac_u   = (u*cols)-col_idx; frac_v  = (v*rows)-row_idx
    in_window = frac_u>.12 and frac_u<.88 and frac_v>.18 and frac_v<.82
    if row_idx==rows-1 and col_idx==cols//2 and in_window:
        return ('\u25ae', max(.55,.88-fog*.4)) if frac_v>.28 else ('\u2550', max(.45,.75-fog*.4))
    if not in_window:
        if   fog<.22: return ('\u2588', max(.55,.95-fog*.5))
        elif fog<.48: return ('\u2593', max(.40,.78-fog*.5))
        elif fog<.72: return ('\u2592', max(.22,.55-fog*.4))
        else:         return ('\u2591', max(.10,.32-fog*.3))
    rand = _pch(wall_x,wall_y,col_idx,row_idx,building_variant)
    is_lit = rand < lit_chance; has_blinds = (rand*17.)%1.<.18
    if is_lit:
        intensity = max(.55,.95-fog*.30)
        if has_blinds: return (PC_WIN_BLIND, intensity*.85)
        return (PC_WIN_LIT, intensity) if (rand*13.)%1.<.40 else ('\u25a1', intensity*.92)
    return (PC_WIN_DARK, max(.10,.30-fog*.3))

# ================================================================ CV SPRITES + PARTICLES

_EYES   = ['(o o)','(@ @)','(x x)','(* *)','(> <)','[o_o]','<o-o>','(0 0)','(^ ^)']
_HAIRS  = ['ZZZ','DDD','GGG','///','###','XXX','|||','~~~']
_TL     = ['<|','[|','\\|','{|','=|','!|']
_TR     = ['|>','|]','|/','|}','|=','|!']
_LEGS   = ['/ \\ ','|_| ','\\|/ ','/_\\ ','(_) ','||| ']
_AL     = ['/','\\','|','<','{','[']
_AR     = ['\\','/','|','>','}',']']
_FACE   = '#@$%&*+=~-|.:^'
_CORPSE = ['  x x  ','  |||  ','  ---  ','       ']
_SPRITE_CACHE = {}

def _make_sprite(seed):
    r = random.Random(seed); w = 8
    return [
        f' {r.choice(_FACE)}{r.choice(_HAIRS)}{r.choice(_FACE)} '[:w].ljust(w),
        f'  {r.choice(_EYES)}  '[:w].ljust(w),
        f' {r.choice(_AL)}{r.choice(_TL)[1:]}{r.choice(_TR)[:-1]}{r.choice(_AR)} '[:w].ljust(w),
        f'  {r.choice(_LEGS)}  '[:w].ljust(w),
    ]

def _sprite_rows(char, flashing=False, eid=None):
    if char=='%': rows=_CORPSE
    else:
        k = eid if eid is not None else id(char)
        if k not in _SPRITE_CACHE: _SPRITE_CACHE[k] = _make_sprite(k ^ (ord(char)*7919))
        rows = _SPRITE_CACHE[k]
    return [' *'+r[2:] for r in rows] if flashing else rows

class Particle:
    __slots__ = ('bx','by','ch','life','vx','vy')
    def __init__(self, bx, by, ch, life):
        self.bx=bx; self.by=by; self.ch=ch; self.life=life
        self.vx=random.choice([-1,0,0,1]); self.vy=random.choice([-1,0,0,1])

class Particles:
    def __init__(self): self.pool=[]
    def emit(self, bx, by, kind='spark', count=4):
        chars = {'spark':'*+.','blood':'#@.','smoke':'.,:','gore':'$%#'}.get(kind,'*')
        for _ in range(count):
            self.pool.append(Particle(bx+random.randint(-3,3), by+random.randint(-2,2),
                                      random.choice(chars), random.randint(4,10)))
    def update(self):
        keep=[]
        for p in self.pool:
            p.life-=1; p.bx+=p.vx; p.by+=p.vy
            if p.life>0: keep.append(p)
        self.pool=keep
    def draw(self, buf, W, H):
        for p in self.pool:
            if 0<=int(p.bx)<W and 0<=int(p.by)<H: buf[int(p.by)][int(p.bx)]=p.ch

class PUSpawner:
    def __init__(self): self.items=[]
    def spawn_near(self, cx, cy, router):
        for _ in range(40):
            angle=random.uniform(0,TAU); r=random.uniform(3,10)
            x=cx+math.cos(angle)*r; y=cy+math.sin(angle)*r
            if router.is_open(x,y): self.items.append([x,y,random.choice(PU_TYPES),900]); return
    def update(self): self.items=[[x,y,t,f-1] for x,y,t,f in self.items if f>0]
    def check(self, px, py):
        for it in self.items:
            if math.hypot(it[0]-px, it[1]-py)<1.1: self.items.remove(it); return it[2]
        return None
    def draw(self, buf, cam, zbuf, W, H):
        for x,y,t,_ in self.items:
            dx=x-cam.pos.x; dy=y-cam.pos.y
            inv=cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y
            if abs(inv)<1e-9: continue
            inv=1./inv; tX=inv*(cam.dir.y*dx-cam.dir.x*dy); tY=inv*(-cam.plane.y*dx+cam.plane.x*dy)
            if tY<.3: continue
            sx=int(W/2*(1+tX/tY)); sz=max(1,abs(int(H/tY)))
            x0=max(0,sx-sz//4); x1=min(W-1,sx+sz//4); y0=max(0,H//2-sz//2); y1=min(H-1,H//2+sz//2)
            zi=max(0,min(W-1,sx))
            if tY<zbuf[zi]:
                g=PU_GLYPHS.get(t,'?')
                for by in range(y0,y1):
                    for bx in range(x0,x1):
                        if 0<=bx<W and 0<=by<H: buf[by][bx]=g

class ArtifactSpawner:
    def __init__(self, router, count=12, seed=0):
        rng=random.Random(seed); self.items=[]
        for _ in range(count):
            for attempt in range(50):
                x=rng.uniform(5,95); y=rng.uniform(5,95)
                if router.is_open(x,y):
                    self.items.append([x,y,rng.choice(ARTIFACTS),False]); break
    def check(self, px, py):
        for it in self.items:
            if not it[3] and math.hypot(it[0]-px,it[1]-py)<1.2:
                it[3]=True; return True
        return False
    def draw(self, buf, cam, zbuf, W, H):
        for x,y,glyph,found in self.items:
            if found: continue
            dx=x-cam.pos.x; dy=y-cam.pos.y
            inv=cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y
            if abs(inv)<1e-9: continue
            inv=1./inv; tX=inv*(cam.dir.y*dx-cam.dir.x*dy); tY=inv*(-cam.plane.y*dx+cam.plane.x*dy)
            if tY<.3: continue
            sx=int(W/2*(1+tX/tY)); sy=H//2
            zi=max(0,min(W-1,sx))
            if tY<zbuf[zi] and 0<=sx<W and 0<=sy<H: buf[sy][sx]=glyph

# ================================================================ WORLD BUBBLE SPAWNER

class WorldBubble:
    """
    Grid-based proximity spawner. Divides the world into CELL_SIZE blocks.
    As the player crosses into a new cell, it rolls a random spawn event:
    enemies, vehicles, and/or a procedural archive log artifact.
    Keeps the world fresh and dense without ever re-spawning the same cell twice.
    """
    CELL_SIZE   = 8          # world units per bubble cell (~1 city block)
    MAX_ENT     = 80         # hard cap on live entities
    MAX_VEH     = 60         # hard cap on vehicles
    LOG_RADIUS  = 3.5        # pickup radius for bubble log shards

    def __init__(self):
        self._visited  = set()   # (cx,cy) cells already processed
        self._log_shards = []    # [(wx,wy,entry_text), ...]  — pickupable log fragments
        self._log_seed = random.randint(0, 0xFFFFFFFF)

    def reset(self):
        self._visited.clear()
        self._log_shards.clear()

    def _cell(self, px, py):
        return (int(math.floor(px / self.CELL_SIZE)),
                int(math.floor(py / self.CELL_SIZE)))

    def tick(self, player):
        """Call once per frame while on foot or in vehicle. Spawns into player lists."""
        if player.router is None: return
        px, py, _ = player.pos()
        cx, cy    = self._cell(px, py)

        # Check a small neighbourhood so fast vehicles don't skip cells
        for dcx in (-1, 0, 1):
            for dcy in (-1, 0, 1):
                key = (cx+dcx, cy+dcy)
                if key in self._visited: continue
                self._visited.add(key)
                self._spawn_cell(player, key)

        # Check log shard pickups
        self._check_log_pickups(player, px, py)

    def _spawn_cell(self, player, cell_key):
        cx, cy = cell_key
        rng    = random.Random(hash((cx, cy, player.planet["seed"] if player.planet else 0)) ^ 0xBEEFCAFE)
        router = player.router
        biome  = player.biome

        # World-space centre of this cell
        wx = cx * self.CELL_SIZE + self.CELL_SIZE / 2
        wy = cy * self.CELL_SIZE + self.CELL_SIZE / 2

        # ---- Enemy spawn ----
        if len(player.entities) < self.MAX_ENT:
            kinds = {
                DUNGEON: ['Z','D','G','B'],
                CITY:    ['Z','G','M'],
                WILDS:   ['G','Z','S'],
                MOON:    ['D','S'],
            }.get(biome, ['Z','G'])
            n_ent = rng.choice([0, 0, 1, 1, 2, 2, 3, 4, 5])   # mostly small bursts
            for _ in range(n_ent):
                for _ in range(20):
                    ex = wx + rng.uniform(-self.CELL_SIZE*.9, self.CELL_SIZE*.9)
                    ey = wy + rng.uniform(-self.CELL_SIZE*.9, self.CELL_SIZE*.9)
                    if router.is_open(ex, ey):
                        player.entities.append(CVEntity(ex, ey, rng.choice(kinds)))
                        break

        # ---- Vehicle spawn ----
        if len(player.vehicles) < self.MAX_VEH:
            n_veh = rng.choice([0, 1, 1, 2, 2, 3, 4, 5, 6, 8])
            next_id = max((v['id'] for v in player.vehicles), default=0) + 1
            for k in range(n_veh):
                for _ in range(20):
                    vx2 = wx + rng.uniform(-self.CELL_SIZE*.9, self.CELL_SIZE*.9)
                    vy2 = wy + rng.uniform(-self.CELL_SIZE*.9, self.CELL_SIZE*.9)
                    if router.is_open(vx2, vy2):
                        player.vehicles.append({
                            'id':    next_id + k,
                            'x':     vx2, 'y': vy2,
                            'angle': rng.uniform(0, TAU),
                            'kind':  'vehicle',
                        })
                        break

        # ---- Procedural log shard ----
        if rng.random() < 0.45:   # ~45% of cells drop a log fragment
            for _ in range(20):
                lx = wx + rng.uniform(-self.CELL_SIZE*.8, self.CELL_SIZE*.8)
                ly = wy + rng.uniform(-self.CELL_SIZE*.8, self.CELL_SIZE*.8)
                if router.is_open(lx, ly):
                    seed = hash((cx, cy, self._log_seed)) & 0x7FFFFFFF
                    # 50% chance use static pool, 50% procedural
                    if rng.random() < 0.5 and LOG_ENTRIES:
                        entry = rng.choice(LOG_ENTRIES)
                    else:
                        entry = _gen_log_entry(seed)
                    self._log_shards.append([lx, ly, entry, False])
                    break

    def _check_log_pickups(self, player, px, py):
        for shard in self._log_shards:
            if shard[3]: continue
            if math.hypot(shard[0]-px, shard[1]-py) < self.LOG_RADIUS:
                shard[3] = True
                entry = shard[2]
                if entry not in player.log_entries:
                    player.log_entries.append(entry)
                return entry   # caller can show HUD msg
        return None

    def draw_shards(self, buf, cam, zbuf, W, H):
        """Draw nearby uncollected log shards as \u2741 glyphs in the raycaster view."""
        for lx, ly, _, found in self._log_shards:
            if found: continue
            dx = lx - cam.pos.x; dy = ly - cam.pos.y
            inv = cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y
            if abs(inv) < 1e-9: continue
            inv = 1./inv
            tX  = inv*(cam.dir.y*dx - cam.dir.x*dy)
            tY  = inv*(-cam.plane.y*dx + cam.plane.x*dy)
            if tY < .3: continue
            sx = int(W/2*(1+tX/tY))
            zi = max(0, min(W-1, sx))
            if tY < zbuf[zi] and 0 <= sx < W and 0 <= H//2 < H:
                buf[H//2][sx] = '\u2741'


# ================================================================ WORLD ROUTERS


class CityRouter:
    STRIDE = 12
    STREET = 2
    def __init__(self, seed=WORLD_SEED): self.seed=seed; self.name=BIOME_NAMES[CITY]
    def get_cell(self, x, y):
        ix,iy = int(math.floor(x)), int(math.floor(y))
        rx,ry = ix%self.STRIDE, iy%self.STRIDE
        if rx<self.STREET or rx>=self.STRIDE-self.STREET: return EMPTY
        if ry<self.STREET or ry>=self.STRIDE-self.STREET: return EMPTY
        rng = random.Random(hash((ix,iy,self.seed)))
        for _ in range(3):
            ox,oy = rng.randint(-4,4), rng.randint(-4,4)
            if abs(rx-6-ox)<2 and abs(ry-6-oy)<2: return EMPTY
        if ix%24==6 and iy%24==6: return TERMINAL
        return WALL
    def is_open(self,x,y): return self.get_cell(x,y)!=WALL

class PhosCityRouter:
    BLOCK_STRIDE=12; STREET_HALF=2
    def __init__(self, seed=WORLD_SEED): self.seed=seed; self.name=BIOME_NAMES[CITY]
    def get_cell(self, x, y):
        cx,cy = int(math.floor(x)), int(math.floor(y))
        rx,ry = cx%self.BLOCK_STRIDE, cy%self.BLOCK_STRIDE
        if rx<self.STREET_HALF or rx>=self.BLOCK_STRIDE-self.STREET_HALF: return 0
        if ry<self.STREET_HALF or ry>=self.BLOCK_STRIDE-self.STREET_HALF: return 0
        bk = (cx//self.BLOCK_STRIDE, cy//self.BLOCK_STRIDE, self.seed)
        return 1 + ((hash(bk)&0x7fffffff) % 4)
    def is_open(self,x,y): return self.get_cell(x,y)==0

class DungeonRouter:
    def __init__(self, seed=WORLD_SEED): self.seed=seed; self.name=BIOME_NAMES[DUNGEON]; self._cache={}
    def _noise(self, x, y, scale): return (hash((int(x/scale),int(y/scale),self.seed))&0xffff)/0xffff
    def get_cell(self, x, y):
        ix,iy = int(math.floor(x)), int(math.floor(y)); k=(ix,iy)
        if k in self._cache: return self._cache[k]
        v = self._noise(ix,iy,6.)*0.7 + self._noise(ix,iy,2.)*0.3
        cell = EMPTY if v>0.45 else WALL
        if v>0.85 and (ix+iy)%17==0: cell=TERMINAL
        if len(self._cache)>8000: self._cache.clear()
        self._cache[k]=cell; return cell
    def is_open(self,x,y): return self.get_cell(x,y)!=WALL

class WildsRouter:
    def __init__(self, seed=WORLD_SEED): self.seed=seed; self.name=BIOME_NAMES[WILDS]
    def get_cell(self, x, y):
        h = hash((int(math.floor(x)),int(math.floor(y)),self.seed)) & 0x7fffffff
        if h%113==0:   return WALL
        if h%1019==0:  return TERMINAL
        return EMPTY
    def is_open(self,x,y): return self.get_cell(x,y)!=WALL

class MoonRouter:
    def __init__(self, seed=WORLD_SEED): self.seed=seed; self.name=BIOME_NAMES[MOON]
    def get_cell(self, x, y):
        ix,iy = int(math.floor(x)), int(math.floor(y))
        rng = random.Random(hash((ix//16,iy//16,self.seed)))
        for _ in range(3):
            cx2=(ix//16)*16+rng.randint(2,13); cy2=(iy//16)*16+rng.randint(2,13); r=rng.randint(2,5)
            if abs((ix-cx2)**2+(iy-cy2)**2 - r*r)<r: return WALL
        if hash((ix,iy,self.seed))%2003==0: return TERMINAL
        return EMPTY
    def is_open(self,x,y): return self.get_cell(x,y)!=WALL

class ShipRouter:
    W,H = 60,30
    def __init__(self, ship_id):
        rng = random.Random((ship_id*31337)^0xCAFEBABE)
        grid = [[WALL]*self.W for _ in range(self.H)]; mid = self.H//2
        self.name = "ENEMY SHIP"
        for x in range(2,self.W-2): grid[mid][x]=grid[mid-1][x]=grid[mid+1][x]=EMPTY
        for _ in range(rng.randint(4,7)):
            rw,rh = rng.randint(4,8), rng.randint(3,5); rx2=rng.randint(3,self.W-rw-3)
            top = rng.choice([True,False]); ry2=max(2,mid-2-rh) if top else min(self.H-rh-2,mid+2)
            for yy in range(ry2,ry2+rh):
                for xx in range(rx2,rx2+rw): grid[yy][xx]=EMPTY
            dx2=rx2+rw//2; lo,hi=(ry2+rh,mid-1) if top else (mid+2,ry2)
            for yy in range(lo,hi): grid[yy][dx2]=EMPTY
        grid[mid][self.W-4]=TERMINAL
        self.grid=grid; self.spawn_x=3.5; self.spawn_y=mid+.5
    def get_cell(self, x, y):
        ix,iy = int(math.floor(x)), int(math.floor(y))
        return self.grid[iy][ix] if 0<=ix<self.W and 0<=iy<self.H else WALL
    def is_open(self,x,y): return self.get_cell(x,y)!=WALL

def biome_for(seed): return abs(hash((seed,'biome'))) % 4
def make_router(biome, seed):
    return {CITY:CityRouter, DUNGEON:DungeonRouter, WILDS:WildsRouter, MOON:MoonRouter}[biome](seed)
def make_vehicle_router(biome, seed):
    return PhosCityRouter(seed) if biome==CITY else make_router(biome,seed)

# ================================================================ COSMOS

STAR_GLYPHS  = ['.', '\u00b7', '*', '+', '\u00b0', "'", '`', '\u2726', '\u2605', '\u2606']
STAR_COLORS  = ["#ffffff","#aabbff","#ffddaa","#aaffff","#ffbbbb","#88aaff","#ffcc88","#ccddff","#ffb000","#88ffcc"]
PLANET_CHARS = ["@","O","#","0","\u0398","\u2295","\u25ce","\u25cf"]
PLANET_COLORS= ["#ff8844","#44aaff","#aaff88","#ffaa44","#ff44aa","#88ffff"]
COMET_CHARS  = ['@','%','#','*','+','\u00b7','.',' ']
COMET_COLORS = ["#ffffff","#aaccff","#ffeeaa","#88ffff","#ffaa88"]
CHUNK_RADIUS = 4000
STARS_PER_CHUNK = 120
COMET_POOL   = 8

class StarChunk:
    __slots__ = ('stars',)
    def __init__(self, key):
        rng=random.Random(hash(key)^0xDEADBEEF); cx,cy,cz=[k*CHUNK_RADIUS*2 for k in key]; self.stars=[]
        for _ in range(STARS_PER_CHUNK):
            phi=rng.uniform(0,TAU); ct=rng.uniform(-1,1); st=math.sqrt(1-ct*ct)
            r=rng.uniform(CHUNK_RADIUS*.2,CHUNK_RADIUS)
            self.stars.append((cx+r*st*math.cos(phi), cy+r*ct, cz+r*st*math.sin(phi),
                               rng.choice(STAR_GLYPHS), rng.choice(STAR_COLORS),
                               rng.choice([8,9,10,11,12])))

class StarField:
    def __init__(self, max_chunks=200): self._chunks={}; self._max=max_chunks
    def _key(self, pos): return tuple(int(math.floor(v/(CHUNK_RADIUS*2))) for v in pos)
    def near(self, pos):
        cx,cy,cz=self._key(pos); stars=[]
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    k=(cx+dx,cy+dy,cz+dz)
                    if k not in self._chunks:
                        if len(self._chunks)>self._max:
                            far=max(self._chunks,key=lambda q:(q[0]-cx)**2+(q[1]-cy)**2+(q[2]-cz)**2)
                            del self._chunks[far]
                        self._chunks[k]=StarChunk(k)
                    stars.extend(self._chunks[k].stars)
        return stars

class Comet:
    def __init__(self, player_pos, player_fwd):
        sp=3000; self.age=0
        self.pos=[player_pos[i]+player_fwd[i]*4000+random.uniform(-sp,sp) for i in range(3)]
        s=random.uniform(30,120); self.vel=[random.uniform(-s,s) for _ in range(3)]
        self.tail_len=random.randint(5,14); self.tail=[]
        self.color=random.choice(COMET_COLORS); self.max_age=random.randint(120,400)
    def update(self):
        self.tail.insert(0,list(self.pos))
        if len(self.tail)>self.tail_len: self.tail.pop()
        self.pos=vadd(self.pos,self.vel); self.age+=1
    def alive(self): return self.age<self.max_age

class PlanetField:
    def __init__(self, count=20):
        rng=random.Random(WORLD_SEED); self.planets=[]
        for i in range(count):
            s=rng.randint(0,10**9)
            self.planets.append({"id":i,"seed":s,
                                  "pos":[rng.uniform(-40000,40000) for _ in range(3)],
                                  "size":rng.randint(40,150),"char":rng.choice(PLANET_CHARS),
                                  "color":rng.choice(PLANET_COLORS),"rot":rng.uniform(0,TAU),
                                  "rot_spd":rng.uniform(-.02,.02),"biome":biome_for(s)})
    def update(self):
        for p in self.planets: p["rot"]+=p["rot_spd"]
    def nearest(self, pos, max_dist=600):
        best,bd=None,max_dist
        for p in self.planets:
            d=math.sqrt(sum((p["pos"][i]-pos[i])**2 for i in range(3)))
            if d<bd: bd,best=d,p
        return best

# ================================================================ ENTITIES

class CVEntity:
    __slots__ = ('x','y','char','hp','speed','dmg','state','flash','dead_timer','attack_cd',
                 'eid','confusion','wander_dir','wander_t','pacified','pacify_t',
                 'wander_nt','shake_freq','msg_text','msg_t','newly_pacified','spoke',
                 'vibration_intensity','vibration_timer',
                 'shake_intensity','shake_timer',
                 'stillness_timer')
    def __init__(self, x, y, char='Z'):
        self.x=float(x); self.y=float(y); self.char=char
        self.hp=ENEMY_HP.get(char,3); self.speed=ENEMY_SPD.get(char,.02); self.dmg=ENEMY_DMG.get(char,8)
        self.state='IDLE'; self.flash=0; self.dead_timer=0; self.attack_cd=0
        self.eid=random.randint(1,0xFFFFFF)
        self.confusion=0; self.wander_dir=random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.wander_t=0; self.pacified=False; self.pacify_t=0
        self.wander_nt=random.uniform(0,100); self.shake_freq=random.uniform(.08,.15)
        self.msg_text=""; self.msg_t=0; self.newly_pacified=False
        self.spoke=False
        self.vibration_intensity=0.; self.vibration_timer=0
        self.shake_intensity=0.; self.shake_timer=0.
        self.stillness_timer=0

    def alive(self): return self.state!='DEAD'

    def glyph(self):
        if self.state=='DEAD':     return '%'
        if self.flash>0:           return '*'
        if self.pacified:          return 'n'
        if self.state=='CONFUSED': return '?'
        if self.state=='ATTACK':   return '!'
        return self.char

    def update(self, cam, router):
        if self.state=='DEAD': self.dead_timer-=1; return

        if self.vibration_intensity>0:
            self.vibration_timer+=1
            if self.vibration_timer>8:
                self.vibration_intensity=0; self.vibration_timer=0
            else:
                wx=random.uniform(-self.vibration_intensity,self.vibration_intensity)
                wy=random.uniform(-self.vibration_intensity,self.vibration_intensity)
                if router.is_open(self.x+wx,self.y): self.x+=wx
                if router.is_open(self.x,self.y+wy): self.y+=wy

        if self.pacify_t>0:
            self.pacify_t-=1
            if self.pacify_t==0:
                self.pacified=True; self.confusion=0; self.dmg=0
                self.wander_dir=random.choice([(1,0),(-1,0),(0,1),(0,-1)])
                self.wander_t=0; self.wander_nt=random.uniform(0,100)
                self.shake_freq=random.uniform(.08,.15)

        if self.attack_cd>=9999: self.state='CONFUSED' if not self.pacified else 'IDLE'; self.dmg=0

        if self.confusion>0 or self.pacified: self.dmg=0; self.attack_cd=9999

        if self.confusion>0: self.confusion=max(0,self.confusion-1)

        if self.confusion>0 or self.pacified: self.dmg=0; self.attack_cd=9999

        if self.msg_t>0: self.msg_t-=1
        if self.msg_t<=0: self.msg_text=""
        if self.flash>0: self.flash-=1
        if self.attack_cd>0 and self.attack_cd<9999: self.attack_cd-=1

        dx=cam.pos.x-self.x; dy=cam.pos.y-self.y; dist=math.hypot(dx,dy)

        if self.confusion>0:
            self.state='CONFUSED'; self.dmg=0; self.attack_cd=9999
            if self.stillness_timer>0:
                self.stillness_timer-=1
                self.shake_intensity=0.15
                self.shake_timer+=self.shake_freq*0.5
                if self.flash>0: self.flash-=1
                else: self.flash=random.randint(1,3)
                self.dmg=0; self.attack_cd=9999; return
            self.wander_nt+=random.uniform(.08,.35)
            scale=max(.3,min(1.8,(.5+.5*math.sin(self.wander_nt*.05))*random.uniform(.7,1.3)))
            self.wander_t+=1
            if self.wander_t>random.randint(10,40):
                self.wander_t=0
                self.wander_dir=(0,0) if random.random()<.25 else random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            dx_m,dy_m=self.wander_dir; mv=self.speed*scale
            nx=self.x+dx_m*mv; ny=self.y+dy_m*mv
            if router.is_open(nx,self.y): self.x=nx
            if router.is_open(self.x,ny): self.y=ny
            self.shake_intensity=0.25; self.shake_timer+=self.shake_freq
            sx=math.sin(self.shake_timer*TAU)*self.shake_intensity*random.uniform(.8,1.2)
            sy=math.cos(self.shake_timer*TAU)*self.shake_intensity*random.uniform(.8,1.2)
            if router.is_open(self.x+sx,self.y): self.x+=sx
            if router.is_open(self.x,self.y+sy): self.y+=sy
            if self.flash>0: self.flash-=1
            else: self.flash=random.randint(1,3)
            self.dmg=0; self.attack_cd=9999; return

        if self.pacified:
            self.state='IDLE'; self.dmg=0; self.attack_cd=9999
            if self.msg_t>0:
                if self.flash>0: self.flash-=1
                return
            self.wander_nt+=random.uniform(.08,.35)*.1
            scale=max(.03,min(.18,(.5+.5*math.sin(self.wander_nt*.05))*random.uniform(.7,1.3)*.1))
            self.wander_t+=1
            if self.wander_t>random.randint(10,40):
                self.wander_t=0
                self.wander_dir=(0,0) if random.random()<.25 else random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            dx_m,dy_m=self.wander_dir; mv=self.speed*scale
            nx=self.x+dx_m*mv; ny=self.y+dy_m*mv
            if router.is_open(nx,self.y): self.x=nx
            if router.is_open(self.x,ny): self.y=ny
            self.shake_intensity=0.025; self.shake_timer+=self.shake_freq
            sx=math.sin(self.shake_timer*TAU)*self.shake_intensity*random.uniform(.8,1.2)
            sy=math.cos(self.shake_timer*TAU)*self.shake_intensity*random.uniform(.8,1.2)
            if router.is_open(self.x+sx,self.y): self.x+=sx
            if router.is_open(self.x,self.y+sy): self.y+=sy
            if self.flash>0: self.flash-=1
            else: self.flash=random.randint(1,3)
            return

        if dist<18:
            if not self.spoke and dist<12 and self.msg_t<=0:
                lines=DIALOGUE.get(self.char,["..."])
                self.msg_text=random.choice(lines); self.msg_t=90; self.spoke=True
            self.state='CHASE'
            angle=math.atan2(dy,dx)
            nx=self.x+math.cos(angle)*self.speed; ny=self.y+math.sin(angle)*self.speed
            if router.is_open(nx,self.y): self.x=nx
            if router.is_open(self.x,ny): self.y=ny
        if dist<1.1 and self.attack_cd<=0 and self.attack_cd<9999:
            self.state='ATTACK'
            if not self.pacified and self.confusion<=0: cam.health-=self.dmg
            self.attack_cd=45

    def hit(self, amount=1):
        if self.pacified: return
        self.hp-=1; self.flash=3
        if self.hp>0: return
        self.attack_cd=9999; self.dmg=0
        self.confusion=930
        self.stillness_timer=930
        self.vibration_intensity=0.15; self.vibration_timer=0
        self.shake_intensity=0.25; self.shake_timer=0.
        self.shake_freq=random.uniform(.08,.15)
        self.pacify_t=620
        self.wander_dir=random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.wander_t=0; self.wander_nt=random.uniform(0,100)
        self.msg_text="Stillness Achieved. Peace and Bliss"
        self.msg_t=620; self.newly_pacified=True

class SpaceEnemy:
    def __init__(self, x, y, z, eid):
        self.pos=V3(x,y,z); self.hp=self.max_hp=40; self.alive_flag=True; self.fire_cd=0.; self.eid=eid
    def update(self, player_pos, dt):
        if not self.alive_flag: return
        to=player_pos-self.pos; dist=to.length()
        if dist>.1: self.pos=self.pos+to.normalize()*(50.*dt)
        self.fire_cd=max(0.,self.fire_cd-dt)
        if dist<300 and self.fire_cd<=0: self.fire_cd=random.uniform(1.,2.)
    def take_damage(self, d): self.hp-=d;
    def alive(self): return self.alive_flag

# ================================================================ CAMERAS

class CVCamera:
    def __init__(self, x=10.5, y=10.5):
        self.pos    = V2(x,y)
        self.dir    = V2(-1., 0.)
        self.plane  = V2(0., 0.66)
        self.pitch  = 0.
        self.bob    = 0.
        self.bob_phase = 0.
        self.health = 100; self.max_health = 100
        self.shield = 50;  self.max_shield = 50
        self.jump_vel=0.; self.jump_off=0.; self.jumping=False; self.landed=False
        self.shake_amp=0.; self.shake_frames=0

    def rotate(self, speed):
        c,s = math.cos(speed), math.sin(speed)
        dx,dy = self.dir.x, self.dir.y
        self.dir.x  = dx*c+dy*s;   self.dir.y  = -dx*s+dy*c
        px,py = self.plane.x, self.plane.y
        self.plane.x= px*c+py*s;   self.plane.y= -px*s+py*c

    def step_bob(self, moving):
        if moving: self.bob_phase+=.18; self.bob=math.sin(self.bob_phase)*2.
        else:      self.bob*=.85

    def land_shake(self, amp=6., frames=14): self.shake_amp,self.shake_frames=amp,frames
    def update_shake(self):
        if self.shake_frames<=0: self.shake_amp=0.; return 0.
        self.shake_frames-=1; decay=self.shake_frames/14.
        off=(random.random()*2-1)*self.shake_amp*decay; self.shake_amp*=.78; return off

    def jump(self):
        if not self.jumping: self.jump_vel=2.8; self.jumping=True; self.landed=False
    def update_jump(self):
        if not self.jumping: self.landed=False; return False
        self.jump_vel -= (.055 if self.jump_vel>0 else .0932)
        self.jump_off += self.jump_vel
        if self.jump_off<=0 and self.jump_vel<0:
            self.jump_off=self.jump_vel=0.; self.jumping=False; self.landed=True; return True
        self.landed=False; return False

    def take_damage(self, dmg):
        rem=dmg
        if self.shield>0: t=min(self.shield,rem); self.shield-=t; rem-=t
        if rem>0: self.health-=rem
        return self.health<=0
    def heal(self, n):           self.health=min(self.max_health,self.health+n)
    def restore_shield(self, n): self.shield=min(self.max_shield,self.shield+n)


class DrivingCamera:
    """
    Phos City driving camera.
    Physics: W/S throttle, A/D steer.
    Arrow LEFT/RIGHT: camera yaw offset (look left/right while driving, without turning the car).
    """
    RPM_IDLE    = 1100.
    RPM_REDLINE = 6800.
    N_GEARS     = 6
    MAX_FWD     = 44.;  MAX_REV  = -8.0
    ACCEL       = 14.;  BRAKE    = 22.;  DRAG = 1.4;  STEER = 1.4
    # Camera yaw (look left/right independent of car heading)
    CAM_YAW_SPD = 0.055   # radians per frame
    CAM_YAW_MAX = 1.10    # max yaw offset (about ±63 degrees)
    CAM_YAW_RTN = 0.06    # return-to-centre speed when key released

    def __init__(self, x=10.5, y=10.5, angle=0.):
        self.x,self.y,self.angle=x,y,angle
        self.speed=self.angular_v=0.; self.fov=math.pi/2.6
        self.shake=0.; self.hp_y=0.; self.gear=1; self._idle=0.
        self.health=100; self.max_health=100
        self.shield=50;  self.max_shield=50
        self.heat=0.;    self.overheated=False
        self.cam_yaw=0.   # current camera yaw offset (added to self.angle for rendering)

    @property
    def rpm(self):
        sf=max(0.,self.speed)/self.MAX_FWD
        if sf<.0015: self._idle+=.06; return self.RPM_IDLE+60.*math.sin(self._idle)
        g=max(1,min(self.N_GEARS,1+int(sf*self.N_GEARS))); self.gear=g
        gl=(g-1)/self.N_GEARS; gh=g/self.N_GEARS
        return self.RPM_IDLE+(self.RPM_REDLINE-self.RPM_IDLE)*(sf-gl)/max(.001,gh-gl)

    @property
    def render_angle(self):
        """The heading used for rendering (car angle + camera yaw offset)."""
        return self.angle + self.cam_yaw

    def update(self, dt, throttle, brake, steer, boost, yaw_left, yaw_right, router=None):
        """
        yaw_left / yaw_right: bool — arrow LEFT / RIGHT held.
        These rotate the camera view without affecting the car's steering.
        """
        mf=self.MAX_FWD*(1.45 if boost else 1.)
        if throttle>0:
            hr=max(0.,1.-self.speed/mf) if self.speed>0 else 1.
            self.speed+=self.ACCEL*throttle*hr*dt*(1.5 if boost else 1.)
        if brake>0:
            self.speed=(max(self.speed-self.BRAKE*brake*dt,-.5) if self.speed>0
                        else max(self.speed-self.ACCEL*.5*brake*dt,self.MAX_REV))
        if not throttle and not brake:
            self.speed=(max(0.,self.speed-self.DRAG*dt) if self.speed>0
                        else min(0.,self.speed+self.DRAG*dt))
        self.speed=max(self.MAX_REV,min(mf,self.speed))
        sf=abs(self.speed)/self.MAX_FWD; auth=.55+.45*(1.-sf*.5)
        self.angular_v=steer*self.STEER*auth*((0.4+0.6*sf) if abs(self.speed)>.2 else 0.)
        self.angle+=self.angular_v*dt
        tgt=-.15 if (throttle and self.speed>.5) else (.20 if brake and self.speed>.5 else 0.)
        self.hp_y+=(tgt-self.hp_y)*min(1.,6.*dt)
        dx=math.cos(self.angle)*self.speed*dt; dy=math.sin(self.angle)*self.speed*dt
        if router is None: self.x+=dx; self.y+=dy
        else:
            nx=self.x+dx
            if router.is_open(nx+(0.18 if dx>0 else-.18),self.y): self.x=nx
            else: self.shake=min(1.,self.shake+.6); self.speed*=.4
            ny=self.y+dy
            if router.is_open(self.x,ny+(0.18 if dy>0 else-.18)): self.y=ny
            else: self.shake=min(1.,self.shake+.6); self.speed*=.4
        self.shake*=max(0.,1.-4.*dt)

        # --- Camera yaw ---
        if yaw_left:
            self.cam_yaw = max(-self.CAM_YAW_MAX, self.cam_yaw - self.CAM_YAW_SPD)
        elif yaw_right:
            self.cam_yaw = min( self.CAM_YAW_MAX, self.cam_yaw + self.CAM_YAW_SPD)
        else:
            # Auto-return to centre when no arrow held
            if abs(self.cam_yaw) < self.CAM_YAW_RTN:
                self.cam_yaw = 0.
            else:
                self.cam_yaw -= math.copysign(self.CAM_YAW_RTN, self.cam_yaw)


class SpacecraftCamera:
    def __init__(self, x=0., y=0., z=0.):
        self.pos=[x,y,z]; self.fwd=[0.,0.,1.]; self.up=[0.,1.,0.]; self.right=[1.,0.,0.]
        self.vel=0.; self.thruster_on=self.boost_on=False; self.boost_fuel=100.
        self.health=150; self.max_health=150; self.shield=100; self.max_shield=100
    def reortho(self):
        self.fwd=vnorm(self.fwd); self.right=vnorm(self.right)
        self.up=vnorm([self.fwd[1]*self.right[2]-self.fwd[2]*self.right[1],
                       self.fwd[2]*self.right[0]-self.fwd[0]*self.right[2],
                       self.fwd[0]*self.right[1]-self.fwd[1]*self.right[0]])
        self.right=vnorm([self.up[1]*self.fwd[2]-self.up[2]*self.fwd[1],
                          self.up[2]*self.fwd[0]-self.up[0]*self.fwd[2],
                          self.up[0]*self.fwd[1]-self.up[1]*self.fwd[0]])
    def update(self, dt, keys):
        ts=0.045
        if 'w' in keys: self.fwd=rodrigues(self.fwd,self.right,-ts); self.up=rodrigues(self.up,self.right,-ts)
        if 's' in keys: self.fwd=rodrigues(self.fwd,self.right, ts); self.up=rodrigues(self.up,self.right, ts)
        if 'a' in keys: self.fwd=rodrigues(self.fwd,self.up,-ts); self.right=rodrigues(self.right,self.up,-ts)
        if 'd' in keys: self.fwd=rodrigues(self.fwd,self.up, ts); self.right=rodrigues(self.right,self.up, ts)
        if 'q' in keys: self.up=rodrigues(self.up,self.fwd, ts); self.right=rodrigues(self.right,self.fwd, ts)
        if 'e' in keys: self.up=rodrigues(self.up,self.fwd,-ts); self.right=rodrigues(self.right,self.fwd,-ts)
        ms=25.
        if 'up'    in keys: self.pos=vadd(self.pos,vmul(self.up,   ms))
        if 'down'  in keys: self.pos=vadd(self.pos,vmul(self.up,  -ms))
        if 'left'  in keys: self.pos=vadd(self.pos,vmul(self.right,-ms))
        if 'right' in keys: self.pos=vadd(self.pos,vmul(self.right, ms))
        bm=4. if self.boost_on else 1.
        target=(320. if self.boost_on else 80.*bm) if self.thruster_on else 0.
        self.vel+=(target-self.vel)*.07
        self.pos=vadd(self.pos,vmul(self.fwd,self.vel))
        if self.boost_on and self.boost_fuel>0:
            self.boost_fuel=max(0.,self.boost_fuel-60.*dt)
            if self.boost_fuel<=0: self.boost_on=False
        elif self.boost_fuel<100.: self.boost_fuel=min(100.,self.boost_fuel+20.*dt)
    def take_damage(self, d):
        r=d
        if self.shield>0: t=min(self.shield,r); self.shield-=t; r-=t
        if r>0: self.health-=r
        return self.health<=0
    def pos_v3(self): return V3(*self.pos)

# ================================================================ PLAYER

class Player:
    FOOT='foot'; VEHICLE='vehicle'; SPACE='space'; BOARD='board'

    def __init__(self):
        self.mode    = self.SPACE
        self.cv      = CVCamera()
        self.veh     = DrivingCamera()
        self.craft   = SpacecraftCamera()
        self.heat=0.; self.overheated=False
        self.powerups={k:0 for k in PU_TYPES}
        self.land_word=''; self.land_t=0
        self.entities=[];  self.vehicles=[]; self.terminals=[]
        self.pu_spawner=PUSpawner(); self.particles=Particles(); self.tracers=[]
        self.artifact_spawner=None
        self.log_entries=[]; self.log_open=False; self.log_scroll=0
        self.space_enemies=[];  self._spawn_space_enemies()
        self.router=None; self.veh_router=None; self.planet=None; self.biome=None
        self.board_router=None; self.boarded=None
        self._stash_ent=[]; self._stash_router=None
        self._step_cd=0; self._v_prev=False
        self.world_bubble=WorldBubble()

    def _spawn_space_enemies(self):
        rng=random.Random(WORLD_SEED^0xBADF00D)
        self.space_enemies=[SpaceEnemy(rng.uniform(-2000,2000),rng.uniform(-2000,2000),
                                        rng.uniform(1000,4000),i) for i in range(6)]

    def _safe_pos(self, router, rng, lo=4., hi=96., tries=120):
        for _ in range(tries):
            x=rng.uniform(lo,hi); y=rng.uniform(lo,hi)
            if router.is_open(x,y): return x,y
        for r in range(1,60):
            for t in range(max(8,r*4)):
                a=t/max(8,r*4)*TAU
                x=50.+r*math.cos(a); y=50.+r*math.sin(a)
                if lo<=x<=hi and lo<=y<=hi and router.is_open(x,y): return x,y
        return 50.,50.

    def _spawn_ground(self, planet, biome):
        rng=random.Random(planet["seed"])
        self.entities=[]; self.vehicles=[]; self.terminals=[]
        self.pu_spawner=PUSpawner(); self.particles=Particles(); self.tracers=[]

        dense = (planet["seed"] % 2 == 0)
        pop_mult = rng.randint(3,5) if dense else rng.randint(1,2)

        base_count, kinds = {
            DUNGEON: (20,  ['Z','D','G','B']),
            CITY:    (16,  ['Z','G','M']),
            WILDS:   (14,  ['G','Z','S']),
            MOON:    (8,   ['D','S']),
        }[biome]
        count = base_count * pop_mult

        for _ in range(count):
            x,y = self._safe_pos(self.router, rng)
            self.entities.append(CVEntity(x, y, rng.choice(kinds)))

        if biome == DUNGEON:
            vcount = rng.randint(30, 45)
        elif dense:
            vcount = rng.randint(50, 70)
        else:
            vcount = rng.randint(35, 50)

        for i in range(vcount):
            x,y = self._safe_pos(self.router, rng)
            self.vehicles.append({
                'id':   i+1,
                'x':    x, 'y': y,
                'angle':rng.uniform(0,TAU),
                'kind': 'vehicle',
            })
        sx,sy = self._safe_pos(self.router, rng, lo=10., hi=90.)
        self.vehicles.append({
            'id':   vcount+1,
            'x':    sx, 'y': sy,
            'angle':rng.uniform(0,TAU),
            'kind': 'ship',
        })

        for _ in range(6):
            x,y = self._safe_pos(self.router, rng)
            self.terminals.append({'x':x,'y':y,'used':False})

        if self.router:
            self.pu_spawner.spawn_near(self.cv.pos.x,self.cv.pos.y,self.router)
            self.artifact_spawner=ArtifactSpawner(self.router,count=25,seed=planet["seed"]^0xABCD)

    def land(self, planet):
        self.planet=planet; self.biome=planet["biome"]
        s=WORLD_SEED^planet["seed"]
        self.router=make_router(self.biome,s); self.veh_router=make_vehicle_router(self.biome,s)
        ox,oy=self._open_spawn(self.router)
        self.cv.pos=V2(ox,oy); self.cv.dir=V2(-1.,0.); self.cv.plane=V2(0.,.66)
        self._spawn_ground(planet,self.biome); self.world_bubble.reset(); self.mode=self.FOOT

    def takeoff(self):
        if self.planet:
            p=self.planet
            self.craft.pos=[p["pos"][0]+p["size"]*4, p["pos"][1], p["pos"][2]]
            self.craft.fwd,self.craft.up,self.craft.right=[0.,0.,1.],[0.,1.,0.],[1.,0.,0.]
            self.craft.vel=0.; self.craft.thruster_on=self.craft.boost_on=False
        self.planet=self.biome=self.router=self.veh_router=None; self.mode=self.SPACE
        self.artifact_spawner=None

    def enter_vehicle(self, vid):
        for v in self.vehicles:
            if v['id']==vid:
                self.veh.x,self.veh.y,self.veh.angle=v['x'],v['y'],v['angle']
                self.veh.speed=0.; self.veh.cam_yaw=0.; self.mode=self.VEHICLE; return True
        return False

    def exit_vehicle(self):
        vx,vy,va = self.veh.x, self.veh.y, self.veh.angle
        fx,fy = math.cos(va), math.sin(va)
        router = self.router

        candidates = [
            ( fx*1.5,  fy*1.5),
            (-fy*1.5,  fx*1.5),
            ( fy*1.5, -fx*1.5),
            (-fx*1.5, -fy*1.5),
            ( fx,      fy),
            (-fy,      fx),
            ( fy,     -fx),
            (-fx,     -fy),
        ]
        for dx,dy in candidates:
            nx,ny = vx+dx, vy+dy
            if router and router.is_open(nx,ny):
                ex,ey = nx,ny; break
        else:
            ex,ey = self._open_spawn(router, vx, vy, default=(vx,vy))

        self.cv.pos   = V2(ex, ey)
        self.cv.dir   = V2(fx, fy)
        self.cv.plane = V2(-fy*.66, fx*.66)
        self.mode = self.FOOT

    def board_ship(self, enemy):
        self.board_router=ShipRouter(enemy.eid); self.boarded=enemy
        self.cv.pos=V2(self.board_router.spawn_x, self.board_router.spawn_y)
        self.cv.dir=V2(0.,1.); self.cv.plane=V2(.66,0.)
        rng=random.Random(enemy.eid^0xBEEF); defenders=[]
        for _ in range(rng.randint(2,4)):
            defenders.append(CVEntity(rng.uniform(20,55),ShipRouter.H//2+rng.uniform(-1,1),'G'))
        self._stash_ent,self._stash_router=self.entities,self.router
        self.entities,self.router=defenders,self.board_router; self.mode=self.BOARD

    def disembark(self):
        self.entities,self.router=self._stash_ent,self._stash_router
        if self.boarded: self.boarded.alive_flag=False
        self.boarded=self.board_router=None; self.mode=self.SPACE

    def teleport_to_ship(self):
        ship=next((v for v in self.vehicles if v['kind']=='ship'),None)
        if ship and self.router:
            x,y = self._open_spawn(self.router, ship['x'], ship['y'])
            self.cv.pos=V2(x, y); return True
        return False

    def _open_spawn(self, router, cx=10.5, cy=10.5, default=None):
        for r in range(60):
            steps = max(8, r*4)
            for t in range(steps):
                a = t/steps * TAU
                x = cx + r*0.6*math.cos(a)
                y = cy + r*0.6*math.sin(a)
                if router.is_open(x,y): return x,y
        return default or (cx, cy)

    def pos(self):
        if self.mode in (self.FOOT,self.BOARD): return self.cv.pos.x,self.cv.pos.y,0.
        if self.mode==self.VEHICLE:             return self.veh.x,self.veh.y,0.
        return tuple(self.craft.pos)

    def nearest_vehicle(self):
        if not self.vehicles: return None
        px,py,_=self.pos()
        return min(self.vehicles, key=lambda v:(px-v['x'])**2+(py-v['y'])**2)

    def dist_terminal(self):
        if not self.terminals: return 1e9
        px,py,_=self.pos()
        return min(math.hypot(px-t['x'],py-t['y']) for t in self.terminals)

    def use_terminal(self):
        px,py,_=self.pos()
        for t in self.terminals:
            if math.hypot(px-t['x'],py-t['y'])<2. and not t['used']:
                t['used']=True; self.cv.heal(30); self.cv.restore_shield(50)
                self.heat=max(0.,self.heat-40.); return True
        return False

    def nearest_space_enemy(self, max_dist=400):
        cp=self.craft.pos_v3(); best,bd=None,max_dist
        for e in self.space_enemies:
            if not e.alive(): continue
            d=(e.pos-cp).length()
            if d<bd: bd,best=d,e
        return best

    def check_artifacts(self, px, py):
        if not self.artifact_spawner: return None
        if self.artifact_spawner.check(px,py):
            unseen=[e for e in LOG_ENTRIES if e not in self.log_entries]
            if unseen:
                entry=random.choice(unseen); self.log_entries.append(entry); return entry
            return "(All knowledge recovered)"
        return None

# ================================================================ RENDERERS

CV_RAMP_WALL  = "@#$B%&W8MX*+=-:. "
CV_RAMP_FLOOR = ".,`' "
CV_RAMP_CEIL  = ",-.'` "

def _buf_write(buf, x, y, text, W, H):
    for i,c in enumerate(text):
        bx=x+i
        if 0<=bx<W and 0<=y<H: buf[y][bx]=c

class CVRenderer:
    def __init__(self, W, H): self.W=W; self.H=H

    def render(self, player, router):
        cam=player.cv; W,H=self.W,self.H
        buf  = [[' ']*W for _ in range(H)]
        zbuf = [1e9]*W
        eye  = max(.45, 1.-cam.jump_off*.16)
        voff = int(cam.pitch + cam.bob + cam.update_shake())

        for y in range(H//2):
            idx = min(len(CV_RAMP_CEIL)-1, int(len(CV_RAMP_CEIL)*y/(H//2)))
            c = CV_RAMP_CEIL[idx]
            if y%3==0:
                for x in range(0,W,4): buf[y][x]=c

        for x in range(W):
            cam_x   = 2*x/W - 1
            ray_dx  = cam.dir.x + cam.plane.x*cam_x
            ray_dy  = cam.dir.y + cam.plane.y*cam_x
            map_x,map_y = int(cam.pos.x), int(cam.pos.y)
            delta_dx = abs(1/ray_dx) if ray_dx else 1e30
            delta_dy = abs(1/ray_dy) if ray_dy else 1e30
            if ray_dx<0: step_x,side_dist_x = -1,(cam.pos.x-map_x)*delta_dx
            else:        step_x,side_dist_x = +1,(map_x+1.-cam.pos.x)*delta_dx
            if ray_dy<0: step_y,side_dist_y = -1,(cam.pos.y-map_y)*delta_dy
            else:        step_y,side_dist_y = +1,(map_y+1.-cam.pos.y)*delta_dy
            hit=side=cell=0; iterations=0
            while not hit and iterations<80:
                if side_dist_x < side_dist_y: side_dist_x+=delta_dx; map_x+=step_x; side=0
                else:                         side_dist_y+=delta_dy; map_y+=step_y; side=1
                cell=router.get_cell(map_x,map_y)
                if cell>0: hit=1
                iterations+=1
            if side==0: perp_dist=(map_x-cam.pos.x+(1-step_x)/2)/ray_dx
            else:       perp_dist=(map_y-cam.pos.y+(1-step_y)/2)/ray_dy
            perp_dist=max(.1,perp_dist); zbuf[x]=perp_dist
            line_h=int(H/(perp_dist*eye))
            draw_start=max(0,-line_h//2+H//2+voff); draw_end=min(H-1,line_h//2+H//2+voff)
            wall_char=CV_RAMP_WALL[min(len(CV_RAMP_WALL)-1,int(perp_dist*1.5))]
            if cell==TERMINAL: wall_char='$'
            if side==1 and wall_char not in '.,': wall_char=wall_char.lower() if wall_char.isalpha() else ':'
            for y in range(draw_start,draw_end): buf[y][x]=wall_char
            for y in range(draw_end,H):
                fi=min(len(CV_RAMP_FLOOR)-1,int((y-H//2)/max(1,H//2)*(len(CV_RAMP_FLOOR)-1)))
                if (x+y)%4==0: buf[y][x]=CV_RAMP_FLOOR[fi]

        live=[e for e in player.entities if e.alive() or e.dead_timer>0]
        for ent in sorted(live, key=lambda e:(cam.pos.x-e.x)**2+(cam.pos.y-e.y)**2, reverse=True):
            self._draw_sprite(buf,zbuf,cam,ent,voff,W,H)

        if player.mode==Player.FOOT:
            for v in player.vehicles:
                self._draw_simple(buf,zbuf,cam,v['x'],v['y'],'S' if v['kind']=='ship' else 'V',voff,W,H)

        player.pu_spawner.draw(buf,cam,zbuf,W,H)
        if player.artifact_spawner: player.artifact_spawner.draw(buf,cam,zbuf,W,H)
        player.world_bubble.draw_shards(buf,cam,zbuf,W,H)

        player.particles.draw(buf,W,H)

        for tracer in player.tracers:
            bx,by,life=tracer
            for dy in range(min(life,H-by)):
                ry=by+dy; jitter=random.randint(-1,1); bxj=bx+jitter
                if 0<=bxj<W and 0<=ry<H: buf[ry][bxj]='|'

        cx,cy=W//2,H//2
        buf[cy][cx]='X' if player.overheated else '+'
        if cx>1: buf[cy][cx-1]='-'; buf[cy][cx+1]='-'
        if cy>1: buf[cy-1][cx]='|'; buf[cy+1][cx]='|'

        self._draw_hud(buf,player,cam,router,W,H)
        return "\n".join("".join(row) for row in buf)

    def _draw_sprite(self, buf, zbuf, cam, ent, voff, W, H):
        sx=ent.x-cam.pos.x; sy=ent.y-cam.pos.y
        inv=cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y + 1e-9; iD=1./inv
        tX=iD*(cam.dir.y*sx-cam.dir.x*sy); tY=iD*(-cam.plane.y*sx+cam.plane.x*sy)
        if tY<=.1: return
        scr_x=int(W/2*(1+tX/tY)); sH=max(1,abs(int(H/tY))); sW=max(1,sH//2)
        y1=max(0,-sH//2+H//2+voff); y2=min(H-1,sH//2+H//2+voff)
        x1=max(0,scr_x-sW//2);     x2=min(W-1,scr_x+sW//2)
        g=ent.glyph(); is_corpse=(g=='%')
        rows=_sprite_rows('%' if is_corpse else ent.char, ent.flash>0, eid=ent.eid)
        fill_char = g
        rs=max(1,y2-y1)
        for sx2 in range(x1,x2):
            if tY<zbuf[sx2]:
                for sy2 in range(y1,y2):
                    ri=min(int((sy2-y1)/rs*len(rows)),len(rows)-1)
                    ci=(sx2-x1)%max(1,len(rows[ri]))
                    sc=rows[ri][ci]; buf[sy2][sx2]=sc if sc.strip() else fill_char
        if ent.msg_t>0 and ent.msg_text:
            ml=len(ent.msg_text); my=max(0,y1-2); mx=max(0,min(scr_x-ml//2,W-ml))
            for i,c in enumerate(ent.msg_text):
                if mx+i<W and my<H: buf[my][mx+i]=c

    def _draw_simple(self, buf, zbuf, cam, sx, sy, char, voff, W, H):
        dx,dy=sx-cam.pos.x,sy-cam.pos.y
        inv=cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y + 1e-9; iD=1./inv
        tX=iD*(cam.dir.y*dx-cam.dir.x*dy); tY=iD*(-cam.plane.y*dx+cam.plane.x*dy)
        if tY<=.1: return
        scr_x=int(W/2*(1+tX/tY)); sH=max(1,abs(int(H/tY)))
        y1=max(0,-sH//2+H//2+voff); y2=min(H-1,sH//2+H//2+voff)
        for px in range(max(0,scr_x-2),min(W-1,scr_x+2)):
            if tY<zbuf[px]:
                for py in range(y1,y2): buf[py][px]=char

    def _draw_hud(self, buf, player, cam, router, W, H):
        mm_w,mm_h=14,7; ox=int(cam.pos.x)-mm_w//2; oy=int(cam.pos.y)-mm_h//2
        for my in range(mm_h):
            for mx in range(mm_w):
                wx,wy=ox+mx,oy+my
                try:    c=router.get_cell(wx,wy)
                except: c=0
                mc='#' if c==WALL else ('$' if c==TERMINAL else '.')
                bx,by=1+mx,2+my
                if 0<=bx<W and 0<=by<H: buf[by][bx]=mc
        buf[2+mm_h//2][1+mm_w//2]='@'
        for v in player.vehicles:
            mx2,my2=int(v['x'])-ox,int(v['y'])-oy
            bx,by=1+mx2,2+my2
            if 0<=bx<W and 0<=by<H:
                g='S' if v['kind']=='ship' else 'V'
                buf[by][bx]=g
                if v['kind']=='ship' and 0<=by-1<H: buf[by-1][bx]='S'
        angle=math.degrees(math.atan2(cam.dir.y,cam.dir.x))%360
        arrow=['\u2192','\u2197','\u2191','\u2196','\u2190','\u2199','\u2193','\u2198'][int((angle+22.5)/45)%8]
        if H>1: buf[1][W//2-4]=arrow
        hb=10; hf=int(max(0,cam.health)/cam.max_health*hb)
        _buf_write(buf,2,H-5,"["+('#'*hf)+(' '*(hb-hf))+f"] HP:{cam.health} SH:{cam.shield}",W,H)
        hth=int(player.heat/100*hb); col='!' if player.heat>70 else '|'
        _buf_write(buf,2,H-4,"["+(col*hth)+(' '*(hb-hth))+
                   ("] JAMMED!" if player.overheated else "] EMITTER READY"),W,H)
        biome_label=BIOME_NAMES.get(player.biome,"?") if player.mode!=Player.BOARD else "ENEMY SHIP"
        hint=""
        if player.mode==Player.FOOT:
            nv=player.nearest_vehicle()
            if nv:
                px,py,_=player.pos(); d=math.hypot(px-nv['x'],py-nv['y'])
                if d<8: hint=("  [E] LAUNCH" if nv['kind']=='ship' else "  [E] ENTER VEHICLE")+f" ({d:.1f})"
            if player.dist_terminal()<2.: hint="  [E] USE TERMINAL"
        _buf_write(buf,2,H-3,f"[{biome_label}]{hint}",W,H)
        pu=player.powerups; bar=""
        if pu.get('SPEED_BOOST',0)>0: bar+=f' [>SPD:{pu["SPEED_BOOST"]//62+1}s]'
        if pu.get('SLOW_TIME',0)>0:   bar+=f' [~SLO:{pu["SLOW_TIME"]//62+1}s]'
        if pu.get('RAPID_FIRE',0)>0:  bar+=f' [!RFR:{pu["RAPID_FIRE"]//62+1}s]'
        if bar: _buf_write(buf,2,H-6,'PWR:'+bar,W,H)
        log_count=len(player.log_entries); art_hint=f"  [L] LOG({log_count})" if log_count>0 else ""
        _buf_write(buf,2,H-2,f"WASD move/strafe  arrows move/turn  V jump  SHIFT sprint  SPACE/LMB emitter  E enter  F takeoff  T teleport{art_hint}",W,H)
        if player.land_t>0:
            msg=player.land_word; sx=W//2-len(msg)//2
            for i,c in enumerate(msg):
                bx=sx+i
                if 0<=bx<W and H//2+4<H: buf[H//2+4][bx]=c


class VehicleRenderer:
    """
    Phos City Night Drive renderer.
    Uses cam.render_angle (car heading + camera yaw offset) for all projections,
    so arrow LEFT/RIGHT look-around is reflected in the scene automatically.
    """
    def __init__(self, W, H): self.W=W; self.H=H

    def render(self, player, router):
        cam=player.veh; W,H=self.W,self.H
        # Use render_angle (car angle + cam yaw) for the view direction
        view_angle = cam.render_angle
        half_h  = H//2; horizon = half_h + int(cam.hp_y*H*.2)
        sk      = cam.shake
        sx_off  = (random.randint(-1,1) if sk>.3 else 0)
        sy_off  = (random.randint(-1,1) if sk>.3 else 0)
        buf     = [[' ']*W for _ in range(H)]
        zbuf    = [9999.]*W

        # Sky
        for y in range(0,max(0,horizon)):
            t=y/max(1,horizon); density=.060*(1.-t*.78)
            for x in range(W):
                ab=(view_angle+(x-W/2)*.012)%TAU
                hv=_pch(x,y,int(ab*80))
                if hv<density:
                    buf[y][x]='*' if hv<density*.25 else ('+' if hv<density*.55 else ('\u00b7' if hv<density*.80 else '.'))
            if horizon>1 and y==horizon-1:
                for x in range(W):
                    if buf[y][x]==' ': buf[y][x]='.'

        # Wall DDA cast — use view_angle instead of cam.angle
        for col in range(W):
            cam_x   = 2.*col/W - 1.
            try:    ray_angle = view_angle + math.atan(cam_x*math.tan(cam.fov/2))
            except: ray_angle = view_angle
            rdx=math.cos(ray_angle); rdy=math.sin(ray_angle)
            mx=int(math.floor(cam.x)); my=int(math.floor(cam.y))
            ddx=1e30 if rdx==0 else abs(1./rdx); ddy=1e30 if rdy==0 else abs(1./rdy)
            if rdx<0: step_x=-1; sdx=(cam.x-mx)*ddx
            else:     step_x=+1; sdx=(mx+1-cam.x)*ddx
            if rdy<0: step_y=-1; sdy=(cam.y-my)*ddy
            else:     step_y=+1; sdy=(my+1-cam.y)*ddy
            hit=side=variant=0
            for _ in range(64):
                if sdx<sdy: sdx+=ddx; mx+=step_x; side=0
                else:       sdy+=ddy; my+=step_y; side=1
                v=router.get_cell(mx,my)
                if v>0: hit=1; variant=v; break
            if not hit: zbuf[col]=9999.; continue
            if side==0: dist=sdx-ddx; wall_x=cam.y+dist*rdy
            else:       dist=sdy-ddy; wall_x=cam.x+dist*rdx
            wall_x -= math.floor(wall_x)
            corr=dist*math.cos(ray_angle-view_angle); corr=max(.001,corr)
            zbuf[col]=corr
            lh=max(1,int(H/corr))
            ds=max(0,horizon-lh//2); de=min(H-1,horizon+lh//2)
            fog=min(1.,corr/22.)
            for y in range(ds,de+1):
                vv=(y-(horizon-lh//2))/max(1,lh); vv=min(.999,max(0.,vv))
                glyph,intensity=_pc_glyph(variant,wall_x,vv,mx,my,fog)
                if side==1: intensity*=.78
                if intensity<.06: continue
                if fog>.85 and glyph in ("\u25a3",'\u25a1',"\u2630"): glyph='\u00b7'
                buf[y][col]=glyph

        # Floor cast — use view_angle
        is_city=isinstance(router,PhosCityRouter)
        for y in range(horizon+1,H):
            p=y-horizon; row_dist=(.5*H)/max(1,p)
            if row_dist>30.: continue
            la=view_angle-cam.fov/2; ra=view_angle+cam.fov/2
            ldx=math.cos(la)*row_dist; ldy=math.sin(la)*row_dist
            rdx2=math.cos(ra)*row_dist; rdy2=math.sin(ra)*row_dist
            sx2=(rdx2-ldx)/W; sy2=(rdy2-ldy)/W; fx=cam.x+ldx; fy=cam.y+ldy
            fog_f=min(1.,row_dist/22.)
            for x in range(W):
                cv_=router.get_cell(fx,fy)
                if cv_!=0: fx+=sx2; fy+=sy2; continue
                if is_city:
                    stride=router.BLOCK_STRIDE; sh=router.STREET_HALF
                    rx=int(math.floor(fx))%stride; ry=int(math.floor(fy))%stride
                    u2=fx-math.floor(fx); vv2=fy-math.floor(fy)
                    xs=rx<sh or rx>=stride-sh; ys=ry<sh or ry>=stride-sh
                    ch=' '; inten=max(.05,.32-fog_f*.28)
                    if xs and ys:
                        if(int(u2*6)+int(vv2*6))%2==0:
                            ch='\u2500' if int(vv2*4)%2==0 else ' '; inten=max(.18,.48-fog_f*.4)
                        elif _pch(int(fx*8),int(fy*8))<.05: ch='.'
                    elif xs:
                        if rx==sh-1 and u2>.92 and int(fy*.6)%2==0: ch='|'; inten=max(.40,.85-fog_f*.5)
                        elif rx==stride-sh and u2<.08 and int(fy*.6)%2==0: ch='|'; inten=max(.40,.85-fog_f*.5)
                        if rx==0 and u2<.10: ch='\u2502'; inten=max(.30,.60-fog_f*.4)
                        if rx==stride-1 and u2>.90: ch='\u2502'; inten=max(.30,.60-fog_f*.4)
                        if ch==' ' and _pch(int(fx*7),int(fy*7),'a')<.04: ch='.'
                    elif ys:
                        if ry==sh-1 and vv2>.92 and int(fx*.6)%2==0: ch='-'; inten=max(.40,.85-fog_f*.5)
                        elif ry==stride-sh and vv2<.08 and int(fx*.6)%2==0: ch='-'; inten=max(.40,.85-fog_f*.5)
                        if ry==0 and vv2<.10: ch='\u2500'; inten=max(.30,.60-fog_f*.4)
                        if ry==stride-1 and vv2>.90: ch='\u2500'; inten=max(.30,.60-fog_f*.4)
                        if ch==' ' and _pch(int(fx*7),int(fy*7),'b')<.04: ch='.'
                    if ch!=' ' and buf[y][x]==' ': buf[y][x]=ch
                else:
                    if (x+y)%5==0: buf[y][x]='.'
                fx+=sx2; fy+=sy2

        self._draw_vehicle_sprites(buf,player,zbuf,cam,W,H,horizon,view_angle)
        self._draw_entity_sprites(buf,player,zbuf,cam,W,H,horizon,view_angle)
        player.world_bubble.draw_shards(buf, type('_FC',(),{'pos':type('_P',(),{'x':cam.x,'y':cam.y})(),'dir':type('_D',(),{'x':math.cos(view_angle),'y':math.sin(view_angle)})(),'plane':type('_Pl',(),{'x':-math.sin(view_angle)*.66,'y':math.cos(view_angle)*.66})()})(), zbuf, W, H)

        if sk>.3 and (sx_off or sy_off):
            nb=[[' ']*W for _ in range(H)]
            for y in range(H):
                for x in range(W):
                    nx2=x+sx_off; ny2=y+sy_off
                    if 0<=nx2<W and 0<=ny2<H: nb[ny2][nx2]=buf[y][x]
            buf=nb

        self._draw_minimap(buf,player,router,W,H)

        biome=BIOME_NAMES.get(player.biome,'?')
        yaw_deg = int(math.degrees(cam.cam_yaw))
        yaw_str = f"  CAM:{yaw_deg:+d}\u00b0" if abs(yaw_deg) > 2 else ""
        # Crosshair at screen centre
        cx2=W//2; cy2=H//2
        buf[cy2][cx2]   = 'X' if cam.overheated else '+'
        if cx2>1: buf[cy2][cx2-1]='-'; buf[cy2][cx2+1]='-'
        if cy2>1: buf[cy2-1][cx2]='|'; buf[cy2+1][cx2]='|'
        # HP / shield bar
        hb=10
        hf=int(max(0,cam.health)/cam.max_health*hb)
        sf2=int(max(0,cam.shield)/cam.max_shield*hb)
        _buf_write(buf,2,H-5,"["+('#'*hf)+(' '*(hb-hf))+f"] HP:{int(cam.health)} SH:{int(cam.shield)}",W,H)
        # Turret heat bar
        hth=int(cam.heat/100*hb); col='!' if cam.heat>70 else '|'
        _buf_write(buf,2,H-4,"["+(col*hth)+(' '*(hb-hth))+("] TURRET JAMMED!" if cam.overheated else "] TURRET READY"),W,H)
        _buf_write(buf,2,H-3,f"[{biome}] GEAR:{cam.gear} RPM:{int(cam.rpm)} SPD:{abs(cam.speed)*2.27:.0f}mph{yaw_str}",W,H)
        _buf_write(buf,2,H-2,"W/S throttle  A/D steer  \u25c4\u25ba look  SHIFT boost  SPACE fire turret  E exit  F takeoff",W,H)
        return "\n".join("".join(row) for row in buf)

    def _draw_vehicle_sprites(self, buf, player, zbuf, cam, W, H, horizon, view_angle):
        for v in player.vehicles:
            if abs(v['x']-cam.x)<.5 and abs(v['y']-cam.y)<.5: continue
            dx,dy=v['x']-cam.x, v['y']-cam.y
            ca,sa=math.cos(-view_angle),math.sin(-view_angle)
            lx=dx*ca-dy*sa; lz=dx*sa+dy*ca
            if lz<.5: continue
            scr_x=int(W/2+(lx/lz)*(W/2)*.7); hr=max(1,int(H/(lz*.5)))
            is_ship=v['kind']=='ship'; height=hr if is_ship else hr//2
            cy2=horizon+height//2; g='S' if is_ship else 'V'
            for py in range(max(0,cy2-height),min(H,cy2)):
                if 0<=scr_x<W and zbuf[scr_x]>lz: buf[py][scr_x]=g

    def _draw_entity_sprites(self, buf, player, zbuf, cam, W, H, horizon, view_angle):
        """Project foot-mode entities (enemies/NPCs) into vehicle view."""
        ca=math.cos(-view_angle); sa=math.sin(-view_angle)
        live=[e for e in player.entities if e.alive() or e.dead_timer>0]
        for ent in sorted(live, key=lambda e:(e.x-cam.x)**2+(e.y-cam.y)**2, reverse=True):
            dx=ent.x-cam.x; dy=ent.y-cam.y
            lx=dx*ca-dy*sa; lz=dx*sa+dy*ca
            if lz<.5: continue
            scr_x=int(W/2+(lx/lz)*(W/2)*.7)
            hr=max(1,int(H/(lz*.6))); height=hr//2
            cy2=horizon+height//2
            g=ent.glyph()
            rows=_sprite_rows('%' if g=='%' else ent.char, ent.flash>0, eid=ent.eid)
            rs=max(1,height)
            for py in range(max(0,cy2-height),min(H,cy2)):
                if 0<=scr_x<W and zbuf[scr_x]>lz:
                    ri=min(int((py-(cy2-height))/rs*len(rows)),len(rows)-1)
                    ci=scr_x%max(1,len(rows[ri]))
                    sc=rows[ri][ci]; buf[py][scr_x]=sc if sc.strip() else g
            if ent.msg_t>0 and ent.msg_text:
                ml=len(ent.msg_text); my=max(0,cy2-height-2)
                mx=max(0,min(scr_x-ml//2,W-ml))
                for i,c in enumerate(ent.msg_text):
                    if mx+i<W and my<H: buf[my][mx+i]=c

    def _draw_minimap(self, buf, player, router, W, H):
        cam=player.veh; mm_w,mm_h=14,7; ox=int(cam.x)-mm_w//2; oy=int(cam.y)-mm_h//2
        for my in range(mm_h):
            for mx in range(mm_w):
                wx,wy=ox+mx,oy+my
                try:    c=router.get_cell(wx,wy)
                except: c=0
                bx,by=W-mm_w-1+mx,2+my
                if 0<=bx<W and 0<=by<H: buf[by][bx]='#' if c>0 else '.'
        buf[2+mm_h//2][W-mm_w//2-1]='@'
        for v in player.vehicles:
            mx2,my2=int(v['x'])-ox,int(v['y'])-oy
            bx,by=W-mm_w-1+mx2,2+my2
            if 0<=bx<W and 0<=by<H:
                g='S' if v['kind']=='ship' else 'V'
                buf[by][bx]=g
                if v['kind']=='ship' and 0<=by-1<H: buf[by-1][bx]='S'


class SpaceRenderer:
    def __init__(self): self.frame=0; self.last_sfx=0; self.shake=0.

    def _project(self, cam, world_pos, w, h, shake_x=0, shake_y=0):
        rel=vsub(world_pos,cam.pos)
        lx,ly,lz=vdot(rel,cam.right),vdot(rel,cam.up),vdot(rel,cam.fwd)
        if lz<10: return None
        f=750/lz; return (w/2+lx*f+shake_x, h/2-ly*f+shake_y, f, lz)

    def _project_back(self, cam, world_pos, w, h, shake_x=0, shake_y=0):
        rel=vsub(world_pos,cam.pos)
        lx,ly,lz=vdot(rel,cam.right),vdot(rel,cam.up),vdot(rel,cam.fwd)
        if lz>-10: return None
        f=750/abs(lz); return (w/2-lx*f*.6+shake_x, h/2+ly*f*.6+shake_y, f*.6, abs(lz))

    def render(self, canvas, player, starfield, planet_field, comets, audio):
        cam=player.craft; canvas.delete("all")
        w=canvas.winfo_width() or SPACE_W; h=canvas.winfo_height() or SPACE_H
        self.shake=min(3.,self.shake+.3) if (cam.thruster_on and cam.vel>10) else self.shake*.85
        sdx=random.uniform(-self.shake,self.shake); sdy=random.uniform(-self.shake,self.shake)
        if cam.vel>30:
            intensity=min(1.,(cam.vel-30)/120)
            for _ in range(int(intensity*20)):
                ang=random.uniform(0,TAU); r0=random.uniform(0,min(w,h)*.05); r1=r0+random.uniform(20,80)*intensity
                canvas.create_line(w/2+math.cos(ang)*r0,h/2+math.sin(ang)*r0,
                                   w/2+math.cos(ang)*r1,h/2+math.sin(ang)*r1,
                                   fill="#ffaa00" if intensity>.5 else "#8888ff",width=1)
        stars=starfield.near(cam.pos); back_count=0
        for sx,sy,sz,glyph,color,fsize in stars:
            res=self._project(cam,[sx,sy,sz],w,h,sdx,sdy)
            if res:
                px,py,factor,_=res
                if 0<=px<=w and 0<=py<=h:
                    fs=max(7,min(fsize,int(factor*4)))
                    g='.' if factor<.05 else (random.choice(['.', '\u00b7',"'", '`']) if factor<.2 else glyph)
                    canvas.create_text(px,py,text=g,fill=color,font=("Courier",fs))
            else:
                r2=self._project_back(cam,[sx,sy,sz],w,h,sdx,sdy)
                if r2 and back_count<80:
                    px,py,_,_=r2
                    if 0<=px<=w and 0<=py<=h: canvas.create_text(px,py,text='\u00b7',fill=color,font=("Courier",8)); back_count+=1
        planet_field.update()
        for p in planet_field.planets:
            res=self._project(cam,p["pos"],w,h,sdx,sdy)
            if not res: continue
            px,py,factor,dist=res; size=max(2,int(p["size"]*factor*.08))
            if size>1 and 0<=px<=w and 0<=py<=h:
                lines=[p["char"]*(size-abs(r)*2) for r in range(-size//4,size//4+1) if size-abs(r)*2>0]
                canvas.create_text(px,py,fill=p["color"],font=("Courier",max(8,size//2),"bold"),
                                   text="\n".join(lines) if len(lines)>1 else p["char"]*size)
                if dist<800:
                    canvas.create_text(px,py+size+12,text=f"[{BIOME_NAMES[p['biome']]}]",
                                       fill=p["color"],font=("Courier",8))
        for e in player.space_enemies:
            if not e.alive(): continue
            res=self._project(cam,[e.pos.x,e.pos.y,e.pos.z],w,h,sdx,sdy)
            if not res: continue
            px,py,factor,dist=res
            if 0<=px<=w and 0<=py<=h:
                fs=max(8,int(factor*18))
                canvas.create_text(px,py,text="\u25c7",fill="#ff8888",font=("Courier",fs,"bold"))
                if dist<400: canvas.create_text(px,py+fs+4,text=f"HP:{e.hp}",fill=RED,font=("Courier",8))
        for comet in comets:
            res=self._project(cam,comet.pos,w,h,sdx,sdy)
            if res:
                px,py,factor,_=res
                if 0<=px<=w and 0<=py<=h:
                    canvas.create_text(px,py,text="@",fill=WHITE,font=("Courier",max(9,int(factor*12)),"bold"))
                    if factor>.3 and self.frame-self.last_sfx>60: audio.play('whoosh'); self.last_sfx=self.frame
            for i,tp in enumerate(comet.tail):
                rt=self._project(cam,tp,w,h,sdx,sdy)
                if not rt: continue
                px,py,factor,_=rt
                if 0<=px<=w and 0<=py<=h:
                    fade=1.-i/max(1,len(comet.tail))
                    tc=f"#{int(0xaa+(0xff-0xaa)*fade):02x}{min(255,int(0x88+(0xff-0x88)*fade*.5)):02x}{min(255,int(0xff*fade*.7)):02x}"
                    canvas.create_text(px,py,text=COMET_CHARS[min(i,len(COMET_CHARS)-1)],fill=tc,font=("Courier",max(7,int(factor*10))))
        self._draw_space_hud(canvas,cam,player,planet_field,audio,w,h)
        self.frame+=1

    def _draw_space_hud(self, canvas, cam, player, planet_field, audio, w, h):
        cx,cy=w/2,h/2; col=GLOW if cam.thruster_on else AMBER
        canvas.create_text(cx,cy,  text="\u2500\u2500[\u2726]\u2500\u2500",fill=col,font=("Courier",14))
        canvas.create_text(cx,cy-18,text="|",fill=col,font=("Courier",12))
        canvas.create_text(cx,cy+18,text="|",fill=col,font=("Courier",12))
        vp=min(1.,abs(cam.vel)/320.); bw=200; fi=int(vp*bw/6)
        canvas.create_text(cx,h-45,text="["+"\u2588"*fi+"\u2591"*(bw//6-fi)+"]",fill=AMBER,font=("Courier",9))
        ts="\u25b6 THRUST ON " if cam.thruster_on else "  THRUST OFF"
        bs=" \u26a1BOOST" if cam.boost_on else ""
        ms="\u266b" if audio.music_on else "\u266a"; sfx_s="~" if audio.sfx_on else "x"
        canvas.create_text(cx,h-25,fill=GLOW,font=("Courier",11),
                           text=f"{ts}{bs}  |  V:{int(cam.vel):4d}  |  HP:{cam.health} SH:{cam.shield}  |  {ms} {sfx_s}")
        canvas.create_text(10,12,anchor="w",fill=DIM,font=("Courier",9),
                           text=f"POS: {int(cam.pos[0]):+08.0f} {int(cam.pos[1]):+08.0f} {int(cam.pos[2]):+08.0f}")
        ccx,ccy,cr=w-70,70,35
        canvas.create_oval(ccx-cr,ccy-cr,ccx+cr,ccy+cr,outline="#333333",width=1)
        yaw=math.atan2(cam.fwd[0],cam.fwd[2]); pitch=math.asin(max(-1,min(1,cam.fwd[1])))
        canvas.create_line(ccx,ccy,ccx+math.sin(yaw)*cr*.8,ccy-math.sin(pitch)*cr*.8,fill=AMBER,width=2)
        canvas.create_text(ccx,ccy+cr+10,text="HDG",fill="#444444",font=("Courier",8))
        near=planet_field.nearest(cam.pos,600)
        if near:
            d=math.sqrt(sum((near["pos"][i]-cam.pos[i])**2 for i in range(3)))
            canvas.create_text(cx,h-70,fill="#88ffaa",font=("Courier",10,"bold"),
                               text=f"PLANET in range \u2014 [F] LAND ({BIOME_NAMES[near['biome']]}, d={int(d)})")
        be=player.nearest_space_enemy(300)
        if be:
            d=(be.pos-player.craft.pos_v3()).length()
            canvas.create_text(cx,h-90,fill="#ff88aa",font=("Courier",10,"bold"),
                               text=f"ENEMY SHIP in range \u2014 [G] BOARD (d={int(d)})")


def _render_log(player, W, H):
    entries=player.log_entries; scroll=player.log_scroll
    lines=[""]
    lines.append("  \u2550"*((W//2)-2)+"  ")
    lines.append(f"   A R T I F A C T   L O G   ({len(entries)} entries)  [L] to close  UP/DOWN to scroll")
    lines.append("  \u2550"*((W//2)-2)+"  ")
    lines.append("")
    visible_start=max(0,scroll)
    visible_entries=entries[visible_start:]
    row=5
    for entry in visible_entries:
        for subline in entry.split('\n'):
            if row>=H-3: break
            lines.append("    "+subline)
            row+=1
        lines.append("")
        row+=1
        if row>=H-3: break
    while len(lines)<H: lines.append("")
    lines.append("  \u2550"*((W//2)-2)+"  ")
    return "\n".join(lines)


# ================================================================ GAME ENGINE

class Game:
    def __init__(self, root, combat=False):
        self.root    = root; self.combat=combat
        root.title("OMNI VOID ENGINE"); root.configure(bg=BG); root.geometry(f"{SPACE_W}x{SPACE_H}")
        self.canvas  = tk.Canvas(root,bg=BG,highlightthickness=0,width=SPACE_W,height=SPACE_H)
        self.label   = tk.Label(root,bg=BG,fg=FG,font=("Courier",10),justify="left",anchor="nw")
        self.canvas.pack(fill=tk.BOTH,expand=True)
        self.audio   = Audio()
        self.player  = Player()
        self.narrator= Narrator()
        self.starfield    = StarField()
        self.planet_field = PlanetField()
        self.comets       = []
        self.cv_ren   = CVRenderer(GRID_W,GRID_H)
        self.veh_ren  = VehicleRenderer(GRID_W,GRID_H)
        self.space_ren= SpaceRenderer()
        self.keys     = set(); self.frame=0; self.msg=""; self.msg_t=0.
        self._lmb     = False
        self._eng_cd  = 0
        root.bind("<KeyPress>",   self._on_key_down)
        root.bind("<KeyRelease>", self._on_key_up)
        root.bind("<Button-1>",         lambda e: setattr(self,'_lmb',True))
        root.bind("<ButtonRelease-1>",  lambda e: setattr(self,'_lmb',False))
        root.protocol("WM_DELETE_WINDOW", self._quit)
        self.audio.music.set_mode('space')
        self.audio.music.start()
        root.after(1600, lambda: self.narrator.say("Omni Void Engine. Deep space. Navigate to a planet."))
        self._loop()

    def _show_msg(self, text, duration=2.5):
        self.msg=text; self.msg_t=duration

    def _on_key_down(self, event):
        k=event.keysym.lower(); self.keys.add(k); P=self.player
        if k=="escape": self._quit(); return
        if k=="space":
            if P.mode==P.SPACE:
                P.craft.thruster_on = not P.craft.thruster_on
                self._show_msg(f"THRUST {'ON' if P.craft.thruster_on else 'OFF'}")
        elif k=="v" and P.mode in (P.FOOT,P.BOARD):
            P.cv.jump(); self.audio.play('jump')
        elif k=="b" and P.mode==P.SPACE:
            P.craft.boost_on=True; self.audio.play('boost'); self._show_msg("BOOST")
        elif k=="e": self._interact()
        elif k=="f": self._f_key()
        elif k=="g": self._board()
        elif k=="x" and P.mode==P.BOARD: self._disembark()
        elif k=="t": self._teleport()
        elif k=="l" and P.mode in (P.FOOT,P.BOARD,P.VEHICLE):
            P.log_open=not P.log_open
            if P.log_open: P.log_scroll=0
        elif k=="prior" and P.log_open: P.log_scroll=max(0,P.log_scroll-1)
        elif k=="next"  and P.log_open: P.log_scroll+=1
        elif k=="m": self._show_msg(f"MUSIC {'ON' if self.audio.toggle_music() else 'OFF'}")
        elif k=="r": self._show_msg(f"SFX {'ON' if self.audio.toggle_sfx() else 'OFF'}")

    def _on_key_up(self, event):
        k=event.keysym.lower(); self.keys.discard(k)
        if k=="b" and self.player.mode==Player.SPACE: self.player.craft.boost_on=False

    def _interact(self):
        P=self.player
        if P.mode==P.FOOT:
            if P.dist_terminal()<2. and P.use_terminal():
                self._show_msg(">>> TERMINAL: HP/SH restored + heat cooled"); self.audio.play('pickup'); return
            v=P.nearest_vehicle()
            if v:
                px,py,_=P.pos()
                if math.hypot(px-v['x'],py-v['y'])<5.:
                    P.enter_vehicle(v['id'])
                    self._show_msg(f">>> ENTER {'SHIP' if v['kind']=='ship' else 'VEHICLE'} #{v['id']}  [E to exit]")
                    self.audio.play('pickup')
        elif P.mode==P.VEHICLE:
            P.exit_vehicle(); self._show_msg(">>> EXIT VEHICLE")
        elif P.mode==P.BOARD and P.dist_terminal()<2.:
            self._show_msg(">>> BRIDGE CAPTURED \u2014 [X] to disembark")

    def _f_key(self):
        P=self.player
        if P.mode==P.SPACE:
            near=self.planet_field.nearest(P.craft.pos,600)
            if near:
                P.land(near); self._show_msg(f">>> LANDED on {BIOME_NAMES[near['biome']]}"); self.audio.play('pickup')
                self.narrator.say(f"Landed. {BIOME_NAMES[near['biome']]}.")
        elif P.mode in (P.FOOT,P.VEHICLE):
            if P.mode==P.VEHICLE: P.exit_vehicle()
            P.takeoff(); self._show_msg(">>> TAKEOFF"); self.audio.play('thruster'); self.narrator.say("Launching.")

    def _board(self):
        P=self.player
        if P.mode!=P.SPACE: return
        target=P.nearest_space_enemy(300)
        if target:
            P.board_ship(target); self._show_msg(f">>> BOARDING SHIP #{target.eid}"); self.audio.play('pickup')
            self.narrator.say("Boarding enemy vessel.")

    def _disembark(self):
        self.player.disembark(); self._show_msg(">>> DISEMBARKED"); self.audio.play('pickup')
        self.narrator.say("Disembarked.")

    def _teleport(self):
        P=self.player
        if P.mode in (P.FOOT,P.BOARD):
            if P.mode==P.BOARD:
                P.disembark()
                self._show_msg(">>> DISEMBARKED — use F to land again for teleport")
                self.audio.play('pickup'); return
            if P.teleport_to_ship():
                self._show_msg(">>> TELEPORTING TO SPACESHIP..."); self.audio.play('pickup')
            else:
                self._show_msg(">>> NO SHIP FOUND ON THIS PLANET")
        elif P.mode==P.VEHICLE:
            P.exit_vehicle()
            if P.teleport_to_ship():
                self._show_msg(">>> TELEPORTING TO SPACESHIP..."); self.audio.play('pickup')
            else:
                self._show_msg(">>> NO SHIP FOUND ON THIS PLANET")

    def _update(self, dt):
        P=self.player; m=P.mode
        if m in (P.FOOT,P.BOARD):
            if not P.log_open:
                self._update_foot(dt)
                self._update_emitter()
                speed_mult=0.25 if P.powerups.get('SLOW_TIME',0)>0 else 1.
                for e in P.entities:
                    e.speed=ENEMY_SPD.get(e.char,.02)*speed_mult; e.update(P.cv,P.router)
                self._check_entity_events()
                if self.combat and P.cv.health<=0:
                    self._respawn_foot()
                P.particles.update(); P.pu_spawner.update()
                if self.frame%40==0:
                    alive=sum(1 for e in P.entities if e.alive())
                    target=max(4, len(P.entities)//3)
                    if alive<target:
                        px2,py2,_=P.pos()
                        sx,sy=P._open_spawn(P.router, px2+random.uniform(-18,18),
                                             py2+random.uniform(-18,18))
                        P.entities.append(CVEntity(sx,sy,random.choice(ENEMY_CHARS)))
                P.entities=[e for e in P.entities if not (e.state=='DEAD' and e.dead_timer<=0)]
                P.tracers=[t for t in P.tracers if t[2]>0]
                for t in P.tracers: t[2]-=2
                for k in P.powerups:
                    if P.powerups[k]>0: P.powerups[k]-=1
                if P.land_t>0: P.land_t-=1
                px,py,_=P.pos()
                entry=P.check_artifacts(px,py)
                if entry:
                    self._show_msg(">>> ARTIFACT FOUND \u2014 entry added to log [L]")
                    self.audio.play('artifact')
                # World bubble tick — proximity spawns + log shard pickups
                shard=P.world_bubble.tick(P)
                if shard:
                    self._show_msg(">>> LOG SHARD RECOVERED \u2014 [L] to read")
                    self.audio.play('artifact')
            self.audio.music.set_mode(BIOME_NAMES.get(P.biome,"OPEN WILDS") if m==P.FOOT else "ENEMY SHIP")
        elif m==P.VEHICLE:
            self._update_vehicle(dt)
            self._update_vehicle_emitter()
            # Keep entities alive and attacking in vehicle mode
            speed_mult=0.25 if P.powerups.get('SLOW_TIME',0)>0 else 1.
            for e in P.entities:
                e.speed=ENEMY_SPD.get(e.char,.02)*speed_mult
                # Use a fake CVCamera-like object so entities can track vehicle pos
                class _VehCam:
                    pass
                vc=_VehCam(); vc.pos=V2(P.veh.x,P.veh.y); vc.health=P.veh.health
                e.update(vc,P.router)
                P.veh.health=vc.health  # propagate any damage back
            if self.combat and P.veh.health<=0:
                self._death_to_space()
            P.entities=[e for e in P.entities if not (e.state=='DEAD' and e.dead_timer<=0)]
            if self.frame%40==0:
                alive=sum(1 for e in P.entities if e.alive())
                target=max(4,len(P.entities)//3)
                if alive<target:
                    px2,py2,_=P.pos()
                    sx,sy=P._open_spawn(P.router,px2+random.uniform(-18,18),
                                         py2+random.uniform(-18,18))
                    P.entities.append(CVEntity(sx,sy,random.choice(ENEMY_CHARS)))
            P.world_bubble.tick(P)
            self.audio.music.set_mode(BIOME_NAMES.get(P.biome,"OPEN WILDS"))
        elif m==P.SPACE:
            for e in P.space_enemies: e.update(P.craft.pos_v3(),dt)
            self._update_space(dt); self._update_comets()
            if self.frame%30==0: P.craft.reortho()
            if P.craft.thruster_on and self.frame%25==0: self.audio.play('thruster')
            self.audio.music.set_mode('space')
        self.msg_t=max(0.,self.msg_t-dt)
        # ---- Auto-regen health + shield all modes ----
        P=self.player
        if m in (P.FOOT, P.BOARD):
            c=P.cv
            if c.health<c.max_health: c.health=min(c.max_health, c.health+0.04)
            if c.shield<c.max_shield: c.shield=min(c.max_shield, c.shield+0.09)
        elif m==P.VEHICLE:
            c=P.veh
            if c.health<c.max_health: c.health=min(c.max_health, c.health+0.04)
            if c.shield<c.max_shield: c.shield=min(c.max_shield, c.shield+0.09)
        elif m==P.SPACE:
            c=P.craft
            if c.health<c.max_health: c.health=min(c.max_health, c.health+0.06)
            if c.shield<c.max_shield: c.shield=min(c.max_shield, c.shield+0.12)

    def _update_foot(self, dt):
        P=self.player; cam=P.cv; router=P.router
        if router is None: return
        sprint = 'shift_l' in self.keys or 'shift_r' in self.keys or 'shift' in self.keys
        pu     = P.powerups
        base_speed = 0.18 if sprint else 0.12
        speed      = base_speed * (2. if pu.get('SPEED_BOOST',0)>0 else 1.)
        if pu.get('SLOW_TIME',0)>0: speed*=.4
        moving=False
        if 'w' in self.keys:
            nx=cam.pos.x+cam.dir.x*speed; ny=cam.pos.y+cam.dir.y*speed
            if router.is_open(nx,cam.pos.y): cam.pos.x=nx
            if router.is_open(cam.pos.x,ny): cam.pos.y=ny
            moving=True
        if 's' in self.keys:
            nx=cam.pos.x-cam.dir.x*speed; ny=cam.pos.y-cam.dir.y*speed
            if router.is_open(nx,cam.pos.y): cam.pos.x=nx
            if router.is_open(cam.pos.x,ny): cam.pos.y=ny
            moving=True
        if 'a' in self.keys:
            nx=cam.pos.x-cam.dir.y*speed; ny=cam.pos.y+cam.dir.x*speed
            if router.is_open(nx,cam.pos.y): cam.pos.x=nx
            if router.is_open(cam.pos.x,ny): cam.pos.y=ny
            moving=True
        if 'd' in self.keys:
            nx=cam.pos.x+cam.dir.y*speed; ny=cam.pos.y-cam.dir.x*speed
            if router.is_open(nx,cam.pos.y): cam.pos.x=nx
            if router.is_open(cam.pos.x,ny): cam.pos.y=ny
            moving=True
        rot=0.062
        # LEFT/RIGHT arrows: turn camera in foot/board mode
        if 'left'  in self.keys: cam.rotate( -rot)
        if 'right' in self.keys: cam.rotate(rot)
        # UP/DOWN arrows: move forward/backward
        if 'up' in self.keys:
            nx=cam.pos.x+cam.dir.x*speed; ny=cam.pos.y+cam.dir.y*speed
            if router.is_open(nx,cam.pos.y): cam.pos.x=nx
            if router.is_open(cam.pos.x,ny): cam.pos.y=ny
            moving=True
        if 'down' in self.keys:
            nx=cam.pos.x-cam.dir.x*speed; ny=cam.pos.y-cam.dir.y*speed
            if router.is_open(nx,cam.pos.y): cam.pos.x=nx
            if router.is_open(cam.pos.x,ny): cam.pos.y=ny
            moving=True
        if 'prior' in self.keys: cam.pitch=min(14, cam.pitch+3)
        if 'next'  in self.keys: cam.pitch=max(-14,cam.pitch-3)
        if not ('prior' in self.keys or 'next' in self.keys): cam.pitch*=.88
        if not cam.jumping: cam.step_bob(moving)
        else:               cam.bob*=.85
        landed=cam.update_jump()
        if landed:
            cam.land_shake(6.,14); self.audio.play('land')
            P.land_word=random.choice(LAND_WORDS); P.land_t=28; P._v_prev=True
        if moving and not cam.jumping:
            P._step_cd-=1
            if P._step_cd<=0: self.audio.play('step'); P._step_cd=22
        picked=P.pu_spawner.check(cam.pos.x,cam.pos.y)
        if picked:
            P.powerups[picked]=PU_DUR; P.land_word=PU_LABELS[picked]; P.land_t=55; self.audio.play('pickup')

    def _update_emitter(self):
        P=self.player; cam=P.cv
        if P.mode not in (P.FOOT,P.BOARD): return
        firing = ('space' in self.keys or self._lmb)
        if firing and not P.overheated:
            rate = .35 if P.powerups.get('RAPID_FIRE',0)>0 else 1.
            P.heat=min(100, P.heat+3.8*rate)
            if P.heat>=100:
                P.overheated=True; self.audio.play('overheat'); self._show_msg("EMITTER JAMMED \u2014 cool down")
            else:
                P.tracers.append([GRID_W//2,   GRID_H//2,   14])
                P.tracers.append([GRID_W//2+2, GRID_H//2+1, 10])
                P.tracers.append([GRID_W//2-2, GRID_H//2-1, 10])
                self._fire_emitter(); self.audio.play('gun')
        else:
            P.heat=max(0., P.heat-2.2)
            if P.heat<=0 and P.overheated: P.overheated=False; self._show_msg("EMITTER READY")

    def _fire_emitter(self):
        cam=self.player.cv; best=None; best_dist=999
        for e in self.player.entities:
            if not e.alive() or e.pacified: continue
            dx=e.x-cam.pos.x; dy=e.y-cam.pos.y; d=math.hypot(dx,dy)
            if d<.5 or d>20: continue
            dot=cam.dir.x*(dx/d) + cam.dir.y*(dy/d)
            if dot>.96 and d<best_dist: best=e; best_dist=d
        if best:
            best.hit(1)
            inv=cam.plane.x*cam.dir.y - cam.dir.x*cam.plane.y + 1e-9; iD=1./inv
            dx=best.x-cam.pos.x; dy=best.y-cam.pos.y
            tY=iD*(-cam.plane.y*dx+cam.plane.x*dy)
            if tY>0:
                tX=iD*(cam.dir.y*dx-cam.dir.x*dy)
                sx=int(GRID_W/2*(1+tX/tY)); sy=GRID_H//2
                self.player.particles.emit(sx,sy,'spark',5)
                if best.confusion>0: self.player.particles.emit(sx,sy,'smoke',4)

    def _update_vehicle_emitter(self):
        """Turret emitter for vehicle mode — SPACE fires, same heat/overheat as foot."""
        P=self.player; cam=P.veh
        firing=('space' in self.keys or self._lmb)
        if firing and not cam.overheated:
            cam.heat=min(100, cam.heat+3.0)
            if cam.heat>=100:
                cam.overheated=True; self.audio.play('overheat')
                self._show_msg("TURRET JAMMED \u2014 cool down")
            else:
                self._fire_vehicle_emitter(); self.audio.play('gun')
        else:
            cam.heat=max(0., cam.heat-1.8)
            if cam.heat<=0 and cam.overheated:
                cam.overheated=False; self._show_msg("TURRET READY")

    def _fire_vehicle_emitter(self):
        """Fire from vehicle — aims along render_angle (car heading + cam yaw)."""
        P=self.player; veh=P.veh
        angle=veh.render_angle
        fwd_x=math.cos(angle); fwd_y=math.sin(angle)
        best=None; best_dist=999
        for e in P.entities:
            if not e.alive() or e.pacified: continue
            dx=e.x-veh.x; dy=e.y-veh.y; d=math.hypot(dx,dy)
            if d<.5 or d>28: continue
            dot=fwd_x*(dx/d)+fwd_y*(dy/d)
            if dot>.94 and d<best_dist: best=e; best_dist=d
        if best:
            best.hit(1)
            P.particles.emit(GRID_W//2, GRID_H//2, 'spark', 5)
            if best.confusion>0: P.particles.emit(GRID_W//2, GRID_H//2, 'smoke', 4)

    def _check_entity_events(self):
        P=self.player
        if any(e.newly_pacified for e in P.entities):
            self._show_msg("STILLNESS ACHIEVED \u2014 Peace and Bliss")
            self.audio.play('still'); self.narrator.say("Stillness achieved. Peace and bliss.")
        for e in P.entities: e.newly_pacified=False
        if self.combat:
            for e in P.entities:
                if (e.alive() and not e.pacified and e.state!='CONFUSED'
                        and e.attack_cd<9999
                        and math.hypot(e.x-P.cv.pos.x,e.y-P.cv.pos.y)<1.2):
                    if P.cv.take_damage(e.dmg//4):
                        self._respawn_foot()

    def _respawn_foot(self):
        P=self.player
        px,py,_=P.pos()
        best_t=None; best_d=1e9
        for t in P.terminals:
            d=math.hypot(px-t['x'],py-t['y'])
            if d<best_d: best_d=d; best_t=t
        if best_t and P.router:
            ox,oy = P._open_spawn(P.router, best_t['x'], best_t['y'])
        else:
            ox,oy = P._open_spawn(P.router)
        P.cv.pos=V2(ox,oy); P.cv.health=P.cv.max_health; P.cv.shield=P.cv.max_shield
        P.heat=0.; self._show_msg(">>> DOWN \u2014 RESPAWNING AT CHECKPOINT"); self.audio.play('death')

    def _update_vehicle(self, dt):
        P=self.player; throttle=brake=steer=0.; boost=False
        # W/S or UP/DOWN = throttle/brake
        if 'w' in self.keys or 'up'    in self.keys: throttle=1.
        if 's' in self.keys or 'down'  in self.keys: brake=1.
        # A/D = steer
        if 'a' in self.keys: steer=-1.
        if 'd' in self.keys: steer= 1.
        # arrow LEFT/RIGHT = camera yaw (look left/look right) — NOT steer
        yaw_left  = 'left'  in self.keys
        yaw_right = 'right' in self.keys
        if 'shift_l' in self.keys or 'shift_r' in self.keys or 'shift' in self.keys: boost=True
        router=P.veh_router if P.veh_router else P.router
        prev_speed=P.veh.speed
        P.veh.update(dt, throttle, brake, steer, boost, yaw_left, yaw_right, router)
        spd=P.veh.speed
        # Vehicle SFX — now uses richer engine_idle on near-stop
        if self._eng_cd>0: self._eng_cd-=1
        else:
            if   spd>prev_speed+.5 and spd>.3:  self.audio.play('accel');      self._eng_cd=25
            elif spd<prev_speed-.8 and prev_speed>2.: self.audio.play('brake'); self._eng_cd=20
            elif spd<-.3 and prev_speed>-.3:    self.audio.play('reverse');     self._eng_cd=30
            elif self.frame%20==0:
                rpm_norm=(P.veh.rpm-P.veh.RPM_IDLE)/(P.veh.RPM_REDLINE-P.veh.RPM_IDLE)
                if rpm_norm < 0.04:
                    self.audio.play('engine_idle')  # warm idle rumble at standstill
                    self._eng_cd=22
                elif rpm_norm < 0.35:
                    self.audio.play('engine_lo');   self._eng_cd=18
                elif rpm_norm < 0.70:
                    self.audio.play('engine_md');   self._eng_cd=18
                else:
                    self.audio.play('engine_hi');   self._eng_cd=16

    def _update_space(self, dt):
        P=self.player; cam=P.craft; cam.update(dt,self.keys)
        if self.combat:
            cp=cam.pos_v3()
            for e in P.space_enemies:
                if e.alive() and e.fire_cd<=0 and (cp-e.pos).length()<200:
                    if cam.take_damage(8):
                        P.craft.pos=[0.,0.,0.]; P.craft.health=P.craft.max_health; P.craft.shield=P.craft.max_shield
                        self._show_msg(">>> SHIP DOWN \u2014 RESPAWNING"); self.audio.play('death'); return

    def _update_comets(self):
        P=self.player
        if len(self.comets)<COMET_POOL and random.random()<.04:
            self.comets.append(Comet(P.craft.pos,P.craft.fwd))
        for c in self.comets: c.update()
        self.comets=[c for c in self.comets if c.alive()]

    def _draw(self):
        P=self.player; m=P.mode

        if m==P.SPACE:
            if self.label.winfo_ismapped(): self.label.pack_forget(); self.canvas.pack(fill=tk.BOTH,expand=True)
            self.space_ren.render(self.canvas,P,self.starfield,self.planet_field,self.comets,self.audio)
            if self.msg_t>0:
                w=self.canvas.winfo_width() or SPACE_W
                self.canvas.create_text(w/2,55,text=self.msg,fill=WHITE,font=("Courier",13,"bold"))
            return

        if self.canvas.winfo_ismapped(): self.canvas.pack_forget(); self.label.pack(fill=tk.BOTH,expand=True)
        if P.router is None: return

        if P.log_open:
            self.label.config(text=_render_log(P,GRID_W,GRID_H))
            return

        if m in (P.FOOT,P.BOARD):
            text=self.cv_ren.render(P,P.router)
        else:
            vr=P.veh_router if P.veh_router else P.router
            text=self.veh_ren.render(P,vr)

        if self.msg_t>0:
            lines=text.split('\n')
            if len(lines)>3:
                mi=len(lines)//4; ml=len(self.msg)
                row=list(lines[mi]); sx=max(0,GRID_W//2-ml//2)
                for i,c in enumerate(self.msg):
                    if sx+i<GRID_W: row[sx+i]=c
                lines[mi]=''.join(row); text='\n'.join(lines)
        self.label.config(text=text)

    def _loop(self):
        try:
            self._update(1./FPS); self._draw()
        except tk.TclError: return
        self.frame+=1
        try: self.root.after(1000//FPS, self._loop)
        except tk.TclError: pass

    def _quit(self):
        try: self.audio.stop()
        except Exception: pass
        try: self.narrator.stop()
        except Exception: pass
        self.root.destroy()


# ================================================================ LAUNCHER

class Launcher:
    def __init__(self, root):
        self.root=root; root.title("OMNI VOID ENGINE \u2014 Launcher")
        root.geometry("760x620"); root.configure(bg=BG)
        tk.Label(root,text="O M N I _ V O I D _ E N G I N E",bg=BG,fg=GLOW,font=("Courier",17,"bold")).pack(pady=(20,4))
        tk.Label(root,text="walk \u00b7 sprint \u00b7 drive \u00b7 fly \u00b7 land \u00b7 board \u00b7 discover",bg=BG,fg=AMBER,font=("Courier",11)).pack(pady=(0,6))
        info=(
            "Begin in deep space.  Find a planet, press [F] to land.\n\n"
            "ON FOOT / BOARDING  (CybervoidFusion raycaster engine):\n"
            "  WASD            move / strafe\n"
            "  arrow UP/DOWN   move forward / backward\n"
            "  arrow LEFT/RIGHT  turn left / right\n"
            "  SHIFT  sprint       V  jump\n"
            "  SPACE/LMB  fire emitter  (confuses \u2192 pacifies, never kills)\n"
            "  E  interact \u2014 enter vehicle / ship / terminal\n"
            "  F  take off to space       T  teleport to stranded ship\n"
            "  L  open artifact log  (collect \u2741 artifacts to fill it)\n\n"
            "IN VEHICLE  (Phos City renderer \u2014 auto-swaps on enter):\n"
            "  W/S or UP/DOWN  throttle   A/D  steer   SHIFT boost   E exit\n"
            "  arrow LEFT / RIGHT  look left / look right (camera yaw, no wheel turn)\n"
            "  Minimap: V = vehicle,  S = spaceship (launch point)\n\n"
            "IN SPACE:\n"
            "  WASD  pitch/yaw   Q/E  roll   arrow-keys  strafe\n"
            "  SPACE  thrust      B  boost   F  land      G  board enemy ship\n"
            "  M  music toggle   R  SFX toggle   ESC  quit\n"
        )
        tk.Label(root,text=info,bg=BG,fg=FG,font=("Courier",9),justify="left").pack(pady=(0,6))
        tk.Button(root,text="PEACEFUL  (no enemy damage)",bg="#003322",fg=GLOW,font=("Courier",12,"bold"),
                  width=34,command=lambda:self._launch(False)).pack(pady=4)
        tk.Button(root,text="COMBAT  (enemies damage you)",bg="#330000",fg=RED,font=("Courier",12,"bold"),
                  width=34,command=lambda:self._launch(True)).pack(pady=4)
        tk.Button(root,text="QUIT",bg=BG,fg=DIM,font=("Courier",10),width=14,command=root.destroy).pack(pady=(12,4))
        tk.Label(root,text="single-file \u00b7 pure stdlib \u00b7 zero dependencies \u00b7 fully offline",
                 bg=BG,fg=DIM,font=("Courier",8)).pack(side="bottom",pady=6)

    def _launch(self, combat):
        self.root.destroy()
        game_root=tk.Tk(); Game(game_root,combat=combat); game_root.mainloop()


# ================================================================ ENTRY POINT

def main():
    root=tk.Tk(); Launcher(root); root.mainloop()

if __name__=="__main__":
    main()












