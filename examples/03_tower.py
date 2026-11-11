"""A round tower with a conical roof, battlements, and decoration.

Run directly:      python examples/03_tower.py
Through the CLI:   python -m mcba run examples/03_tower.py --out tower.litematic
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcba import Build, nbt

b = Build("round_tower", author="mcba", description="stone tower with a spire")

RADIUS = 5
HEIGHT = 16

# Foundation and hollow shaft
b.cylinder(0, 0, 0, RADIUS, 1, "stone_bricks")
b.cylinder(0, 1, 0, RADIUS, HEIGHT, "stone_bricks", hollow=True)

# Floor rings every 5 blocks
for y in (1, 6, 11, 16):
    b.cylinder(0, y, 0, RADIUS - 1, 1, "spruce_planks")

# Door on the south side
b.door(0, 1, RADIUS, "dark_oak", facing="north")
b.set(0, 3, RADIUS, "dark_oak_planks")
b.set(-1, 3, RADIUS, "dark_oak_planks")
b.set(1, 3, RADIUS, "dark_oak_planks")

# Arrow-slit windows on four sides
for dx, dz in ((0, RADIUS), (0, -RADIUS), (RADIUS, 0), (-RADIUS, 0)):
    for y in (4, 9, 14):
        b.set(dx, y, dz, "glass_pane")

# Battlements: alternating merlons around the top
for i in range(36):
    angle = i * math.tau / 36
    x = round((RADIUS + 0.5) * math.cos(angle))
    z = round((RADIUS + 0.5) * math.sin(angle))
    if i % 2 == 0:
        b.set(x, HEIGHT, z, "stone_bricks")

# Conical spire
for layer in range(7):
    radius = RADIUS - layer * 0.7
    b.cylinder(0, HEIGHT + 1 + layer, 0, radius, 1, "dark_oak_planks")

# Spire cap and a lantern
b.set(0, HEIGHT + 8, 0, "dark_oak_planks")
b.set(0, HEIGHT + 9, 0, "lantern", hanging=False)

# Interior light and a chest
for y in (2, 7, 12):
    b.set(0, y, 0, "lantern", hanging=True)
b.chest_with_items(2, 2, 2, [
    {"slot": 0, "id": "minecraft:gold_ingot", "count": 12},
    {"slot": 1, "id": "minecraft:iron_sword", "count": 1},
])

# Two guards and a decorative tree outside
b.fill(-8, 0, -1, -7, 0, 1, "stone_bricks")
b.fill(13, 0, -1, 14, 0, 1, "stone_bricks")
b.add_entity("minecraft:armor_stand", -RADIUS - 2.5, 1.0, 0.5, {
    "ShowArms": True,
    "NoBasePlate": True,
    "Pose": {
        "RightArm": [nbt.F(-80), nbt.F(0), nbt.F(0)],
        "LeftArm": [nbt.F(-80), nbt.F(0), nbt.F(0)],
    },
})
b.add_entity("minecraft:villager", RADIUS + 2.5, 1.0, 0.5, {
    "VillagerData": {
        "type": "minecraft:plains",
        "profession": "minecraft:weaponsmith",
        "level": 3,
    },
    "PersistenceRequired": True,
})
b.tree(RADIUS + 6, 1, 3, height=6, log_material="oak", leaf_material="oak")

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out")
    os.makedirs(out, exist_ok=True)
    b.save(os.path.join(out, "round_tower.litematic"))
    b.save(os.path.join(out, "round_tower.schem"))
    print(b.describe())
