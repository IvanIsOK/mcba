"""Redstone components and a few simple circuits.

Run directly:      python examples/02_redstone.py
Through the CLI:   python -m mcba run examples/02_redstone.py --out redstone.litematic
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcba import Build

b = Build("redstone_demo", author="mcba")

# Test floor
b.fill(0, 0, 0, 14, 0, 8, "smooth_stone")

# 1. Lever -> dust -> repeater -> lamp
b.lever(0, 1, 2, face="floor", facing="east", powered=True)
b.wire_line(1, 1, 2, 7, 1, 2, power=15)
b.repeater(8, 1, 2, facing="east", delay=2, powered=True)
b.lamp(9, 1, 2, lit=True)

# 2. Comparator reading a chest (back points at the chest)
b.chest_with_items(3, 1, 7, [
    {"slot": 0, "id": "minecraft:diamond", "count": 32},
    {"slot": 1, "id": "minecraft:emerald", "count": 16},
])
b.comparator(3, 1, 6, facing="north", mode="compare")
b.wire_line(3, 1, 5, 3, 1, 4, power=0)

# 3. Observer watching a note block
b.set(11, 1, 6, "note_block", instrument="harp", note=12, powered=False)
b.observer(11, 1, 5, facing="south", powered=False)
b.lamp(11, 1, 4, lit=False)

# 4. Sticky piston and a block to move
b.piston(13, 1, 2, facing="up", sticky=True, extended=False)
b.set(13, 2, 2, "oak_planks")

# 5. Pressure plate and a hidden light
b.set(6, 1, 6, "stone_pressure_plate", powered=False)
b.wire(6, 1, 5, power=0)
b.lamp(6, 1, 4, lit=False)

# 6. Simple repeater clock (ring): repeaters first, then connecting dust
b.repeater(2, 1, 5, facing="east", delay=2, powered=True)
b.repeater(3, 1, 6, facing="south", delay=2, powered=True)
b.repeater(2, 1, 7, facing="west", delay=2, powered=True)
b.repeater(1, 1, 6, facing="north", delay=2, powered=True)
b.wire(1, 1, 5, power=15)
b.wire(3, 1, 5, power=15)
b.wire(3, 1, 7, power=15)
b.wire(1, 1, 7, power=15)

# 7. Logic gate inputs and outputs as labelled signs
b.sign_text(0, 1, 4, ["Lever -> lamp"])
b.sign_text(2, 1, 4, ["Chest -> comparator"])
b.sign_text(10, 1, 3, ["Observer -> lamp"])

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out")
    os.makedirs(out, exist_ok=True)
    b.save(os.path.join(out, "redstone_demo.litematic"))
    b.save(os.path.join(out, "redstone_demo.schem"))
    print(b.describe())
