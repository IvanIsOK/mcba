"""Automatic spruce 2x2 mega-tree farm with a caged wither and bonemeal input.

Based on the standard wither-tree-farm design:
- 4x4 podzol planting platform with 2x2 spruce sapling clusters.
- Dispensers on each side feed bonemeal.
- A hopper line carries bonemeal from a chest (connect your bonemeal farm).
- A bedrock wither cage sits above the trees; the wither breaks wood.
- Water streams carry drops to collection chests.

This is a buildable concept; redstone timing and collection tuning need
in-game testing. Run with:  python examples/spruce_farm.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcba import Build
from mcba import blocks as bk

b = Build("spruce_wither_farm", author="mcba",
          description="4x4 spruce farm with caged wither")

# --- Platform: podzol floor (spruce needs podzol/dirt for mega trees) -----
b.fill(0, 0, 0, 3, 0, 3, "podzol")

# --- Planting positions: 2x2 sapling clusters (one per quadrant) ---------
for x in range(0, 4, 2):
    for z in range(0, 4, 2):
        for dx in range(2):
            for dz in range(2):
                b.set(x + dx, 1, z + dz, "spruce_sapling")

# --- Bonemeal dispensers around the platform (one per side) ---------------
for x in range(0, 4):
    b.set(x, 2, -1, bk.dispenser(facing="south", triggered=False))
    b.set(x, 2, 4, bk.dispenser(facing="north", triggered=False))
for z in range(0, 4):
    b.set(-1, 2, z, bk.dispenser(facing="east", triggered=False))
    b.set(4, 2, z, bk.dispenser(facing="west", triggered=False))

# --- Bonemeal input chest + hopper line ---------------------------------
b.chest_with_items(-3, 1, 1, [
    {"slot": 0, "id": "minecraft:bone_meal", "count": 64},
])
b.set(-2, 1, 1, bk.hopper(facing="east"))
b.set(-1, 1, 1, bk.hopper(facing="east"))

# --- Wither cage (bedrock, 5x5x5, open bottom above platform) ------------
# Floor of cage at y=14, ceiling at y=18, walls around
for x in range(-1, 5):
    for z in range(-1, 5):
        b.set(x, 14, z, "bedrock")
        b.set(x, 18, z, "bedrock")
for y in range(14, 19):
    for x in (-1, 5):
        for z in range(-1, 6):
            b.set(x, y, z, "bedrock")
    for z in (-1, 5):
        for x in range(-1, 6):
            b.set(x, y, z, "bedrock")
# Soul sand floor under the wither so it stays
b.fill(0, 13, 0, 3, 13, 3, "soul_sand")
# Wither spawn position
b.add_entity("minecraft:wither", 1.5, 14.0, 1.5, {
    "Invulnerable": True,
    "NoAI": True,
    "PersistenceRequired": True,
})
# Damage mechanism: dispenser shoots arrows at the wither to trigger
# its block-breaking ability (wither breaks blocks in a 3x3x4 radius
# around itself whenever it is hurt).
b.set(5, 15, 1, bk.dispenser(facing="west", triggered=False))
b.chest_with_items(5, 16, 1, [
    {"slot": 0, "id": "minecraft:arrow", "count": 64},
])

# --- Collection: water streams to chests below the platform ---------------
# Water source blocks at platform edges
for x in range(0, 4):
    b.set(x, 1, -1, "water")
    b.set(x, 1, 4, "water")
for z in range(0, 4):
    b.set(-1, 1, z, "water")
    b.set(4, 1, z, "water")

# Collection chests below the platform
for x in range(0, 4):
    b.chest_with_items(x, -1, 5, [])

# --- Labels -------------------------------------------------------------
b.sign_text(1, 1, -2, ["Spruce farm", "bonemeal in", "wither cage", "above"])

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out")
    os.makedirs(out, exist_ok=True)
    b.save(os.path.join(out, "spruce_farm.litematic"))
    b.save(os.path.join(out, "spruce_farm.schem"))
    print(b.describe())