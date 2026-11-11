# Minecraft Build & Game-Logic Reference

This is the knowledge base for agents working in this folder. It explains how
to think about Minecraft builds, redstone, entities, items, and the export
formats used by the `mcba` Python package.

- Target: **Java Edition 1.21.1**, data version **3955**, unless a section says
  otherwise. Java and Bedrock redstone differ; the schematics here are Java
  formats.
- Coordinates used by `mcba`: `+X` = east, `+Y` = up, `+Z` = south.
  A block position is the corner with the smallest coordinates.
- The game runs at **20 game ticks per second** (1 tick = 50 ms). A
  **redstone tick** is 2 game ticks (0.1 s). Most redstone components work in
  redstone-tick steps; dust updates every game tick.
- In this document "block" means a block state (id plus properties), not just
  the id. Two states of the same block can behave differently.

The package API is summarized at the end of each relevant section and in
`README.md`. Run `python -m mcba --help` for the CLI.

---

## 1. World, coordinates, and limits

| Thing | Java 1.21 value |
| --- | --- |
| World height | Y = -64 to 319 (384 blocks) |
| Chunk | 16 x 16 columns, full world height |
| Build limit | Y = 320 (blocks cannot be placed at 320) |
| Sea level | Y = 63 (approximately) |
| Simulation distance | server setting; affects redstone/entity ticking |
| Overworld day | 24,000 ticks = 20 minutes |
| Normal mob despawn | 128 blocks from player (hostile) |
| Random tick | each chunk section gets random ticks per game tick |

Directions and offsets used by `mcba`:

| Direction | Offset `(dx,dy,dz)` | Axis |
| --- | --- | --- |
| north | `(0,0,-1)` | -Z |
| south | `(0,0,+1)` | +Z |
| west | `(-1,0,0)` | -X |
| east | `(+1,0,0)` | +X |
| up | `(0,+1,0)` | +Y |
| down | `(0,-1,0)` | -Y |

`facing=north` means the block's front points north. For stairs, `facing` is
the direction the **ascending side** faces (the high side is opposite the
facing direction). For observers and pistons, `facing` is the direction the
functional face points; see the component tables.

---

## 2. Versions, data versions, and formats

Data version is what tells Minecraft how to interpret block states and item
data. The writers in `mcba` stamp `MinecraftDataVersion` / `DataVersion`.

| Minecraft Java | Data version | Notes |
| --- | --- | --- |
| 1.13.2 | 1631 | flattening, first modern block states |
| 1.18 | 2860 | new world height |
| 1.19.2 | 3120 | Litematica subversion 1 threshold |
| 1.20.5 | 3837 | item components replace item tags; Litematica v7 |
| 1.21 | 3953 | |
| 1.21.1 | 3955 | **default in this package** |
| 1.21.4 | 4189 | |
| 1.21.5 | 4325 | equipment field, SNBT text components |
| 1.21.8 | 4440 | |
| 1.21.9 | 4554 | |
| 1.21.10 | 4556 | |
| 1.21.11 | 4671 | |
| 26.1 | 4786 | future/experimental naming in some tools |
| 26.2 | 4903 | |

Litematica file version chosen by `schematic_version_for_data_version`:

| Data version | Litematica `Version` | `SubVersion` |
| --- | --- | --- |
| < 1631 | 4 | absent |
| 1631 .. 2859 | 5 | absent |
| 2860 .. 3119 | 6 | absent |
| 3120 .. 3836 | 6 | 1 |
| >= 3837 | 7 | 1 |

Sponge `.schem`: use **v2** for maximum tool compatibility; v3 is supported by
newer WorldEdit/FAWE. Both are gzip-compressed NBT.

Important: Minecraft ignores unknown block-state properties in many contexts,
but missing required properties can produce a state the game repairs or
rejects. Always emit complete states when you care about exact appearance.
`mcba`'s block factories do this for common blocks.

---

## 3. Block states

### 3.1 Syntax

```
minecraft:oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]
```

- Namespace defaults to `minecraft:` when omitted.
- Property names and values are lower-case snake_case.
- Booleans are written `true` / `false`.
- Order of properties does not matter; `mcba` sorts them for stable output.

In `mcba`:

```python
from mcba import Build
b = Build("states")
b.set(0, 0, 0, "oak_stairs", facing="north", half="bottom")
b.set(1, 0, 0, "minecraft:oak_stairs[facing=east]")
b.set(2, 0, 0, "redstone_wire", power=7)   # incomplete state, avoid in real builds
b.set(3, 0, 0, "oak_log", axis="x")
```

Prefer the factories (`stairs`, `slab`, `wall`, `fence`, `pane`, `door`,
`trapdoor`, `piston`, `observer`, `repeater`, `comparator`, `redstone_wire`,
`rail`, ...) when a block has many properties.

### 3.2 Property tables

#### Stairs (`*_stairs`)

| Property | Values | Meaning |
| --- | --- | --- |
| `facing` | north/south/west/east | direction the high side faces |
| `half` | bottom/top | normal or upside-down |
| `shape` | straight/inner_left/inner_right/outer_left/outer_right | corner shape |
| `waterlogged` | true/false | contains water |

#### Slabs (`*_slab`)

| Property | Values |
| --- | --- |
| `type` | bottom/top/double |
| `waterlogged` | true/false |

#### Walls (`*_wall`)

| Property | Values |
| --- | --- |
| `north`, `east`, `south`, `west` | none/low/tall |
| `up` | true/false |
| `waterlogged` | true/false |

Walls connect to solid blocks and to other walls. A wall with `up=false` is a
wall post without the central pillar.

#### Fences (`*_fence`) and panes (`*_pane`)

| Property | Values |
| --- | --- |
| `north`, `east`, `south`, `west` | true/false |
| `waterlogged` | true/false |

#### Doors (`*_door`)

Two blocks: lower and upper half. Both halves must exist and share `facing`,
`hinge`, and `open`; only the lower half has `powered`.

| Property | Values |
| --- | --- |
| `facing` | north/south/west/east (direction the door faces when closed) |
| `half` | lower/upper |
| `hinge` | left/right |
| `open` | true/false |
| `powered` | true/false (lower half only) |

#### Trapdoors (`*_trapdoor`)

| Property | Values |
| --- | --- |
| `facing` | north/south/west/east |
| `half` | top/bottom |
| `open` | true/false |
| `powered` | true/false |
| `waterlogged` | true/false |

#### Fence gates (`*_fence_gate`)

| Property | Values |
| --- | --- |
| `facing` | north/south/west/east |
| `in_wall` | true/false |
| `open` | true/false |
| `powered` | true/false |

#### Levers

| Property | Values |
| --- | --- |
| `face` | floor/wall/ceiling |
| `facing` | north/south/west/east (the direction the lever points) |
| `powered` | true/false |

#### Buttons (`*_button`)

| Property | Values |
| --- | --- |
| `face` | floor/wall/ceiling |
| `facing` | north/south/west/east |
| `powered` | true/false |

Stone buttons stay pressed for 1 second (20 ticks); wooden buttons for 1.5 s
(30 ticks). A button is a pulse source, not a switch.

#### Pressure plates

| Block | Property |
| --- | --- |
| wooden/stone/weighted plates | `powered` true/false |
| weighted plates | analog signal 1..15 based on entities/items |

#### Redstone wire (`redstone_wire`)

| Property | Values |
| --- | --- |
| `power` | 0..15 |
| `north`, `east`, `south`, `west` | none/side/up |
| `waterlogged` | true/false (unused in normal play) |

Dust connects to adjacent dust, components, and blocks with a redstone
connection. `side`/`up` describe visual connections; power still follows the
rules in section 4.

#### Repeater (`repeater`)

| Property | Values |
| --- | --- |
| `facing` | north/south/west/east (output direction) |
| `delay` | 1..4 (redstone ticks; 2..8 game ticks) |
| `locked` | true/false |
| `powered` | true/false |

#### Comparator (`comparator`)

| Property | Values |
| --- | --- |
| `facing` | north/south/west/east (output direction) |
| `mode` | compare/subtract |
| `powered` | true/false |

#### Piston / sticky piston

| Property | Values |
| --- | --- |
| `facing` | north/south/west/east/up/down |
| `extended` | true/false |

The piston head block (`piston_head`) has `facing`, `type` (normal/sticky),
and `short` (true/false).

#### Observer

| Property | Values |
| --- | --- |
| `facing` | north/south/west/east/up/down (the **output** side) |
| `powered` | true/false |

The observer's input face is opposite `facing`.

#### Rails

| Block | Properties |
| --- | --- |
| `rail` | `shape` (north_south, east_west, ascending_*, curved_*) |
| `powered_rail` | `shape`, `powered` |
| `detector_rail` | `shape`, `powered` |
| `activator_rail` | `shape`, `powered` |

#### Logs and wood

| Property | Values |
| --- | --- |
| `axis` | x/y/z |
| `wood` (`*_wood`, `*_hyphae`) | `axis` |

#### Leaves

| Property | Values |
| --- | --- |
| `persistent` | true/false |
| `distance` | 1..7 |
| `waterlogged` | true/false |

Set `persistent=true` for decorative leaves that should not decay.

#### Containers and functional blocks

| Block | Key properties |
| --- | --- |
| `chest`, `trapped_chest`, `barrel` | `facing` (chest/barrel); chest has `type` single/left/right |
| `furnace`, `blast_furnace`, `smoker` | `facing`, `lit` |
| `hopper` | `facing` (down/north/south/west/east), `enabled` |
| `dispenser`, `dropper` | `facing`, `triggered` |
| `observer` | see above |
| `note_block` | `instrument`, `note` 0..24, `powered` |
| `jukebox` | `has_record` |
| `lectern` | `facing`, `has_book`, `powered` |
| `campfire` | `facing`, `lit`, `signal_fire`, `waterlogged` |
| `candle` | `candles` 1..4, `lit`, `waterlogged` |
| `sign` / `wall_sign` | `rotation` 0..15 (floor) or `facing` (wall), `waterlogged` |
| `bed` | `facing`, `part` foot/head, `occupied` |
| `banner` / `wall_banner` | `rotation` 0..15 or `facing` |

#### Crops and plants

| Block | Properties |
| --- | --- |
| `wheat`, `carrots`, `potatoes`, `beetroots` | `age` 0..7 (beetroots 0..3) |
| `sweet_berry_bush` | `age` 0..3 |
| `nether_wart` | `age` 0..3 |
| `cocoa` | `age` 0..2, `facing` |
| `pumpkin_stem`, `melon_stem` | `age` 0..7 |
| `sugar_cane`, `bamboo`, `cactus` | `age` (growth stage) |
| `sapling` | `stage` 0/1 |
| `big_dripleaf` | `facing`, `tilt`, `waterlogged` |
| `glow_lichen`, `sculk_vein`, `vine` | `north/east/south/west/up/down` booleans |

### 3.3 Material families

Woods: `oak`, `spruce`, `birch`, `jungle`, `acacia`, `dark_oak`, `mangrove`,
`cherry`, `bamboo`, `crimson`, `warped`, `pale_oak`.

Colours: `white`, `orange`, `magenta`, `light_blue`, `yellow`, `lime`, `pink`,
`gray`, `light_gray`, `cyan`, `purple`, `blue`, `brown`, `green`, `red`,
`black`.

Common stone families: `stone`, `cobblestone`, `mossy_cobblestone`,
`stone_bricks`, `mossy_stone_bricks`, `cracked_stone_bricks`,
`chiseled_stone_bricks`, `granite`, `polished_granite`, `diorite`,
`polished_diorite`, `andesite`, `polished_andesite`, `deepslate`,
`cobbled_deepslate`, `polished_deepslate`, `deepslate_bricks`,
`deepslate_tiles`, `tuff`, `polished_tuff`, `tuff_bricks`, `calcite`,
`dripstone_block`, `blackstone`, `polished_blackstone`,
`polished_blackstone_bricks`, `basalt`, `smooth_basalt`, `sandstone`,
`smooth_sandstone`, `cut_sandstone`, `red_sandstone`, `brick`, `mud_bricks`,
`quartz_block`, `smooth_quartz`, `purpur_block`, `end_stone_bricks`,
`prismarine`, `prismarine_bricks`, `dark_prismarine`, `nether_bricks`,
`red_nether_bricks`.

Naming traps:

- `spruce_planks` -> `spruce_stairs`, not `spruce_planks_stairs`.
- `stone_bricks` -> `stone_brick_stairs` (singular `brick`).
- `deepslate_tiles` -> `deepslate_tile_stairs`.
- `quartz_block` -> `quartz_stairs` / `quartz_slab`.
- `purpur_block` -> `purpur_stairs` / `purpur_slab`.
- `mud_bricks` -> `mud_brick_stairs`.
- Not every material has stairs or slabs; verify before use.

---

## 4. Redstone fundamentals

### 4.1 Signal and power

- Signal strength is 0..15. Most sources emit 15.
- **Power sources**: redstone block (15), lever (15), button (15 pulse),
  pressure plate (15 or analog), redstone torch (15), repeater (15),
  comparator (0..15), observer (15 pulse), daylight detector (0..15), target
  block (0..15), trapped chest (0..15), weighted plate (1..15), sculk sensor
  (1..15), lightning rod (15 pulse), detector rail (15 pulse).
- **Transmission**: redstone dust (loses 1 per dust block), repeaters
  (restore to 15), comparators (pass or subtract).
- **Mechanisms**: piston, sticky piston, dispenser, dropper, hopper (lock),
  redstone lamp, note block, powered rail, activator rail, door, trapdoor,
  fence gate, TNT, redstone torch (as an input), bell, copper bulb, crafter.

### 4.2 Strong vs weak power

- A **strongly powered** solid block powers adjacent redstone dust.
- A **weakly powered** solid block powers mechanisms and repeaters/comparators
  next to it but does **not** power adjacent dust.
- Strong power sources into a block: repeater/comparator pointing into it,
  redstone torch under it, observer facing into it, lever/button/tripwire
  hook/lightning rod attached to it, pressure plate/detector rail/trapped
  chest/lectern/sculk sensor on top of it.
- Dust on top of, or pointing into, a solid block weakly powers that block.

This is why a repeater can power a block and then dust next to that block, but
dust alone cannot do the same.

### 4.3 Redstone dust rules

- Dust takes the strongest input and decreases by 1 for each dust block.
  A 15 source reaches 15 dust blocks; the 16th is unpowered.
- Dust can go up or down one block at a time on adjacent columns, but a solid
  block directly above dust cuts its upward connection.
- Dust does not power through solid blocks. It powers mechanisms and
  repeaters/comparators it points into, and weakly powers the block beneath.
- Dust connects visually to adjacent dust and to components; a component can
  be selectively connected by right-clicking, but schematics store the
  resulting `north/east/south/west` values.
- Dust updates every game tick, so it can carry 1-game-tick pulses even though
  most components work in 2-tick steps.

### 4.4 Redstone torch

- Output 15; turns off when the block it is attached to is powered (or the
  block above it, for a floor torch).
- Turns on with no delay; turns off after 1 redstone tick (2 game ticks).
- **Burnout**: if it turns off 8 times within 60 game ticks (3 s), it stays off
  and ignores updates. It checks again after about 160 game ticks (8 s), and
  relights only if it has had fewer than 8 off-events in the last 3 s.
- A redstone torch strongly powers the block above it. It is the classic
  inverter and the basis of many compact clocks.

### 4.5 Repeater

- Delay 1..4 redstone ticks (2..8 game ticks).
- Restores signal to 15; only passes power from back to front.
- Can be locked by a powered repeater or comparator pointing into its side;
  while locked it keeps its output and ignores the back input.
- A repeater pointing into a solid block strongly powers that block.
- Repeaters do not pass analog strength; they output 15 when powered.

### 4.6 Comparator

- Delay 1 redstone tick (2 game ticks).
- **Compare mode**: output = back input, unless a side input is stronger, in
  which case output = 0.
- **Subtract mode**: output = back input - strongest side input, minimum 0.
- Side inputs can be dust, a redstone block, or a repeater/comparator pointing
  into the side.
- Reads container fullness, cake, cauldron, composter, lectern, jukebox,
  respawn anchor, bee nest/hive, decorated pot, command block, end portal
  frame, and (through one solid block) the block behind it or an item frame.
- Comparator output for containers is based on fullness, not item count; a
  nearly full container outputs 15.
- Comparator can read a block through one solid block, which enables hidden
  detectors.

### 4.7 Observer

- Watches the block/fluid/air in front of its input face; when a block state
  changes, it emits a **15-strength pulse for 2 game ticks** (1 redstone tick)
  from its output face, after a **2-game-tick delay**.
- It detects block state changes (including shape updates), not entity
  movement or inventory changes.
- Moving an observer with a piston can produce a pulse; this is the basis of
  flying machines. Behavior when moved while already pulsing differs by
  version.
- Observers strongly power the block they face on the output side.

### 4.8 Pistons and sticky pistons

- A piston pushes up to **12 blocks** total (including the block directly in
  front and blocks dragged by slime/honey).
- Movement takes 2 game ticks; blocks become normal on the next tick.
- Sticky pistons pull the block in front when retracting, unless it is
  immovable or a glazed terracotta (push-only).
- Slime blocks drag adjacent blocks; honey blocks drag but do not stick to
  slime. Both can move entities.
- Immovable blocks include obsidian, crying obsidian, bedrock, reinforced
  deepslate, respawn anchor, lodestone, anvils, grindstone, end portal frame,
  extended pistons, and most block entities (chests, furnaces, hoppers,
  jukeboxes, beacons, etc.).
- Fragile blocks (torches, plants, dust, rails, etc.) break when pushed.
- **Quasi-connectivity (QC)**: pistons, sticky pistons, dispensers, and
  droppers also react to power in the block **directly above** the piston
  base, even though that block is not visually connected. This is a Java
  Edition quirk and is widely used in hidden doors and farms. Newer versions
  have not removed it; verify behavior for your target version.
- A piston that cannot push its full block set does not extend.
- 0-tick and 1-tick piston behavior has changed across versions; do not rely
  on sub-tick tricks unless the target version is fixed and tested.

### 4.9 Update order and pulses

- Block updates propagate in a version-dependent order. Two identical-looking
  circuits can behave differently depending on which block updates first.
- A **block update detector (BUD)** reacts to updates that do not change the
  visible state. Observers replaced most BUD use, but QC pistons still act as
  BUDs.
- **1-tick pulse**: a pulse lasting one game tick. Dust can carry it; many
  components cannot react to it.
- **0-tick pulse**: a pulse shorter than a game tick, historically used to
  move blocks instantly. Behavior is version-specific and often patched.
- **Monostable**: turns any input pulse into a fixed-length output pulse.
- **Edge detector**: emits only on rising or falling edge.
- **Pulse extender**: lengthens a short pulse (repeater chain, comparator
  fade-out, piston-based extender).
- **Clock**: repeating pulse. Repeater loop, observer loop, hopper clock,
  comparator clock, daylight sensor clock. Repeater loops are the most
  predictable.

### 4.10 Lag and reliability

- Every powered component and every scheduled tick costs CPU. Large dust
  networks, observer clocks, and hopper arrays are common lag sources.
- Chunk unloading stops redstone and entity ticks; circuits spanning chunk
  borders can behave unexpectedly.
- Use repeaters to isolate long lines and to avoid update-order surprises.
- Prefer observers over complex BUDs when possible.
- Test circuits in the target version; redstone is not fully portable between
  versions.

---

## 5. Redstone circuit cookbook

These are conceptual layouts. Build them with `mcba` by placing dust, torches,
repeaters, and solid blocks. Directions assume the signal flows along +X unless
noted.

### 5.1 Logic gates

| Gate | Idea | Notes |
| --- | --- | --- |
| NOT | torch inverter | input powers block, torch turns off |
| AND | two inputs into one dust line with a repeater | output only when both on |
| OR | two dust lines merge | output when either on |
| XOR | two paths, one inverted, then AND/OR | classic 3-torch or comparator design |
| NAND | AND then NOT | |
| NOR | OR then NOT | |
| XNOR | XOR then NOT | equality detector |

Truth tables (1 = powered):

```
AND: 00->0 01->0 10->0 11->1
OR:  00->0 01->1 10->1 11->1
XOR: 00->0 01->1 10->1 11->0
```

Compact XOR with comparators: feed both inputs into the back and side of a
comparator in subtract mode; the output is the difference, which is 0 when
equal and non-zero when different. Combine with a comparator compare stage to
get a digital XOR.

### 5.2 Clocks

- **Repeater loop**: dust ring with a repeater; period = 2 x (repeater delay) +
  dust travel. Reliable, easy to tune.
- **Observer clock**: two observers facing each other; each pulse triggers the
  other. Period is short (about 4 game ticks end-to-end). Use a repeater to
  slow it down.
- **Hopper clock**: items circulating between two hoppers; period depends on
  item count. Good for long, adjustable periods.
- **Comparator clock**: comparator in subtract mode feeding its own side
  through a block; period set by the comparator delay and dust.
- **Daylight sensor clock**: inverted daylight detector plus repeater; pulses
  at dawn/dusk.

### 5.3 Latches and memory

- **RS latch (NOR)**: two cross-coupled NOR gates. Set and reset inputs;
  output remembers the last set/reset.
- **RS latch (NAND)**: two cross-coupled NAND gates; inputs are active-low.
- **T flip-flop**: toggles on each input pulse. Build with a sticky piston,
  observer, or comparator memory cell.
- **D flip-flop**: captures input on a clock edge; used in registers.
- **Memory cell**: repeater loop holding a state, or a comparator reading a
  container. Use a locked repeater to freeze a value.
- **Counter**: chain of T flip-flops or a comparator reading a hopper with a
  known item count.

### 5.4 Pulse shaping

- **Pulse extender**: input charges a comparator; the comparator's fading
  output drives the load. Length depends on the comparator's side signal.
- **Monostable**: input triggers a repeater loop that runs once, then resets.
- **Rising-edge detector**: input and a delayed input feed an AND gate; output
  only on the transition.
- **Falling-edge detector**: invert one input before the AND.
- **Pulse limiter**: repeater with a short delay to ignore too-fast inputs.

### 5.5 Adders and arithmetic

- **Half adder**: XOR for sum, AND for carry.
- **Full adder**: two half adders plus an OR for carry.
- **Ripple-carry adder**: chain full adders; carry propagates left.
- **Subtractor**: add the two's complement (invert bits and add 1).
- **Comparator analog adder**: comparator in add mode? Vanilla comparators do
  not add directly; use subtract mode and signal strength encoding, or build
  digital adders.

### 5.6 Item handling

- **Hopper pipe**: hoppers move one item every 8 game ticks (2.5 items/s).
  A hopper with a redstone signal is disabled.
- **Item sorter**: a row of hoppers with a comparator reading a hopper that
  contains a filter. A repeater locks the hopper when the signal is strong
  enough; overflow goes to the next hopper.
- **Overflow protection**: a second hopper or a comparator threshold prevents
  the sorter from filling with junk.
- **Super smelter**: array of furnaces fed by hoppers, with fuel and output
  collection; use minecart chests or hopper lines for scale.
- **Auto farm**: observer detects crop growth; piston or dispenser harvests;
  hopper minecart collects. Water streams move items.
- **Storage system**: chests + hoppers + comparators for fullness readout;
  double chests share inventory.
- **Dropper elevator**: droppers facing up move items vertically; a hopper at
  the top collects.
- **Water elevator**: soul sand bubble column up, magma block down; items and
  entities rise/fall. Use signs or trapdoors to break water flow where needed.

### 5.7 Doors and hidden entrances

- **Piston door**: sticky pistons pull blocks into the wall; use slime blocks
  for 2x2 or larger doors.
- **Hidden door**: a wall section moved by pistons; use QC or observers to
  trigger. Keep the mechanism behind the wall.
- **Vault door**: rotating piston arrays; test push limits and block updates.
- **Drawbridge**: slime-block chain with pistons; ensure no immovable blocks.
- **Secret staircase**: piston-pushed stairs; use a memory cell to hold state.

### 5.8 Transport

- **Powered rail**: boost minecarts; power every 8th rail or use a powered
  rail line with redstone blocks. A powered rail powers up to 8 rails along a
  connected line.
- **Detector rail**: emits a pulse when a minecart passes; use for stations.
- **Activator rail**: activates TNT minecarts, hopper minecarts, and
  minecarts with mobs; can eject riders.
- **Boat ice road**: blue ice + boats for fast travel; pack ice for normal
  boats.
- **Entity elevator**: bubble columns or piston/slime launchers.
- **Flying machine**: observer + piston + slime block; moves itself. Beware of
  chunk borders and version-specific observer behavior.

---

## 6. Building techniques

### 6.1 Plan the build before placing blocks

1. Decide the footprint (x/z) and height (y). Keep the origin at a round
   coordinate; `mcba` uses the minimum corner for export.
2. Block out the silhouette with cheap full blocks (`stone`, `dirt`) first.
3. Choose a palette of 3-6 blocks: a main material, a secondary, a trim, a
   roof, and 1-2 accents.
4. Add depth: frames, overhangs, recessed windows, columns.
5. Add texture: mix variants (stone bricks, cracked, mossy) deterministically.
6. Add lighting, landscaping, and interiors.
7. Export, reload with `mcba`, and inspect the block counts and bounds.

### 6.2 Palette rules

- Use one dominant material family (e.g., oak + cobblestone + spruce roof).
- Use a darker trim for edges and a lighter accent for highlights.
- Limit the number of colours; 3-5 is usually enough.
- Warm palettes: oak, spruce, brick, terracotta, sandstone.
- Cool palettes: stone, deepslate, prismarine, warped/crimson, blue ice.
- Natural palettes: mossy cobblestone, moss, azalea leaves, roots.
- Avoid placing every variant randomly; use clusters and gradients.

### 6.3 Gradients and texturing

Vertical gradient (ground to sky):

```
deepslate -> tuff -> stone -> andesite -> calcite
```

Depth gradient (front to back):

```
cobblestone -> stone_bricks -> stone -> smooth_stone
```

Texturing pattern (deterministic, no randomness needed):

```python
from mcba import Build
b = Build("wall")
materials = ["stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks"]
for x in range(20):
    for y in range(8):
        block = materials[(x * 3 + y * 5) % len(materials)]
        b.set(x, y, 0, block)
```

Use a hash-like formula rather than `random` so the build is reproducible.

### 6.4 Depth and silhouette

- Add a 1-block frame around walls; make the frame a different material.
- Recess windows by 1 block and add a sill and lintel.
- Add overhanging eaves and roof trim.
- Use buttresses, pilasters, or quoins at corners.
- Break long flat walls with columns, arches, or a change in material.
- Vary the roofline: gables, dormers, chimneys, towers.
- Avoid perfectly square footprints; add an L-shape, a bay, or a porch.

### 6.5 Roofs

- **Gable**: two slopes meeting at a ridge. `mcba` has `gable_roof`.
- **Hip**: four slopes meeting at a ridge; build with stairs and slabs.
- **Shed**: one slope; simple and modern.
- **Mansard**: steep lower slope + shallow upper slope.
- **Spire**: steep pyramid, often on towers.
- **Flat**: parapet, roof garden, or terrace.
- **Curved**: layer stairs/slabs to approximate a curve; use slabs for half
  steps.
- Overhang the roof by 1 block; add a trim line at the eave.
- Use stairs for the slope and slabs for the ridge; alternate materials for
  shingles.

`mcba` gable roof:

```python
b.gable_roof(0, 0, 9, 6, 4, "spruce_planks")          # ridge along X
b.gable_roof(0, 0, 6, 9, 4, "spruce_planks", ridge_axis="z")
```

The helper derives `spruce_stairs` and `spruce_slab` from
`spruce_planks`. Pass `stair_block=` and `slab_block=` to override.

### 6.6 Walls, windows, and doors

- Wall thickness: 1 block for small builds, 2 for large; a 2-block wall lets
  you recess windows and run lighting.
- Windows: glass panes, fences, or trapdoors; add a frame of stairs/slabs.
- Doors: 2 blocks high; use a 3-block opening for a grand entrance.
- Arches: stairs upside down and right side up to approximate a curve.
- Half-timbering: dark oak logs as a frame with white terracotta/plaster
  infill.
- Quoins: alternate stone blocks at corners for a rugged look.
- Buttresses: vertical supports every 3-5 blocks on large walls.

### 6.7 Interiors

- Floor: wood planks, stone, or carpet over a solid floor.
- Ceiling: slabs or trapdoors for detail; avoid a flat solid slab if you want
  depth.
- Lighting: lanterns, candles, glowstone behind trapdoors, sea lanterns,
  froglight, copper bulbs.
- Furniture: stairs as chairs, slabs as tables, barrels/chests as storage,
  item frames and paintings for decoration.
- Use a consistent room height (3-4 blocks); large halls need columns.
- Add a focal point: fireplace, window, staircase, or artwork.

### 6.8 Terrain and landscaping

- Build terrain in layers: stone core, dirt subsoil, grass/snow surface.
- Use `sphere`/`ellipsoid` for boulders and hills; `cylinder` for tree trunks
  and towers.
- Trees: `b.tree(x, y, z, height=6, log_material="oak")`.
- Paths: coarse dirt, gravel, cobblestone, or packed mud; vary the edges.
- Water: dig a basin, line it, and add a water source; use slabs/stairs for
  banks.
- Cliffs: exposed stone with dirt/grass on top; add vines and overhangs.
- Ruins: break symmetry, add missing blocks, moss, cracks, and overgrowth.
- Snow: layer snow on top of solid blocks; use powder snow for depth.

### 6.9 Scale and proportion

- Human scale: door 2 blocks, ceiling 3-4, room 5-8 wide.
- Large builds: increase wall thickness and detail size; a 1-block detail
  disappears at distance.
- Use the golden ratio or simple ratios (1:1, 1:2, 2:3) for facades.
- Keep roof pitch consistent with the style: steep for Gothic, shallow for
  modern.
- Leave space around the build for landscaping and viewing.

### 6.10 Lighting and mood

- Light levels: torch 14, lantern 15, glowstone 15, sea lantern 15, candle 3
  per candle (up to 12), campfire 15.
- Warm light: torches, lanterns, campfires, candles, lava.
- Cool light: soul lanterns/torches (blue), sea lanterns, prismarine.
- Hide light sources behind trapdoors, carpets, or leaves for soft light.
- Avoid lighting every surface; contrast creates atmosphere.

### 6.11 Determinism and review

- Use deterministic patterns (coordinate math) instead of random.
- Keep a `meta` dict for notes (style, palette, version).
- After export, reload and print `block_counts()`; look for accidental
  `air`, missing stairs, or wrong materials.
- Render/inspect in-game or with a schematic viewer before sharing.

---

## 7. Entities and mobs

Entities are stored separately from blocks. `mcba` writes them into both
Litematica and Sponge files.

```python
b.add_entity("minecraft:armor_stand", 2.5, 1.0, 2.5, {
    "NoGravity": True,
    "Invisible": True,
    "ShowArms": True,
    "Pose": {
        "RightArm": [nbt.F(-30), nbt.F(0), nbt.F(0)],
        "Head": [nbt.F(10), nbt.F(20), nbt.F(0)],
    },
})
```

`Pos` is filled by `mcba`; do not pass it. `add_entity` takes world
coordinates. In Litematica files, `Pos` is relative to the region position;
`mcba` handles that conversion.

### 7.1 Common entity fields

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | entity id, e.g. `minecraft:zombie` |
| `Pos` | list of 3 doubles | world position (set by `mcba`) |
| `Motion` | list of 3 doubles | velocity |
| `Rotation` | list of 2 floats | yaw, pitch |
| `CustomName` | string (JSON text) | name tag; 1.21.5+ may be inline text |
| `CustomNameVisible` | byte | always show name |
| `NoGravity` | byte | float in place |
| `Invulnerable` | byte | cannot take damage |
| `Silent` | byte | no sounds |
| `NoAI` | byte | no movement/behavior |
| `Glowing` | byte | glowing outline |
| `Tags` | list of strings | scoreboard/command tags |
| `Passengers` | list of compounds | riders |
| `Fire` | short | ticks remaining on fire |
| `Air` | short | air ticks remaining |
| `PortalCooldown` | int | ticks before portal use |
| `PersistenceRequired` | byte | never despawn |
| `Health` | float | current health |
| `AbsorptionAmount` | float | absorption hearts |
| `ActiveEffects` | list | potion effects |
| `HandDropChances` | list of floats | equipment drop chance |
| `ArmorDropChances` | list of floats | armor drop chance |

Equipment format:

- **1.20.4 and earlier**: `HandItems` (mainhand, offhand) and `ArmorItems`
  (feet, legs, chest, head) as lists of item compounds with `id`, `Count`,
  `tag`.
- **1.20.5 .. 1.21.4**: still `HandItems` / `ArmorItems`, but each item uses
  the new stack format `id`, `count`, `components`.
- **1.21.5+**: a single `equipment` compound keyed by slot: `head`, `chest`,
  `legs`, `feet`, `mainhand`, `offhand`, `body`, `saddle`; each value is an
  item stack with `id`, `count`, `components`.

Use the format for the target data version. `mcba` does not convert between
them.

### 7.2 Mob catalog (common)

| Entity id | Notes and key NBT |
| --- | --- |
| `minecraft:zombie` | `IsBaby`, `CanBreakDoors`, `HandItems`/`equipment` |
| `minecraft:husk` | desert zombie; no drowning |
| `minecraft:drowned` | water zombie; `HandItems` trident |
| `minecraft:skeleton` | bow; `HandItems` |
| `minecraft:stray` | slowness arrows |
| `minecraft:wither_skeleton` | Nether; wither effect |
| `minecraft:creeper` | `powered`, `ExplosionRadius`, `Fuse`, `ignited` |
| `minecraft:spider` | `Size`? (cave spider uses `Size`-like behavior) |
| `minecraft:cave_spider` | poison |
| `minecraft:enderman` | `carriedBlockState`, anger |
| `minecraft:witch` | potions; `HandItems` |
| `minecraft:slime` | `Size` 1/2/4 |
| `minecraft:magma_cube` | `Size` |
| `minecraft:ghast` | fireballs |
| `minecraft:blaze` | fireballs |
| `minecraft:piglin` | `CannotHunt`, `IsBaby`, `Inventory` |
| `minecraft:piglin_brute` | |
| `minecraft:hoglin` | |
| `minecraft:zoglin` | |
| `minecraft:villager` | `VillagerData`, `Offers`, `Xp`, `Age` |
| `minecraft:wandering_trader` | `Offers`, `DespawnDelay` |
| `minecraft:iron_golem` | `PlayerCreated` |
| `minecraft:snow_golem` | `Pumpkin` |
| `minecraft:wolf` | `Owner`, `Sitting`, `Tame`, `CollarColor` |
| `minecraft:cat` | `Owner`, `Sitting`, `Tame`, `variant` |
| `minecraft:ocelot` | `Trusting` |
| `minecraft:horse` | `Tame`, `SaddleItem`, `ArmorItem`, `Variant` |
| `minecraft:donkey` | chest inventory |
| `minecraft:mule` | chest inventory |
| `minecraft:llama` | `Strength`, `DecorItem`, `Items` |
| `minecraft:trader_llama` | |
| `minecraft:sheep` | `Color`, `Sheared` |
| `minecraft:cow` | |
| `minecraft:mooshroom` | `Type` red/brown |
| `minecraft:pig` | `Saddle` |
| `minecraft:chicken` | `IsChickenJockey` |
| `minecraft:rabbit` | `RabbitType` |
| `minecraft:fox` | `Type`, `Sitting`, `Trusted` |
| `minecraft:panda` | `MainGene`, `HiddenGene` |
| `minecraft:polar_bear` | |
| `minecraft:turtle` | |
| `minecraft:axolotl` | `Variant`, `FromBucket` |
| `minecraft:bee` | `HasNectar`, `HasStung`, `TicksInHive`, `HivePos` |
| `minecraft:allay` | `CanDuplicate` |
| `minecraft:frog` | `variant` |
| `minecraft:tadpole` | |
| `minecraft:goat` | `IsScreamingGoat` |
| `minecraft:glow_squid` | |
| `minecraft:squid` | |
| `minecraft:dolphin` | |
| `minecraft:guardian` | |
| `minecraft:elder_guardian` | |
| `minecraft:shulker` | `Color`, `AttachFace` |
| `minecraft:phantom` | `Size` |
| `minecraft:vex` | |
| `minecraft:evoker` | |
| `minecraft:vindicator` | |
| `minecraft:pillager` | |
| `minecraft:ravager` | |
| `minecraft:illusioner` | |
| `minecraft:warden` | |
| `minecraft:ender_dragon` | |
| `minecraft:wither` | |
| `minecraft:bat` | |
| `minecraft:parrot` | `Variant`, `Owner` |
| `minecraft:armor_stand` | see below |
| `minecraft:item_frame` | see below |
| `minecraft:glow_item_frame` | see below |
| `minecraft:painting` | see below |
| `minecraft:item` | dropped item |
| `minecraft:experience_orb` | |
| `minecraft:minecart` | |
| `minecraft:chest_minecart` | `Items` |
| `minecraft:hopper_minecart` | `Items`, `Enabled` |
| `minecraft:tnt_minecart` | |
| `minecraft:furnace_minecart` | |
| `minecraft:boat` | `Type` |
| `minecraft:chest_boat` | `Items` |
| `minecraft:leash_knot` | |
| `minecraft:end_crystal` | `beam_target` |
| `minecraft:firework_rocket` | `FireworksItem`, `Life`, `LifeTime` |
| `minecraft:arrow` | `item`, `damage` |
| `minecraft:trident` | |
| `minecraft:snowball` | |
| `minecraft:egg` | |
| `minecraft:eye_of_ender` | |
| `minecraft:potion` | splash/lingering |
| `minecraft:area_effect_cloud` | |
| `minecraft:marker` | invisible marker |
| `minecraft:interaction` | hitbox |
| `minecraft:display` | display entity (block/item/text) |

### 7.3 Armor stands

| Field | Meaning |
| --- | --- |
| `ShowArms` | show wooden arms |
| `NoBasePlate` | hide the base |
| `Small` | mini size |
| `Invisible` | invisible body, items still show |
| `Marker` | zero-size hitbox |
| `Pose` | `Head`, `Body`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`, each `[x,y,z]` degrees |
| `DisabledSlots` | bit field to lock equipment slots |

Pose values are floats; use `nbt.F(...)` if the game is strict about types.

### 7.4 Item frames and paintings

- Item frame: `Facing` byte (`0` down, `1` up, `2` north, `3` south,
  `4` west, `5` east), `Item` (item stack), `ItemRotation` (`0..7`), `Fixed`,
  `Invisible`, `ItemDropChance`.
- Glow item frame: same, but `id` is `minecraft:glow_item_frame`.
- Painting: `variant` (e.g. `minecraft:kebab`), `facing` (`0` south, `1` west,
  `2` north, `3` east), and `TileX/TileY/TileZ` for the block it occupies.
  Paintings occupy multiple blocks; place the entity at the lower-left block.

### 7.5 Spawners

A monster spawner block entity (`minecraft:mob_spawner`) uses:

| Field | Meaning |
| --- | --- |
| `SpawnData.entity` | entity compound to spawn |
| `SpawnPotentials` | list of `{weight, data:{entity:{...}}}` |
| `SpawnCount` | short, mobs per spawn |
| `SpawnRange` | short, radius |
| `MinSpawnDelay` / `MaxSpawnDelay` | short, ticks |
| `MaxNearbyEntities` | short |
| `RequiredPlayerRange` | short |
| `Delay` | short, ticks until next spawn |

`mcba` helper:

```python
b.spawner(5, 1, 5, "minecraft:zombie")
b.spawner(7, 1, 5, "minecraft:skeleton", spawn_data={"IsBaby": False},
          count=2, min_delay=100, max_delay=300)
```

Spawners only run when a player is within `RequiredPlayerRange` and the
spawn conditions (light, space, block below) are met. Use them for dungeons,
not for guaranteed decorative mobs; use `add_entity` for static mobs.

### 7.6 Mob behavior basics

- **Pathfinding**: mobs use A* over walkable blocks; fences, walls, water,
  and height changes affect paths. Doors can be opened by villagers and some
  mobs; iron doors cannot.
- **Line of sight**: hostile mobs target players within detection range
  (typically 16-35 blocks) and need line of sight; walls and height break it.
- **Spawn conditions**: hostile mobs need a solid block below, space above,
  and low light. In the Overworld since 1.18, block light must be 0 (sky light
  can be up to 7). The Nether allows higher block light; the End requires 0.
- **Despawning**: hostile mobs despawn beyond 128 blocks; passive mobs persist
  more. `PersistenceRequired:1` prevents despawn.
- **Breeding**: animals need food and a pair; baby age is negative ticks.
- **Trading**: villagers need a workstation and bed; `VillagerData` sets
  profession/type/level; `Offers.Recipes` defines trades.
- **Taming**: wolves/cats/horses use `Owner` (UUID) and `Tame`; use a player
  UUID or omit for wild.
- **Leashes**: `leash` on the mob and a `leash_knot` entity; fence knots are
  entity-based.
- **Raid**: triggered by bad omen; pillagers/ravagers/vindicators/evokers/
  witches. Not usually part of a static build.
- **Warden/sculk**: sculk shrieker + sensor; vibrations; wool blocks dampen.
- **Piglins**: barter with gold; `CannotHunt` prevents hunting; they zombify
  in the Overworld.
- **Allays**: pick up items; `CanDuplicate`.
- **Frogs**: eat small magma cubes; `variant` sets color.
- **Axolotls**: play dead; `FromBucket`.

### 7.7 Entity IDs and namespaces

Use full ids (`minecraft:zombie`). `mcba` normalizes missing namespaces. For
modded or newer entities, use the exact registry id; unknown ids may be
dropped or replaced by the game.

---

## 8. Items and block entities

### 8.1 Item stack format

**1.20.5+ (including 1.21.1)**:

```
{id: "minecraft:diamond_sword", count: 1, components: {...}}
```

**Before 1.20.5**:

```
{id: "minecraft:diamond_sword", Count: 1b, tag: {...}}
```

`mcba.chest_with_items` accepts either `components` or `tag` per item.

### 8.2 Common components (1.21.1)

| Component | Value |
| --- | --- |
| `minecraft:custom_name` | JSON text string, e.g. `'{"text":"Excalibur","italic":false}'` |
| `minecraft:item_name` | JSON text string; not italic |
| `minecraft:lore` | list of JSON text strings |
| `minecraft:enchantments` | `{levels:{"minecraft:sharpness":5}, show_in_tooltip:true}` in 1.21.1 |
| `minecraft:stored_enchantments` | same shape, for enchanted books |
| `minecraft:unbreakable` | `{}` (or `{show_in_tooltip:true}`) |
| `minecraft:custom_data` | free-form compound for your own keys |
| `minecraft:custom_model_data` | int (1.21.1) |
| `minecraft:dyed_color` | `{rgb: 12345}` (1.21.1) |
| `minecraft:potion_contents` | `{potion:"minecraft:healing", custom_effects:[...]}` |
| `minecraft:profile` | player head profile |
| `minecraft:entity_data` | entity NBT for spawn eggs |
| `minecraft:block_entity_data` | block entity NBT for chests, signs, etc. |
| `minecraft:container` | list of `{slot, item}` for shulker boxes |
| `minecraft:trim` | armor trim material/pattern |
| `minecraft:banner_patterns` | list of patterns |
| `minecraft:written_book_content` | author, title, pages |
| `minecraft:writable_book_content` | pages |
| `minecraft:fireworks` | flight duration, explosions |
| `minecraft:charged_projectiles` | crossbow ammo |
| `minecraft:bundle_contents` | bundle items |

1.21.5 changes: text components are inline SNBT instead of JSON strings,
`enchantments` drops the `levels` wrapper, `dyed_color` is an int, and
`attribute_modifiers` is a plain list. Target the version you will load into.

Examples:

```python
b.chest_with_items(0, 1, 0, [
    {"slot": 0, "id": "minecraft:diamond_sword", "count": 1, "components": {
        "minecraft:custom_name": '{"text":"Excalibur","italic":false}',
        "minecraft:enchantments": {"levels": {"minecraft:sharpness": 5}},
        "minecraft:unbreakable": {},
    }},
    {"slot": 1, "id": "minecraft:bread", "count": 16},
])
```

### 8.3 Container slot maps

| Container | Slots |
| --- | --- |
| Chest / barrel / shulker box | 0..26 (single); 0..53 (double chest) |
| Hopper / dropper / dispenser | 0..4 / 0..8 |
| Furnace / smoker / blast furnace | 0 input, 1 fuel, 2 output |
| Brewing stand | 0..2 bottles, 3 ingredient, 4 fuel |
| Beacon | 0 payment |
| Crafter | 0..8 |
| Lectern | book slot |
| Campfire | 0..3 cooking slots |
| Villager | `Inventory` 0..7, `Offers` trades |
| Horse/donkey/mule/llama | `Items` 0..14 (donkey/mule 0..14, llama by strength) |

For double chests, place two chests adjacent with the correct `type`
(`left`/`right`) and `facing`; the game merges them.

### 8.4 Signs

1.20+ sign block entity:

```
front_text: {
  messages: ["line1","line2","line3","line4"],
  color: "black",
  has_glowing_text: 0b
}
back_text: {...}
is_waxed: 1b
```

Messages are JSON text strings (1.20-1.21.4) or inline text (1.21.5+).
`mcba.sign_text` JSON-encodes each line as `{"text": "..."}`; pass a raw JSON
string to the block entity yourself if you need colors, clicks, or
translations.

```python
b.sign_text(2, 1, 1, ["Welcome", "to the", "build"])
```

### 8.5 Written books

```
written_book_content: {
  author: "Name",
  title: "Title",
  generation: 0,
  pages: ['{"text":"Page 1"}', '{"text":"Page 2"}']
}
```

Pages are JSON text strings in 1.21.1; 1.21.5+ uses inline text.

### 8.6 Banners and heads

- Banner: `base_color` and `banner_patterns` (component) or block entity
  `Patterns` list of `{Pattern:"...", Color:n}` for older formats.
- Player head: `profile` component with `name`, `id` (UUID int array), and
  `properties` (textures). Use a known profile or leave blank for a default
  head.
- Mob heads are normal items; place them as blocks or in item frames.

### 8.7 Block entity data

Block entities store data not in the block state: chests (`Items`), signs
(`front_text`), spawners, furnaces (`Items`, `BurnTime`, `CookTime`),
jukeboxes (`RecordItem`), lecterns (`Book`), beacons (`Levels`, `Primary`,
`Secondary`), banners (`Patterns`), beds (`color`), skulls (`SkullOwner`),
command blocks (`Command`, `auto`), structure blocks, etc.

`mcba`:

```python
b.set(0, 1, 0, "chest", facing="north")
b.add_block_entity(0, 1, 0, {
    "id": "minecraft:chest",
    "Items": nbt.NBTList([
        nbt.NBTCompound({"Slot": nbt.B(0), "id": "minecraft:diamond",
                         "count": nbt.I(3)})
    ], elem_type=nbt.TAG_COMPOUND),
})
```

When using helpers (`chest_with_items`, `sign_text`, `spawner`), the block and
the block entity are created together.

### 8.8 NBT type strictness

Minecraft's codecs are type-sensitive. `mcba` maps plain Python `int` to Int,
`float` to Double, `bool` to Byte, `str` to String, `dict` to Compound, and
`list` to List. If a field requires a different numeric type, wrap it:

```python
from mcba import nbt
nbt.B(1)    # Byte
nbt.S(20)   # Short
nbt.I(5)    # Int
nbt.L(100)  # Long
nbt.F(1.5)  # Float
nbt.D(2.5)  # Double
```

This matters for fields such as `Health` (Float), `Pose` (Float), `Fire`
(Short), `Count` in pre-1.20.5 items (Byte), and `Delay` in spawners (Short).
Wrong numeric types are a common cause of "the entity spawns but ignores its
data".

---

## 9. World and game logic

### 9.1 Light

- Light levels 0..15. Sky light 15 at the surface, decreasing under cover;
  block light from sources.
- Hostile mobs in the Overworld since 1.18 need block light **0** and sky
  light at most 7. In the Nether, higher block light is tolerated; the End
  requires 0.
- Passive mobs need block light 9+ when not under sky (Java).
- Light sources: torch 14, lantern 15, glowstone 15, sea lantern 15, jack
  o'lantern 15, campfire 15, lava 15, candle 3 per candle (max 12), amethyst
  cluster 5, crying obsidian 10, magma block 3, sculk catalyst 1.
- Light passes through transparent blocks with varying attenuation; water
  reduces light by 1 per block, leaves by 1 (or more), glass 0.

### 9.2 Gravity and fluids

- Gravity blocks: sand, red sand, gravel, concrete powder, anvil, dragon egg,
  pointed dripstone (falls when unsupported), scaffolding.
- Water spreads 7 blocks horizontally, 1 block per 5 ticks; it flows down
  infinitely. Lava spreads 3 blocks in the Overworld/End and 7 in the Nether,
  at 1 block per 30 ticks (Overworld/End) or 10 ticks (Nether).
- Water + lava: source lava + water = obsidian; flowing lava + water =
  cobblestone; lava flowing onto water = stone.
- Waterlogged blocks contain water without flowing; use them for detail
  without flooding.
- Bubble columns: soul sand up, magma down. They affect entities and items.

### 9.3 Block updates and ticks

- **Neighbor updates** occur when a block changes; many blocks react.
- **Random ticks** affect crops, leaves, fire, ice, etc.; not every block
  every tick.
- **Scheduled ticks** handle repeaters, fluids, fire, and other timed events.
- **Shape updates** are what observers detect; not every state change emits
  one.
- Chunk borders and simulation distance can change timing. Keep large
  contraptions inside a small area or force-load chunks.

### 9.4 Dimensions

| Dimension | Height | Notes |
| --- | --- | --- |
| Overworld | -64..319 | water, lava, weather |
| Nether | 0..255 | lava sea, no water, beds explode |
| End | 0..255 | void, end stone islands |

Schematics are dimension-agnostic, but block behavior can differ (water in
the Nether evaporates, beds explode, compasses spin).

### 9.5 Spawn-proofing and mob control

- Light up caves and buildings; hostile spawns need block light 0.
- Use slabs, carpets, buttons, or trapdoors on floors to prevent spawns
  (mobs need a full block surface).
- Use fences, walls, and water moats to contain mobs.
- Use `PersistenceRequired` for named/display mobs; use `NoAI` for statues.
- Spawners can be disabled with light or by breaking the block; a redstone
  signal does not disable a spawner directly (use light or commands).

### 9.6 Common block interactions

- Note block: instrument depends on the block below (stone, wood, sand,
  glass, etc.); `note` 0..24; powered triggers.
- Redstone lamp: lights while powered; 1-tick pulses may not light it.
- Copper bulbs: toggle on pulse; oxidation affects light.
- Crafter: 3x3 grid; redstone pulse crafts; `triggered` state.
- Decorated pot: `sherds` list; use as storage/decor.
- Chiseled bookshelf: `last_interaction_book_type`, `slot_0_occupied` etc.
- Command block: `Command`, `auto`, `conditionMet`, `powered`; needs operator
  to edit. Avoid in survival builds unless intentional.
- Structure block: saves/loads structures; not the same as schematics.
- Jigsaw block: worldgen only.
- Barrier/light blocks: invisible; useful for maps and lighting.
- Item frames can hold items and emit comparator signals based on rotation.

---

## 10. Schematic format internals

### 10.1 Litematica `.litematic`

Gzip-compressed NBT. Root compound:

```
Version: int
SubVersion: int (optional)
MinecraftDataVersion: int
Metadata: {
  Name, Author, Description,
  RegionCount: int, TotalBlocks: int, TotalVolume: int,
  TimeCreated: long, TimeModified: long,
  EnclosingSize: {x,y,z}
}
Regions: {
  <region name>: {
    Position: {x,y,z}          # region origin
    Size: {x,y,z}              # can be negative in old files
    BlockStatePalette: [ {Name, Properties?}, ... ]
    BlockStates: [long, ...]   # packed indices
    TileEntities: [ {id, x,y,z, ...}, ... ]
    Entities: [ {id, Pos:[x,y,z], ...}, ... ]
    PendingBlockTicks: []
    PendingFluidTicks: []
  }
}
```

Packing:

- Air is always palette index 0.
- `bits = max(2, (palette_size - 1).bit_length())`.
- Values are packed LSB-first and **may cross a 64-bit boundary**; do not use
  a naive "bits per long" scheme.
- Index order is `(y * size_z + z) * size_x + x`: X fastest, then Z, then Y.
- Tile-entity `x/y/z` and entity `Pos` are relative to the region
  `Position` (the minimum corner). `mcba` converts to/from world coordinates.
- `Size` can be negative in files from some tools; normalize by shifting the
  origin and taking absolute values.

`mcba` writes `Position` equal to the build's minimum corner by default, so
round-tripping preserves world coordinates. Pass `origin=(0,0,0)` to
`save_litematic` if you want a local-origin file.

### 10.2 Sponge `.schem`

**v2** (recommended):

```
root name: "Schematic"
Version: int = 2
DataVersion: int
Metadata: {Name, Author, Description}
Width, Height, Length: short
Offset: [int,int,int]       # world offset of the min corner
PaletteMax: int             # number of palette entries
Palette: { "block[state]": int, ... }
BlockData: [byte, ...]      # varint-encoded palette indices
BlockEntities: [ {Id, Pos:[x,y,z], ...}, ... ]
Entities: [ {Id, Pos:[x,y,z], ...}, ... ]
```

**v3**:

```
root name: ""
Schematic: {
  Version: 3, DataVersion, Metadata,
  Width, Height, Length, Offset,
  Blocks: {
    Palette: {...},
    Data: [byte...],          # varint indices
    BlockEntities: [...]
  },
  Entities: [...]
}
```

Sponge details:

- `PaletteMax` = number of entries in `Palette` (v2).
- Block order is `x + z * Width + y * Width * Length`: X fastest, then Z, then
  Y.
- `BlockData` is a byte array of varints (LEB128-style, 7 bits per byte,
  high bit = continue).
- Block entity `Pos` and entity `Pos` are local to the schematic min corner;
  `Offset` shifts them back to world coordinates.
- v3 block entities live inside `Blocks`, entities at the schematic level.
- Sponge uses full block-state strings in the palette keys, e.g.
  `minecraft:oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]`.

`mcba` writes v2 by default and v3 with `version=3`. `Offset` defaults to the
build's minimum corner for round-trip fidelity.

### 10.3 Which format to use

| Need | Use |
| --- | --- |
| Litematica mod, large builds, multiple regions | `.litematic` |
| WorldEdit/FAWE, broad tool support | `.schem` v2 |
| Newer WorldEdit, Sponge v3 features | `.schem` v3 |
| Version-controlled, diffable output | not supported; schematics are binary |

### 10.4 Data version choice

- Default `3955` (1.21.1). Change with `data_version=` or the CLI flag.
- The data version does not convert block ids or item components. If you use
  1.21.5-only syntax (equipment field, inline text), stamp a 1.21.5+ data
  version; otherwise the game may misinterpret the data.
- Loading an old schematic into a new version is usually fine; the game
  remaps ids and may drop removed blocks.

---

## 11. Agent workflow and pitfalls

### 11.1 Recommended loop

1. Write a Python build script using `Build`.
2. Keep coordinates positive and the origin at `(0,0,0)` unless you need
   world alignment.
3. Use helpers for repetitive shapes and redstone components.
4. Save to both formats if the user may use different tools:
   `b.save("out.litematic")` and `b.save("out.schem")`.
5. Reload and check:
   ```python
   from mcba import load
   back = load("out.litematic")
   print(back.describe())
   print(back.block_counts())
   ```
6. Validate entities and block entities by listing them.
7. If possible, open the file in Litematica/WorldEdit or a viewer.

### 11.2 Common mistakes

- **Wrong stair/slab names**: `spruce_planks_stairs` does not exist.
- **Incomplete block states**: `redstone_wire` with only `power` may be
  repaired by the game; use the factory or include all connection props.
- **Air in the palette**: air must be index 0 in Litematica; `mcba` handles
  it, but custom writers must too.
- **Entity positions**: Litematica entity `Pos` is region-relative; Sponge
  entity `Pos` is local. Do not write world coordinates directly.
- **Block entity coordinates**: Litematica uses relative `x/y/z`; Sponge uses
  local `Pos`. Mixing them shifts containers/signs.
- **Item format mismatch**: 1.20.5+ uses `count`/`components`; older uses
  `Count`/`tag`. The wrong one silently loses data.
- **Equipment format mismatch**: 1.21.5+ uses `equipment`; older uses
  `HandItems`/`ArmorItems`.
- **NBT numeric types**: `Health` and `Pose` are Float; `Fire` is Short;
  `Count` in old items is Byte. Use `nbt.F/S/B`.
- **Negative sizes in imported Litematica files**: normalize origin and size.
- **Data version mismatch**: 1.21.5 text components and equipment differ from
  1.21.1.
- **QC surprises**: pistons react to power above them; a circuit that works
  in a test may behave differently when embedded in a wall.
- **Chunk borders**: redstone and entities stop at unloaded chunks.
- **Lag**: large dust/observer/hopper systems can lag or fail on servers.
- **Bedrock vs Java**: redstone, block states, and NBT differ; these formats
  are Java.

### 11.3 Style checklist

- Does the build have a clear silhouette from 20+ blocks away?
- Is there a consistent palette with a trim/accent?
- Are windows/doors recessed or framed?
- Is the roof overhanging and detailed?
- Are there interior floors, ceilings, and lighting?
- Is the terrain integrated (not a floating box)?
- Are there accidental holes, floating blocks, or missing stairs?
- Do entities stand on solid ground and face the right way?
- Are containers/signs populated and correctly positioned?
- Does the schematic reload with the same block count?

---

## 12. Quick reference

### 12.1 `mcba` API cheat sheet

```python
from mcba import Build, load, info, nbt

b = Build("name", author="me", description="...")

# Blocks
b.set(x, y, z, "minecraft:stone")
b.set(x, y, z, "oak_stairs", facing="north")
b.fill(x1, y1, z1, x2, y2, z2, "stone")
b.hollow_box(...); b.walls(...); b.floor(...); b.ceiling(...)
b.frame(...); b.line(...); b.cylinder(...); b.sphere(...); b.ellipsoid(...)
b.replace("stone", "stone_bricks")
b.stamp_ascii(x, y, z, rows, {"#": "stone", ".": "air"})

# Redstone
b.wire(x, y, z, power=0)
b.wire_line(x1, y1, z1, x2, y2, z2, power=15)
b.lever(...); b.torch(...); b.repeater(...); b.comparator(...)
b.observer(...); b.piston(...); b.lamp(...); b.door(...); b.bed(...)

# Structure
b.gable_roof(x1, z1, x2, z2, y, "spruce_planks")
b.tree(x, y, z, height=6)

# Entities and block entities
b.add_entity("minecraft:armor_stand", x, y, z, {...})
b.add_block_entity(x, y, z, {...})
b.spawner(x, y, z, "minecraft:zombie")
b.chest_with_items(x, y, z, [{"slot": 0, "id": "minecraft:diamond"}])
b.sign_text(x, y, z, ["line 1", "line 2"])

# Transforms
b.translate(dx, dy, dz); b.rotate_y(1); b.mirror_x(); b.mirror_z()
b.paste(other, dx, dy, dz); b.clone()

# Output
b.save("build.litematic")
b.save("build.schem")
b.save("build.schem", version=3)
b.save("build.litematic", data_version=3955)
```

CLI:

```
python -m mcba run build_script.py --out build.litematic
python -m mcba run build_script.py --out build.schem --format schem
python -m mcba info build.litematic
python -m mcba info build.schem --json
python -m mcba convert build.litematic build.schem
```

### 12.2 Block-state direction cheat sheet

- `facing`: stairs high side, door front, piston/observer output, repeater/
  comparator output, chest front, furnace front.
- `axis`: logs, pillars, basalt, bone blocks.
- `rotation`: floor signs/banners, 0..15 (0 = south, 4 = west, 8 = north,
  12 = east).
- `half`: stairs/trapdoors top/bottom; doors lower/upper.
- `type`: slabs bottom/top/double; chests single/left/right.
- `shape`: stairs straight/inner/outer; rails north_south/east_west/
  ascending_*/curved_*.
- `power`: dust 0..15.
- `delay`: repeater 1..4.
- `mode`: comparator compare/subtract.
- `lit`: furnace/campfire/candle/lamp.
- `open`: door/trapdoor/fence gate.
- `powered`: most mechanisms.

### 12.3 Timing cheat sheet

| Event | Time |
| --- | --- |
| Game tick | 50 ms |
| Redstone tick | 2 game ticks, 100 ms |
| Repeater delay 1..4 | 2..8 game ticks |
| Comparator delay | 2 game ticks |
| Observer delay + pulse | 2 + 2 game ticks |
| Torch turn-off | 2 game ticks |
| Piston move | 2 game ticks |
| Hopper transfer | 8 game ticks |
| Water spread | 5 ticks/block |
| Lava spread | 30 ticks/block (Overworld/End), 10 (Nether) |
| Button (stone/wood) | 20 / 30 ticks |
| Day | 24,000 ticks |

### 12.4 Useful ids and tags

- Air: `minecraft:air`, `minecraft:cave_air`, `minecraft:void_air`.
- Light: `minecraft:light` (block, level 0..15), `minecraft:barrier`.
- Structure: `minecraft:structure_void`, `minecraft:jigsaw`.
- Command: `minecraft:command_block`, `chain_command_block`,
  `repeating_command_block`.
- Copper bulbs: `minecraft:copper_bulb`, `exposed_copper_bulb`,
  `weathered_copper_bulb`, `oxidized_copper_bulb` (and waxed variants).
- Sculk: `sculk_sensor`, `calibrated_sculk_sensor`, `sculk_shrieker`,
  `sculk_catalyst`, `sculk_vein`.
- Deep dark: `reinforced_deepslate`, `sculk`.
- Nether: `netherrack`, `basalt`, `blackstone`, `soul_sand`, `soul_soil`,
  `magma_block`, `glowstone`, `shroomlight`, `nether_bricks`.
- End: `end_stone`, `end_stone_bricks`, `purpur_block`, `purpur_pillar`,
  `obsidian`, `end_rod`, `chorus_plant`, `chorus_flower`.
- Ocean: `prismarine`, `prismarine_bricks`, `dark_prismarine`, `sea_lantern`,
  `kelp`, `seagrass`, `tube_coral_block`.

---

## 13. Sources and verification

The details above were cross-checked against the Minecraft Wiki (block states,
redstone mechanics, observer, repeater, comparator, piston, fluids, light,
spawning, data components, villager/armor stand NBT, data versions) and the
Litematica/Sponge schematic specifications. Redstone behavior changes between
versions; when a build depends on a quirk (QC, 0-tick, update order), test it
in the exact target version.

If you need a behavior that is not covered here, prefer a small in-game test
over guessing, and record the result in `meta` or in this file.
