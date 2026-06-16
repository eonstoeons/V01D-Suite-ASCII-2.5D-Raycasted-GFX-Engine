#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║  V O I D _ E N G I N E _ U L T I M A T E  //  v∞.0             ║
║  6-DOF · INFINITE PROCEDURAL COSMOS · DEEP SPACE AUDIO          ║
║  VOID_FORGE + VOID_MIND + FREEFLOW + PYAMBY + SDK_CORE FUSED    ║
║  Single file · Zero deps · Pure Python · Pure Math · Pure Void  ║
╚══════════════════════════════════════════════════════════════════╝
CONTROLS:
  W/S        — Pitch up/down
  A/D        — Yaw left/right
  Q/E        — Roll
  ARROWS     — Strafe (up/dn/lt/rt)
  SPACE      — Toggle main thruster
  B          — Boost (hold)
  M          — Toggle ambient music
  R          — Toggle rumble/SFX
  F          — Fullscreen
  ESC        — Quit
"""
import tkinter as tk
import math, random, time, threading, array, struct, os, sys

# ═══════════════════════════════════════════════════════════════════
#  AUDIO ENGINE — pure math, no deps
# ═══════════════════════════════════════════════════════════════════
SAMPLE_RATE = 22050
AUDIO_AVAILABLE = False
try:
    import audioop, wave, io
    # Try to get a playback backend
    try:
        import winsound as _ws
        AUDIO_BACKEND = "winsound"
        AUDIO_AVAILABLE = True
    except ImportError:
        pass
    if not AUDIO_AVAILABLE:
        try:
            import subprocess as _sp
            _sp.run(["aplay","--version"],capture_output=True)
            AUDIO_BACKEND = "aplay"
            AUDIO_AVAILABLE = True
        except Exception:
            pass
    if not AUDIO_AVAILABLE:
        try:
            import subprocess as _sp
            _sp.run(["afplay","--help"],capture_output=True)
            AUDIO_BACKEND = "afplay"
            AUDIO_AVAILABLE = True
        except Exception:
            pass
except ImportError:
    pass

# Try ctypes winmm as fallback on Windows
if not AUDIO_AVAILABLE:
    try:
        import ctypes
        _mm = ctypes.windll.winmm
        AUDIO_BACKEND = "winmm"
        AUDIO_AVAILABLE = True
    except Exception:
        pass

def synth_wave(freq, duration, amplitude=0.4, wave_type="sine", sr=SAMPLE_RATE):
    n = int(sr * duration)
    samples = []
    for i in range(n):
        t = i / sr
        if wave_type == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif wave_type == "saw":
            v = 2 * ((freq * t) % 1.0) - 1.0
        elif wave_type == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        elif wave_type == "noise":
            v = random.uniform(-1, 1)
        elif wave_type == "tri":
            p = (freq * t) % 1.0
            v = (4 * p - 1) if p < 0.5 else (3 - 4 * p)
        else:
            v = 0.0
        env = min(i, n-i, sr*0.05) / (sr*0.05)  # tiny fade in/out
        samples.append(int(max(-32767, min(32767, v * amplitude * 32767 * env))))
    return array.array('h', samples)

def mix_waves(waves):
    if not waves: return array.array('h', [])
    length = max(len(w) for w in waves)
    result = []
    for i in range(length):
        s = 0
        for w in waves:
            if i < len(w): s += w[i]
        result.append(int(max(-32767, min(32767, s / len(waves)))))
    return array.array('h', result)

def samples_to_wav_bytes(samples, sr=SAMPLE_RATE):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()

def play_wav_bytes_async(wav_bytes, backend):
    """Fire and forget wav playback."""
    def _play():
        try:
            if backend == "winsound":
                import winsound
                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY | winsound.SND_ASYNC)
            elif backend in ("aplay", "afplay"):
                import tempfile
                tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tf.write(wav_bytes)
                tf.close()
                import subprocess
                cmd = ["aplay", "-q", tf.name] if backend == "aplay" else ["afplay", tf.name]
                subprocess.Popen(cmd)
            elif backend == "winmm":
                import ctypes, tempfile
                tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tf.write(wav_bytes)
                tf.close()
                ctypes.windll.winmm.PlaySoundW(tf.name, None, 0x00020001)  # SND_FILENAME|SND_ASYNC
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()

class VoidAudio:
    """Layered ambient deep space synthesizer."""
    def __init__(self):
        self.enabled = AUDIO_AVAILABLE
        self.rumble_enabled = AUDIO_AVAILABLE
        self.backend = AUDIO_BACKEND if AUDIO_AVAILABLE else None
        self._amb_thread = None
        self._amb_running = False
        self._thruster_playing = False
        self._frame = 0
        # Pre-bake some ambient layers
        self._cache = {}
        if self.enabled:
            threading.Thread(target=self._prebake, daemon=True).start()

    def _prebake(self):
        """Generate ambient sounds in background."""
        try:
            # Deep drone layer 1 — 40Hz sub rumble
            d1 = synth_wave(40, 3.0, 0.15, "sine")
            d2 = synth_wave(80, 3.0, 0.08, "sine")
            d3 = synth_wave(120, 3.0, 0.05, "tri")
            d4 = synth_wave(0.5, 3.0, 0.03, "noise")  # cosmic static
            drone = mix_waves([d1, d2, d3, d4])
            self._cache['drone'] = samples_to_wav_bytes(drone)

            # High shimmer
            s1 = synth_wave(880, 2.0, 0.04, "sine")
            s2 = synth_wave(1320, 2.0, 0.02, "sine")
            shimmer = mix_waves([s1, s2])
            self._cache['shimmer'] = samples_to_wav_bytes(shimmer)

            # Thruster rumble
            t1 = synth_wave(60, 1.0, 0.25, "saw")
            t2 = synth_wave(0.5, 1.0, 0.15, "noise")
            thruster = mix_waves([t1, t2])
            self._cache['thruster'] = samples_to_wav_bytes(thruster)

            # Comet whoosh
            w1 = synth_wave(200, 0.5, 0.2, "noise")
            w2 = synth_wave(100, 0.5, 0.1, "sine")
            whoosh = mix_waves([w1, w2])
            self._cache['whoosh'] = samples_to_wav_bytes(whoosh)

            # Warp / boost
            b1 = synth_wave(55, 1.5, 0.3, "saw")
            b2 = synth_wave(110, 1.5, 0.2, "sine")
            b3 = synth_wave(220, 1.5, 0.1, "tri")
            boost = mix_waves([b1, b2, b3])
            self._cache['boost'] = samples_to_wav_bytes(boost)

            self._start_ambient_loop()
        except Exception:
            pass

    def _start_ambient_loop(self):
        self._amb_running = True
        self._amb_thread = threading.Thread(target=self._ambient_loop, daemon=True)
        self._amb_thread.start()

    def _ambient_loop(self):
        while self._amb_running and self.enabled:
            try:
                if 'drone' in self._cache:
                    play_wav_bytes_async(self._cache['drone'], self.backend)
                time.sleep(2.8)
                if random.random() < 0.4 and 'shimmer' in self._cache:
                    play_wav_bytes_async(self._cache['shimmer'], self.backend)
                time.sleep(0.2)
            except Exception:
                time.sleep(1)

    def play_thruster(self):
        if not self.enabled or not self.rumble_enabled: return
        if 'thruster' in self._cache:
            play_wav_bytes_async(self._cache['thruster'], self.backend)

    def play_whoosh(self):
        if not self.enabled or not self.rumble_enabled: return
        if 'whoosh' in self._cache:
            play_wav_bytes_async(self._cache['whoosh'], self.backend)

    def play_boost(self):
        if not self.enabled or not self.rumble_enabled: return
        if 'boost' in self._cache:
            play_wav_bytes_async(self._cache['boost'], self.backend)

    def toggle_music(self):
        self.enabled = not self.enabled
        if self.enabled and not self._amb_running and self._cache:
            self._start_ambient_loop()
        elif not self.enabled:
            self._amb_running = False

    def toggle_rumble(self):
        self.rumble_enabled = not self.rumble_enabled

    def stop(self):
        self._amb_running = False

# ═══════════════════════════════════════════════════════════════════
#  MATH CORE
# ═══════════════════════════════════════════════════════════════════
def vdot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def vsub(a, b): return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]
def vadd(a, b): return [a[0]+b[0], a[1]+b[1], a[2]+b[2]]
def vmul(v, s): return [v[0]*s, v[1]*s, v[2]*s]
def vnorm(v):
    m = math.sqrt(v[0]**2+v[1]**2+v[2]**2)
    return [v[0]/m, v[1]/m, v[2]/m] if m > 1e-9 else [0,0,1]

def rodrigues(v, axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    cross = [axis[1]*v[2]-axis[2]*v[1], axis[2]*v[0]-axis[0]*v[2], axis[0]*v[1]-axis[1]*v[0]]
    dot = vdot(axis, v)
    return [v[i]*c + cross[i]*s + axis[i]*dot*(1-c) for i in range(3)]

# ═══════════════════════════════════════════════════════════════════
#  INFINITE PROCEDURAL STAR FIELD — spherical seeded chunks
# ═══════════════════════════════════════════════════════════════════
CHUNK_RADIUS = 4000
STARS_PER_CHUNK = 120
COMET_POOL = 8

STAR_GLYPHS = ['.', '·', '*', '+', '°', '\'', '`', '✦', '✧', '★', '☆']
STAR_COLORS = [
    "#ffffff", "#aabbff", "#ffddaa", "#ffeedd",
    "#aaffff", "#ffbbbb", "#88aaff", "#ffcc88",
    "#ccddff", "#ffb000", "#ffcc00", "#88ffcc",
]

class StarChunk:
    __slots__ = ['key', 'stars']
    def __init__(self, key, pos_seed):
        self.key = key
        rng = random.Random(hash(key) ^ 0xDEADBEEF)
        # Stars distributed spherically around chunk center
        cx, cy, cz = [k * CHUNK_RADIUS * 2 for k in key]
        stars = []
        for _ in range(STARS_PER_CHUNK):
            # Spherical uniform distribution
            phi = rng.uniform(0, 2*math.pi)
            costheta = rng.uniform(-1, 1)
            sintheta = math.sqrt(1 - costheta**2)
            r = rng.uniform(CHUNK_RADIUS * 0.2, CHUNK_RADIUS)
            x = cx + r * sintheta * math.cos(phi)
            y = cy + r * costheta
            z = cz + r * sintheta * math.sin(phi)
            glyph = rng.choice(STAR_GLYPHS)
            color = rng.choice(STAR_COLORS)
            size  = rng.choice([8, 9, 10, 11, 12, 10, 9, 9, 8])
            bright = rng.uniform(0.3, 1.0)
            stars.append((x, y, z, glyph, color, size, bright))
        self.stars = stars

class InfiniteStarField:
    def __init__(self):
        self._chunks = {}
        self._max_chunks = 200

    def _chunk_key(self, pos):
        return (
            int(math.floor(pos[0] / (CHUNK_RADIUS*2))),
            int(math.floor(pos[1] / (CHUNK_RADIUS*2))),
            int(math.floor(pos[2] / (CHUNK_RADIUS*2))),
        )

    def get_stars_near(self, pos):
        """Return all stars from surrounding 3³=27 chunks."""
        cx, cy, cz = self._chunk_key(pos)
        stars = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                for dz in range(-1, 2):
                    key = (cx+dx, cy+dy, cz+dz)
                    if key not in self._chunks:
                        if len(self._chunks) > self._max_chunks:
                            # Evict farthest chunk
                            farthest = max(
                                self._chunks.keys(),
                                key=lambda k: (k[0]-cx)**2+(k[1]-cy)**2+(k[2]-cz)**2
                            )
                            del self._chunks[farthest]
                        self._chunks[key] = StarChunk(key, pos)
                    stars.extend(self._chunks[key].stars)
        return stars

# ═══════════════════════════════════════════════════════════════════
#  COMET / METEOR SYSTEM (ASCII Galaxyfall algo)
# ═══════════════════════════════════════════════════════════════════
COMET_CHARS = ['@', '%', '#', '*', '+', '·', '.', ' ']
COMET_COLORS = ["#ffffff", "#aaccff", "#ffeeaa", "#88ffff", "#ffaa88"]

class Comet:
    def __init__(self, player_pos, player_fwd):
        self.age = 0
        # Spawn ahead-ish in a random cone
        spread = 3000
        self.pos = [
            player_pos[0] + player_fwd[0]*4000 + random.uniform(-spread, spread),
            player_pos[1] + player_fwd[1]*4000 + random.uniform(-spread, spread),
            player_pos[2] + player_fwd[2]*4000 + random.uniform(-spread, spread),
        ]
        speed = random.uniform(30, 120)
        # Random direction biased toward player
        self.vel = [random.uniform(-speed, speed), random.uniform(-speed, speed), random.uniform(-speed, speed)]
        self.tail_len = random.randint(5, 14)
        self.tail = []
        self.color = random.choice(COMET_COLORS)
        self.max_age = random.randint(120, 400)

    def update(self):
        self.tail.insert(0, list(self.pos))
        if len(self.tail) > self.tail_len:
            self.tail.pop()
        self.pos = vadd(self.pos, self.vel)
        self.age += 1

    def alive(self): return self.age < self.max_age

# ═══════════════════════════════════════════════════════════════════
#  PLANETS / DEEP SPACE OBJECTS
# ═══════════════════════════════════════════════════════════════════
PLANET_CHARS = ["@", "O", "#", "0", "Θ", "⊕", "◎", "●"]
PLANET_COLORS = ["#ff8844", "#44aaff", "#aaff88", "#ffaa44", "#ff44aa", "#88ffff"]

class PlanetField:
    def __init__(self):
        rng = random.Random(42)
        self.planets = []
        for _ in range(20):
            p = {
                "pos": [rng.uniform(-40000, 40000) for _ in range(3)],
                "size": rng.randint(40, 150),
                "char": rng.choice(PLANET_CHARS),
                "color": rng.choice(PLANET_COLORS),
                "rot": rng.uniform(0, math.pi*2),
                "rot_speed": rng.uniform(-0.02, 0.02),
            }
            self.planets.append(p)

    def update(self):
        for p in self.planets:
            p["rot"] += p["rot_speed"]

# ═══════════════════════════════════════════════════════════════════
#  MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════
W, H = 1100, 800
BG    = "#000005"
AMBER = "#ffb000"
GLOW  = "#ffcc00"
WHITE = "#ffffff"
CYAN  = "#44ffff"
FPS   = 45

class VoidEngineUltimate:
    def __init__(self, root):
        self.root = root
        self.root.title("V O I D _ E N G I N E _ U L T I M A T E  //  v∞.0")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # — Ship state —
        self.pos   = [0.0, 0.0, 0.0]
        self.fwd   = [0.0, 0.0, 1.0]
        self.up    = [0.0, 1.0, 0.0]
        self.right = [1.0, 0.0, 0.0]
        self.vel   = 0.0
        self.lat_vel = [0.0, 0.0, 0.0]  # lateral momentum

        self.thruster_on = False
        self.boost_on    = False
        self.active_keys = set()

        # — Systems —
        self.starfield  = InfiniteStarField()
        self.planet_field = PlanetField()
        self.comets     = []
        self.audio      = VoidAudio()

        # — FX state —
        self.frame       = 0
        self.last_thruster_sfx = 0
        self.last_comet_sfx    = 0
        self.screen_shake      = 0.0
        self.warp_lines        = []
        self.twinkle_phase     = {}

        # — HUD —
        self.hud_msg     = ""
        self.hud_msg_ttl = 0

        # — Binds —
        self.root.bind("<KeyPress>",   self._keydown)
        self.root.bind("<KeyRelease>", self._keyup)
        self.root.bind("<Configure>",  self._on_resize)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        self._loop()

    # ─── Input ───────────────────────────────────────────────────
    def _keydown(self, e):
        k = e.keysym.lower()
        self.active_keys.add(k)
        if k == "space":
            self.thruster_on = not self.thruster_on
            self._hud(f"THRUST {'ON' if self.thruster_on else 'OFF'}")
        elif k == "b":
            self.boost_on = True
            self.audio.play_boost()
            self._hud("BOOST ENGAGED")
        elif k == "m":
            self.audio.toggle_music()
            self._hud(f"MUSIC {'ON' if self.audio.enabled else 'OFF'}")
        elif k == "r":
            self.audio.toggle_rumble()
            self._hud(f"SFX {'ON' if self.audio.rumble_enabled else 'OFF'}")
        elif k == "f":
            fs = not self.root.attributes("-fullscreen")
            self.root.attributes("-fullscreen", fs)
            self._hud("FULLSCREEN ON" if fs else "FULLSCREEN OFF")
        elif k == "escape":
            self._quit()

    def _keyup(self, e):
        k = e.keysym.lower()
        self.active_keys.discard(k)
        if k == "b":
            self.boost_on = False

    def _on_resize(self, e): pass

    def _hud(self, msg, ttl=80):
        self.hud_msg = msg
        self.hud_msg_ttl = ttl

    def _quit(self):
        self.audio.stop()
        self.root.destroy()

    # ─── Physics ─────────────────────────────────────────────────
    def _update_physics(self):
        ts = 0.045  # turn speed

        if 'w' in self.active_keys:
            self.fwd = rodrigues(self.fwd, self.right, -ts)
            self.up  = rodrigues(self.up,  self.right, -ts)
        if 's' in self.active_keys:
            self.fwd = rodrigues(self.fwd, self.right, ts)
            self.up  = rodrigues(self.up,  self.right, ts)
        if 'a' in self.active_keys:
            self.fwd   = rodrigues(self.fwd,   self.up, -ts)
            self.right = rodrigues(self.right,  self.up, -ts)
        if 'd' in self.active_keys:
            self.fwd   = rodrigues(self.fwd,   self.up, ts)
            self.right = rodrigues(self.right,  self.up, ts)
        if 'q' in self.active_keys:
            self.up    = rodrigues(self.up,    self.fwd, ts)
            self.right = rodrigues(self.right, self.fwd, ts)
        if 'e' in self.active_keys:
            self.up    = rodrigues(self.up,    self.fwd, -ts)
            self.right = rodrigues(self.right, self.fwd, -ts)

        # Re-orthonormalize occasionally to prevent drift
        if self.frame % 30 == 0:
            self.fwd   = vnorm(self.fwd)
            self.right = vnorm(self.right)
            # Cross product to keep up perpendicular
            self.up = vnorm([
                self.fwd[1]*self.right[2] - self.fwd[2]*self.right[1],
                self.fwd[2]*self.right[0] - self.fwd[0]*self.right[2],
                self.fwd[0]*self.right[1] - self.fwd[1]*self.right[0],
            ])
            self.right = vnorm([
                self.up[1]*self.fwd[2] - self.up[2]*self.fwd[1],
                self.up[2]*self.fwd[0] - self.up[0]*self.fwd[2],
                self.up[0]*self.fwd[1] - self.up[1]*self.fwd[0],
            ])

        # Strafe
        ms = 25.0
        if 'up'    in self.active_keys: self.pos = vadd(self.pos, vmul(self.up,    ms))
        if 'down'  in self.active_keys: self.pos = vadd(self.pos, vmul(self.up,   -ms))
        if 'left'  in self.active_keys: self.pos = vadd(self.pos, vmul(self.right,-ms))
        if 'right' in self.active_keys: self.pos = vadd(self.pos, vmul(self.right, ms))

        # Main thrust
        boost_mult = 4.0 if self.boost_on else 1.0
        target_vel = 80.0 * boost_mult if self.thruster_on else 0.0
        if self.boost_on and self.thruster_on:
            target_vel = 320.0
        self.vel += (target_vel - self.vel) * 0.07

        self.pos = vadd(self.pos, vmul(self.fwd, self.vel))

        # Screen shake when thrusting
        if self.thruster_on and self.vel > 10:
            self.screen_shake = min(3.0, self.screen_shake + 0.3)
        else:
            self.screen_shake *= 0.85

        # Thruster SFX
        if self.thruster_on and (self.frame - self.last_thruster_sfx) > 25:
            self.audio.play_thruster()
            self.last_thruster_sfx = self.frame

    # ─── Comets ──────────────────────────────────────────────────
    def _update_comets(self):
        # Spawn
        if len(self.comets) < COMET_POOL and random.random() < 0.04:
            self.comets.append(Comet(self.pos, self.fwd))

        for c in self.comets:
            c.update()

        self.comets = [c for c in self.comets if c.alive()]

    # ─── Projection ──────────────────────────────────────────────
    def project(self, wp, w, h, shake_dx=0, shake_dy=0):
        rel = vsub(wp, self.pos)
        lx  = vdot(rel, self.right)
        ly  = vdot(rel, self.up)
        lz  = vdot(rel, self.fwd)
        if lz < 10: return None
        f  = 750 / lz
        sx = (w/2) + lx*f + shake_dx
        sy = (h/2) - ly*f + shake_dy
        return sx, sy, f, lz

    # ─── Back-projection (stars behind player) ───────────────────
    def project_back(self, wp, w, h, shake_dx=0, shake_dy=0):
        """Project points behind the player onto a virtual 'rear view' annulus."""
        rel = vsub(wp, self.pos)
        lx  = vdot(rel, self.right)
        ly  = vdot(rel, self.up)
        lz  = vdot(rel, self.fwd)
        if lz > -10: return None
        f   = 750 / abs(lz)
        # Mirror onto the periphery of the screen
        sx = (w/2) - lx*f*0.6 + shake_dx
        sy = (h/2) + ly*f*0.6 + shake_dy
        return sx, sy, f*0.6, abs(lz)

    # ─── Draw ─────────────────────────────────────────────────────
    def _draw(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()  or W
        h = c.winfo_height() or H

        shake_dx = random.uniform(-self.screen_shake, self.screen_shake)
        shake_dy = random.uniform(-self.screen_shake, self.screen_shake)

        t = self.frame / FPS

        # ── Warp lines (thruster FX) ──────────────────────────────
        if self.vel > 30:
            intensity = min(1.0, (self.vel - 30) / 120)
            num_lines = int(intensity * 20)
            for _ in range(num_lines):
                ang = random.uniform(0, 2*math.pi)
                r0  = random.uniform(0, min(w,h)*0.05)
                r1  = r0 + random.uniform(20, 80) * intensity
                x0  = w/2 + math.cos(ang) * r0
                y0  = h/2 + math.sin(ang) * r0
                x1  = w/2 + math.cos(ang) * r1
                y1  = h/2 + math.sin(ang) * r1
                alpha_hex = format(int(intensity * 180), '02x')
                lcolor = f"#{'ff'}{alpha_hex}{'00'}" if intensity > 0.5 else f"#{'88'}{'88'}{'ff'}"
                c.create_line(x0, y0, x1, y1, fill=lcolor, width=1)

        # ── Infinite Stars ────────────────────────────────────────
        stars = self.starfield.get_stars_near(self.pos)
        drawn_back = 0
        for sx, sy, sz, glyph, color, fsize, bright in stars:
            # Forward hemisphere
            res = self.project([sx, sy, sz], w, h, shake_dx, shake_dy)
            if res:
                px, py, factor, dist = res
                if 0 <= px <= w and 0 <= py <= h:
                    # Twinkle
                    tp = self.twinkle_phase.get(id((sx,sy,sz)), random.uniform(0, math.pi*2))
                    twinkle = 0.6 + 0.4*math.sin(t*2.5 + tp)
                    # Size & brightness by distance
                    fs = max(7, min(fsize, int(factor * 4)))
                    # Dim far stars
                    if factor < 0.05:
                        g = '.'
                    elif factor < 0.2:
                        g = random.choice(['.',  '·', '\'', '`'])
                    else:
                        g = glyph
                    c.create_text(px, py, text=g, fill=color,
                                  font=("Courier", fs))
            else:
                # Try rear hemisphere — stars behind player visible on screen edges
                res2 = self.project_back([sx, sy, sz], w, h, shake_dx, shake_dy)
                if res2 and drawn_back < 80:
                    px, py, factor, dist = res2
                    if 0 <= px <= w and 0 <= py <= h:
                        c.create_text(px, py, text='·', fill=color,
                                      font=("Courier", 8))
                        drawn_back += 1

        # ── Planets ───────────────────────────────────────────────
        self.planet_field.update()
        for p in self.planet_field.planets:
            res = self.project(p["pos"], w, h, shake_dx, shake_dy)
            if res:
                px, py, factor, dist = res
                size = max(2, int(p["size"] * factor * 0.08))
                if size > 1 and 0 <= px <= w and 0 <= py <= h:
                    # Build planet ring
                    lines = []
                    for row in range(-size//4, size//4+1):
                        pad = size - abs(row)*2
                        if pad > 0:
                            lines.append(p["char"] * pad)
                    planet_str = "\n".join(lines) if len(lines) > 1 else p["char"] * size
                    c.create_text(px, py, text=planet_str,
                                  fill=p["color"],
                                  font=("Courier", max(8, size//2), "bold"))

        # ── Comets ────────────────────────────────────────────────
        for comet in self.comets:
            # Head
            res = self.project(comet.pos, w, h, shake_dx, shake_dy)
            if res:
                px, py, factor, dist = res
                if 0 <= px <= w and 0 <= py <= h:
                    c.create_text(px, py, text="@", fill="#ffffff",
                                  font=("Courier", max(9, int(factor*12)), "bold"))
                    # SFX trigger
                    if factor > 0.3 and (self.frame - self.last_comet_sfx) > 60:
                        self.audio.play_whoosh()
                        self.last_comet_sfx = self.frame
            # Tail
            for i, tp in enumerate(comet.tail):
                res_t = self.project(tp, w, h, shake_dx, shake_dy)
                if res_t:
                    px, py, factor, dist = res_t
                    if 0 <= px <= w and 0 <= py <= h:
                        idx = min(i, len(COMET_CHARS)-1)
                        fade_char = COMET_CHARS[idx]
                        fs = max(7, int(factor * 10))
                        # Fade color
                        fade = 1.0 - i / max(1, len(comet.tail))
                        r_val = int(0xaa + (0xff-0xaa)*fade)
                        g_val = int(0x88 + (0xff-0x88)*fade*0.5)
                        b_val = int(0xff * fade * 0.7)
                        tc = f"#{r_val:02x}{min(255,g_val):02x}{min(255,b_val):02x}"
                        c.create_text(px, py, text=fade_char, fill=tc,
                                      font=("Courier", fs))

        # ── HUD ───────────────────────────────────────────────────
        cx, cy = w/2, h/2

        # Crosshair
        ch_color = GLOW if self.thruster_on else AMBER
        c.create_text(cx, cy, text="──[✦]──", fill=ch_color, font=("Courier", 14))
        c.create_text(cx, cy-18, text="|", fill=ch_color, font=("Courier", 12))
        c.create_text(cx, cy+18, text="|", fill=ch_color, font=("Courier", 12))

        # Velocity bar
        vel_pct = min(1.0, abs(self.vel) / 320.0)
        bar_w   = 200
        filled  = int(vel_pct * bar_w / 6)
        vel_bar = "[" + "█"*filled + "░"*(bar_w//6-filled) + "]"
        c.create_text(cx, h-45, text=vel_bar, fill=AMBER, font=("Courier", 9))

        # Status line
        thrust_str = "▶ THRUST ON " if self.thruster_on else "  THRUST OFF"
        boost_str  = " ⚡BOOST" if self.boost_on else ""
        music_str  = "♫" if self.audio.enabled else "♪̶"
        sfx_str    = "~" if self.audio.rumble_enabled else "~̶"
        status = f"{thrust_str}{boost_str}  |  V:{int(self.vel):4d}  |  {music_str} {sfx_str}"
        c.create_text(cx, h-25, text=status, fill=GLOW, font=("Courier", 11))

        # Position readout (top-left)
        px_str = f"POS: {int(self.pos[0]):+08.0f} {int(self.pos[1]):+08.0f} {int(self.pos[2]):+08.0f}"
        c.create_text(10, 12, text=px_str, fill="#446644", font=("Courier", 9), anchor="w")

        # Comets counter (top-right)
        c.create_text(w-10, 12, text=f"COMETS:{len(self.comets):02d}  STARS:{len(stars):04d}",
                      fill="#334433", font=("Courier", 9), anchor="e")

        # Title flash
        if self.frame < 120:
            alpha_i = min(self.frame, 80) / 80
            c.create_text(cx, 40,
                          text="V O I D _ E N G I N E _ U L T I M A T E",
                          fill=GLOW, font=("Courier", 16, "bold"))
            c.create_text(cx, 60,
                          text="W/S:Pitch  A/D:Yaw  Q/E:Roll  SPACE:Thrust  B:Boost  M:Music  F:Full",
                          fill=AMBER, font=("Courier", 9))

        # HUD message
        if self.hud_msg_ttl > 0:
            alpha = min(1.0, self.hud_msg_ttl / 20)
            c.create_text(cx, h//2 + 60, text=self.hud_msg,
                          fill=WHITE, font=("Courier", 13, "bold"))
            self.hud_msg_ttl -= 1

        # Compass rose (which direction fwd points in world space)
        compass_x, compass_y, compass_r = w-70, 70, 35
        c.create_oval(compass_x-compass_r, compass_y-compass_r,
                      compass_x+compass_r, compass_y+compass_r,
                      outline="#333333", width=1)
        # Project forward vector onto compass
        yaw   = math.atan2(self.fwd[0], self.fwd[2])
        pitch = math.asin(max(-1, min(1, self.fwd[1])))
        needle_x = compass_x + math.sin(yaw)   * compass_r * 0.8
        needle_y = compass_y - math.sin(pitch)  * compass_r * 0.8
        c.create_line(compass_x, compass_y, needle_x, needle_y,
                      fill=AMBER, width=2)
        c.create_text(compass_x, compass_y+compass_r+10,
                      text="HDG", fill="#444444", font=("Courier", 8))

    # ─── Main Loop ────────────────────────────────────────────────
    def _loop(self):
        self._update_physics()
        self._update_comets()
        self._draw()
        self.frame += 1
        self.root.after(1000 // FPS, self._loop)

# ═══════════════════════════════════════════════════════════════════
#  BOOT
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry(f"{W}x{H}")
    root.configure(bg=BG)
    app = VoidEngineUltimate(root)
    root.mainloop()


