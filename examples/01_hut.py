"""A small starter hut.

Run directly:      python examples/01_hut.py
Through the CLI:   python -m mcba run examples/01_hut.py --out hut.litematic
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcba import Build

b = Build("starter_hut", author="mcba", description="7x7 oak hut")

# Foundation and floor
b.fill(0, 0, 0, 6, 0, 6, "stone_bricks")
b.fill(0, 1, 0, 6, 1, 6, "oak_planks")

# Walls
b.walls(0, 1, 0, 6, 3, 6, "oak_planks")

# Door and windows
b.door(3, 1, 0, "oak", facing="north")
b.set(1, 2, 0, "glass_pane")
b.set(5, 2, 0, "glass_pane")
b.set(0, 2, 3, "glass_pane")
b.set(6, 2, 3, "glass_pane")

# Roof
b.gable_roof(0, 0, 6, 6, 4, "spruce_planks")

# Interior
b.set(1, 1, 1, "crafting_table")
b.set(2, 1, 1, "furnace", facing="north")
b.chest_with_items(5, 1, 5, [
    {"slot": 0, "id": "minecraft:bread", "count": 8},
    {"slot": 1, "id": "minecraft:torch", "count": 16},
])
b.set(5, 2, 5, "torch")

# Exterior details
b.set(0, 1, 0, "oak_log", axis="y")
b.set(6, 1, 0, "oak_log", axis="y")
b.set(0, 1, 6, "oak_log", axis="y")
b.set(6, 1, 6, "oak_log", axis="y")
b.sign_text(4, 1, 1, ["Starter Hut", "built with mcba"])

# A resident
b.add_entity("minecraft:villager", 3.5, 1.0, 3.5, {
    "VillagerData": {
        "type": "minecraft:plains",
        "profession": "minecraft:farmer",
        "level": 2,
    },
    "PersistenceRequired": True,
})

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out")
    os.makedirs(out, exist_ok=True)
    b.save(os.path.join(out, "starter_hut.litematic"))
    b.save(os.path.join(out, "starter_hut.schem"))
    print(b.describe())
