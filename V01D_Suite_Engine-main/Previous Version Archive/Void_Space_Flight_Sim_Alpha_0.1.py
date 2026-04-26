import tkinter as tk
import math
import random

# --- VOID CONFIG ---
WIDTH, HEIGHT = 1024, 768
COLOR_AMBER = "#ffb000"
COLOR_GLOW = "#ffcc00"
BG_VOID = "#0a0700"
FPS = 30

def vec_dot(a, b): return sum(x*y for x, y in zip(a, b))
def vec_sub(a, b): return [x-y for x, y in zip(a, b)]
def vec_mul(v, s): return [x*s for x in v]
def vec_add(a, b): return [x+y for x, y in zip(a, b)]

def rotate_vec(v, axis, angle):
    """Rotates a vector around an arbitrary axis (Rodrigues' rotation formula)."""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    cross = [
        axis[1]*v[2] - axis[2]*v[1],
        axis[2]*v[0] - axis[0]*v[2],
        axis[0]*v[1] - axis[1]*v[0]
    ]
    dot = vec_dot(axis, v)
    return [
        v[i]*cos_a + cross[i]*sin_a + axis[i]*dot*(1 - cos_a)
        for i in range(3)
    ]

class VoidSimSwapped:
    def __init__(self, root):
        self.root = root
        self.root.title("VOID_ENGINE // 6-DOF_NAV_CORE (SWAPPED)")
        self.root.configure(bg=BG_VOID)
        
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG_VOID, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Ship Orientation Vectors
        self.pos = [0, 0, 0]
        self.fwd = [0, 0, 1]
        self.up  = [0, 1, 0]
        self.right = [1, 0, 0]
        
        self.vel = 0
        self.thruster_on = False
        self.active_keys = set()
        
        # Generative Entities
        self.stars = [[random.uniform(-3000, 3000) for _ in range(3)] for _ in range(250)]
        self.planets = [{"p": [random.uniform(-5000, 5000) for _ in range(3)], 
                         "s": random.randint(30, 80), 
                         "c": random.choice(["@", "O", "#"])} for _ in range(5)]

        self.root.bind("<KeyPress>", lambda e: self.active_keys.add(e.keysym.lower()))
        self.root.bind("<KeyRelease>", lambda e: self.active_keys.discard(e.keysym.lower()))
        self.root.bind("<space>", self.toggle_thruster)
        self.root.bind("f", self.toggle_fs)
        self.root.bind("<Escape>", lambda e: self.root.quit())

        self.loop()

    def toggle_thruster(self, e): self.thruster_on = not self.thruster_on
    def toggle_fs(self, e): self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def update_physics(self):
        turn_speed = 0.05
        
        # Pitch
        if 'w' in self.active_keys:
            self.fwd = rotate_vec(self.fwd, self.right, -turn_speed)
            self.up = rotate_vec(self.up, self.right, -turn_speed)
        if 's' in self.active_keys:
            self.fwd = rotate_vec(self.fwd, self.right, turn_speed)
            self.up = rotate_vec(self.up, self.right, turn_speed)
            
        # Yaw (SWAPPED: A -> RIGHT, D -> LEFT)
        if 'a' in self.active_keys: 
            self.fwd = rotate_vec(self.fwd, self.up, -turn_speed)
            self.right = rotate_vec(self.right, self.up, -turn_speed)
        if 'd' in self.active_keys: 
            self.fwd = rotate_vec(self.fwd, self.up, turn_speed)
            self.right = rotate_vec(self.right, self.up, turn_speed)
            
        # Roll
        if 'q' in self.active_keys:
            self.up = rotate_vec(self.up, self.fwd, turn_speed)
            self.right = rotate_vec(self.right, self.fwd, turn_speed)
        if 'e' in self.active_keys:
            self.up = rotate_vec(self.up, self.fwd, -turn_speed)
            self.right = rotate_vec(self.right, self.fwd, -turn_speed)

        # Strafe Movement (Arrow Keys)
        move_speed = 20
        if 'up' in self.active_keys: self.pos = vec_add(self.pos, vec_mul(self.up, move_speed))
        if 'down' in self.active_keys: self.pos = vec_add(self.pos, vec_mul(self.up, -move_speed))
        if 'left' in self.active_keys: self.pos = vec_add(self.pos, vec_mul(self.right, -move_speed))
        if 'right' in self.active_keys: self.pos = vec_add(self.pos, vec_mul(self.right, move_speed))

        # Velocity Logic
        target_vel = 60 if self.thruster_on else 0
        self.vel += (target_vel - self.vel) * 0.08
        self.pos = vec_add(self.pos, vec_mul(self.fwd, self.vel))

    def project(self, world_pos):
        rel = vec_sub(world_pos, self.pos)
        lx = vec_dot(rel, self.right)
        ly = vec_dot(rel, self.up)
        lz = vec_dot(rel, self.fwd)

        if lz < 15: return None
        
        factor = 700 / lz
        sx = (WIDTH / 2) + (lx * factor)
        sy = (HEIGHT / 2) - (ly * factor)
        return sx, sy, factor

    def draw(self):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()

        # Render Stars
        for s in self.stars:
            res = self.project(s)
            if res:
                sx, sy, f = res
                char = "*" if f > 0.8 else "."
                self.canvas.create_text(sx, sy, text=char, fill=COLOR_AMBER)

        # Render Generative Planets
        for p in self.planets:
            res = self.project(p["p"])
            if res:
                sx, sy, f = res
                size = int(p["s"] * f * 0.1)
                if size > 1:
                    self.canvas.create_text(sx, sy, text=p["c"] * (size//2), 
                                           fill=COLOR_AMBER, font=("Courier", size, "bold"))

        # HUD Overlay
        thruster_label = "[ THRUST: ON ]" if self.thruster_on else "[ THRUST: OFF ]"
        self.canvas.create_text(w/2, h-60, 
                                text=f"{thruster_label} | VELOCITY: {int(self.vel)} | YAW: SWAPPED", 
                                fill=COLOR_GLOW, font=("Courier", 11))
        
        # Crosshair HUD
        self.canvas.create_text(w/2, h/2, text="--[ + ]--", fill=COLOR_GLOW, font=("Courier", 14))

    def loop(self):
        self.update_physics()
        self.draw()
        self.root.after(1000 // FPS, self.loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = VoidSimSwapped(root)
    root.mainloop()

