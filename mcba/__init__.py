"""mcba - a small, dependency-free toolkit that lets AI agents author
Minecraft builds and export them to ``.litematic`` or ``.schem``.

Quick start::

    from mcba import Build

    b = Build("hut", author="agent")
    b.fill(0, 0, 0, 6, 0, 6, "stone_bricks")          # floor
    b.walls(0, 1, 0, 6, 3, 6, "oak_planks")           # walls
    b.gable_roof(0, 0, 6, 6, 4, "spruce_planks")      # roof
    b.door(3, 1, 0, "oak", facing="north")
    b.save("hut.litematic")
"""

from . import nbt
from .nbt import B, D, F, I, L, S
from .blocks import (
    AIR, BlockState, as_block,
    banner, bed, button, campfire, candle, chest, comparator, dispenser,
    door, dropper, fence, fence_gate, furnace, hopper, lantern, leaves, lever,
    log, observer, pane, piston, piston_head, pressure_plate, rail,
    redstone_lamp, redstone_torch, redstone_wire, repeater, sign, slab,
    stairs, torch, trapdoor, wall, rotate_facing, mirror_facing,
    COLORS, DIRECTIONS, HORIZONTAL, OPPOSITE, OFFSET, STONE_MATERIALS, WOODS,
)
from .builder import Build, Entity, to_nbt
from .schematic import (
    DEFAULT_DATA_VERSION, decode_varints, encode_varints, info, load,
    load_litematic, load_sponge, save, save_litematic, save_sponge,
    schematic_version_for_data_version,
)

__all__ = [
    "nbt", "B", "S", "I", "L", "F", "D",
    "Build", "Entity", "BlockState", "as_block", "AIR", "to_nbt",
    "save", "load", "info", "save_litematic", "save_sponge",
    "load_litematic", "load_sponge", "DEFAULT_DATA_VERSION",
    "schematic_version_for_data_version", "encode_varints", "decode_varints",
    "stairs", "slab", "wall", "fence", "pane", "log", "leaves", "piston",
    "piston_head", "observer", "repeater", "comparator", "redstone_wire",
    "redstone_torch", "torch", "redstone_lamp", "lever", "button",
    "pressure_plate", "door", "trapdoor", "fence_gate", "rail", "hopper",
    "dropper", "dispenser", "chest", "furnace", "lantern", "campfire", "sign",
    "banner", "bed", "candle", "rotate_facing", "mirror_facing",
    "COLORS", "DIRECTIONS", "HORIZONTAL", "OPPOSITE", "OFFSET",
    "STONE_MATERIALS", "WOODS",
]
