# Interview Preparation — Crowd Runner

A study sheet for answering the instructor's questions. Sections 1–3 are the three requested categories
(classes, algorithms, technical details). Section 4 suggests **who answers what**, and section 5 has
practice questions with short model answers.

> Tip: when you answer, name the file and the method (e.g. "`Camera.project()` in `game/core/camera.py`").
> It shows you know where things are.

---

## 1. List of classes

| Class | File | Responsibility (one sentence) |
|---|---|---|
| `Game` | `main.py` | Owns the window, the game loop and the state machine (MENU / SETTINGS / CONFIRM / PLAYING / PAUSED / WIN / LOSE); updates and draws everything each frame. |
| `Camera` | `game/core/camera.py` | Converts world coordinates `(x, z)` to screen coordinates and a scale (pseudo-3D perspective); also does screen shake. |
| `Crowd` | `game/world/crowd.py` | The player's crowd: real `count`, steering, crowd physics, losing people, drawing with animations. |
| `Person` | `game/world/crowd.py` | One simulated representative in the crowd: offset from the centre, velocity, animation timer. |
| `Gate` | `game/world/gate.py` | One gate with an operation (`+ − × ÷`) and a value; `apply(count)` returns the new count. |
| `GatePair` | `game/world/gate.py` | Two gates side by side at the same distance; applies the one under the crowd and flashes it. |
| `Obstacle` | `game/world/obstacle.py` | A moving block; anyone overlapping it is lost; can predict its future position. |
| `EnemyGroup` | `game/world/enemy.py` | An enemy army: charges, pulls the crowd in, fights people one by one; **parent class of `Boss`**. |
| `Boss` | `game/world/boss.py` | Inherits `EnemyGroup`; adds intro/approach/attack phases, attack animations, impacts and overlays for 9 boss styles. |
| `Particle` | `game/world/effects.py` | One particle (spark, pow, chip, dust) with position, height, velocity, age and life (`__slots__` for speed). |
| `Effects` | `game/world/effects.py` | Creates, updates and draws all particles (hit sparks, running dust, boss slams). |
| `Level` | `game/world/level.py` | Data of one level: name, start count, speed, finish distance, list of objects, boss. |

**Relationships to remember**
- **Inheritance**: `Boss(EnemyGroup)`. The base class defines defaults (`name`, `chip_color`, `impact`,
  `impact_strength`, `contact_z`, `engaged`, `draw_overlay`) and `Boss` overrides them, so `main.py` can
  fight any enemy with the same code (**polymorphism**).
- **Common interface** for everything on the road: `x`, `z`, `used`, `update(dt)`, `on_reach(crowd)`,
  `draw(screen, camera, font)`. `main.py` loops over `level.objects` without knowing their exact type.
- **Composition**: `Game` has a `Camera`, a `Crowd`, an `Effects`, a `Level` (which has the objects);
  `GatePair` has two `Gate`s; `Effects` has many `Particle`s; `Crowd` has many `Person`s.
- **Encapsulation example**: `Crowd.count` is a property; setting it calls `set_count()`, which also
  adds/removes simulated `Person` objects so the two always match.

Modules without classes (collections of functions): `sprites.py`, `sound.py`, `scores.py`, `ui.py`,
`trees.py`, plus the pose/drawing functions in `boss.py` and the analysis functions in `level.py`.

---

## 2. Key algorithms and logic

### 2.1 Game loop with delta time (`Game.run`)
Each frame: `dt = clock.tick(60) / 1000` (seconds, capped at 0.05) → events → update → draw.
Every movement is multiplied by `dt`, so the game runs at the same speed at 30 or 144 FPS.
The cap stops a lag spike from moving the crowd through a gate in one frame.

### 2.2 Finite state machine (`Game.state`)
MENU → PLAYING → WIN/LOSE, with PAUSED in between, and SETTINGS (sound panel) and CONFIRM
("Reset scores?" panel) reachable from MENU.
Each state handles keys differently (`handle_key`), and `update()` does nothing unless the state is
PLAYING. PAUSED and SETTINGS share the same sound controls (`sound_key`, `ui.draw_sound_panel`) —
one piece of code, two screens.

### 2.3 Pseudo-3D perspective projection (`Camera.project`)
`scale = FOCAL / (z − camera.z)`, `screen_x = CENTER_X + x·scale`, `screen_y = HORIZON_Y + CAM_HEIGHT·scale`.
Objects twice as far are half as big and closer to the horizon. Game logic only uses world coordinates;
only the camera knows about the screen, so changing the camera changes everything consistently.

### 2.4 Painter's algorithm (`Game.draw_world`)
Objects and trees are sorted by `z` and drawn far → near, so nearer things cover farther ones.
Trees nearer than the crowd are drawn after it.

### 2.5 Crowd simulation (`Crowd.update`)
A simple particle/flocking model for each `Person`:
cohesion (pull toward the centre), separation (push away from neighbours closer than `PERSON_SPACING`;
8 random neighbours are checked instead of all, which keeps it fast), a little random wander, and damping.
**Representative sampling**: at most 150 people are simulated and 40 drawn, however big the real count;
`spread() = (real / simulated) ^ 0.2` makes a big crowd look bigger.

### 2.6 Proportional loss and centre of mass (`Crowd.remove`)
If 3 of 150 representatives hit an obstacle, the real crowd loses 3/150 of its people. Then the crowd
centre moves to the survivors' average position.

### 2.7 Collision: 1-D interval overlap
Gates: is the crowd centre's `x` on the left (`x < 0`) or right side? Obstacles: a person is hit if
`|person_x − obstacle_x| ≤ width / 2`. Triggering uses `crowd.z >= object.z` (not `==`, because `z`
jumps several units per frame).

### 2.8 Enemy fight with a fractional accumulator (`EnemyGroup.update`)
Rate = `max(FIGHT_MIN_RATE, min(enemy, crowd) / FIGHT_TIME)` people per second. Each frame
`carry += rate · dt`; the whole part is subtracted from **both** sides and the fraction is kept for the
next frame, so the total is exact. Big and small fights take about the same time (~1 s; bosses 4 s,
with their own lower minimum rate `BOSS_MIN_RATE` so a small boss still fights the full 4 s).

### 2.9 Enemy charge and pull (`EnemyGroup.rush`, `pull_crowd`)
When the crowd is within `ENEMY_RUSH_DIST`, the enemy's real `z` moves toward the crowd, and the crowd is
pulled sideways with exponential smoothing: `x += (target − x) · min(1, ENEMY_PULL · dt)`. Steering is
locked until the fight ends.

### 2.10 Best possible count — greedy, proven optimal (`level.best_count`)
Always take the gate that gives more people. This is optimal because every operation (`+ − × ÷`, enemy
fights) is **monotonic**: more people in never gives fewer people out. Used for stars and tests.

### 2.11 Level difficulty score (`level.difficulty`)
0–100 = 40 × (fraction of gates where one wrong pick loses) + 25 × strictness `1 / (max wrong picks + 1)`
+ 15 × speed + 20 × obstacle count. `max_wrong_picks` is a **recursive search (DFS)** that tries both choices
at every gate (2^gates paths; fine for about 10 gates). Tests require every level to be no easier than the
hardest earlier level by more than 5 points.

### 2.12 Randomization that keeps fairness
- Gates (`randomize_gates`): change one gate at a time to a random nearby value; keep the change only if the
  difficulty score is **exactly** unchanged (rejection sampling, up to 6 tries per gate); randomly swap sides.
- Obstacles (`randomize_obstacles` + `dodge_spans`): walk along the best route and keep a set of reachable
  x-intervals. Between objects, intervals grow by `side_speed × time`; gates cut them to the good side;
  each obstacle cuts out the area it sweeps (predicted with `x_at(t)`). A random obstacle is accepted only
  if enough safe width remains (rejection sampling, up to 15 tries), so **every layout is dodgeable**.
  Interval helpers: `_merge`, `_clip`, `_cut`.
- Checked with a bot playing all 10 levels on 40 random layouts each: 3 stars every time.

### 2.13 Obstacle motion prediction
Position is a sine wave `start_x + sin((start_time + t) · swing_speed) · amplitude`, so the position at any
future time is a formula. Obstacles freeze during fights, so the prediction stays correct.

### 2.14 Boss logic (`Boss`)
- **Data-driven design**: each boss is a dictionary in `STYLES` (animations, fps, hit frames, strength,
  lunge, lift, distances). The same `Boss` class runs all 9.
- **Phases**: idle → (intro) → approach at `run_speed` → engaged fight → finished; `engaged` tells `main.py`
  when real hits start.
- **Animation from time**: `frame = int(attack_t · fps) % frames`; `impact` is raised only on the first frame
  of a hit frame (edge detection), so the camera shakes once per hit.
- **Random moves without repeats** (boss 9): `random.choice([m for m in moves if m != current])`.
- **Spring physics for the cape** (boss 9): the cape tip is a mass on a damped spring attached to the
  shoulders (`a = K·(anchor − pos) − DRAG·v`), integrated with small sub-steps (semi-implicit Euler).
- **Rapid-punch timing** (boss 3): each arm's punch phase is computed from time; a hit is counted when the
  phase passes the "fist reaches the crowd" point between two frames.

### 2.15 Procedural graphics
- Road: a brick texture generated with a fixed seed, cut into rows; far away, pre-averaged rows
  ("mipmaps") are used so the road doesn't flicker.
- Trees: crowns are unions of circles; each pixel is lit like a dome (dot product with a light direction),
  quantized to 5 greens with a **Bayer ordered-dither**; dark creases where clumps overlap.
- Bosses 4–9: drawn from pose descriptions (limbs as chains of circles, polygons for armour, crescent
  "smears" for sword trails).
- Enemy army: people placed on a **golden-angle spiral** (`angle = i · 2.39996`, `radius ∝ √i`), which fills
  a circle evenly.

### 2.16 Sound synthesis (`sound._synth`)
Each sound is a list of notes; for each sample the phase advances by `2π · frequency / sample_rate`
(phase accumulation, so frequency slides are smooth); wave = 0.7 sine + 0.3 square (retro sound),
optional noise for hits; multiplied by an envelope (fast attack, fading tail); stored as 16-bit integers.

### 2.17 Particles and screen shake
Particles move by velocity × `dt`; chips have gravity and bounce once; dead particles are removed;
at most 350. Screen shake: a random offset whose size decreases linearly to 0 over its duration.

### 2.18 Stars and high scores
Stars from the ratio `count / best` (≥ 0.25 → 2, ≥ 0.5 → 3). High score keeps the best count **and** the
best stars separately, because the random layout changes the best possible count every run.

---

## 3. Technical details

**Technology**
- Python 3 (developed on 3.14) and **pygame-ce 2.5** (window, drawing, images, fonts, input, mixer).
- Standard library only otherwise: `json` (levels, scores, settings), `math`, `random`, `array`
  (building sound samples), `bisect` (fast range lookups), `pathlib` (file paths).
- Almost no asset files: road, grass, clouds, trees, flowers, bosses and sound effects are generated in
  code. The only files are the 16×32 character sheets, the menu picture and three background-music
  mp3s (`game/core/music/`: menu, in-game, boss). `Game.music_theme()` picks the track for the current
  screen every frame; `sound.play_music()` only reloads when the track changes, and calls `stop()`
  before `load()` because starting a track during a fade-out blocks until the fade ends.

**Data structures**
- Lists sorted by `z` (`level.objects`, tufts, trees) + `bisect` to find only what is visible (O(log n)).
- Dictionaries: `STYLES` (boss data), `settings`, high scores, and many **caches**
  (`(frame, width, height) → scaled image`) so scaling/rendering happens once.
- Tuples for colours and positions; a `set` of ids for fast removal checks; interval lists `[[a, b], …]`
  for reachable positions; `__slots__` in `Particle` for less memory.
- JSON files: `levels/*.json` (data separated from code), `highscores.json`, `settings.json`.

**Code organization / design decisions**
- `main.py` entry point; `game/core` shared basics; `game/world` world objects; `game/ui.py` screens.
- All constants and file paths in `config.py`: tuning never requires searching other files.
- Logic in world units, drawing only through `Camera.project()`.
- Pure functions where possible (`Gate.apply`, `scores.stars`, `level.best_count`): easy to test.
- Data-driven content: levels are JSON, bosses are dictionaries.

**Performance**
- Average frame ≈ 3–5 ms (budget at 60 FPS is 16.7 ms). Tricks: simulate ≤ 150 people and draw ≤ 40;
  cache scaled images; skip off-screen objects; pre-generate textures and boss frames once.

**Testing and quality**
- 35 automated tests (`tests/test_logic.py`) that run without opening the game window: rules, fairness of
  every level, randomization, bosses, scores.
- During the refactor the whole game was "fingerprinted" (every boss frame, every screen, and frame-by-frame
  state of seeded bot playthroughs of all 10 levels) and compared before/after: identical.
- Team workflow with Git/GitHub branches and pull requests (old guide in `docs/archive/GUIDE_TH.md`).

---

## 4. Suggested split for answering (based on file ownership)

| Member | Main topics | Files |
|---|---|---|
| **A** | Game loop, delta time, state machine, input (keyboard/mouse), camera projection and shake, painter's algorithm, sound synthesis and settings, particles | `main.py`, `camera.py`, `sound.py`, `effects.py` |
| **B** | Crowd physics and sampling, gates, obstacles and collisions, enemy charge/fight, sprites, bosses (inheritance, STYLES, phases, spring cape) | `crowd.py`, `gate.py`, `obstacle.py`, `enemy.py`, `sprites.py`, `boss.py` |
| **C** | Level JSON, best count, difficulty score, randomization and fairness checks, UI screens, stars/high scores, tests, procedural trees, menu picture tool | `level.py`, `levels/`, `ui.py`, `scores.py`, `trees.py`, `tests/`, `tools/` |

Everyone should be able to explain: the overall structure (section 4 of README), what a class is for,
and how one frame flows (input → update → draw).

---

## 5. Practice questions (short model answers)

**General**
1. *How does one frame work?* — `run()` gets `dt` from `clock.tick`, `handle_events()` reads input,
   `update()` moves the camera/crowd and triggers objects, `draw()` renders far → near, then `display.flip()`.
2. *Why multiply by `dt`?* — Same speed on fast and slow computers (frame-rate independent).
3. *How is the game "3D"?* — It's 2D with perspective: `Camera.project` scales by `FOCAL / distance`.
4. *How did you organize the code?* — `core` (shared basics), `world` (objects), `ui` (screens), `main`
   (loop). Constants in `config.py`; level data in JSON.

**Classes / OOP**
5. *Show an example of inheritance.* — `Boss(EnemyGroup)`: reuses the fight-by-rate logic, overrides
   `update`, `draw`, `on_reach`, `engaged`, `contact_z`, `draw_overlay`.
6. *Polymorphism?* — `main.py` calls `obj.on_reach(crowd)` / `obj.draw(...)` on gates, obstacles, enemies
   and bosses without checking their type.
7. *Why is `count` a property in `Crowd`?* — Setting it must also keep the simulated people list in sync.

**Algorithms**
8. *How do you decide which gate the crowd takes?* — The centre `x`: `x < 0` → left gate, else right.
9. *How do you know a level can be won?* — `best_count` (greedy, optimal because operations are monotonic)
   must be > 0; tests check every level.
10. *How do you make sure random obstacles are dodgeable?* — `dodge_spans` tracks reachable x-intervals
    along the route; a random obstacle is rejected if the safe gap is too small.
11. *How does randomizing gates keep the same difficulty?* — Change one gate, recompute `difficulty()`,
    keep the change only if the score is identical.
12. *How is the difficulty computed?* — Weighted sum: fatal gates 40, strictness 25, speed 15, obstacles 20;
    `max_wrong_picks` is a recursive search over all choices.
13. *How does a fight work?* — People are subtracted from both sides at a fixed rate; a fractional
    "carry" keeps the total exact.
14. *Why not simulate all 3000 people?* — Too slow (~25 ms/frame); 150 representatives scaled by `spread()`.
15. *How does the boss know when to shake the screen?* — `impact` becomes `True` only on the first frame of
    a hit frame listed in its style; `main.py` reacts to it.
16. *How does the final boss avoid repeating attacks?* — Picks randomly from the moves except the current one.
17. *How does the cape move?* — Damped spring physics, integrated with sub-steps.

**Technical**
18. *Which libraries?* — pygame-ce plus Python's standard library (json, math, random, array, bisect, pathlib).
19. *Where are sounds from?* — Synthesized in code from note lists (sine + square + optional noise, envelope).
20. *How do you save scores and settings?* — JSON files in the game folder; a missing or broken file starts fresh.
21. *How did you test?* — 35 automated tests; a bot playing every level on many random layouts; screenshots;
    a before/after fingerprint to prove the refactor changed nothing.
22. *How do you keep it fast?* — Caching scaled images, limiting simulated/drawn people, skipping off-screen
    objects, `bisect` for visible scenery, generating textures once.
