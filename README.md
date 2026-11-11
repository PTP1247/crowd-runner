# Crowd Runner

A pseudo-3D crowd runner made with **Python + pygame-ce** (midterm project).
You steer a crowd down a road, pick the gate that gives you more people (`+ - × ÷`), dodge obstacles,
beat enemy armies, and finish each level with a boss fight. There are 10 levels and 9 bosses.

---

## 1. Running the game

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Requirements: Python 3 (developed and tested on 3.14) and `pygame-ce` 2.5+ (see `requirements.txt`). No other packages are needed;
sound effects, trees and flowers are generated in code; the background music is three mp3 files in
`game/core/music/`.

### Tests

```bash
python -m pytest            # if pytest is installed
python tests/test_logic.py  # works without pytest
```

There are 34 tests. They need no window and check the game rules, the level design rules and the boss logic.

---

## 2. Controls

| Where | Key / mouse | Action |
|---|---|---|
| Level menu | Up/Down (W/S) + Space/Enter, or **click a level** | Choose and start a level (hover highlights it) |
| Level menu | Down past the last level + Enter, or **click "Music & Sound"** | Open the sound settings (same sliders/boxes as the pause screen; Esc, Backspace or a click outside the panel goes back) |
| Level menu | U (hidden, no on-screen hint) | Unlock all levels temporarily (testing/demo, not saved) |
| Playing | Left/Right or A/D | Steer the crowd |
| Playing | P or Esc | Pause |
| Playing | R | Restart the level |
| Anywhere | N | Turn all sound on/off |
| Pause / Sound settings | Up/Down (W/S) or mouse hover | Choose the Music or Effect row |
| Pause / Sound settings | Left/Right (A/D), or click/drag the slider | Volume 0–100% (hold the key to slide) |
| Pause / Sound settings | Enter/Space, or click the box | Turn that sound on/off (box with ✕ = on) |
| Pause | Esc or P | Continue playing |
| Pause | R / M | Restart / back to the level menu |
| You Win | Enter / R / M | Next level / play again / level menu |
| Game Over | Enter / M | Try again / level menu |

---

## 3. How the game works (rules)

- **Gates**: two gates side by side. The crowd's centre decides which one you pass through. Numbers are
  re-randomized every run, but the level's difficulty score is kept exactly the same.
- **Obstacles**: yellow-and-black blocks. Everyone who overlaps the block is lost. Width, position and
  movement are random every run, but always checked to be dodgeable.
- **Enemy armies** (red people): when you get close they charge; your steering locks and the crowd is
  pulled toward them. Both sides lose people one by one for about 1 second, and running stops meanwhile.
- **Boss**: waits past the finish line. Once the whole crowd has crossed, the boss fights you the same
  way as an enemy army (with its own animations, impact shakes and effects).
- **Win**: the whole crowd crosses the finish line (and beats the boss if there is one).
  **Lose**: the crowd count reaches 0.
- **Stars**: 1 star for winning, 2 stars for ≥ 25% and 3 stars for ≥ 50% of the best possible count for
  that run's random layout (`level.best_count`).
- **Unlocking**: level 1 is always open; every other level needs the previous level won.
- **Scenery**: trees and flowers are scattered randomly beside the road each run (decoration only).

---

## 4. Project structure

```
crowd-runner/
├── main.py                  Entry point: the Game class (game loop + state machine)
├── game/                    All game code (a Python package)
│   ├── core/                Shared basics used everywhere
│   │   ├── config.py        Every constant + file paths
│   │   ├── camera.py        World (x, z) → screen (pseudo-3D projection) + screen shake
│   │   ├── sprites.py       Load / cut / tint / scale sprite sheets (with caches)
│   │   ├── sound.py         Synthesized sound effects, background music switching, volume settings
│   │   ├── music/           Background music: menu_theme, in-game_theme, boss_theme (.mp3)
│   │   └── scores.py        Stars, high scores, unlocking
│   ├── world/               Everything that lives in the game world
│   │   ├── crowd.py         The player's crowd (physics, drawing, losing people)
│   │   ├── gate.py          Gate / GatePair (+ − × ÷)
│   │   ├── obstacle.py      Moving obstacle blocks
│   │   ├── enemy.py         EnemyGroup (also the parent class of Boss)
│   │   ├── boss.py          The 9 bosses: styles, procedural pixel art, fight logic
│   │   ├── effects.py       Particles: sparks, "pow", flying chips, dust
│   │   ├── trees.py         Procedural trees + flowers beside the road
│   │   └── level.py         Load levels from JSON, randomize them, check they are fair
│   └── ui.py                Screens that are not the world: menu, HUD, pause, end screen
├── levels/level1..10.json   Level data (gates, obstacles, enemies, boss)
├── assets/                  Sprite sheets (16x32 characters), menu background picture
├── tests/test_logic.py      Automated tests
├── tools/make_menu_bg.py    Script that renders assets/menu_bg.png from the game's own renderer
└── docs/                    INTERVIEW_PREP.md + archive/ (old team guide and changelog)
```

Files created at runtime and ignored by git: `highscores.json` (best scores and stars) and
`settings.json` (volume settings).

### How the parts depend on each other

```
main.py (Game)
  ├── game.ui                 draws menu / HUD / pause / end screens
  ├── game.world.level        builds the Level (objects list) from levels/*.json
  │     ├── gate, obstacle, enemy, boss      the objects on the road
  ├── game.world.crowd        the player's crowd
  ├── game.world.effects, trees
  └── game.core.*             config, camera, sprites, sound, scores (used by everything)
```

Every object on the road follows the same small **interface**, so `main.py` can treat them the same way:
`x`, `z`, `used`, `update(dt)`, `on_reach(crowd)` (called once when the crowd reaches it) and
`draw(screen, camera, font)`. To add a new object type you write a class with these methods and add one
`if` to `level.build_object()`.

---

## 5. Module-by-module explanation

### 5.1 `main.py` — the game loop and state machine

The `Game` class owns everything that changes during play.

**State machine** (`self.state`):

```
MENU ──(choose a level)──▶ PLAYING ──(whole crowd crosses the finish)──▶ WIN
                              │  └──(crowd count reaches 0)──────────▶ LOSE
                              └──(P / Esc)──▶ PAUSED ──(Esc / P)──▶ PLAYING
PAUSED / WIN / LOSE ──(M)──▶ MENU        WIN ──(R / Enter)──▶ PLAYING      LOSE ──(Enter)──▶ PLAYING
MENU ──("Music & Sound" button)──▶ SETTINGS ──(Esc / click outside)──▶ MENU
```

**Game loop** (`run`): every frame → `clock.tick(60)` gives `dt` (seconds, capped at 0.05 so a lag spike
can't make the crowd skip through a gate) → `handle_events()` → `update()` → `draw()`.

Important methods:

| Method | What it does |
|---|---|
| `__init__` | Opens the window, builds procedural textures (brick road, grass tufts, clouds, trees), loads the level list once (names + difficulty tiers for the menu) |
| `reset` | Loads the selected level **with randomization**, computes `best` (for stars), creates the `Crowd`, `Effects`, scenery |
| `handle_events` / `handle_key` | Keyboard per state; steering is ignored while `crowd_locked()` |
| `move_selection` | Up/Down in the menu: cycles through unlocked levels, then the "Music & Sound" button, and wraps |
| `handle_menu_mouse`, `handle_pause_mouse`, `hold_pause_keys` | Mouse hover/click in the menu, sliders and boxes in the pause and sound-settings screens, hold-to-slide volume |
| `sound_key`, `open_settings`, `close_sound_panel` | Keys shared by both sound panels (row, volume, on/off); open the settings screen; save settings and leave |
| `crowd_locked` | `True` while an enemy is charging or a fight is on (player can't steer) |
| `update` | Moves the camera forward (`camera.z += speed·dt`), keeps the crowd `CROWD_OFFSET` ahead, lets the next enemy charge, triggers every object the crowd has reached (`on_reach`), checks win/lose |
| `reached` | Road objects trigger when the crowd's centre passes them; the boss triggers when the **last** person crosses the finish band |
| `update_fight` | While fighting: no running; the fight subtracts people, the crowd is pulled to the enemy, camera shakes, hit sparks/impacts, ends the fight |
| `react` | After a gate/obstacle: floating `+20`/`-35` text, sound, camera shake, remembers the lose cause |
| `finish_level` | Computes stars, saves high score, switches to WIN/LOSE |
| `draw_world` | Sky, striped grass, tufts, brick road (with "mip-mapped" rows to avoid flicker far away), centre line, finish line, then objects + trees sorted far→near (painter's algorithm), crowd, boss overlay, particles |
| `draw` | Menu screen, or world + HUD + popups + tips + pause/end overlays |

### 5.2 `game/core/config.py` — constants

All tuning numbers live here (screen 480×800, 60 FPS, road half width 150, crowd/enemy/boss/shake
timings, colours) plus the file paths (`ROOT`, `ASSET_DIR`, `LEVEL_DIR`, `SCORE_FILE`, `SETTINGS_FILE`).
Keeping them in one file means changing the game feel never requires hunting through other files.

### 5.3 `game/core/camera.py` — pseudo-3D projection

The world uses `x` = left/right (0 = road centre) and `z` = distance forward. The game logic only uses
world coordinates; **only `Camera.project()` knows how to draw**:

```
rel   = z − camera.z                 distance in front of the camera
scale = FOCAL / rel                  twice as far → half as big
sx    = CENTER_X + x · scale
sy    = HORIZON_Y + CAM_HEIGHT · scale
```

`visible(z)` skips anything closer than `Z_NEAR` or further than `Z_FAR`. `shake(power, duration)`
adds a random screen offset that fades out linearly (used for hits, fights and boss impacts).

### 5.4 `game/core/sprites.py` — sprite sheets

`frames(sheet, row, tint)` cuts a row of 32×32 frames from `assets/16x32/16x32 <sheet>-Sheet.png`
(5 rows = 5 facing directions), optionally multiplies a tint colour (red enemies), and caches the result.
`scaled(surface, w, h)` caches scaled copies, because scaling every frame is slow.
If a file is missing, a grey placeholder is returned so the game never crashes.

### 5.5 `game/core/sound.py` — sound

- Sound effects are **synthesized at start-up** (no audio files): each sound is a list of notes
  (start frequency, end frequency, duration) turned into a 16-bit wave (sine + a little square wave,
  optional noise for hits) with a fast attack and fading envelope.
- **Background music** (`play_music(theme)`): three looping tracks in `game/core/music/`
  (`THEMES`). `main.py` calls it every frame with `Game.music_theme()`:

  | Screen | Track |
  |---|---|
  | Level menu, sound settings | `menu_theme.mp3` |
  | Running, paused | `in-game_theme.mp3` |
  | From the moment the boss and the crowd start hitting each other (`engaged`, not during the boss's intro/walk) until the level ends | `boss_theme.mp3` |
  | You Win / Game Over | music fades out so the win/lose jingle is clear |

  Asking for the track that is already playing does nothing, so the music only restarts when the
  screen changes. A new track fades in over `MUSIC_FADE_MS`. It always calls `music.stop()` before
  `load()`: starting a track while the old one is still fading out makes SDL wait for the fade
  (a ~0.6 s freeze). A missing file or no audio device just means silence.
- `settings` holds volume (0–1) and on/off for `music` and `effect`; it is saved to `settings.json`
  and loaded at start-up. Without an audio device the game runs silently.

### 5.6 `game/core/scores.py` — stars and high scores

`stars(won, count, best)`, `thresholds(best)` (people needed for 2 and 3 stars), `load_scores()`,
`record()` (keeps the best count **and** the best stars separately, because the random layout changes
the best possible count every run) and `is_unlocked()`. A missing or broken `highscores.json` simply
starts fresh.

### 5.7 `game/world/crowd.py` — the player's crowd

- `count` is the real number of people (can be thousands). Only up to `SIM_PEOPLE = 150`
  representative `Person` objects are simulated and up to `MAX_DRAWN_PEOPLE = 40` are drawn.
  `spread()` = (real / simulated) ^ `CROWD_GROWTH` scales their positions so a big crowd looks bigger.
- `update(dt)`: keeps the crowd on the road, measures sideways speed (to pick the straight / left /
  right running animation) and runs a small **particle physics**: pull toward the centre (cohesion),
  push away from neighbours closer than `PERSON_SPACING` (separation), a little random wander, damping.
- `remove(people)`: representatives hit by an obstacle are removed and the real count drops by the same
  proportion; the crowd centre then shifts to the survivors (centre of mass).
- `draw`: far people first, each scaled by distance, with a small bobbing; run / attack / wait animations;
  the blue count label on top.
- `blob_radius(count)` / `edge_gap(count)`: the crowd's size for any count (a measured table), used for
  road limits, enemy group size and the level fairness checks.

### 5.8 `game/world/gate.py` — gates

`Gate(x_min, x_max, op, value)`: `apply(count)` is a pure function (`+`, `−` never below 0, `×`,
`÷` with integer division), `is_good()`, `label()`, `contains(x)`.
`GatePair(z, left, right)`: the left gate covers `x < 0`, the right gate `x ≥ 0`. `on_reach` applies the
gate under the crowd's centre and flashes it. Gates are drawn see-through with a darker frame; labels are
cached per size.

### 5.9 `game/world/obstacle.py` — obstacles

`Obstacle(x, z, width)`: `randomize()` picks width, a movement pattern (still / slow / fast swing) and a
starting phase. The position is a sine wave: `x = start_x + sin((start_time + t) · swing_speed) · amplitude`,
so `x_at(t)` can predict where it will be (used by the fairness check). `on_reach` removes every person
whose real position overlaps the block. Drawn as a 3D-looking box with a hazard-stripe texture.

### 5.10 `game/world/enemy.py` — enemy armies

`EnemyGroup(z, count, x)`:
- `rush()`: when the crowd is within `ENEMY_RUSH_DIST`, the army runs toward it (its real `z` decreases)
  and `pull_crowd()` pulls the crowd sideways to the army.
- `on_reach()`: starts the fight with a rate of `max(FIGHT_MIN_RATE, min(both counts) / FIGHT_TIME)`
  people per second; `update(dt)` subtracts from both sides with a fractional "carry" so the result is
  exact, then ends the fight when one side reaches 0.
- Drawn as a round blob of red people placed on a **golden-angle spiral** (evenly filled circle).
- It is also the **parent class of `Boss`**: it defines the defaults `main.py` relies on (`name`,
  `chip_color`, `impact`, `impact_strength`, `contact_z`, `engaged`, `draw_overlay`) and the boss
  overrides them.

### 5.11 `game/world/boss.py` — the 9 bosses

| Kind | Name | Level | Look and attack |
|---|---|---|---|
| 1 | the Grey Brute | 2 | Grey giant, ground punch with a shockwave |
| 2 | the Blue Stomper | 3 | Raises a leg and stomps (pose built from the sheet frame) |
| 3 | the Iron Barrage | 4 | Rapid punches drawn as real arms + motion-blur trails over the crowd |
| 4 | the Green Boxer | 5 | Muscular redrawn body, jab → hook → uppercut combo |
| 5 | the Shadow Ninja | 6 | Waits far away, ninja-runs in while drawing a kunai, left/right slashes |
| 6 | the Iron Knight | 7 | Unsheathes and takes a stance (intro), walks in, 3-cut sword combo |
| 7 | the Wandering Samurai | 8 | Kneels, iai-draws with a flash, then fast random-direction cuts |
| 8 | the Rotting Giant | 9 | Zombie limp, claw swipes leaving scratch marks |
| 9 | the Dread Knight | 10 | Greatsword; random non-repeating sweep / jump slam / thrust / double slash; cape spring physics |

How it is built:
- **`STYLES` dict**: one entry per boss kind describing everything as data: idle/attack/run/intro
  animations (`*_build` = pose lists), frame rates, `impact` frames and their `impact_strength`,
  `lunge` (step toward the crowd per frame), `lift` (jump height), `stand` distance, `run_speed`,
  `moves` (boss 9), colours and label. **Adding a boss = adding a dict entry** (+ poses).
- **Procedural pixel art**: bosses 1–3 recolour/re-pose the 16×32 character sheet (grayscale ×
  tint, cut limbs and rotate them, draw angry faces). Bosses 4–9 are drawn entirely in code
  (`*_pose()` functions) from pose descriptions: limbs, armour, weapons, sword trails (crescent
  "smears"), scratches, sparkles. `boss_frames(kind, part)` builds and caches every frame once.
- **`Boss(EnemyGroup)`** adds the fight phases: idle → (optional intro, e.g. drawing a sword) →
  approach (run/walk toward the crowd at `run_speed`) → `engaged` fight → finished.
  Both sides lose people at `max(BOSS_MIN_RATE, min(both counts) / BOSS_FIGHT_TIME)` per second, so every
  boss fight lasts about `BOSS_FIGHT_TIME` = 4 s, enough time to see several attacks.
  `update()` picks the attack frame, raises `impact` exactly on hit frames (main.py shakes the camera
  and plays a sound) and handles boss 9's random move picker (`next_move_frame`, never the same move
  twice in a row). `draw()` scales the frame by distance (`BOSS_SCALE`), draws the shadow, shockwaves and
  the label; `draw_overlay()` draws things that must be on top of the crowd (barrage fists, the thrust blade).
- The Dread Knight's cape is a **damped spring simulation** (`_dk_cape`): the cape tip is a mass pulled
  toward the shoulders, so it lags behind swings and jumps and swings past naturally.

### 5.12 `game/world/effects.py` — particles

`Particle` stores world position (`x`, `z`), height `h` and velocity; `Effects` manages up to 350 of them.
`hit()` (spark + chips + dust), `puff()` (running dust), `slam()` (boss ground impact: "pow" burst + ring of
dust + flying rocks). Chips fall with gravity and bounce once. Everything is drawn through
`camera.project`, so particles shrink with distance and shake with the camera.

### 5.13 `game/world/trees.py` — scenery

Three tree types and a flower are drawn **pixel by pixel in code** (no image files): the tree crown is a
union of circles, each pixel is shaded like a small dome lit from the top-left, then quantized to 5 greens
with a 2×2 ordered-dither (Bayer) pattern for a leafy look; dark creases separate the leaf clumps.
`scatter()` places trees and 1–3-flower patches randomly on both sides of the road; `main.py` draws them
depth-sorted together with the road objects.

### 5.14 `game/world/level.py` — levels, randomization and fairness

- `load_level(file, rng)`: reads `levels/levelN.json`, builds objects (`build_object`), appends the boss
  behind the finish line. With an `rng` it also calls `randomize_gates` and `randomize_obstacles`.
- `best_count(level)`: the best possible final count (greedy: always take the bigger gate; proven optimal
  because every operation is monotonic — more people in always means more people out).
- `run_count`, `fatal_gates`, `max_wrong_picks` (recursive search over every right/wrong choice) and
  `difficulty(level)` = a 0–100 score: fatal gates (40) + strictness (25) + speed (15) + obstacle count (20).
- `randomize_gates`: changes each gate's number (and sometimes swaps sides) but only keeps a change if
  the difficulty score stays **exactly** the same.
- `dodge_spans` / `randomize_obstacles`: walk along the best route, keeping the set of x-intervals the
  crowd can reach in time (reach = side speed × time); each obstacle cuts out its swept area. An obstacle
  layout is accepted only if a wide enough safe gap remains → every random layout is dodgeable.

### 5.15 `game/ui.py` — screens

`draw_menu` (background picture, see-through level rows with difficulty bars, stars, best count, locks,
mouse/keyboard highlight, and the "Music & Sound" button with a speaker icon that shows ✕ when all
sound is off), `draw_hud` (level name and progress bar), `draw_sound_panel` + `pause_layout` (title,
sliders and on/off boxes; the layout function is shared by drawing and mouse hit-testing so they always
match), used by both `draw_pause` (adds R/M and "Press ESC to continue") and `draw_sound_settings`
(the smaller panel opened from the menu, "Press ESC to go back"), `draw_end` (box sized to its lines; over-wide text is shrunk with `fit_text` so nothing overflows),
`draw_popups` (floating numbers that rise and fade), `draw_tips` (first-level hints).

### 5.16 Level files (`levels/*.json`)

```json
{
  "name": "Level 11 - Example",
  "start_count": 20,
  "speed": 320,
  "finish_z": 6000,
  "boss": {"kind": 2, "count": 125},
  "objects": [
    {"type": "gate_pair", "z": 700,  "left": ["+", 20], "right": ["x", 2]},
    {"type": "obstacle",  "z": 1200, "x": -75, "width": 150},
    {"type": "enemy",     "z": 2500, "count": 80}
  ]
}
```

Gate operators are `"+"`, `"-"`, `"x"`, `"/"`. Obstacle `x`/`width` are only used without randomization
(tests); in play they are re-randomized. New `levelN.json` files appear in the menu automatically
(sorted by number). Run the tests after editing a level: they check every level is winnable, dodgeable and
harder than the previous ones.

### 5.17 Tests and tools

- `tests/test_logic.py`: gate maths, obstacle hits, crowd size, enemy fights and charging, boss phases
  (approach, intro, never-repeating moves), level fairness (winnable, dodgeable, difficulty ordering),
  randomization keeps difficulty, stars/high scores/unlocking.
- `tools/make_menu_bg.py`: renders the menu background with the game's own `draw_world()` using a special
  camera (low, offset to the side), then adds the enemies, clouds and a big running player.

---

## 6. Assets

`assets/16x32/` character sprite sheets (Idle, Run, Attack, …; 32×32 frames, 5 directions) and
`assets/menu_bg.png` (generated by `tools/make_menu_bg.py`). Everything else (road, grass, clouds, trees,
flowers, bosses, sound effects) is generated in code. Background music: `game/core/music/*.mp3`.
