#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OMNI VOID ENGINE 3 — single-file zero-dependency offline Python/tkinter.

Three pure archived GFX engines, surgically merged:
  CybervoidFusion      -> ON FOOT/BOARD : dir/plane DDA raycaster, look L/R/U/D,
                          emitter turret (SPACE or LMB), particles, powerups, sprites
  Phos City Night Drive-> IN VEHICLE    : full Phos City renderer with windowed buildings,
                          road-lane floor-cast, cabin pitch, shake — auto-swaps on enter
  Void Space Sim       -> IN SPACE      : 6-DOF chunk-starfield cosmos

GFX swaps automatically:
  FOOT / BOARD  -> CybervoidFusion dir/plane raycaster  (true L/R look)
  VEHICLE       -> Phos City renderer  (NOT on enemy ships)
  SPACE         -> Void Space cosmos

Minimap (ground): V = vehicle rect, S = spaceship (tall rect)
Vehicles on all planets. Emitter always accessible.

Controls:
  FOOT/BOARD: WASD move/strafe  L/R turn  UP/DN pitch  SHIFT sprint  V jump
              SPACE/LMB emitter (beam, confuse->pacify)
              E = enter vehicle | LAUNCH spaceship | use terminal | exit vehicle
  VEHICLE:    W/S throttle  A/D steer  SHIFT boost  E exit
  SPACE:      WASD pitch/yaw  Q/E roll  arrows strafe  SPACE thrust  B boost
              F land  G board ship  M music  R sfx  ESC quit
"""

import tkinter as tk
import math,random,time,threading,array,io,wave,subprocess,tempfile

# ================================================================ CONFIG
WORLD_SEED=42
GRID_W,GRID_H=140,44
SPACE_W,SPACE_H=1100,800
FPS=45
SR=22050
TAU=math.tau
BG="#000005";FG="#00ff88";WHITE="#ffffff"
AMBER="#ffb000";GLOW="#ffcc00";RED="#ff4444";DIM="#446644"

# Cell types
EMPTY=0;WALL=1;TERMINAL=2

# CybervoidFusion archived ramps
CV_RAMP_WALL ="@#$B%&W8MX*+=-:. "
CV_RAMP_FLOOR=".,`' "
CV_RAMP_CEIL =",-.'` "

# Phos City archived ramps / glyphs
PC_WIN_LIT="\u25a3";PC_WIN_DIM="\u25a2";PC_WIN_DARK="\u00b7";PC_WIN_BLIND="\u2630"

# Cosmos
STAR_GLYPHS=['.', '\u00b7', '*', '+', '\u00b0', "'", '`', '\u2726', '\u2605', '\u2606']
STAR_COLORS=["#ffffff","#aabbff","#ffddaa","#aaffff","#ffbbbb","#88aaff","#ffcc88","#ccddff","#ffb000","#88ffcc"]
PLANET_CHARS=["@","O","#","0","\u0398","\u2295","\u25ce","\u25cf"]
PLANET_COLORS=["#ff8844","#44aaff","#aaff88","#ffaa44","#ff44aa","#88ffff"]
COMET_CHARS=['@','%','#','*','+','\u00b7','.',' ']
COMET_COLORS=["#ffffff","#aaccff","#ffeeaa","#88ffff","#ffaa88"]
CHUNK_R,STARS_PER_CHUNK,COMET_POOL=4000,120,8
CITY,DUNGEON,WILDS,MOON=0,1,2,3
BIOME_NAMES={CITY:"PHOS CITY",DUNGEON:"VOID DUNGEON",WILDS:"OPEN WILDS",MOON:"MOON SURFACE"}

# CybervoidFusion enemy tables
ENEMY_CHARS=['Z','D','G','S','B','M']
ENEMY_HP   ={'Z':17,'D':17,'G':17,'S':17,'B':17,'M':17}
ENEMY_SPD  ={'Z':0.020,'D':0.015,'G':0.035,'S':0.010,'B':0.025,'M':0.020}
ENEMY_DMG  ={'Z':8,'D':5,'G':10,'S':4,'B':12,'M':7}
PU_TYPES=['SPEED_BOOST','SLOW_TIME','RAPID_FIRE']
PU_GLYPHS={'SPEED_BOOST':'>','SLOW_TIME':'~','RAPID_FIRE':'!'}
PU_LABELS={'SPEED_BOOST':'> SPEED x2','SLOW_TIME':'~ SLOW TIME','RAPID_FIRE':'! RAPID FIRE'}
PU_DUR=620
LAND_WORDS=["K-KLANNNG","THOOM","KRAKOOOM","WHUMPH","B-DONNNG","CRANNNG","CHONK","SKHRRRANG"]
MEDITATE=["Thank you","I'm finally free","I feel pure peace","I find stillness","[entering meditative state]"]

# ================================================================ AUDIO
def _detect_audio():
    try:import winsound;return"winsound"
    except Exception:pass
    for nm,probe in(("afplay",["which","afplay"]),("aplay",["aplay","--version"])):
        try:
            if subprocess.run(probe,capture_output=True).returncode==0:return nm
        except Exception:pass
    try:import ctypes;ctypes.windll.winmm;return"winmm"
    except Exception:return None

BACKEND=_detect_audio()

def _wave(freq,dur,amp=0.4,kind="sine"):
    n=int(SR*dur);fade=max(1,int(SR*0.05));out=[]
    for i in range(n):
        t=i/SR
        if kind=="sine":v=math.sin(TAU*freq*t)
        elif kind=="saw":v=2*((freq*t)%1)-1.0
        elif kind=="square":v=1.0 if math.sin(TAU*freq*t)>=0 else-1.0
        elif kind=="tri":p=(freq*t)%1;v=4*p-1 if p<0.5 else 3-4*p
        else:v=random.uniform(-1,1)
        out.append(int(max(-32767,min(32767,v*amp*32767*min(i,n-i,fade)/fade))))
    return array.array('h',out)

def _mix(*ws):
    if not ws:return array.array('h',[])
    L=max(len(w)for w in ws);n=len(ws);out=[]
    for i in range(L):
        s=sum(w[i]for w in ws if i<len(w))
        out.append(int(max(-32767,min(32767,s/n))))
    return array.array('h',out)

def _wav(s):
    b=io.BytesIO()
    with wave.open(b,'wb')as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(s.tobytes())
    return b.getvalue()

def _play(data):
    if not BACKEND or not data:return
    def _go():
        try:
            if BACKEND=="winsound":
                import winsound;winsound.PlaySound(data,winsound.SND_MEMORY|winsound.SND_ASYNC)
            elif BACKEND in("aplay","afplay"):
                tf=tempfile.NamedTemporaryFile(suffix=".wav",delete=False);tf.write(data);tf.close()
                subprocess.Popen(["aplay","-q",tf.name]if BACKEND=="aplay"else["afplay",tf.name],
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            elif BACKEND=="winmm":
                import ctypes;tf=tempfile.NamedTemporaryFile(suffix=".wav",delete=False)
                tf.write(data);tf.close()
                ctypes.windll.winmm.PlaySoundW(tf.name,None,0x00020001)
        except Exception:pass
    threading.Thread(target=_go,daemon=True).start()

class Audio:
    def __init__(self):
        self.music_on=self.sfx_on=bool(BACKEND);self.c={};self._run=False
        if BACKEND:threading.Thread(target=self._bake,daemon=True).start()
    def _bake(self):
        c=self.c
        try:
            c['drone']=_wav(_mix(_wave(40,3,.15),_wave(80,3,.08),_wave(120,3,.05,"tri"),_wave(.5,3,.03,"noise")))
            c['shimmer']=_wav(_mix(_wave(880,2,.04),_wave(1320,2,.02)))
            c['thruster']=_wav(_mix(_wave(60,1,.25,"saw"),_wave(.5,1,.15,"noise")))
            c['whoosh']=_wav(_mix(_wave(200,.5,.20,"noise"),_wave(100,.5,.10)))
            c['boost']=_wav(_mix(_wave(55,1.5,.30,"saw"),_wave(110,1.5,.20),_wave(220,1.5,.10,"tri")))
            # emitter: sweeping whoosh burst (CV style)
            c['gun']=_wav(_mix(_wave(1200,.08,.35,"saw"),_wave(600,.08,.20,"tri")))
            c['hit']=_wav(_wave(150,.10,.40))
            c['death']=_wav(_mix(_wave(100,.3,.30,"noise"),_wave(50,.3,.20)))
            c['pickup']=_wav(_wave(880,.10,.20))
            c['space_shot']=_wav(_wave(300,.20,.30,"saw"))
            c['engine']=_wav(_mix(_wave(90,.4,.20,"saw"),_wave(180,.4,.10,"saw")))
            c['step']=_wav(_wave(80,.06,.15,"noise"))
            c['jump']=_wav(_mix(_wave(200,.15,.20,"saw"),_wave(150,.15,.10)))
            c['land']=_wav(_mix(_wave(60,.25,.40,"noise"),_wave(40,.25,.30)))
            c['overheat']=_wav(_mix(_wave(400,.5,.25,"square"),_wave(200,.5,.15)))
            c['still']=_wav(_mix(_wave(440,.4,.25),_wave(550,.6,.15),_wave(330,.8,.10)))
            self._run=True;threading.Thread(target=self._loop,daemon=True).start()
        except Exception:pass
    def _loop(self):
        while self._run and self.music_on:
            try:_play(self.c.get('drone'));time.sleep(2.8)
            except Exception:time.sleep(1)
            if random.random()<0.4:
                try:_play(self.c.get('shimmer'));time.sleep(0.2)
                except Exception:pass
    def play(self,k):
        if self.sfx_on:_play(self.c.get(k))
    def toggle_music(self):
        self.music_on=not self.music_on
        if self.music_on and not self._run and self.c:
            self._run=True;threading.Thread(target=self._loop,daemon=True).start()
        elif not self.music_on:self._run=False
        return self.music_on
    def toggle_sfx(self):self.sfx_on=not self.sfx_on;return self.sfx_on
    def stop(self):self._run=False

# ================================================================ MATH
class V2:
    __slots__=('x','y')
    def __init__(self,x=0.,y=0.):self.x=float(x);self.y=float(y)
    def copy(self):return V2(self.x,self.y)

class V3:
    __slots__=('x','y','z')
    def __init__(self,x=0.,y=0.,z=0.):self.x,self.y,self.z=float(x),float(y),float(z)
    def __add__(self,o):return V3(self.x+o.x,self.y+o.y,self.z+o.z)
    def __sub__(self,o):return V3(self.x-o.x,self.y-o.y,self.z-o.z)
    def __mul__(self,s):return V3(self.x*s,self.y*s,self.z*s)
    def dot(self,o):return self.x*o.x+self.y*o.y+self.z*o.z
    def length(self):return math.sqrt(self.x**2+self.y**2+self.z**2)
    def normalize(self):m=self.length();return V3(0,0,1)if m<1e-9 else V3(self.x/m,self.y/m,self.z/m)

def vdot(a,b):return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def vsub(a,b):return[a[0]-b[0],a[1]-b[1],a[2]-b[2]]
def vadd(a,b):return[a[0]+b[0],a[1]+b[1],a[2]+b[2]]
def vmul(v,s):return[v[0]*s,v[1]*s,v[2]*s]
def vnorm(v):
    m=math.sqrt(v[0]**2+v[1]**2+v[2]**2)
    return[v[0]/m,v[1]/m,v[2]/m]if m>1e-9 else[0,0,1]
def rodrigues(v,axis,ang):
    c,s=math.cos(ang),math.sin(ang)
    cr=[axis[1]*v[2]-axis[2]*v[1],axis[2]*v[0]-axis[0]*v[2],axis[0]*v[1]-axis[1]*v[0]]
    d=vdot(axis,v);return[v[i]*c+cr[i]*s+axis[i]*d*(1-c)for i in range(3)]

# ================================================================ PHOS CITY WALL TEXTURE (archived)
def _pch(*a):h=hash(a)&0xffffffff;return((h*2654435761)&0xffffffff)/4294967296.0

def _pc_glyph(variant,u,v,wx,wy,fog):
    if variant==1:cols,rows,lit=5,9,0.30
    elif variant==2:cols,rows,lit=4,16,0.42
    elif variant==3:cols,rows,lit=7,18,0.55
    else:cols,rows,lit=6,12,0.35
    cu=int(u*cols);cv_=int(v*rows);fu=(u*cols)-cu;fv=(v*rows)-cv_
    in_w=fu>0.12 and fu<0.88 and fv>0.18 and fv<0.82
    if cv_==rows-1 and cu==cols//2 and in_w:
        return('\u25ae',max(0.55,0.88-fog*0.4))if fv>0.28 else('\u2550',max(0.45,0.75-fog*0.4))
    if not in_w:
        if fog<0.22:return('\u2588',max(0.55,0.95-fog*0.5))
        elif fog<0.48:return('\u2593',max(0.40,0.78-fog*0.5))
        elif fog<0.72:return('\u2592',max(0.22,0.55-fog*0.4))
        else:return('\u2591',max(0.10,0.32-fog*0.3))
    rs=_pch(wx,wy,cu,cv_,variant);is_lit=rs<lit;bl=(rs*17.0)%1.0<0.18
    if is_lit:
        it=max(0.55,0.95-fog*0.30)
        if bl:return(PC_WIN_BLIND,it*0.85)
        return(PC_WIN_LIT,it)if(rs*13.0)%1.0<0.40 else('\u25a1',it*0.92)
    return(PC_WIN_DARK,max(0.10,0.30-fog*0.3))

# ================================================================ CV SPRITES + PARTICLES (archived)
_EP=['(o o)','(@ @)','(x x)','(* *)','(> <)','[o_o]','<o-o>','(0 0)','(^ ^)']
_HP=['ZZZ','DDD','GGG','///','###','XXX','|||','~~~']
_TL=['<|','[|','\\|','{|','=|','!|'];_TR=['|>','|]','|/','|}','|=','|!']
_LP=['/ \\ ','|_| ','\\|/ ','/_\\ ','(_) ','||| ']
_AL=['/','\\','|','<','{','['];_AR=['\\','/','|','>','}',']']
_FC='#@$%&*+=~-|.:^';_CO=['  x x  ','  |||  ','  ---  ','       ']
_SC={}

def _mksprite(seed):
    r=random.Random(seed);w=8
    return[f' {r.choice(_FC)}{r.choice(_HP)}{r.choice(_FC)} '[:w].ljust(w),
           f'  {r.choice(_EP)}  '[:w].ljust(w),
           f' {r.choice(_AL)}{r.choice(_TL)[1:]}{r.choice(_TR)[:-1]}{r.choice(_AR)} '[:w].ljust(w),
           f'  {r.choice(_LP)}  '[:w].ljust(w)]

def _sprite_rows(char,flash=False,eid=None):
    if char=='%':rows=_CO
    else:
        k=eid if eid is not None else id(char)
        if k not in _SC:_SC[k]=_mksprite(k^(ord(char)*7919))
        rows=_SC[k]
    return[' *'+r[2:]for r in rows]if flash else rows

class Particle:
    __slots__=('bx','by','ch','life','vx','vy')
    def __init__(self,bx,by,ch,life):
        self.bx=bx;self.by=by;self.ch=ch;self.life=life
        self.vx=random.choice([-1,0,0,1]);self.vy=random.choice([-1,0,0,1])

class Particles:
    def __init__(self):self.p=[]
    def emit(self,bx,by,kind='spark',n=4):
        cs={'spark':'*+.','blood':'#@.','smoke':'.,:','gore':'$%#'}.get(kind,'*')
        for _ in range(n):
            self.p.append(Particle(bx+random.randint(-3,3),by+random.randint(-2,2),
                                   random.choice(cs),random.randint(4,10)))
    def update(self):
        a=[]
        for p in self.p:
            p.life-=1;p.bx+=p.vx;p.by+=p.vy
            if p.life>0:a.append(p)
        self.p=a
    def draw(self,buf,W,H):
        for p in self.p:
            if 0<=int(p.bx)<W and 0<=int(p.by)<H:buf[int(p.by)][int(p.bx)]=p.ch

class PUSpawner:
    """CybervoidFusion archived powerup spawner with plane-projection draw."""
    def __init__(self):self.items=[]
    def spawn_near(self,cx,cy,router):
        for _ in range(40):
            a=random.uniform(0,TAU);r=random.uniform(3,10)
            x=cx+math.cos(a)*r;y=cy+math.sin(a)*r
            if router.is_open(x,y):self.items.append([x,y,random.choice(PU_TYPES),900]);return
    def update(self):self.items=[[x,y,t,f-1]for x,y,t,f in self.items if f>0]
    def check(self,px,py):
        for it in self.items:
            if math.hypot(it[0]-px,it[1]-py)<1.1:self.items.remove(it);return it[2]
        return None
    def draw(self,buf,cam,zbuf,W,H):
        for x,y,t,_ in self.items:
            dx=x-cam.pos.x;dy=y-cam.pos.y
            inv=cam.plane.x*cam.dir.y-cam.dir.x*cam.plane.y
            if abs(inv)<1e-9:continue
            inv=1.0/inv
            tX=inv*(cam.dir.y*dx-cam.dir.x*dy);tY=inv*(-cam.plane.y*dx+cam.plane.x*dy)
            if tY<0.3:continue
            sx=int(W/2*(1+tX/tY));sz=max(1,abs(int(H/tY)))
            x0=max(0,sx-sz//4);x1=min(W-1,sx+sz//4)
            y0=max(0,H//2-sz//2);y1=min(H-1,H//2+sz//2)
            zi=max(0,min(W-1,sx))
            if tY<zbuf[zi]:
                g=PU_GLYPHS.get(t,'?')
                for by in range(y0,y1):
                    for bx in range(x0,x1):
                        if 0<=bx<W and 0<=by<H:buf[by][bx]=g

# ================================================================ ROUTERS
class CityRouter:
    STRIDE,STREET=12,2
    def __init__(self,seed=WORLD_SEED):self.seed=seed;self.name=BIOME_NAMES[CITY]
    def get_cell(self,x,y):
        ix,iy=int(math.floor(x)),int(math.floor(y))
        rx,ry=ix%self.STRIDE,iy%self.STRIDE
        if rx<self.STREET or rx>=self.STRIDE-self.STREET:return EMPTY
        if ry<self.STREET or ry>=self.STRIDE-self.STREET:return EMPTY
        rng=random.Random(hash((ix,iy,self.seed)))
        for _ in range(3):
            ox,oy=rng.randint(-4,4),rng.randint(-4,4)
            if abs(rx-6-ox)<2 and abs(ry-6-oy)<2:return EMPTY
        if ix%24==6 and iy%24==6:return TERMINAL
        return WALL
    def is_open(self,x,y):return self.get_cell(x,y)!=WALL

class PhosCityRouter:
    """Phos City archived router — vehicle mode (richer building variants)."""
    BLOCK_STRIDE=12;STREET_HALF=2
    def __init__(self,seed=WORLD_SEED):self.seed=seed;self.name=BIOME_NAMES[CITY]
    def get_cell(self,x,y):
        cx=int(math.floor(x));cy=int(math.floor(y))
        rx=cx%self.BLOCK_STRIDE;ry=cy%self.BLOCK_STRIDE
        if rx<self.STREET_HALF or rx>=self.BLOCK_STRIDE-self.STREET_HALF:return 0
        if ry<self.STREET_HALF or ry>=self.BLOCK_STRIDE-self.STREET_HALF:return 0
        bk=(cx//self.BLOCK_STRIDE,cy//self.BLOCK_STRIDE,self.seed)
        return 1+((hash(bk)&0x7fffffff)%4)
    def is_open(self,x,y):return self.get_cell(x,y)==0

class DungeonRouter:
    def __init__(self,seed=WORLD_SEED):self.seed=seed;self.name=BIOME_NAMES[DUNGEON];self._c={}
    def _n(self,x,y,sc):return(hash((int(x/sc),int(y/sc),self.seed))&0xffff)/0xffff
    def get_cell(self,x,y):
        ix,iy=int(math.floor(x)),int(math.floor(y));k=(ix,iy)
        if k in self._c:return self._c[k]
        v=self._n(ix,iy,6.0)*0.7+self._n(ix,iy,2.0)*0.3
        c=EMPTY if v>0.45 else WALL
        if v>0.85 and(ix+iy)%17==0:c=TERMINAL
        if len(self._c)>8000:self._c.clear()
        self._c[k]=c;return c
    def is_open(self,x,y):return self.get_cell(x,y)!=WALL

class WildsRouter:
    def __init__(self,seed=WORLD_SEED):self.seed=seed;self.name=BIOME_NAMES[WILDS]
    def get_cell(self,x,y):
        h=hash((int(math.floor(x)),int(math.floor(y)),self.seed))&0x7fffffff
        if h%113==0:return WALL
        if h%1019==0:return TERMINAL
        return EMPTY
    def is_open(self,x,y):return self.get_cell(x,y)!=WALL

class MoonRouter:
    def __init__(self,seed=WORLD_SEED):self.seed=seed;self.name=BIOME_NAMES[MOON]
    def get_cell(self,x,y):
        ix,iy=int(math.floor(x)),int(math.floor(y))
        rng=random.Random(hash((ix//16,iy//16,self.seed)))
        for _ in range(3):
            cx2=(ix//16)*16+rng.randint(2,13);cy2=(iy//16)*16+rng.randint(2,13)
            r=rng.randint(2,5)
            if abs((ix-cx2)**2+(iy-cy2)**2-r*r)<r:return WALL
        if hash((ix,iy,self.seed))%2003==0:return TERMINAL
        return EMPTY
    def is_open(self,x,y):return self.get_cell(x,y)!=WALL

class ShipRouter:
    """Enemy ship interior — no vehicle GFX swap here."""
    W,H=60,30
    def __init__(self,sid):
        rng=random.Random((sid*31337)^0xCAFEBABE)
        g=[[WALL]*self.W for _ in range(self.H)];sy=self.H//2
        self.name="ENEMY SHIP"
        for x in range(2,self.W-2):g[sy][x]=g[sy-1][x]=g[sy+1][x]=EMPTY
        for _ in range(rng.randint(4,7)):
            rw,rh=rng.randint(4,8),rng.randint(3,5);rx2=rng.randint(3,self.W-rw-3)
            top=rng.choice([True,False]);ry2=max(2,sy-2-rh)if top else min(self.H-rh-2,sy+2)
            for yy in range(ry2,ry2+rh):
                for xx in range(rx2,rx2+rw):g[yy][xx]=EMPTY
            dx2=rx2+rw//2
            lo,hi=(ry2+rh,sy-1)if top else(sy+2,ry2)
            for yy in range(lo,hi):g[yy][dx2]=EMPTY
        g[sy][self.W-4]=TERMINAL
        self.grid=g;self.spawn_x,self.spawn_y=3.5,sy+0.5
    def get_cell(self,x,y):
        ix,iy=int(math.floor(x)),int(math.floor(y))
        return self.grid[iy][ix]if 0<=ix<self.W and 0<=iy<self.H else WALL
    def is_open(self,x,y):return self.get_cell(x,y)!=WALL

def biome_for(seed):return abs(hash((seed,'biome')))%4
def make_router(biome,seed):
    return{CITY:CityRouter,DUNGEON:DungeonRouter,WILDS:WildsRouter,MOON:MoonRouter}[biome](seed)
def make_veh_router(biome,seed):
    return PhosCityRouter(seed)if biome==CITY else make_router(biome,seed)

# ================================================================ COSMOS
class StarChunk:
    __slots__=('stars',)
    def __init__(self,key):
        rng=random.Random(hash(key)^0xDEADBEEF);cx,cy,cz=[k*CHUNK_R*2 for k in key];self.stars=[]
        for _ in range(STARS_PER_CHUNK):
            phi=rng.uniform(0,TAU);ct=rng.uniform(-1,1);st=math.sqrt(1-ct*ct)
            r=rng.uniform(CHUNK_R*0.2,CHUNK_R)
            self.stars.append((cx+r*st*math.cos(phi),cy+r*ct,cz+r*st*math.sin(phi),
                               rng.choice(STAR_GLYPHS),rng.choice(STAR_COLORS),
                               rng.choice([8,9,10,11,12])))

class StarField:
    def __init__(self,cap=200):self._c={};self._cap=cap
    def _key(self,p):return tuple(int(math.floor(v/(CHUNK_R*2)))for v in p)
    def near(self,pos):
        cx,cy,cz=self._key(pos);stars=[]
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                for dz in(-1,0,1):
                    k=(cx+dx,cy+dy,cz+dz)
                    if k not in self._c:
                        if len(self._c)>self._cap:
                            far=max(self._c,key=lambda q:(q[0]-cx)**2+(q[1]-cy)**2+(q[2]-cz)**2)
                            del self._c[far]
                        self._c[k]=StarChunk(k)
                    stars.extend(self._c[k].stars)
        return stars

class Comet:
    def __init__(self,pp,pf):
        sp=3000;self.age=0
        self.pos=[pp[i]+pf[i]*4000+random.uniform(-sp,sp)for i in range(3)]
        s=random.uniform(30,120);self.vel=[random.uniform(-s,s)for _ in range(3)]
        self.tail_len=random.randint(5,14);self.tail=[]
        self.color=random.choice(COMET_COLORS);self.max_age=random.randint(120,400)
    def update(self):
        self.tail.insert(0,list(self.pos))
        if len(self.tail)>self.tail_len:self.tail.pop()
        self.pos=vadd(self.pos,self.vel);self.age+=1
    def alive(self):return self.age<self.max_age

class PlanetField:
    def __init__(self,n=20):
        rng=random.Random(WORLD_SEED);self.planets=[]
        for i in range(n):
            s=rng.randint(0,10**9)
            self.planets.append({"id":i,"seed":s,"pos":[rng.uniform(-40000,40000)for _ in range(3)],
                                 "size":rng.randint(40,150),"char":rng.choice(PLANET_CHARS),
                                 "color":rng.choice(PLANET_COLORS),"rot":rng.uniform(0,TAU),
                                 "rot_spd":rng.uniform(-0.02,0.02),"biome":biome_for(s)})
    def update(self):
        for p in self.planets:p["rot"]+=p["rot_spd"]
    def nearest(self,pos,md=600):
        best,bd=None,md
        for p in self.planets:
            d=math.sqrt(sum((p["pos"][i]-pos[i])**2 for i in range(3)))
            if d<bd:bd,best=d,p
        return best

# ================================================================ ENTITIES
class CVEntity:
    """CybervoidFusion archived entity: full confusion/pacify state machine."""
    __slots__=('x','y','char','hp','speed','dmg','state','flash','dead_timer','attack_cd',
               'eid','confusion','wander_dir','wander_t','pacified','pacify_t',
               'wander_nt','shake_freq','msg_text','msg_t','newly_pacified')
    def __init__(self,x,y,char='Z'):
        self.x=float(x);self.y=float(y);self.char=char
        self.hp=ENEMY_HP.get(char,3);self.speed=ENEMY_SPD.get(char,0.02)
        self.dmg=ENEMY_DMG.get(char,8);self.state='IDLE'
        self.flash=0;self.dead_timer=0;self.attack_cd=0
        self.eid=random.randint(1,0xFFFFFF)
        self.confusion=0;self.wander_dir=random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.wander_t=0;self.pacified=False;self.pacify_t=0
        self.wander_nt=random.uniform(0,100);self.shake_freq=random.uniform(0.08,0.15)
        self.msg_text="";self.msg_t=0;self.newly_pacified=False
    def alive(self):return self.state!='DEAD'
    def update(self,cam,router):
        if self.state=='DEAD':self.dead_timer-=1;return
        if self.pacified:self._wander_peaceful(router);
        if self.msg_t>0:self.msg_t-=1
        else:self.msg_text=""
        if self.flash>0:self.flash-=1
        if self.attack_cd>0:self.attack_cd-=1
        if self.pacified:return
        dx=cam.pos.x-self.x;dy=cam.pos.y-self.y;dist=math.hypot(dx,dy)
        if self.confusion>0:
            self.confusion-=1
            if self.confusion==0 and not self.pacified:
                self.pacify_t+=1
                if self.pacify_t>=600:
                    self.pacified=True;self.newly_pacified=True;self.state='IDLE'
                    self.msg_text=random.choice(MEDITATE);self.msg_t=180
            self._wander_confused(router)
        elif dist<18:
            self.state='CHASE';a=math.atan2(dy,dx)
            nx2=self.x+math.cos(a)*self.speed;ny2=self.y+math.sin(a)*self.speed
            if router.is_open(nx2,self.y):self.x=nx2
            if router.is_open(self.x,ny2):self.y=ny2
        if dist<1.2 and self.attack_cd<=0:
            cam.health-=self.dmg;self.attack_cd=45
    def _wander_confused(self,router):
        self.wander_nt+=0.05;nd=self.wander_nt
        dx=math.sin(nd*1.3+self.shake_freq)*0.7+math.cos(nd*0.7)*0.3
        dy=math.cos(nd*1.1+self.shake_freq)*0.7+math.sin(nd*0.9)*0.3
        sp=self.speed*0.6
        if router.is_open(self.x+dx*sp,self.y):self.x+=dx*sp
        if router.is_open(self.x,self.y+dy*sp):self.y+=dy*sp
    def _wander_peaceful(self,router):
        self.wander_t-=1
        if self.wander_t<=0:
            self.wander_dir=random.choice([(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)])
            self.wander_t=random.randint(20,60)
        dx,dy=self.wander_dir;sp=self.speed*0.4
        if router.is_open(self.x+dx*sp,self.y):self.x+=dx*sp
        else:self.wander_dir=(-dx,dy);self.wander_t=0
        if router.is_open(self.x,self.y+dy*sp):self.y+=dy*sp
        else:self.wander_dir=(dx,-dy);self.wander_t=0
    def hit(self,_=1):
        if self.pacified:return
        self.confusion=min(self.confusion+180,600);self.flash=8
        if self.confusion>=600:
            self.pacified=True;self.newly_pacified=True;self.state='IDLE'
            self.msg_text=random.choice(MEDITATE);self.msg_t=180

class SpaceEnemy:
    def __init__(self,x,y,z,eid):
        self.pos=V3(x,y,z);self.hp=self.max_hp=40;self.alive_flag=True
        self.fire_cd=0.0;self.eid=eid
    def update(self,ppos,dt):
        if not self.alive_flag:return
        to=ppos-self.pos;dist=to.length()
        if dist>0.1:self.pos=self.pos+to.normalize()*(50.0*dt)
        self.fire_cd=max(0.0,self.fire_cd-dt)
        if dist<300 and self.fire_cd<=0:self.fire_cd=random.uniform(1.0,2.0)
    def take_damage(self,d):
        self.hp-=d
        if self.hp<=0:self.alive_flag=False
    def alive(self):return self.alive_flag

# ================================================================ CAMERAS
class CVCamera:
    """CybervoidFusion archived dir/plane vector camera — true L/R look."""
    def __init__(self,x=10.5,y=10.5):
        self.pos=V2(x,y)
        self.dir=V2(-1.,0.)      # direction vector
        self.plane=V2(0.,0.66)   # camera plane (FOV ~66deg)
        self.pitch=0.;self.bob=0.;self.bob_phase=0.
        self.health=100;self.max_health=100
        self.shield=50;self.max_shield=50
        self.jump_vel=0.0;self.jump_off=0.0;self.jumping=False;self.landed=False
        self.shake_amp=0.0;self.shake_frames=0
    def rotate(self,spd):
        c,s=math.cos(spd),math.sin(spd)
        dx,dy=self.dir.x,self.dir.y
        self.dir.x=dx*c+dy*s;self.dir.y=-dx*s+dy*c
        px,py=self.plane.x,self.plane.y
        self.plane.x=px*c+py*s;self.plane.y=-px*s+py*c
    def step_bob(self,moving):
        if moving:self.bob_phase+=0.18;self.bob=math.sin(self.bob_phase)*2.0
        else:self.bob*=0.85
    def land_shake(self,amp=6.0,frames=14):self.shake_amp,self.shake_frames=amp,frames
    def update_shake(self):
        if self.shake_frames<=0:self.shake_amp=0.0;return 0.0
        self.shake_frames-=1;decay=self.shake_frames/14.0
        off=(random.random()*2-1)*self.shake_amp*decay;self.shake_amp*=0.78;return off
    def jump(self):
        if not self.jumping:self.jump_vel=2.8;self.jumping=True;self.landed=False
    def update_jump(self):
        if not self.jumping:self.landed=False;return False
        self.jump_vel-=(0.055 if self.jump_vel>0 else 0.0932)
        self.jump_off+=self.jump_vel
        if self.jump_off<=0 and self.jump_vel<0:
            self.jump_off=self.jump_vel=0.0;self.jumping=False;self.landed=True;return True
        self.landed=False;return False
    def take_damage(self,dmg):
        rem=dmg
        if self.shield>0:t=min(self.shield,rem);self.shield-=t;rem-=t
        if rem>0:self.health-=rem
        return self.health<=0
    def heal(self,n):self.health=min(self.max_health,self.health+n)
    def restore_shield(self,n):self.shield=min(self.max_shield,self.shield+n)

class DrivingCamera:
    """Phos City archived driving camera — pure split update()/step() like the source."""
    RPM_IDLE=1100.;RPM_REDLINE=6800.;N_GEARS=6
    MAX_FWD=11.;MAX_REV=-3.5;ACCEL=7.;BRAKE=14.;DRAG=1.6;STEER=2.6
    def __init__(self,x=10.5,y=10.5,angle=0.0):
        self.x,self.y,self.angle=x,y,angle
        self.speed=self.angular_v=0.0;self.fov=math.pi/2.6
        self.shake=0.;self.hp_y=0.;self.gear=1;self._idle=0.
        self.health=100
    @property
    def rpm(self):
        sf=max(0.,self.speed)/self.MAX_FWD
        if sf<0.0015:self._idle+=0.06;return self.RPM_IDLE+60.*math.sin(self._idle)
        g=max(1,min(self.N_GEARS,1+int(sf*self.N_GEARS)));self.gear=g
        gl=(g-1)/self.N_GEARS;gh=g/self.N_GEARS
        return self.RPM_IDLE+(self.RPM_REDLINE-self.RPM_IDLE)*(sf-gl)/max(0.001,gh-gl)
    def update(self,dt,throttle,brake,steer,boost):
        """Physics only — no position change. Matches Phos City Camera.update() exactly."""
        mf=self.MAX_FWD*(1.45 if boost else 1.)
        if throttle>0:
            hr=max(0.,1.-self.speed/mf)if self.speed>0 else 1.
            self.speed+=self.ACCEL*throttle*hr*dt*(1.5 if boost else 1.)
        if brake>0:
            if self.speed>0:self.speed=max(self.speed-self.BRAKE*brake*dt,-0.5)
            else:self.speed=max(self.speed-self.ACCEL*.5*brake*dt,self.MAX_REV)
        if not throttle and not brake:
            self.speed=(max(0.,self.speed-self.DRAG*dt)if self.speed>0
                        else min(0.,self.speed+self.DRAG*dt))
        self.speed=max(self.MAX_REV,min(mf,self.speed))
        sf=abs(self.speed)/self.MAX_FWD;auth=0.55+0.45*(1.-sf*.5)
        self.angular_v=steer*self.STEER*auth*((0.4+0.6*sf)if abs(self.speed)>0.2 else 0.)
        self.angle+=self.angular_v*dt
        tgt=-0.15 if(throttle and self.speed>.5)else(.20 if brake and self.speed>.5 else 0.)
        self.hp_y+=(tgt-self.hp_y)*min(1.,6.*dt)
    def step(self,dt,router):
        """Position integration with collision — Phos City Camera.step() archived exactly."""
        dx=math.cos(self.angle)*self.speed*dt;dy=math.sin(self.angle)*self.speed*dt
        nx=self.x+dx
        if router.is_open(nx+(0.18 if dx>0 else-0.18),self.y):self.x=nx
        else:self.shake=min(1.,self.shake+0.6);self.speed*=0.4
        ny=self.y+dy
        if router.is_open(self.x,ny+(0.18 if dy>0 else-0.18)):self.y=ny
        else:self.shake=min(1.,self.shake+0.6);self.speed*=0.4
        self.shake*=max(0.,1.-4.*dt)

class SpacecraftCamera:
    def __init__(self,x=0.,y=0.,z=0.):
        self.pos=[x,y,z];self.fwd=[0.,0.,1.];self.up=[0.,1.,0.];self.right=[1.,0.,0.]
        self.vel=0.;self.thruster_on=self.boost_on=False;self.boost_fuel=100.
        self.health=150;self.max_health=150;self.shield=100;self.max_shield=100
    def reortho(self):
        self.fwd=vnorm(self.fwd);self.right=vnorm(self.right)
        self.up=vnorm([self.fwd[1]*self.right[2]-self.fwd[2]*self.right[1],
                       self.fwd[2]*self.right[0]-self.fwd[0]*self.right[2],
                       self.fwd[0]*self.right[1]-self.fwd[1]*self.right[0]])
        self.right=vnorm([self.up[1]*self.fwd[2]-self.up[2]*self.fwd[1],
                          self.up[2]*self.fwd[0]-self.up[0]*self.fwd[2],
                          self.up[0]*self.fwd[1]-self.up[1]*self.fwd[0]])
    def update(self,dt,keys):
        ts=0.045
        if'w'in keys:self.fwd=rodrigues(self.fwd,self.right,-ts);self.up=rodrigues(self.up,self.right,-ts)
        if's'in keys:self.fwd=rodrigues(self.fwd,self.right,ts);self.up=rodrigues(self.up,self.right,ts)
        if'a'in keys:self.fwd=rodrigues(self.fwd,self.up,-ts);self.right=rodrigues(self.right,self.up,-ts)
        if'd'in keys:self.fwd=rodrigues(self.fwd,self.up,ts);self.right=rodrigues(self.right,self.up,ts)
        if'q'in keys:self.up=rodrigues(self.up,self.fwd,ts);self.right=rodrigues(self.right,self.fwd,ts)
        if'e'in keys:self.up=rodrigues(self.up,self.fwd,-ts);self.right=rodrigues(self.right,self.fwd,-ts)
        ms=25.
        if'up'in keys:self.pos=vadd(self.pos,vmul(self.up,ms))
        if'down'in keys:self.pos=vadd(self.pos,vmul(self.up,-ms))
        if'left'in keys:self.pos=vadd(self.pos,vmul(self.right,-ms))
        if'right'in keys:self.pos=vadd(self.pos,vmul(self.right,ms))
        bm=4. if self.boost_on else 1.
        target=(320. if self.boost_on else 80.*bm)if self.thruster_on else 0.
        self.vel+=(target-self.vel)*0.07
        self.pos=vadd(self.pos,vmul(self.fwd,self.vel))
        if self.boost_on and self.boost_fuel>0:
            self.boost_fuel=max(0.,self.boost_fuel-60.*dt)
            if self.boost_fuel<=0:self.boost_on=False
        elif self.boost_fuel<100.:self.boost_fuel=min(100.,self.boost_fuel+20.*dt)
    def take_damage(self,d):
        r=d
        if self.shield>0:t=min(self.shield,r);self.shield-=t;r-=t
        if r>0:self.health-=r
        return self.health<=0
    def pos_v3(self):return V3(*self.pos)

# ================================================================ PLAYER
class Player:
    FOOT,VEHICLE,SPACE,BOARD='foot','vehicle','space','board'
    def __init__(self):
        self.mode=self.SPACE
        self.cv=CVCamera();self.veh=DrivingCamera();self.craft=SpacecraftCamera()
        # emitter state
        self.heat=0.;self.overheated=False
        self.powerups={k:0 for k in PU_TYPES}
        self.land_word='';self.land_t=0
        # world
        self.entities=[];self.vehicles=[];self.terminals=[]
        self.pu_spawner=PUSpawner();self.particles=Particles();self.tracers=[]
        self.space_enemies=[];self._spawn_space_enemies()
        self.router=None;self.veh_router=None;self.planet=None;self.biome=None
        self.board_router=None;self.boarded=None
        self._stash_ent=[];self._stash_router=None
        self._step_cd=0;self._v_prev=False

    def _spawn_space_enemies(self):
        rng=random.Random(WORLD_SEED^0xBADF00D)
        self.space_enemies=[SpaceEnemy(rng.uniform(-2000,2000),rng.uniform(-2000,2000),
                                        rng.uniform(1000,4000),i)for i in range(6)]

    def _spawn_ground(self,planet,biome):
        rng=random.Random(planet["seed"])
        self.entities=[];self.vehicles=[];self.terminals=[]
        self.pu_spawner=PUSpawner();self.particles=Particles();self.tracers=[]
        count,kinds={DUNGEON:(12,['Z','D','G']),CITY:(8,['Z','G']),
                     WILDS:(6,['G','Z']),MOON:(4,['D'])}[biome]
        for _ in range(count):
            self.entities.append(CVEntity(rng.uniform(5,95),rng.uniform(5,95),rng.choice(kinds)))
        # Vehicles: many scattered, always present, fast — faster than sprint
        vcount=8 if biome!=DUNGEON else 5
        for i in range(vcount):
            self.vehicles.append({'id':i+1,'x':rng.uniform(6,94),'y':rng.uniform(6,94),
                                  'angle':rng.uniform(0,TAU),'kind':'vehicle'})
        # One stranded spaceship per planet — takeoff point (S on minimap)
        self.vehicles.append({'id':vcount+1,'x':rng.uniform(15,75),'y':rng.uniform(15,75),
                               'angle':rng.uniform(0,TAU),'kind':'ship'})
        for _ in range(4):
            self.terminals.append({'x':rng.uniform(8,90),'y':rng.uniform(8,90),'used':False})
        if self.router:
            self.pu_spawner.spawn_near(self.cv.pos.x,self.cv.pos.y,self.router)

    def land(self,planet):
        self.planet=planet;self.biome=planet["biome"]
        s=WORLD_SEED^planet["seed"]
        self.router=make_router(self.biome,s)
        self.veh_router=make_veh_router(self.biome,s)
        ox,oy=self._open_spawn(self.router)
        self.cv.pos=V2(ox,oy);self.cv.dir=V2(-1.,0.);self.cv.plane=V2(0.,0.66)
        self._spawn_ground(planet,self.biome);self.mode=self.FOOT

    def takeoff(self):
        if self.planet:
            p=self.planet
            self.craft.pos=[p["pos"][0]+p["size"]*4,p["pos"][1],p["pos"][2]]
            self.craft.fwd,self.craft.up,self.craft.right=[0.,0.,1.],[0.,1.,0.],[1.,0.,0.]
            self.craft.vel=0.;self.craft.thruster_on=self.craft.boost_on=False
        self.planet=self.biome=self.router=self.veh_router=None;self.mode=self.SPACE

    def enter_vehicle(self,vid):
        for v in self.vehicles:
            if v['id']==vid:
                self.veh.x,self.veh.y,self.veh.angle=v['x'],v['y'],v['angle']
                self.veh.speed=0.;self.mode=self.VEHICLE;return True
        return False

    def exit_vehicle(self):
        fx,fy=math.cos(self.veh.angle),math.sin(self.veh.angle)
        self.cv.pos=V2(self.veh.x+2.*fx,self.veh.y+2.*fy)
        # Align foot camera to vehicle heading
        self.cv.dir=V2(fx,fy);self.cv.plane=V2(-fy*0.66,fx*0.66)
        self.mode=self.FOOT

    def board_ship(self,enemy):
        self.board_router=ShipRouter(enemy.eid);self.boarded=enemy
        self.cv.pos=V2(self.board_router.spawn_x,self.board_router.spawn_y)
        self.cv.dir=V2(1.,0.);self.cv.plane=V2(0.,0.66)
        rng=random.Random(enemy.eid^0xBEEF);defenders=[]
        for _ in range(rng.randint(2,4)):
            defenders.append(CVEntity(rng.uniform(20,55),ShipRouter.H//2+rng.uniform(-1,1),'G'))
        self._stash_ent,self._stash_router=self.entities,self.router
        self.entities,self.router=defenders,self.board_router;self.mode=self.BOARD

    def disembark(self):
        self.entities,self.router=self._stash_ent,self._stash_router
        if self.boarded:self.boarded.alive_flag=False
        self.boarded=self.board_router=None;self.mode=self.SPACE

    def _open_spawn(self,router,default=(10.5,10.5)):
        for r in range(40):
            for t in range(16):
                a=t/16.*TAU;x,y=10.5+r*.5*math.cos(a),10.5+r*.5*math.sin(a)
                if router.is_open(x,y):return x,y
        return default

    def pos(self):
        if self.mode in(self.FOOT,self.BOARD):return self.cv.pos.x,self.cv.pos.y,0.
        if self.mode==self.VEHICLE:return self.veh.x,self.veh.y,0.
        return tuple(self.craft.pos)

    def nearest_vehicle(self):
        if not self.vehicles:return None
        px,py,_=self.pos()
        return min(self.vehicles,key=lambda v:(px-v['x'])**2+(py-v['y'])**2)

    def dist_terminal(self):
        if not self.terminals:return 1e9
        px,py,_=self.pos()
        return min(math.hypot(px-t['x'],py-t['y'])for t in self.terminals)

    def use_terminal(self):
        px,py,_=self.pos()
        for t in self.terminals:
            if math.hypot(px-t['x'],py-t['y'])<2. and not t['used']:
                t['used']=True;self.cv.heal(30);self.cv.restore_shield(50)
                self.heat=max(0.,self.heat-40.);return True
        return False

    def nearest_space_enemy(self,md=400):
        cp=self.craft.pos_v3();best,bd=None,md
        for e in self.space_enemies:
            if not e.alive():continue
            d=(e.pos-cp).length()
            if d<bd:bd,best=d,e
        return best

# ================================================================ RENDERERS

class CVRenderer:
    """CybervoidFusion archived DDA raycaster — dir/plane vector, true L/R look."""
    def __init__(self,W,H):self.W=W;self.H=H

    def render(self,player,router):
        cam=player.cv;W,H=self.W,self.H
        buf=[[' ']*W for _ in range(H)];zbuf=[1e9]*W
        eye=max(0.45,1.-cam.jump_off*0.16)
        voff=int(cam.pitch+cam.bob+cam.update_shake())

        # ceiling — CV archived sparse gradient
        for y in range(H//2):
            idx=min(len(CV_RAMP_CEIL)-1,int(len(CV_RAMP_CEIL)*y/(H//2)))
            c=CV_RAMP_CEIL[idx]
            if y%3==0:
                for x in range(0,W,4):buf[y][x]=c

        # DDA per column — CV archived dir/plane system
        for x in range(W):
            camX=2*x/W-1
            rDX=cam.dir.x+cam.plane.x*camX
            rDY=cam.dir.y+cam.plane.y*camX
            mX,mY=int(cam.pos.x),int(cam.pos.y)
            dDX=abs(1/rDX)if rDX else 1e30
            dDY=abs(1/rDY)if rDY else 1e30
            sX,sDX=(-1,(cam.pos.x-mX)*dDX)if rDX<0 else(1,(mX+1.-cam.pos.x)*dDX)
            sY,sDY=(-1,(cam.pos.y-mY)*dDY)if rDY<0 else(1,(mY+1.-cam.pos.y)*dDY)
            hit=side=cell=0;it=0
            while not hit and it<80:
                if sDX<sDY:sDX+=dDX;mX+=sX;side=0
                else:sDY+=dDY;mY+=sY;side=1
                cell=router.get_cell(mX,mY)
                if cell>0:hit=1
                it+=1
            pwd=((mX-cam.pos.x+(1-sX)/2)/rDX if side==0
                 else(mY-cam.pos.y+(1-sY)/2)/rDY)
            pwd=max(0.1,pwd);zbuf[x]=pwd
            lineH=int(H/(pwd*eye))
            dS=max(0,-lineH//2+H//2+voff);dE=min(H-1,lineH//2+H//2+voff)
            wc=CV_RAMP_WALL[min(len(CV_RAMP_WALL)-1,int(pwd*1.5))]
            if cell==TERMINAL:wc='$'
            if side==1 and wc not in'.,':wc=wc.lower()if wc.isalpha()else':'
            for y in range(dS,dE):buf[y][x]=wc
            for y in range(dE,H):
                fi=min(len(CV_RAMP_FLOOR)-1,int((y-H//2)/max(1,H//2)*(len(CV_RAMP_FLOOR)-1)))
                if(x+y)%4==0:buf[y][x]=CV_RAMP_FLOOR[fi]

        # sprites — CV archived multi-row sorted by dist
        live=[e for e in player.entities if e.alive()or e.dead_timer>0]
        for ent in sorted(live,key=lambda e:(cam.pos.x-e.x)**2+(cam.pos.y-e.y)**2,reverse=True):
            self._cv_sprite(buf,zbuf,cam,ent,voff,W,H)

        # vehicles as simple sprites (foot mode only)
        if player.mode==Player.FOOT:
            for v in player.vehicles:
                self._simple_sprite(buf,zbuf,cam,v['x'],v['y'],
                                    'S'if v['kind']=='ship'else'V',voff,W,H)

        # powerup pickups
        player.pu_spawner.draw(buf,cam,zbuf,W,H)
        # particles
        player.particles.draw(buf,W,H)
        # emitter beam — CV archived: downward jitter beam, life controls length
        for t in player.tracers:
            bx,by,life=t
            for dy in range(min(life,H-by)):
                ry=by+dy;jitter=random.randint(-1,1);bxj=bx+jitter
                if 0<=bxj<W and 0<=ry<H:buf[ry][bxj]='|'

        # crosshair — CV style with side lines
        cx,cy=W//2,H//2
        buf[cy][cx]='X'if player.overheated else'+'
        if cx>1:buf[cy][cx-1]='-';buf[cy][cx+1]='-'
        if cy>1:buf[cy-1][cx]='|';buf[cy+1][cx]='|'

        self._hud(buf,player,cam,router,W,H)
        return"\n".join("".join(r)for r in buf)

    def _cv_sprite(self,buf,zbuf,cam,ent,voff,W,H):
        sX=ent.x-cam.pos.x;sY=ent.y-cam.pos.y
        inv=cam.plane.x*cam.dir.y-cam.dir.x*cam.plane.y+1e-9;iD=1./inv
        tX=iD*(cam.dir.y*sX-cam.dir.x*sY);tY=iD*(-cam.plane.y*sX+cam.plane.x*sY)
        if tY<=0.1:return
        scrX=int(W/2*(1+tX/tY));sH=max(1,abs(int(H/tY)));sW=max(1,sH//2)
        y1=max(0,-sH//2+H//2+voff);y2=min(H-1,sH//2+H//2+voff)
        x1=max(0,scrX-sW//2);x2=min(W-1,scrX+sW//2)
        rows=_sprite_rows(ent.char if ent.alive()else'%',ent.flash>0,eid=ent.eid)
        rs=max(1,y2-y1)
        for sx in range(x1,x2):
            if tY<zbuf[sx]:
                for sy in range(y1,y2):
                    ri=min(int((sy-y1)/rs*len(rows)),len(rows)-1)
                    ci=(sx-x1)%max(1,len(rows[ri]))
                    sc=rows[ri][ci];buf[sy][sx]=sc if sc.strip()else ent.char
        if ent.msg_t>0 and ent.msg_text:
            ml=len(ent.msg_text);my=max(0,y1-2)
            mx=max(0,min(scrX-ml//2,W-ml))
            for i,c in enumerate(ent.msg_text):
                if mx+i<W and my<H:buf[my][mx+i]=c

    def _simple_sprite(self,buf,zbuf,cam,sx,sy,char,voff,W,H):
        dx,dy=sx-cam.pos.x,sy-cam.pos.y
        inv=cam.plane.x*cam.dir.y-cam.dir.x*cam.plane.y+1e-9;iD=1./inv
        tX=iD*(cam.dir.y*dx-cam.dir.x*dy);tY=iD*(-cam.plane.y*dx+cam.plane.x*dy)
        if tY<=0.1:return
        scrX=int(W/2*(1+tX/tY));sH=max(1,abs(int(H/tY)))
        y1=max(0,-sH//2+H//2+voff);y2=min(H-1,sH//2+H//2+voff)
        for px in range(max(0,scrX-2),min(W-1,scrX+2)):
            if tY<zbuf[px]:
                for py in range(y1,y2):buf[py][px]=char

    def _hud(self,buf,player,cam,router,W,H):
        # minimap (CV archived style, top-left)
        mm_w,mm_h=14,7
        ox=int(cam.pos.x)-mm_w//2;oy=int(cam.pos.y)-mm_h//2
        for my in range(mm_h):
            for mx in range(mm_w):
                wx=ox+mx;wy=oy+my
                try:c=router.get_cell(wx,wy)
                except:c=0
                mc='#'if c==WALL else('$'if c==TERMINAL else'.')
                bx=1+mx;by=2+my
                if 0<=bx<W and 0<=by<H:buf[by][bx]=mc
        # player marker
        buf[2+mm_h//2][1+mm_w//2]='@'
        # vehicles: V = single row, S = two rows tall
        for v in player.vehicles:
            mx=int(v['x'])-ox;my=int(v['y'])-oy
            bx=1+mx;by=2+my
            if 0<=bx<W and 0<=by<H:
                g='S'if v['kind']=='ship'else'V'
                buf[by][bx]=g
                if v['kind']=='ship'and 0<=by-1<H:buf[by-1][bx]='S'
        # direction indicator
        a=math.degrees(math.atan2(cam.dir.y,cam.dir.x))%360
        arr=['\u2192','\u2197','\u2191','\u2196','\u2190','\u2199','\u2193','\u2198'][int((a+22.5)/45)%8]
        if H>1:buf[1][W//2-4]=arr
        # HP / shield / heat bars
        hpf=max(0,cam.health)/cam.max_health;hb=10;hf=int(hpf*hb)
        _w(buf,2,H-5,"["+('#'*hf)+(' '*(hb-hf))+f"] HP:{cam.health} SH:{cam.shield}",W,H)
        hth=int(player.heat/100*hb);col='!'if player.heat>70 else'|'
        _w(buf,2,H-4,"["+(col*hth)+(' '*(hb-hth))+("] JAMMED!"if player.overheated else"] EMITTER READY"),W,H)
        # biome + nearby vehicle hint
        bl=BIOME_NAMES.get(player.biome,"?")if player.mode!=Player.BOARD else"ENEMY SHIP"
        nv=player.nearest_vehicle()
        hint=""
        if nv and player.mode==Player.FOOT:
            px,py,_=player.pos()
            d=math.hypot(px-nv['x'],py-nv['y'])
            if d<8:hint=("  [E] LAUNCH spaceship"if nv['kind']=='ship'else f"  [E] ENTER VEHICLE")+f" ({d:.1f})"
        _w(buf,2,H-3,f"[{bl}]{hint}",W,H)
        # powerup bar
        pu=player.powerups;bar=''
        if pu.get('SPEED_BOOST',0)>0:bar+=f' [>SPD:{pu["SPEED_BOOST"]//62+1}s]'
        if pu.get('SLOW_TIME',0)>0:bar+=f' [~SLO:{pu["SLOW_TIME"]//62+1}s]'
        if pu.get('RAPID_FIRE',0)>0:bar+=f' [!RFR:{pu["RAPID_FIRE"]//62+1}s]'
        if bar:_w(buf,2,H-6,'PWR:'+bar,W,H)
        # controls reminder
        _w(buf,2,H-2,"WASD move  L/R turn  UP/DN pitch  V jump  SHIFT sprint  SPACE/LMB emitter  E interact/launch  G board",W,H)
        # land word flash
        if player.land_t>0:
            msg=player.land_word;sx=W//2-len(msg)//2
            for i,c in enumerate(msg):
                bx=sx+i
                if 0<=bx<W and H//2+4<H:buf[H//2+4][bx]=c

def _w(buf,x,y,text,W,H):
    for i,c in enumerate(text):
        bx=x+i
        if 0<=bx<W and 0<=y<H:buf[y][bx]=c

class VehicleRenderer:
    """Phos City archived renderer: perspective DDA + floor cast + road lanes + cabin pitch + shake."""
    def __init__(self,W,H):self.W=W;self.H=H

    def render(self,player,router):
        cam=player.veh;W,H=self.W,self.H
        half_h=H//2;horizon=half_h+int(cam.hp_y*H*0.2)
        sk=cam.shake
        sx_off=(random.randint(-1,1)if sk>0.3 else 0)
        sy_off=(random.randint(-1,1)if sk>0.3 else 0)
        buf=[[' ']*W for _ in range(H)];zbuf=[9999.]*W

        # sky — Phos City phosphor starfield
        for y in range(0,max(0,horizon)):
            t=y/max(1,horizon);dens=0.060*(1.-t*0.78);row=buf[y]
            for x in range(W):
                ab=(cam.angle+(x-W/2)*0.012)%TAU
                hv=_pch(x,y,int(ab*80))
                if hv<dens:
                    row[x]='*'if hv<dens*.25 else('+'if hv<dens*.55 else('\u00b7'if hv<dens*.80 else'.'))
            if horizon>1 and y==horizon-1:
                for x in range(W):
                    if buf[y][x]==' ':buf[y][x]='.'

        # Phos City DDA wall cast
        for col in range(W):
            cam_x=2.*col/W-1.
            try:ray_a=cam.angle+math.atan(cam_x*math.tan(cam.fov/2))
            except:ray_a=cam.angle
            rdx=math.cos(ray_a);rdy=math.sin(ray_a)
            mx=int(math.floor(cam.x));my=int(math.floor(cam.y))
            ddx=1e30 if rdx==0 else abs(1./rdx);ddy=1e30 if rdy==0 else abs(1./rdy)
            if rdx<0:step_x=-1;sdx=(cam.x-mx)*ddx
            else:step_x=1;sdx=(mx+1-cam.x)*ddx
            if rdy<0:step_y=-1;sdy=(cam.y-my)*ddy
            else:step_y=1;sdy=(my+1-cam.y)*ddy
            hit=0;side=0;variant=0
            for _ in range(64):
                if sdx<sdy:sdx+=ddx;mx+=step_x;side=0
                else:sdy+=ddy;my+=step_y;side=1
                v=router.get_cell(mx,my)
                if v>0:hit=1;variant=v;break
            if not hit:zbuf[col]=9999.;continue
            if side==0:dist=sdx-ddx;wall_x=cam.y+dist*rdy
            else:dist=sdy-ddy;wall_x=cam.x+dist*rdx
            wall_x-=math.floor(wall_x)
            corr=dist*math.cos(ray_a-cam.angle)
            if corr<0.001:corr=0.001
            zbuf[col]=corr
            lh=max(1,int(H/corr))
            ds=max(0,horizon-lh//2);de=min(H-1,horizon+lh//2)
            fog=min(1.,corr/22.);wx=mx;wy=my
            for y in range(ds,de+1):
                vv=(y-(horizon-lh//2))/max(1,lh);vv=min(.999,max(0.,vv))
                glyph,inten=_pc_glyph(variant,wall_x,vv,wx,wy,fog)
                if side==1:inten*=0.78
                if inten<0.06:continue
                if fog>0.85 and glyph in(PC_WIN_LIT,'\u25a1',PC_WIN_BLIND):glyph='\u00b7'
                buf[y][col]=glyph

        # Phos City floor cast — road lanes for city router
        is_city=isinstance(router,PhosCityRouter)
        for y in range(horizon+1,H):
            p=y-horizon;row_dist=(.5*H)/max(1,p)
            if row_dist>30.:continue
            la=cam.angle-cam.fov/2;ra=cam.angle+cam.fov/2
            ldx=math.cos(la)*row_dist;ldy=math.sin(la)*row_dist
            rdx2=math.cos(ra)*row_dist;rdy2=math.sin(ra)*row_dist
            sx2=(rdx2-ldx)/W;sy2=(rdy2-ldy)/W
            fx=cam.x+ldx;fy=cam.y+ldy;fog_f=min(1.,row_dist/22.)
            for x in range(W):
                cv_=router.get_cell(fx,fy)
                if cv_!=0:fx+=sx2;fy+=sy2;continue
                if is_city:
                    stride=router.BLOCK_STRIDE;sh=router.STREET_HALF
                    rx=int(math.floor(fx))%stride;ry=int(math.floor(fy))%stride
                    u2=fx-math.floor(fx);vv2=fy-math.floor(fy)
                    xs=rx<sh or rx>=stride-sh;ys=ry<sh or ry>=stride-sh
                    ch=' ';inten=max(.05,.32-fog_f*.28)
                    if xs and ys:
                        if(int(u2*6)+int(vv2*6))%2==0:ch='\u2500'if int(vv2*4)%2==0 else' ';inten=max(.18,.48-fog_f*.4)
                        elif _pch(int(fx*8),int(fy*8))<.05:ch='.'
                    elif xs:
                        if rx==sh-1 and u2>.92 and int(fy*.6)%2==0:ch='|';inten=max(.40,.85-fog_f*.5)
                        elif rx==stride-sh and u2<.08 and int(fy*.6)%2==0:ch='|';inten=max(.40,.85-fog_f*.5)
                        if rx==0 and u2<.10:ch='\u2502';inten=max(.30,.60-fog_f*.4)
                        if rx==stride-1 and u2>.90:ch='\u2502';inten=max(.30,.60-fog_f*.4)
                        if ch==' 'and _pch(int(fx*7),int(fy*7),'a')<.04:ch='.'
                    elif ys:
                        if ry==sh-1 and vv2>.92 and int(fx*.6)%2==0:ch='-';inten=max(.40,.85-fog_f*.5)
                        elif ry==stride-sh and vv2<.08 and int(fx*.6)%2==0:ch='-';inten=max(.40,.85-fog_f*.5)
                        if ry==0 and vv2<.10:ch='\u2500';inten=max(.30,.60-fog_f*.4)
                        if ry==stride-1 and vv2>.90:ch='\u2500';inten=max(.30,.60-fog_f*.4)
                        if ch==' 'and _pch(int(fx*7),int(fy*7),'b')<.04:ch='.'
                    if ch!=' 'and buf[y][x]==' ':buf[y][x]=ch
                else:
                    if(x+y)%5==0:buf[y][x]='.'
                fx+=sx2;fy+=sy2

        # parked vehicle sprites
        self._veh_sprites(buf,player,zbuf,cam,W,H,horizon)

        # shake jitter
        if sk>0.3 and(sx_off or sy_off):
            nb=[[' ']*W for _ in range(H)]
            for y in range(H):
                for x in range(W):
                    nx2=x+sx_off;ny2=y+sy_off
                    if 0<=nx2<W and 0<=ny2<H:nb[ny2][nx2]=buf[y][x]
            buf=nb

        # minimap (top-right)
        self._minimap(buf,player,router,W,H)

        # HUD bottom
        biome=BIOME_NAMES.get(player.biome,'?')
        _w(buf,2,H-2,f"[{biome}] GEAR:{cam.gear} RPM:{int(cam.rpm)} SPD:{cam.speed:+.1f}  VEHICLE MODE",W,H)
        _w(buf,2,H-1,"W/S throttle  A/D steer  SHIFT boost  E exit vehicle",W,H)
        return"\n".join("".join(r)for r in buf)

    def _veh_sprites(self,buf,player,zbuf,cam,W,H,horizon):
        for v in player.vehicles:
            if abs(v['x']-cam.x)<.5 and abs(v['y']-cam.y)<.5:continue
            dx,dy=v['x']-cam.x,v['y']-cam.y
            ca,sa=math.cos(-cam.angle),math.sin(-cam.angle)
            lx=dx*ca-dy*sa;lz=dx*sa+dy*ca
            if lz<.5:continue
            scr_x=int(W/2+(lx/lz)*(W/2)*.7)
            hr=max(1,int(H/(lz*.5)))
            is_ship=v['kind']=='ship'
            height=hr if is_ship else hr//2
            cy2=horizon+height//2;g='S'if is_ship else'V'
            for py in range(max(0,cy2-height),min(H,cy2)):
                if 0<=scr_x<W and zbuf[scr_x]>lz:buf[py][scr_x]=g

    def _minimap(self,buf,player,router,W,H):
        cam=player.veh;mm_w,mm_h=14,7
        ox=int(cam.x)-mm_w//2;oy=int(cam.y)-mm_h//2
        for my in range(mm_h):
            for mx in range(mm_w):
                wx=ox+mx;wy=oy+my
                try:c=router.get_cell(wx,wy)
                except:c=0
                bx=W-mm_w-1+mx;by=2+my
                if 0<=bx<W and 0<=by<H:buf[by][bx]='#'if c>0 else'.'
        buf[2+mm_h//2][W-mm_w//2-1]='@'
        for v in player.vehicles:
            mx=int(v['x'])-ox;my=int(v['y'])-oy
            bx=W-mm_w-1+mx;by=2+my
            if 0<=bx<W and 0<=by<H:
                g='S'if v['kind']=='ship'else'V'
                buf[by][bx]=g
                if v['kind']=='ship'and 0<=by-1<H:buf[by-1][bx]='S'

class SpaceRenderer:
    def __init__(self):self.frame=0;self.last_sfx=0;self.shake=0.
    def _p(self,cam,wp,w,h,sdx=0,sdy=0):
        rel=vsub(wp,cam.pos);lx,ly,lz=vdot(rel,cam.right),vdot(rel,cam.up),vdot(rel,cam.fwd)
        if lz<10:return None
        f=750/lz;return(w/2+lx*f+sdx,h/2-ly*f+sdy,f,lz)
    def _pb(self,cam,wp,w,h,sdx=0,sdy=0):
        rel=vsub(wp,cam.pos);lx,ly,lz=vdot(rel,cam.right),vdot(rel,cam.up),vdot(rel,cam.fwd)
        if lz>-10:return None
        f=750/abs(lz);return(w/2-lx*f*.6+sdx,h/2+ly*f*.6+sdy,f*.6,abs(lz))
    def render(self,canvas,player,sf,pf,comets,audio):
        cam=player.craft;canvas.delete("all")
        w=canvas.winfo_width()or SPACE_W;h=canvas.winfo_height()or SPACE_H
        self.shake=min(3.,self.shake+.3)if(cam.thruster_on and cam.vel>10)else self.shake*.85
        sdx,sdy=random.uniform(-self.shake,self.shake),random.uniform(-self.shake,self.shake)
        if cam.vel>30:
            inten=min(1.,(cam.vel-30)/120)
            for _ in range(int(inten*20)):
                ang=random.uniform(0,TAU);r0=random.uniform(0,min(w,h)*.05);r1=r0+random.uniform(20,80)*inten
                canvas.create_line(w/2+math.cos(ang)*r0,h/2+math.sin(ang)*r0,
                                   w/2+math.cos(ang)*r1,h/2+math.sin(ang)*r1,
                                   fill="#ffaa00"if inten>.5 else"#8888ff",width=1)
        stars=sf.near(cam.pos);back=0
        for sx,sy,sz,glyph,color,fsize in stars:
            res=self._p(cam,[sx,sy,sz],w,h,sdx,sdy)
            if res:
                px,py,factor,_=res
                if 0<=px<=w and 0<=py<=h:
                    fs=max(7,min(fsize,int(factor*4)))
                    g='.'if factor<.05 else random.choice(['.', '\u00b7',"'", '`'])if factor<.2 else glyph
                    canvas.create_text(px,py,text=g,fill=color,font=("Courier",fs))
            else:
                r2=self._pb(cam,[sx,sy,sz],w,h,sdx,sdy)
                if r2 and back<80:
                    px,py,_,_=r2
                    if 0<=px<=w and 0<=py<=h:canvas.create_text(px,py,text='\u00b7',fill=color,font=("Courier",8));back+=1
        pf.update()
        for p in pf.planets:
            res=self._p(cam,p["pos"],w,h,sdx,sdy)
            if not res:continue
            px,py,factor,dist=res;size=max(2,int(p["size"]*factor*.08))
            if size>1 and 0<=px<=w and 0<=py<=h:
                lines=[p["char"]*(size-abs(r)*2)for r in range(-size//4,size//4+1)if size-abs(r)*2>0]
                canvas.create_text(px,py,text="\n".join(lines)if len(lines)>1 else p["char"]*size,
                                   fill=p["color"],font=("Courier",max(8,size//2),"bold"))
                if dist<800:canvas.create_text(px,py+size+12,text=f"[{BIOME_NAMES[p['biome']]}]",fill=p["color"],font=("Courier",8))
        for e in player.space_enemies:
            if not e.alive():continue
            res=self._p(cam,[e.pos.x,e.pos.y,e.pos.z],w,h,sdx,sdy)
            if not res:continue
            px,py,factor,dist=res
            if 0<=px<=w and 0<=py<=h:
                fs=max(8,int(factor*18))
                canvas.create_text(px,py,text="\u25c7",fill="#ff8888",font=("Courier",fs,"bold"))
                if dist<400:canvas.create_text(px,py+fs+4,text=f"HP:{e.hp}",fill=RED,font=("Courier",8))
        for comet in comets:
            res=self._p(cam,comet.pos,w,h,sdx,sdy)
            if res:
                px,py,factor,_=res
                if 0<=px<=w and 0<=py<=h:
                    canvas.create_text(px,py,text="@",fill=WHITE,font=("Courier",max(9,int(factor*12)),"bold"))
                    if factor>.3 and self.frame-self.last_sfx>60:audio.play('whoosh');self.last_sfx=self.frame
            for i,tp in enumerate(comet.tail):
                rt=self._p(cam,tp,w,h,sdx,sdy)
                if not rt:continue
                px,py,factor,_=rt
                if 0<=px<=w and 0<=py<=h:
                    fade=1.-i/max(1,len(comet.tail))
                    tc=f"#{int(0xaa+(0xff-0xaa)*fade):02x}{min(255,int(0x88+(0xff-0x88)*fade*.5)):02x}{min(255,int(0xff*fade*.7)):02x}"
                    canvas.create_text(px,py,text=COMET_CHARS[min(i,len(COMET_CHARS)-1)],fill=tc,font=("Courier",max(7,int(factor*10))))
        self._hud(canvas,cam,player,pf,audio,w,h);self.frame+=1

    def _hud(self,canvas,cam,player,pf,audio,w,h):
        cx,cy=w/2,h/2;col=GLOW if cam.thruster_on else AMBER
        canvas.create_text(cx,cy,text="\u2500\u2500[\u2726]\u2500\u2500",fill=col,font=("Courier",14))
        canvas.create_text(cx,cy-18,text="|",fill=col,font=("Courier",12))
        canvas.create_text(cx,cy+18,text="|",fill=col,font=("Courier",12))
        vp=min(1.,abs(cam.vel)/320.);bw=200;fi=int(vp*bw/6)
        canvas.create_text(cx,h-45,text="["+"\u2588"*fi+"\u2591"*(bw//6-fi)+"]",fill=AMBER,font=("Courier",9))
        ts="\u25b6 THRUST ON "if cam.thruster_on else"  THRUST OFF";bs=" \u26a1BOOST"if cam.boost_on else""
        ms="\u266b"if audio.music_on else"\u266a";sfx_s="~"if audio.sfx_on else"x"
        canvas.create_text(cx,h-25,fill=GLOW,font=("Courier",11),
                           text=f"{ts}{bs}  |  V:{int(cam.vel):4d}  |  HP:{cam.health} SH:{cam.shield}  |  {ms} {sfx_s}")
        canvas.create_text(10,12,anchor="w",fill=DIM,font=("Courier",9),
                           text=f"POS: {int(cam.pos[0]):+08.0f} {int(cam.pos[1]):+08.0f} {int(cam.pos[2]):+08.0f}")
        ccx,ccy,cr=w-70,70,35
        canvas.create_oval(ccx-cr,ccy-cr,ccx+cr,ccy+cr,outline="#333333",width=1)
        yaw=math.atan2(cam.fwd[0],cam.fwd[2]);pitch=math.asin(max(-1,min(1,cam.fwd[1])))
        canvas.create_line(ccx,ccy,ccx+math.sin(yaw)*cr*.8,ccy-math.sin(pitch)*cr*.8,fill=AMBER,width=2)
        canvas.create_text(ccx,ccy+cr+10,text="HDG",fill="#444444",font=("Courier",8))
        near=pf.nearest(cam.pos,600)
        if near:
            d=math.sqrt(sum((near["pos"][i]-cam.pos[i])**2 for i in range(3)))
            canvas.create_text(cx,h-70,fill="#88ffaa",font=("Courier",10,"bold"),
                               text=f"PLANET in range \u2014 [F] LAND ({BIOME_NAMES[near['biome']]}, d={int(d)})")
        be=player.nearest_space_enemy(300)
        if be:
            d=(be.pos-player.craft.pos_v3()).length()
            canvas.create_text(cx,h-90,fill="#ff88aa",font=("Courier",10,"bold"),
                               text=f"ENEMY SHIP in range \u2014 [G] BOARD (d={int(d)})")

# ================================================================ GAME ENGINE
class Game:
    def __init__(self,root,combat=False):
        self.root=root;self.combat=combat
        root.title("OMNI VOID ENGINE 3");root.configure(bg=BG);root.geometry(f"{SPACE_W}x{SPACE_H}")
        self.canvas=tk.Canvas(root,bg=BG,highlightthickness=0,width=SPACE_W,height=SPACE_H)
        self.canvas.pack(fill=tk.BOTH,expand=True)
        self.audio=Audio();self.player=Player()
        self.starfield=StarField();self.planet_field=PlanetField();self.comets=[]
        self.cv_ren=CVRenderer(GRID_W,GRID_H)
        self.veh_ren=VehicleRenderer(GRID_W,GRID_H)
        self.space_ren=SpaceRenderer()
        self.keys=set();self.frame=0;self.msg="";self.msg_t=0.
        self._lmb=False
        root.bind("<KeyPress>",self._kdn);root.bind("<KeyRelease>",self._kup)
        root.bind("<Button-1>",lambda e:setattr(self,'_lmb',True))
        root.bind("<ButtonRelease-1>",lambda e:setattr(self,'_lmb',False))
        root.protocol("WM_DELETE_WINDOW",self._quit)
        self._loop()

    def _hud(self,msg,ttl=2.5):self.msg,self.msg_t=msg,ttl

    def _kdn(self,e):
        k=e.keysym.lower();self.keys.add(k);P=self.player
        if k=="escape":self._quit();return
        # SPACE: emitter on foot/board, thrust toggle in space
        if k=="space":
            if P.mode==P.SPACE:
                P.craft.thruster_on=not P.craft.thruster_on
                self._hud(f"THRUST {'ON'if P.craft.thruster_on else'OFF'}")
            # foot/board: emitter handled in _update_emitter (held check)
            # do NOT discard space — need it held for continuous fire
        elif k=="v":
            if P.mode in(P.FOOT,P.BOARD):P.cv.jump();self.audio.play('jump')
        elif k=="b"and P.mode==P.SPACE:
            P.craft.boost_on=True;self.audio.play('boost');self._hud("BOOST")
        elif k=="e":self._interact()
        elif k=="f":self._f_key()
        elif k=="g":self._board()
        elif k=="x"and P.mode==P.BOARD:self._disembark()
        elif k=="m":self._hud(f"MUSIC {'ON'if self.audio.toggle_music()else'OFF'}")
        elif k=="r":self._hud(f"SFX {'ON'if self.audio.toggle_sfx()else'OFF'}")

    def _kup(self,e):
        k=e.keysym.lower();self.keys.discard(k)
        if k=="b"and self.player.mode==Player.SPACE:self.player.craft.boost_on=False

    def _interact(self):
        P=self.player
        if P.mode==P.FOOT:
            # Terminal first
            if P.dist_terminal()<2. and P.use_terminal():
                self._hud(">>> TERMINAL: HP/SH restored + heat cooled");self.audio.play('pickup');return
            # Nearest vehicle/ship
            v=P.nearest_vehicle()
            if v:
                px,py,_=P.pos();d=math.hypot(px-v['x'],py-v['y'])
                if d<5.:
                    if v['kind']=='ship':
                        # Spaceship = takeoff point — launch to space
                        P.takeoff();self._hud(">>> LAUNCH — leaving planet");self.audio.play('thruster')
                    else:
                        P.enter_vehicle(v['id'])
                        self._hud(f">>> ENTER VEHICLE #{v['id']}  [E to exit]")
                        self.audio.play('pickup')
        elif P.mode==P.VEHICLE:
            P.exit_vehicle();self._hud(">>> EXIT VEHICLE")
        elif P.mode==P.BOARD and P.dist_terminal()<2.:
            self._hud(">>> BRIDGE CAPTURED \u2014 [X] to disembark")

    def _f_key(self):
        P=self.player
        # F only works in space — land on nearest planet
        if P.mode==P.SPACE:
            near=self.planet_field.nearest(P.craft.pos,600)
            if near:P.land(near);self._hud(f">>> LANDED on {BIOME_NAMES[near['biome']]}");self.audio.play('pickup')

    def _board(self):
        P=self.player
        if P.mode!=P.SPACE:return
        t=P.nearest_space_enemy(300)
        if t:P.board_ship(t);self._hud(f">>> BOARDING SHIP #{t.eid}");self.audio.play('pickup')

    def _disembark(self):
        self.player.disembark();self._hud(">>> DISEMBARKED");self.audio.play('pickup')

    def _update(self,dt):
        P=self.player;m=P.mode
        if m in(P.FOOT,P.BOARD):
            self._update_foot(dt)
            self._update_emitter()
            _spd_m=0.25 if P.powerups.get('SLOW_TIME',0)>0 else 1.
            for e in P.entities:
                e.speed=ENEMY_SPD.get(e.char,.02)*_spd_m
                e.update(P.cv,P.router)
            self._check_entity_events()
            P.particles.update();P.pu_spawner.update()
            # trickle respawn — keep ~8 alive
            if self.frame%40==0:
                alive=sum(1 for e in P.entities if e.alive())
                if alive<8:
                    ang=random.uniform(0,TAU);dist=random.uniform(14,22)
                    sx=P.cv.pos.x+math.cos(ang)*dist;sy=P.cv.pos.y+math.sin(ang)*dist
                    if P.router.is_open(sx,sy):
                        P.entities.append(CVEntity(sx,sy,random.choice(ENEMY_CHARS)))
            P.entities=[e for e in P.entities if not(e.state=='DEAD'and e.dead_timer<=0)]
            P.tracers=[t for t in P.tracers if t[2]>0]
            for t in P.tracers:t[2]-=2
            for k in P.powerups:
                if P.powerups[k]>0:P.powerups[k]-=1
            if P.land_t>0:P.land_t-=1
        elif m==P.VEHICLE:
            self._update_vehicle(dt)
        elif m==P.SPACE:
            for e in P.space_enemies:e.update(P.craft.pos_v3(),dt)
            self._update_space(dt);self._update_comets()
            if self.frame%30==0:P.craft.reortho()
            if P.craft.thruster_on and self.frame%25==0:self.audio.play('thruster')
        if m==P.VEHICLE and self.frame%25==0 and abs(P.veh.speed)>1.:self.audio.play('engine')
        self.msg_t=max(0.,self.msg_t-dt)

    def _update_foot(self,dt):
        P=self.player;cam=P.cv;router=P.router
        if router is None:return
        sprint='shift_l'in self.keys or'shift_r'in self.keys or'shift'in self.keys
        _pu=P.powerups
        base=0.18 if sprint else 0.12
        spd=base*(2. if _pu.get('SPEED_BOOST',0)>0 else 1.)
        if _pu.get('SLOW_TIME',0)>0:spd*=.4
        moving=False
        # WASD move (CV archived exact: nx += dir*spd then collision per-axis)
        if'w'in self.keys:
            nx=cam.pos.x+cam.dir.x*spd;ny=cam.pos.y+cam.dir.y*spd
            if router.is_open(nx,cam.pos.y):cam.pos.x=nx  # x-axis slide
            if router.is_open(cam.pos.x,ny):cam.pos.y=ny  # y-axis slide
            moving=True
        if's'in self.keys:
            nx=cam.pos.x-cam.dir.x*spd;ny=cam.pos.y-cam.dir.y*spd
            if router.is_open(nx,cam.pos.y):cam.pos.x=nx
            if router.is_open(cam.pos.x,ny):cam.pos.y=ny
            moving=True
        if'a'in self.keys:  # strafe left (CV: -dir.y, +dir.x)
            nx=cam.pos.x-cam.dir.y*spd;ny=cam.pos.y+cam.dir.x*spd
            if router.is_open(nx,cam.pos.y):cam.pos.x=nx
            if router.is_open(cam.pos.x,ny):cam.pos.y=ny
            moving=True
        if'd'in self.keys:  # strafe right (CV: +dir.y, -dir.x)
            nx=cam.pos.x+cam.dir.y*spd;ny=cam.pos.y-cam.dir.x*spd
            if router.is_open(nx,cam.pos.y):cam.pos.x=nx
            if router.is_open(cam.pos.x,ny):cam.pos.y=ny
            moving=True
        # LEFT/RIGHT look — CV archived exact: left=+rot, right=-rot
        rot=0.062
        if'left'in self.keys:cam.rotate(rot)
        if'right'in self.keys:cam.rotate(-rot)
        # UP/DOWN pitch
        if'up'in self.keys:cam.pitch=min(14,cam.pitch+3)
        if'down'in self.keys:cam.pitch=max(-14,cam.pitch-3)
        if not('up'in self.keys or'down'in self.keys):cam.pitch*=.88
        # bob + jump
        if not cam.jumping:cam.step_bob(moving)
        else:cam.bob*=.85
        landed=cam.update_jump()
        if landed:
            cam.land_shake(6.,14);self.audio.play('land')
            P.land_word=random.choice(LAND_WORDS);P.land_t=28
            P._v_prev=True  # require re-press before next jump
        if moving and not cam.jumping:
            P._step_cd-=1
            if P._step_cd<=0:self.audio.play('step');P._step_cd=22
        # powerup pickup
        picked=P.pu_spawner.check(cam.pos.x,cam.pos.y)
        if picked:
            P.powerups[picked]=PU_DUR
            P.land_word=PU_LABELS[picked];P.land_t=55;self.audio.play('pickup')

    def _update_emitter(self):
        """CybervoidFusion archived: SPACE or LMB fires emitter. Heat/overheat/cooldown."""
        P=self.player;cam=P.cv
        firing='space'in self.keys or self._lmb
        if P.mode not in(P.FOOT,P.BOARD):return
        if firing and not P.overheated:
            rf=.35 if P.powerups.get('RAPID_FIRE',0)>0 else 1.
            P.heat=min(100,P.heat+3.8*rf)
            if P.heat>=100:
                P.overheated=True;self.audio.play('overheat')
                self._hud("EMITTER JAMMED — cool down")
            else:
                # CV archived: one tracer per shot, beam rendered from life counter
                P.tracers.append([GRID_W//2,GRID_H//2,14])
                self._fire_emitter();self.audio.play('gun')
        else:
            P.heat=max(0.,P.heat-2.2)
            if P.heat<=0 and P.overheated:
                P.overheated=False;self._hud("EMITTER READY")

    def _fire_emitter(self):
        """CV archived: confuse closest enemy in crosshair. Pacify, never kill."""
        cam=self.player.cv;best=None;bd=999
        for e in self.player.entities:
            if not e.alive()or e.pacified:continue
            dx=e.x-cam.pos.x;dy=e.y-cam.pos.y;d=math.hypot(dx,dy)
            if d<.5 or d>20:continue
            dot=cam.dir.x*(dx/d)+cam.dir.y*(dy/d)
            if dot>.96 and d<bd:best=e;bd=d
        if best:
            best.hit(1)
            inv=cam.plane.x*cam.dir.y-cam.dir.x*cam.plane.y+1e-9;iD=1./inv
            dx=best.x-cam.pos.x;dy=best.y-cam.pos.y
            tY=iD*(-cam.plane.y*dx+cam.plane.x*dy)
            if tY>0:
                tX=iD*(cam.dir.y*dx-cam.dir.x*dy)
                sx=int(GRID_W/2*(1+tX/tY));sy=GRID_H//2
                self.player.particles.emit(sx,sy,'spark',5)
                if best.pacified:self.player.particles.emit(sx,sy,'smoke',4)

    def _check_entity_events(self):
        P=self.player
        if any(e.newly_pacified for e in P.entities):
            self._hud("STILLNESS ACHIEVED — Peace and Bliss");self.audio.play('still')
        for e in P.entities:e.newly_pacified=False
        if self.combat:
            for e in P.entities:
                if e.alive()and not e.pacified and math.hypot(e.x-P.cv.pos.x,e.y-P.cv.pos.y)<1.2:
                    if P.cv.take_damage(e.dmg//4):
                        ox,oy=P._open_spawn(P.router)
                        P.cv.pos=V2(ox,oy);P.cv.health=P.cv.max_health;P.cv.shield=P.cv.max_shield
                        P.heat=0.;self._hud(">>> DOWN \u2014 RESPAWNING");self.audio.play('death')

    def _update_vehicle(self,dt):
        P=self.player;throttle=brake=steer=0.;boost=False
        # Phos City archived exact control mapping
        if'w'in self.keys or'up'in self.keys:throttle=1.
        if's'in self.keys or'down'in self.keys:brake=1.
        if'a'in self.keys or'left'in self.keys:steer=-1.
        if'd'in self.keys or'right'in self.keys:steer=1.
        if'shift_l'in self.keys or'shift_r'in self.keys or'shift'in self.keys:boost=True
        router=P.veh_router if P.veh_router else P.router
        # Pure Phos City: physics first, then position integration
        P.veh.update(dt,throttle,brake,steer,boost)
        P.veh.step(dt,router)

    def _update_space(self,dt):
        P=self.player;cam=P.craft;cam.update(dt,self.keys)
        if self.combat:
            cp=cam.pos_v3()
            for e in P.space_enemies:
                if e.alive()and e.fire_cd<=0 and(cp-e.pos).length()<200:
                    if cam.take_damage(8):
                        P.craft.pos=[0.,0.,0.];P.craft.health=P.craft.max_health;P.craft.shield=P.craft.max_shield
                        self._hud(">>> SHIP DOWN \u2014 RESPAWNING");self.audio.play('death');return

    def _update_comets(self):
        P=self.player
        if len(self.comets)<COMET_POOL and random.random()<.04:
            self.comets.append(Comet(P.craft.pos,P.craft.fwd))
        for c in self.comets:c.update()
        self.comets=[c for c in self.comets if c.alive()]

    def _draw(self):
        P=self.player;m=P.mode
        if m==P.SPACE:
            self.space_ren.render(self.canvas,P,self.starfield,self.planet_field,self.comets,self.audio)
        else:
            self.canvas.delete("all")
            if P.router is None:return
            # GFX AUTO-SWAP:
            # FOOT/BOARD -> CybervoidFusion dir/plane DDA raycaster
            # VEHICLE    -> Phos City perspective renderer (NOT on enemy ships)
            if m in(P.FOOT,P.BOARD):
                text=self.cv_ren.render(P,P.router)
            else:
                vr=P.veh_router if P.veh_router else P.router
                text=self.veh_ren.render(P,vr)
            y=12
            for line in text.split('\n'):
                self.canvas.create_text(10,y,text=line,fill=FG,font=("Courier",10),anchor="w");y+=14
        if self.msg_t>0:
            w=self.canvas.winfo_width()or SPACE_W
            self.canvas.create_text(w/2,55,text=self.msg,fill=WHITE,font=("Courier",13,"bold"))

    def _loop(self):
        try:self._update(1./FPS);self._draw()
        except tk.TclError:return
        self.frame+=1
        try:self.root.after(1000//FPS,self._loop)
        except tk.TclError:pass

    def _quit(self):
        try:self.audio.stop()
        except Exception:pass
        self.root.destroy()

# ================================================================ LAUNCHER
class Launcher:
    def __init__(self,root):
        self.root=root;root.title("OMNI VOID ENGINE 3 \u2014 Launcher")
        root.geometry("760x580");root.configure(bg=BG)
        tk.Label(root,text="O M N I _ V O I D _ E N G I N E _ 3",bg=BG,fg=GLOW,font=("Courier",17,"bold")).pack(pady=(20,4))
        tk.Label(root,text="walk \u00b7 sprint \u00b7 drive \u00b7 fly \u00b7 land \u00b7 board",bg=BG,fg=AMBER,font=("Courier",11)).pack(pady=(0,6))
        info=("Begin in deep space.\n\n"
              "ON FOOT / BOARDING  (CybervoidFusion GFX engine):\n"
              "  WASD        move / strafe\n"
              "  LEFT/RIGHT  look (turn)    UP/DOWN  pitch\n"
              "  SHIFT       sprint  (faster than walk, slower than vehicle)\n"
              "  V           jump\n"
              "  SPACE / LMB fire emitter  (confuses \u2192 pacifies, never kills)\n"
              "  E near vehicle   \u2014  enter it\n"
              "  E near spaceship \u2014  LAUNCH back to space\n"
              "  E near terminal  \u2014  restore HP/SH/heat\n\n"
              "IN VEHICLE  (Phos City GFX engine \u2014 auto-swaps on enter):\n"
              "  W/S throttle    A/D steer    SHIFT boost\n"
              "  E to exit vehicle.  Faster than sprinting.\n"
              "  Minimap: V = vehicle,  S = spaceship (launch point)\n\n"
              "IN SPACE:\n"
              "  WASD pitch/yaw  Q/E roll  arrows strafe\n"
              "  SPACE thrust    B boost   F land   G board enemy ship\n"
              "  M music    R sfx    ESC quit\n")
        tk.Label(root,text=info,bg=BG,fg=FG,font=("Courier",9),justify="left").pack(pady=(0,6))
        tk.Button(root,text="PEACEFUL  (no enemy damage)",bg="#003322",fg=GLOW,font=("Courier",12,"bold"),
                  width=34,command=lambda:self._launch(False)).pack(pady=4)
        tk.Button(root,text="COMBAT  (enemies damage you)",bg="#330000",fg=RED,font=("Courier",12,"bold"),
                  width=34,command=lambda:self._launch(True)).pack(pady=4)
        tk.Button(root,text="QUIT",bg=BG,fg=DIM,font=("Courier",10),width=14,command=root.destroy).pack(pady=(12,4))
        tk.Label(root,text="single-file \u00b7 pure stdlib \u00b7 offline \u00b7 zero dependencies",bg=BG,fg=DIM,font=("Courier",8)).pack(side="bottom",pady=6)

    def _launch(self,combat):
        self.root.destroy();g=tk.Tk();Game(g,combat=combat);g.mainloop()

def main():
    root=tk.Tk();Launcher(root);root.mainloop()

if __name__=="__main__":
    main()


