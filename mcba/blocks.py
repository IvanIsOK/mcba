"""Block states and helpers for common building / redstone blocks.

Minecraft block states are written as ``namespace:block[prop=value,...]``.
The helpers here are just convenience: every block can also be placed with a
plain string.  Property names are case sensitive and use ``snake_case``.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from . import nbt

# Directions use Minecraft's coordinate system: +X = east, +Y = up, +Z = south.
DIRECTIONS = ("north", "south", "west", "east", "up", "down")
HORIZONTAL = ("north", "south", "west", "east")
OPPOSITE = {
    "north": "south",
    "south": "north",
    "west": "east",
    "east": "west",
    "up": "down",
    "down": "up",
}
AXIS_OF = {"north": "z", "south": "z", "west": "x", "east": "x", "up": "y", "down": "y"}
# Offset (dx, dy, dz) for each direction.
OFFSET = {
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
    "east": (1, 0, 0),
    "up": (0, 1, 0),
    "down": (0, -1, 0),
}
# Rotate a facing clockwise (viewed from above) by 90 degrees, N -> E -> S -> W.
CLOCKWISE = {"north": "east", "east": "south", "south": "west", "west": "north"}

WOODS = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove",
         "cherry", "bamboo", "crimson", "warped", "pale_oak")
COLORS = ("white", "orange", "magenta", "light_blue", "yellow", "lime", "pink",
          "gray", "light_gray", "cyan", "purple", "blue", "brown", "green",
          "red", "black")
STONE_MATERIALS = ("stone", "cobblestone", "mossy_cobblestone", "stone_bricks",
                   "mossy_stone_bricks", "cracked_stone_bricks",
                   "chiseled_stone_bricks", "granite", "polished_granite",
                   "diorite", "polished_diorite", "andesite",
                   "polished_andesite", "deepslate", "cobbled_deepslate",
                   "polished_deepslate", "deepslate_bricks",
                   "deepslate_tiles", "tuff", "polished_tuff", "tuff_bricks",
                   "calcite", "dripstone_block", "blackstone",
                   "polished_blackstone", "polished_blackstone_bricks",
                   "basalt", "smooth_basalt", "sandstone", "smooth_sandstone",
                   "cut_sandstone", "red_sandstone", "brick", "mud_bricks",
                   "quartz_block", "smooth_quartz", "purpur_block",
                   "end_stone_bricks", "prismarine", "prismarine_bricks",
                   "dark_prismarine", "nether_bricks", "red_nether_bricks")
AIR_NAMES = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}

# Blocks that redstone dust visually connects to (a conservative subset).
REDSTONE_CONNECTS_TO = {
    "minecraft:redstone_wire", "minecraft:redstone_torch",
    "minecraft:wall_redstone_torch", "minecraft:repeater",
    "minecraft:comparator", "minecraft:observer", "minecraft:lever",
    "minecraft:redstone_lamp", "minecraft:piston", "minecraft:sticky_piston",
    "minecraft:dispenser", "minecraft:dropper", "minecraft:hopper",
    "minecraft:note_block", "minecraft:tnt", "minecraft:target",
    "minecraft:daylight_detector", "minecraft:tripwire_hook",
    "minecraft:powered_rail", "minecraft:detector_rail",
    "minecraft:activator_rail", "minecraft:redstone_block",
    "minecraft:crafter",
}


def normalize_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("empty block name")
    if ":" not in name:
        return "minecraft:" + name
    return name


def _prop_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class BlockState:
    """An immutable Minecraft block state."""

    __slots__ = ("name", "props")

    def __init__(self, name: str, props: Mapping[str, Any] | None = None,
                 **kwargs: Any):
        self.name = normalize_name(name)
        merged: dict[str, str] = {}
        if props:
            merged.update({str(k): _prop_value(v) for k, v in props.items()})
        merged.update({str(k): _prop_value(v) for k, v in kwargs.items()})
        self.props = tuple(sorted(merged.items()))

    @classmethod
    def parse(cls, text: str) -> "BlockState":
        text = text.strip()
        if "[" not in text:
            return cls(text)
        if not text.endswith("]"):
            raise ValueError(f"bad block state {text!r}")
        name, rest = text[:-1].split("[", 1)
        props: dict[str, str] = {}
        for part in rest.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" not in part:
                raise ValueError(f"bad property {part!r} in {text!r}")
            key, value = part.split("=", 1)
            props[key.strip()] = value.strip()
        return cls(name, props)

    def get(self, key: str, default: Any = None) -> Any:
        for k, v in self.props:
            if k == key:
                return v
        return default

    def with_props(self, **kwargs: Any) -> "BlockState":
        props = dict(self.props)
        props.update({k: _prop_value(v) for k, v in kwargs.items()})
        return BlockState(self.name, props)

    @property
    def short_name(self) -> str:
        return self.name.split(":", 1)[1]

    @property
    def is_air(self) -> bool:
        return self.name in AIR_NAMES

    def to_nbt(self) -> nbt.NBTCompound:
        tag = nbt.NBTCompound({"Name": self.name})
        if self.props:
            tag["Properties"] = nbt.NBTCompound(
                {k: v for k, v in self.props})
        return tag

    def __str__(self) -> str:
        if not self.props:
            return self.name
        body = ",".join(f"{k}={v}" for k, v in self.props)
        return f"{self.name}[{body}]"

    def __repr__(self) -> str:
        return f"BlockState({str(self)!r})"

    def __hash__(self) -> int:
        return hash((self.name, self.props))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BlockState):
            return NotImplemented
        return self.name == other.name and self.props == other.props


def as_block(value: str | BlockState, **props: Any) -> BlockState:
    """Turn a string or BlockState into a BlockState, applying extra props."""
    state = BlockState.parse(value) if isinstance(value, str) else value
    if props:
        state = state.with_props(**props)
    return state


AIR = BlockState("minecraft:air")


# ---------------------------------------------------------------------------
# Factories for common blocks
# ---------------------------------------------------------------------------

def stairs(material: str, facing: str = "north", half: str = "bottom",
           shape: str = "straight", waterlogged: bool = False) -> BlockState:
    return BlockState(f"{material}_stairs", facing=facing, half=half,
                      shape=shape, waterlogged=waterlogged)


def slab(material: str, kind: str = "bottom",
         waterlogged: bool = False) -> BlockState:
    return BlockState(f"{material}_slab", type=kind, waterlogged=waterlogged)


def wall(material: str, north: str = "none", east: str = "none",
         south: str = "none", west: str = "none", up: bool = True,
         waterlogged: bool = False) -> BlockState:
    return BlockState(f"{material}_wall", north=north, east=east, south=south,
                      west=west, up=up, waterlogged=waterlogged)


def fence(material: str, north: bool = False, east: bool = False,
          south: bool = False, west: bool = False,
          waterlogged: bool = False) -> BlockState:
    return BlockState(f"{material}_fence", north=north, east=east, south=south,
                      west=west, waterlogged=waterlogged)


def pane(material: str, north: bool = False, east: bool = False,
         south: bool = False, west: bool = False,
         waterlogged: bool = False) -> BlockState:
    name = material if material.endswith("_pane") else f"{material}_pane"
    return BlockState(name, north=north, east=east, south=south, west=west,
                      waterlogged=waterlogged)


def log(material: str, axis: str = "y") -> BlockState:
    return BlockState(f"{material}_log", axis=axis)


def leaves(material: str, persistent: bool = False,
           distance: int = 7, waterlogged: bool = False) -> BlockState:
    return BlockState(f"{material}_leaves", persistent=persistent,
                      distance=distance, waterlogged=waterlogged)


def piston(facing: str = "north", sticky: bool = False,
           extended: bool = False) -> BlockState:
    name = "sticky_piston" if sticky else "piston"
    return BlockState(name, facing=facing, extended=extended)


def piston_head(facing: str = "north", sticky: bool = False,
                short: bool = False) -> BlockState:
    return BlockState("piston_head", facing=facing, type="sticky" if sticky
                      else "normal", short=short)


def observer(facing: str = "north", powered: bool = False) -> BlockState:
    return BlockState("observer", facing=facing, powered=powered)


def repeater(facing: str = "north", delay: int = 1, locked: bool = False,
             powered: bool = False) -> BlockState:
    return BlockState("repeater", facing=facing, delay=delay, locked=locked,
                      powered=powered)


def comparator(facing: str = "north", mode: str = "compare",
               powered: bool = False) -> BlockState:
    return BlockState("comparator", facing=facing, mode=mode,
                      powered=powered)


def redstone_wire(power: int = 0, north: str = "none", east: str = "none",
                  south: str = "none", west: str = "none") -> BlockState:
    return BlockState("redstone_wire", power=power, north=north, east=east,
                      south=south, west=west)


def redstone_torch(lit: bool = True, wall: str | None = None) -> BlockState:
    if wall is not None:
        return BlockState("wall_redstone_torch", facing=wall, lit=lit)
    return BlockState("redstone_torch", lit=lit)


def torch(wall: str | None = None) -> BlockState:
    if wall is not None:
        return BlockState("wall_torch", facing=wall)
    return BlockState("torch")


def redstone_lamp(lit: bool = False) -> BlockState:
    return BlockState("redstone_lamp", lit=lit)


def lever(face: str = "floor", facing: str = "north",
          powered: bool = False) -> BlockState:
    return BlockState("lever", face=face, facing=facing, powered=powered)


def button(material: str = "stone", face: str = "floor", facing: str = "north",
           powered: bool = False) -> BlockState:
    name = material if material.endswith("_button") else f"{material}_button"
    return BlockState(name, face=face, facing=facing, powered=powered)


def pressure_plate(material: str = "stone",
                   powered: bool = False) -> BlockState:
    name = material if material.endswith("_pressure_plate") \
        else f"{material}_pressure_plate"
    return BlockState(name, powered=powered)


def door(material: str, facing: str = "north", half: str = "lower",
         hinge: str = "left", open: bool = False,
         powered: bool = False) -> BlockState:
    name = material if material.endswith("_door") else f"{material}_door"
    return BlockState(name, facing=facing, half=half, hinge=hinge, open=open,
                      powered=powered)


def trapdoor(material: str, facing: str = "north", half: str = "bottom",
             open: bool = False, powered: bool = False,
             waterlogged: bool = False) -> BlockState:
    name = material if material.endswith("_trapdoor") else f"{material}_trapdoor"
    return BlockState(name, facing=facing, half=half, open=open,
                      powered=powered, waterlogged=waterlogged)


def fence_gate(material: str, facing: str = "north", open: bool = False,
               in_wall: bool = False, powered: bool = False) -> BlockState:
    name = material if material.endswith("_fence_gate") \
        else f"{material}_fence_gate"
    return BlockState(name, facing=facing, open=open, in_wall=in_wall,
                      powered=powered)


def rail(shape: str = "north_south", powered: bool | None = None,
         detector: bool = False, waterlogged: bool = False) -> BlockState:
    if detector:
        return BlockState("detector_rail", shape=shape,
                          powered=bool(powered), waterlogged=waterlogged)
    if powered is not None:
        return BlockState("powered_rail", shape=shape, powered=powered,
                          waterlogged=waterlogged)
    return BlockState("rail", shape=shape, waterlogged=waterlogged)


def hopper(facing: str = "down", enabled: bool = True) -> BlockState:
    return BlockState("hopper", facing=facing, enabled=enabled)


def dropper(facing: str = "north", triggered: bool = False) -> BlockState:
    return BlockState("dropper", facing=facing, triggered=triggered)


def dispenser(facing: str = "north", triggered: bool = False) -> BlockState:
    return BlockState("dispenser", facing=facing, triggered=triggered)


def chest(facing: str = "north", kind: str = "single",
          waterlogged: bool = False) -> BlockState:
    return BlockState("chest", facing=facing, type=kind,
                      waterlogged=waterlogged)


def furnace(facing: str = "north", lit: bool = False) -> BlockState:
    return BlockState("furnace", facing=facing, lit=lit)


def lantern(soul: bool = False, hanging: bool = False,
            waterlogged: bool = False) -> BlockState:
    return BlockState("soul_lantern" if soul else "lantern", hanging=hanging,
                      waterlogged=waterlogged)


def campfire(soul: bool = False, facing: str = "north", lit: bool = True,
             signal_fire: bool = False,
             waterlogged: bool = False) -> BlockState:
    return BlockState("soul_campfire" if soul else "campfire", facing=facing,
                      lit=lit, signal_fire=signal_fire,
                      waterlogged=waterlogged)


def sign(material: str, rotation: int = 0, wall: str | None = None,
         waterlogged: bool = False) -> BlockState:
    name = f"{material}_sign"
    if wall is not None:
        return BlockState(f"{material}_wall_sign", facing=wall,
                          waterlogged=waterlogged)
    return BlockState(name, rotation=rotation, waterlogged=waterlogged)


def banner(material: str, rotation: int = 0, wall: str | None = None) -> BlockState:
    if wall is not None:
        return BlockState(f"{material}_wall_banner", facing=wall)
    return BlockState(f"{material}_banner", rotation=rotation)


def bed(material: str, facing: str = "north", part: str = "foot",
        occupied: bool = False) -> BlockState:
    return BlockState(f"{material}_bed", facing=facing, part=part,
                      occupied=occupied)


def candle(material: str = "", candles: int = 1, lit: bool = False,
           waterlogged: bool = False) -> BlockState:
    name = f"{material}_candle" if material else "candle"
    return BlockState(name, candles=candles, lit=lit,
                      waterlogged=waterlogged)


def rotate_facing(facing: str, quarter_turns: int) -> str:
    """Rotate a horizontal facing clockwise by N quarter turns."""
    if facing in ("up", "down"):
        return facing
    result = facing
    for _ in range(quarter_turns % 4):
        result = CLOCKWISE[result]
    return result


def mirror_facing(facing: str, axis: str = "x") -> str:
    """Mirror a horizontal facing across the given axis (x or z)."""
    if facing in ("up", "down"):
        return facing
    if axis == "x":
        # east <-> west
        return {"east": "west", "west": "east"}.get(facing, facing)
    # north <-> south
    return {"north": "south", "south": "north"}.get(facing, facing)


def auto_wire_connections(build: "Any", x: int, y: int, z: int,
                          north: str = "none", east: str = "none",
                          south: str = "none", west: str = "none") -> dict[str, str]:
    """Best-effort visual connections for redstone dust at ``(x, y, z)``.

    Wires never connect up/down vertically unless the neighbour is a wire one
    block above (the ``up`` state).  Components and solid blocks get ``side``.
    """
    result = {"north": north, "east": east, "south": south, "west": west}
    for direction, (dx, dy, dz) in OFFSET.items():
        if direction not in HORIZONTAL:
            continue
        if result[direction] != "none":
            continue
        neighbour = build.get(x + dx, y + dy, z + dz)
        if neighbour is None:
            continue
        if neighbour.name == "minecraft:redstone_wire":
            result[direction] = "side"
            continue
        above = build.get(x + dx, y + 1, z + dz)
        if above is not None and above.name == "minecraft:redstone_wire":
            result[direction] = "up"
            continue
        if neighbour.name in REDSTONE_CONNECTS_TO:
            result[direction] = "side"
            continue
        if neighbour.name not in AIR_NAMES and neighbour.name.endswith(
                ("_block", "stone", "bricks", "planks", "concrete", "terracotta",
                 "deepslate", "andesite", "diorite", "granite", "glass",
                 "wool", "log", "wood", "slab", "stairs", "sand", "dirt",
                 "grass_block", "gravel", "obsidian", "iron", "gold",
                 "diamond", "emerald", "netherite", "quartz")):
            result[direction] = "side"
    return result
