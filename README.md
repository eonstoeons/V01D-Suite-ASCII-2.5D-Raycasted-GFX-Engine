# V01D-Suite & ASCII-2.5D-Raycasted-GFX-Engine
A single-file Python suite with two 2.5D ASCII raycast engines, an AI code generator, offline chatbot, games, IDE, TTS studio, and a full game-building SDK — all embedded. Zero dependencies. Build, play, create.

--------------------------------------------------------------------------------------------------------------------------------------------------

# V01D Suite 0.2 Alpha

**“ONE FILE. EVERY APP.”**

A single Python file containing the entire V01D ecosystem:
12 fully-preserved apps, two real‑time and first-person ASCII, DDS raycasted 2.5D GFX engines, an IDE, an AI code generator,
an injectible "PyCart / json-cart" system, and a complete SDK for building your own games and tools.

Database updated with open source knowledge base compiled by Claude AI, as well as a number of public
domain e-books from Project Gutenberg.

**Zero external dependencies — pure Python 3 + tkinter stdlib.**
Works on Windows, macOS, and Linux.

---

## Quick Start

```bash
python V01D_Engine_Suite_v1_1.py
```
or

open and run in a Python IDE, for example, Thonny works well.

That’s it. No pip, no virtualenv, no downloads. Everything is embedded.

---

## What’s Inside

### 🎮 Two Real‑Time GFX Engines

- **Phos City** – night‑drive simulator with infinite procedural ASCII cityscapes, raycaster engine, and full audio synthesis (ambient city soundscape).

- **Void Space** – infinite starfield flight sim with particles, comets, procedural planets, and deep space soundtracks. - Full plane of movement,
                   6DOF (6 degrees of freedom), fly 360 degrees in any direction infinitely

### 🛠️ SDK & Dev Tools

- **V01D Engine SDK** – complete game‑building SDK on the Phos/Void raycasting core. Build FPS, RPG, racers, 2D platformers, rogue‑likes, and more. Comes with a generic game base, map routers, entity system, missions, audio engine, and PyCart export.

- **V01D Forge** (v2.0) – an offline AI code generator. Type what you want (Python, C89, x86 assembly), and get complete, runnable code. Includes built‑in templates, self‑test loops, macro recorder, and an offline reference base.

- **CodeForge Editor** – a white‑phosphor Python editor and file manager with run/export.

### 🤖 Knowledge Base, AI, LLM, Markov Brain

- **V01D Mind** – a fully offline, local knowledge base with 10,149 KB of entries using BM25 retrieval over GenericsKB, SimpleWiki, and Gutenberg.
                  
- **ZenLocal APEX** – another AI/chatbot. Trainable Markov brain and option to upload new text files to its DB.

### 🎨 Creative

- **PyAmby** – Procedurally generated ambient music, nature SFX, and the ability to export custom WAV files

- **TTS Studio** - Text-To-Speech tool trained off Piper, exported to MP3 with custom settings. Use for in-game dialogue, Text to Audiobook, etc.

- **Pysplore** - Offline, fully local utility, creation, entertainment suite. Barebones simple OS emulator. Completely local and offline.
                 Includes 10 apps: DAW (music maker), media player, ambience generator, paint tool, journal, clock (with calender, timer,            stopwatch), Calculator, Chess and Checkers (1 or 2 player local), and Solitaire.
                 
### 🕹️ Games (standalone)

- **Klondike Solitaire** - Classic Solitaire

- **ASCII Galaxyfall** - Randomized ASCII starfall generator

### 📦 PyCart System

All apps are stored as “PyCarts” – base64‑encoded Python scripts in JSON cartridges.
You can create, export, import, and share `.pycart.json` files. The SDK launcher auto‑discovers all carts in `~/v01d_workspace/carts/`.

---

## Workspace Layout

After first launch, a workspace is created in `~/v01d_workspace/`:

```
~/v01d_workspace/
    scripts/     ← your editable .py files
    carts/       ← exported PyCarts (.pycart.json)
    exports/     ← extracted apps
```

You can edit scripts in the built‑in editor, run them, save as PyCarts, and manage your library.

---

## Embedded Apps (12 total)

| App | Type | Description |
|-----|------|-------------|
| Phos City | Engine / Driving Sim | Infinite procedural night‑city raycaster |
| Void Space | Engine / Space Sim | Infinite starfield flight with particles & comets |
| V01D Engine SDK | SDK / Game Builder | Full game builder on the Phos/Void engine |
| V01D Forge | SDK / AI Coder | Local AI code generator (Python, C89, ASM) |
| CodeForge | Editor / File Manager | White‑phosphor Python editor |
| V01D Mind | AI / Knowledge Base | Local BM25 search with 10MB+ of text |
| ZenLocal APEX | AI / Chatbot | Another offline AI |
| PyAmby | Creative | (placeholder) |
| TTS Studio | Creative | Text‑to‑speech |
| Pysplore | Creative | (placeholder) |
| Klondike Solitaire | Game | Classic solitaire |
| ASCII Galaxyfall | Game | ASCII Comet / starfall animation tool |

---

## How to Build Your Own Game

The built‑in **V01D Engine SDK** tab provides templates and a complete API for 3D raycasting, 2D top‑down, or canvas‑based games.
A simple FPS example:

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

Save as a `.py` file, import into the SDK, and export as a PyCart to share!

---

## License

MIT Open Source License 2026 – Do whatever you want. Credit appreciated.

## Authors

- Original concept & code: **eonstoeons**
- Co‑coded with **Claude Opus** (Anthropic)

GitHub: [github.com/eonstoeons](https://github.com/eonstoeons)

Other MIT repos and creators that made this possible. All credit goes where it is due:

---------------------------------------------------

https://github.com/irmen/raycaster.git
https://github.com/Magoninho/raycasting-python.git
Piper TTS (github.com/rhasspy/piper)
https://github.com/s-macke/VoxelSpace.git 
https://github.com/rhasspy/piper.git 
https://github.com/JayWalker512/ascii_raytracer.git 
https://github.com/LingDong-/asciimare.git 
https://github.com/Dozed12/df-style-worldgen.git

---------------------------------------------------

Enjoy the v01d.
