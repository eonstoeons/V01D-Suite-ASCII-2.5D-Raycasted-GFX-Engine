# V01D Engine 1.0

A single Python file containing the entire V01D ecosystem and graphics engines:
17 fully-preserved apps, real-time and first-person ASCII, DDA raycasted 2.5D GFX engines, an experimental IDE and localized code generator,
an injectable "PyCart / json-cart" system, and an SDK for building your own games and tools.

Database updated with open source knowledge base compiled by Claude AI, as well as a number of public
domain e-books from Project Gutenberg.

**Zero external dependencies — pure Python 3 + tkinter stdlib.**
Works on Windows, macOS, and Linux.

---

## Quick Start

```bash
python V01D_Engine_Suite_v1_0.py
```
or open and run in a Python IDE — Thonny works well.

That's it. No pip, no virtualenv, no downloads. Everything is embedded.

---

## Files in This Repository

### 🌐 `OMNIV01D_BROWSER_VERSION_v1_0.html`
**OMNIV01D Engine — BR0WSER EDITION**

A complete zero-dependency browser port of the OMNIV01D Engine. Single HTML file — open it and play instantly, no install, no server. Features all three rendering modes in one: first-person ASCII raycaster on foot, driving view in vehicles, and a 3D canvas starfield in space. Includes procedural planets, enemy ships to board, an artifact log system with floating ⚙ pickup indicators, generative ambient music via the Web Audio API, save/load with passcodes, and a full pause menu. Runs entirely in JavaScript — no external libraries.

---

### 🐍 `Omnivoid_Consolidated_GFX_Engine_v1_0_Alpha.py`
**OMNIV01D Engine — PYth0N EDITION**

All three GFX engines merged into a single Python/tkinter file. Auto-swaps renderer based on your current mode:
- **On foot / boarding** → CybervoidFusion DDA raycaster with true look left/right
- **In vehicle** → Phos City night-drive renderer with windowed buildings
- **In space** → Void Space 6-DOF starfield cosmos

Pure stdlib, zero dependencies. Includes the full entity, mission, audio, and world systems from all three engines. Beginner-friendly mod guide built into the header — change colors, speeds, enemies, worlds, and audio with no deep code knowledge needed.

---

### 🐍 `CybervoidFusion_Alpha_0_1.py`
**V01D Engine v2.1 — Confusion Protocol / "The Void Depths"**

The core first-person combat and exploration engine. A DDA raycaster driving an infinite procedural world rendered in ASCII. Features a confusion emitter weapon that pacifies rather than kills enemies, a full particle system (sparks, blood, smoke), adaptive difficulty meta-loop, mission system (kill/key/portal), Schroeder reverb engine with wall-proximity detection, always-on sub-bass BassRumbleEngine (18–42 Hz), generative AmbientEngine with metal pings and void hums, procedural sprite and dialogue generators, and a minimap/compass HUD. Pure Python + tkinter, no external dependencies.

---

### 🐍 `First_Person_ASCII_Infinite_City_Night_Drive_Sim_0_1.py`
**Phos City v1.0 — Night Drive Sim**

A pure GFX showcase — all combat stripped, just the drive. An infinite procedural night-city raycaster: endless lit canyons of stacked highrises, windows glowing, trees and lamp posts lining the curb, lane stripes receding to the horizon. Fully synthesized ambient audio — HVAC void-hum, wind gusts, distant traffic rumble, structure groans — generated live with no audio files. Controls: throttle, brake/reverse, steer, boost, road recentering. Pure Python + tkinter.

---

### 🐍 `Void_Space_Flight_Sim_Alpha_0_2.py`
**Void Engine Ultimate — 6-DOF Space Flight Sim**

Infinite procedural cosmos flight simulator. Full 6 degrees of freedom — pitch, yaw, roll, and strafe in any direction forever. Features particle starfields, procedural planet and comet rendering, deep space generative audio synthesis, and a boost system. Toggle thrust, roll through asteroid fields, and navigate a living void. Pure math, pure Python, zero dependencies.

---

### 🐍 `V01D_Engine_Suite_v1_0.py`
**V01D Master SDK — Launcher**

One Python file. Every app. Forever. A PyCart launcher embedding 15 fully self-contained apps as plain-text JSON cartridges — no base64, no compression, readable by anyone. Launches each cart as a subprocess with SHA-256 checksum verification. Includes a Workshop to build and export your own carts, a built-in IDE, and a file manager. Carts auto-discovered from `~/v01d_workspace/user_carts/`.

**Embedded carts:**

| Cart | Genre | Description |
|------|-------|-------------|
| **AeonForge — Map SDK** | SDK / Map Builder | Tile-based map builder. Place terminals, relics, and hologram remnant beings. Saves to `.map.json`. |
| **CodeForge Editor** | Dev Tool / Editor | White-phosphor Python editor + file manager. Run scripts, edit code, manage your script library. |
| **ASCII Galaxyfall** | Demo / Generator | Animated ASCII meteor shower starfield. Pure Tkinter — lovely demo and GFX reference. |
| **Minigame Harness** | SDK / Tool | Run any cart as a gating minigame. Door-unlocks, terminal-hacks, branching scenes. Returns pass/fail via JSON result file. |
| **PHOS CITY — Night Drive Sim** | GFX Engine / Driving Sim | Infinite procedural ASCII night-city raycaster. The headline rendering engine for new SDK games. |
| **PyAmby — Ambient Studio** | Audio / Ambient | Ambient soundscape generator. Pure Python audio synthesis — no deps. |
| **Pysplore — Explorer** | Utility / Explorer | Pure-Python multi-tool suite: Solitaire, Chess, Checkers, DAW, Paint, Journal, and more. |
| **Scene Chain** | SDK / Tool | Stitch maps, dialogues, minigames, and scripts into a single playable sequence via `.chain.json` manifests. |
| **Solitaire** | Game / Card | Gentle Klondike. Infinite undo, smart hints, auto-complete, optional gentle deal mode. |
| **TTS Studio Freeflow** | Audio / TTS | Local text-to-speech studio. Free-flowing voice synthesis — fully offline. |
| **V01D Engine SDK** | SDK / Game Builder | Complete game-building SDK on the Void Engine raycaster core. Build FPS, RPG, racing, space, or puzzle games. |
| **V01D Forge — AI Coder** | SDK / AI Code Generator | Type what you want, get complete runnable code. Local AI coder — generates and perfects Python. |
| **V01D Mind — Local AI** | AI / Chatbot | 10,149 KB knowledge base. BM25 retrieval over GenericsKB, SimpleWiki, Gutenberg, and more. Fully offline. |
| **VOID SPACE — Flight Sim** | GFX Engine / Space Sim | Pure-Tk space flight sim with particle starfields, audio synthesis, and procedural celestial rendering. |
| **ZenLocal APEX** | AI / Knowledge | BM25 search + N-gram Markov brain. 10,149 knowledge entries. Fully offline, zero deps. |

---

## Workspace Layout

After first launch, a workspace is created at `~/v01d_workspace/`:

```
~/v01d_workspace/
    scripts/        ← your editable .py files
    exports/        ← Library "Export .py" target
    user_carts/     ← Workshop "Build Cart" output (.json)
```

Edit scripts in the built-in IDE, run them, save as PyCarts, and manage your library from the launcher.

---

## How to Build Your Own Game

The built-in **V01D Engine SDK** cart provides templates and a complete API for 3D raycasting, 2D top-down, or canvas-based games. A simple FPS example:

```python
from V01D_ENGINE_SDK_v1_0 import VoidGameBase, DungeonWorld, Entity

class MyGame(VoidGameBase):
    TITLE = "My Void Game"
    RENDER_MODE = "3D"
    WORLD_CLASS = DungeonWorld

    def setup(self):
        self.score = 0

    def on_update(self):
        pass

    def on_hud(self, buf):
        buf[0][0] = f"Score: {self.score}"

root = tk.Tk()
game = MyGame(root)
game.start()
root.mainloop()
```

Save as a `.py` file, import into the Workshop, and export as a PyCart to share.

---

## PyCart System

All apps are stored as "PyCarts" — plain-text Python scripts embedded in JSON cartridges. Cart schema:

```json
{
  "id":       "my_cart",
  "title":    "My Cart",
  "author":   "you",
  "genre":    "Game",
  "version":  "1.0",
  "tag":      "tool",
  "icon":     "■",
  "desc":     "What this does...",
  "source":   "import tkinter ... # the whole .py file as a string",
  "checksum": "<first 16 hex chars of sha256(source bytes)>",
  "size":     12345
}
```

Create your own: open the Workshop tab, paste your code, fill in the form, click **BUILD CART**. The launcher writes the JSON to `~/v01d_workspace/user_carts/` and it appears in the library automatically.

---

## License

MIT Open Source License 2026 — Do whatever you want. Credit appreciated.

## Authors

- Original concept & code: **eonstoeons**
- Co-coded with **Claude Opus** (Anthropic)

GitHub: [github.com/eonstoeons](https://github.com/eonstoeons)

Other MIT repos and creators that made this possible. All credit goes where it is due:

```
https://github.com/irmen/raycaster
https://github.com/Magoninho/raycasting-python
https://github.com/rhasspy/piper  (Piper TTS)
https://github.com/s-macke/VoxelSpace
https://github.com/JayWalker512/ascii_raytracer
https://github.com/LingDong-/asciimare
https://github.com/Dozed12/df-style-worldgen
```

Enjoy the void.
