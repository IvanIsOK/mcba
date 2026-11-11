# mcba - Minecraft build authoring for agents

`mcba` is a dependency-free Python package for authoring Minecraft Java builds
in code and exporting them as **`.litematic`** (Litematica) or **`.schem`**
(Sponge v2/v3, WorldEdit/FAWE). It also reads both formats back, so builds can
be inspected, transformed, and converted.

It is designed for AI agents: a small, explicit API, deterministic output,
entities and block entities, and a companion knowledge base
([`MINECRAFT_LOGIC.md`](MINECRAFT_LOGIC.md)) covering blocks, redstone,
building techniques, items, mobs, and game logic.

## Install

No third-party dependencies. Python 3.9+.

```bash
pip install -e .
# or just run from this directory
python -m mcba --help
```

## Quick start

```python
from mcba import Build

b = Build("hut", author="agent")
b.fill(0, 0, 0, 6, 0, 6, "stone_bricks")        # floor
b.walls(0, 1, 0, 6, 3, 6, "oak_planks")         # walls
b.gable_roof(0, 0, 6, 6, 4, "spruce_planks")    # roof
b.door(3, 1, 0, "oak", facing="north")
b.set(2, 1, 0, "glass_pane")
b.set(4, 1, 0, "glass_pane")

b.chest_with_items(1, 1, 1, [
    {"slot": 0, "id": "minecraft:diamond", "count": 3},
])
b.sign_text(2, 1, 1, ["Welcome", "to the", "hut"])
b.add_entity("minecraft:armor_stand", 2.5, 1.0, 2.5,
             {"NoGravity": True, "ShowArms": True})

b.save("hut.litematic")
b.save("hut.schem")
```

Load and inspect:

```python
from mcba import load, info

back = load("hut.litematic")
print(back.describe())
print(back.block_counts())
print([(e.id, e.pos) for e in back.entities])
print(info("hut.schem")["size"])
```

## Examples

- `examples/01_hut.py` - starter hut with roof, door, chest, sign, villager.
- `examples/02_redstone.py` - clock, repeater delay, observer, lamp, piston.
- `examples/03_tower.py` - round tower, battlements, guards, tree.
- `examples/04_entities.py` - equipped armor stand, custom items, spawner,
  chest minecart, dropped item.

Run any of them directly (`python examples/01_hut.py`) or through the CLI.
Outputs are written to `examples/out/`.

## CLI

```bash
python -m mcba run build_script.py --out hut.litematic
python -m mcba run build_script.py --out hut.schem --format schem --schem-version 2
python -m mcba info hut.litematic
python -m mcba info hut.schem --json
python -m mcba convert hut.litematic hut.schem
```

A build script is ordinary Python. It gets `Build`, `nbt`, `save`, `load`, and
the block factories in scope; leave the result in `build` or `b`:

```python
b = Build("tower")
b.cylinder(0, 0, 0, 3, 12, "stone_bricks", hollow=True)
b.set(0, 12, 0, "sea_lantern")
```

## API overview

### `Build`

- `set(x, y, z, block, **props)` / `place(...)`
- `fill(x1,y1,z1, x2,y2,z2, block)`, `hollow_box`, `walls`, `floor`,
  `ceiling`, `frame`, `line`, `cylinder`, `sphere`, `ellipsoid`
- `replace(old, new)`, `stamp_ascii(...)`
- redstone helpers: `wire`, `wire_line`, `lever`, `torch`, `repeater`,
  `comparator`, `observer`, `piston`, `lamp`, `door`, `bed`
- structure: `gable_roof`, `tree`
- entities: `add_entity`, `add_block_entity`, `spawner`, `chest_with_items`,
  `sign_text`
- transforms: `translate`, `mirror_x`, `mirror_z`, `rotate_y`, `paste`,
  `clone`
- output: `save(path, fmt=None, **kwargs)`, `describe`, `block_counts`

### Block states

Any block can be placed by string, including properties:

```python
b.set(0, 0, 0, "minecraft:oak_stairs[facing=east,half=top]")
b.set(1, 0, 0, "oak_stairs", facing="east", half="top")
```

Factories in `mcba.blocks` fill in complete states for stairs, slabs, walls,
fences, panes, doors, trapdoors, gates, pistons, observers, repeaters,
comparators, wire, rails, containers, and more.

### Entities

`add_entity` takes world coordinates and a plain dict. NBT types are inferred
(int -> Int, float -> Double, bool -> Byte). Use `mcba.nbt` wrappers when a
field needs a specific type:

```python
from mcba import Build, nbt

b = Build("statue")
b.add_entity("minecraft:armor_stand", 0.5, 1.0, 0.5, {
    "ShowArms": True,
    "NoBasePlate": True,
    "Pose": {"RightArm": [nbt.F(-30), nbt.F(0), nbt.F(0)]},
})
```

## Formats

- **Litematica v7** (default for 1.21.1, data version 3955), air at palette
  index 0, LSB-first bit packing that can cross 64-bit boundaries, entities and
  tile entities relative to the region position.
- **Sponge v2** (default) and **v3**, varint block data, `x + z*W + y*W*L`
  order, local entity/block-entity positions plus `Offset`.

The writers were cross-checked by loading output with `litemapy` and by
reading `.schem` files produced by `mcschematic`. See
[`MINECRAFT_LOGIC.md`](MINECRAFT_LOGIC.md) section 10 for the full format
details.

## Tests

```bash
python -m unittest discover -s tests -v
```

The suite covers NBT round-trips, block placement and transforms, Litematica
and Sponge v2/v3 round-trips (including entities, block entities, negative
coordinates, explicit origin/offset translation, entity-only builds, and
palettes larger than 128 states), and the CLI.

## Notes

- Target Java Edition. Bedrock redstone and formats differ.
- Data version is not a converter: if you use 1.21.5+ item/equipment syntax,
  stamp a 1.21.5+ `data_version`.
- Redstone quirks (quasi-connectivity, 0-tick pulses, update order) are
  version-specific. Test in the target version.

## License

Public domain / CC0. Use it however you like.
