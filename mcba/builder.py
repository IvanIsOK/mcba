"""The :class:`Build` API: place blocks, carve shapes, add entities, export.

Coordinates are integers: ``+X`` east, ``+Y`` up, ``+Z`` south.  A block
position ``(x, y, z)`` is the corner of the block with the smallest
coordinates, exactly like Minecraft block positions.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping

from . import blocks as bk
from . import nbt
from .blocks import BlockState


@dataclass
class Entity:
    id: str
    pos: tuple[float, float, float]
    data: nbt.NBTCompound = field(default_factory=nbt.NBTCompound)


def to_nbt(value: Any) -> Any:
    """Recursively convert plain Python data into typed NBT values."""
    if isinstance(value, (nbt.NBTByte, nbt.NBTShort, nbt.NBTInt, nbt.NBTLong,
                          nbt.NBTFloat, nbt.NBTDouble, nbt.NBTByteArray,
                          nbt.NBTIntArray, nbt.NBTLongArray, nbt.NBTList,
                          nbt.NBTCompound)):
        return value
    if isinstance(value, bool):
        return nbt.NBTByte(1 if value else 0)
    if isinstance(value, int):
        return nbt.NBTInt(value)
    if isinstance(value, float):
        return nbt.NBTDouble(value)
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return nbt.NBTCompound({str(k): to_nbt(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        items = [to_nbt(v) for v in value]
        elem_type = nbt.tag_id(items[0]) if items else nbt.TAG_COMPOUND
        return nbt.NBTList(items, elem_type=elem_type)
    raise TypeError(f"cannot convert {type(value)!r} to NBT")


class Build:
    """An in-memory Minecraft build."""

    def __init__(self, name: str = "build", author: str = "mcba",
                 description: str = ""):
        self.name = name
        self.author = author
        self.description = description
        self.blocks: dict[tuple[int, int, int], BlockState] = {}
        self.block_entities: dict[tuple[int, int, int], nbt.NBTCompound] = {}
        self.entities: list[Entity] = []
        self.meta: dict[str, Any] = {}

    # -- basic access -----------------------------------------------------
    def get(self, x: int, y: int, z: int) -> BlockState | None:
        return self.blocks.get((int(x), int(y), int(z)))

    def __contains__(self, pos: tuple[int, int, int]) -> bool:
        return pos in self.blocks

    def __len__(self) -> int:
        return len(self.blocks)

    def __iter__(self) -> Iterator[tuple[tuple[int, int, int], BlockState]]:
        return iter(self.blocks.items())

    def bounds(self) -> tuple[int, int, int, int, int, int] | None:
        if not self.blocks:
            return None
        xs = [p[0] for p in self.blocks]
        ys = [p[1] for p in self.blocks]
        zs = [p[2] for p in self.blocks]
        return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)

    def size(self) -> tuple[int, int, int]:
        b = self.bounds()
        if b is None:
            return (0, 0, 0)
        return (b[3] - b[0] + 1, b[4] - b[1] + 1, b[5] - b[2] + 1)

    def non_air_count(self) -> int:
        return sum(1 for s in self.blocks.values() if not s.is_air)

    def block_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for state in self.blocks.values():
            counts[state.name] = counts.get(state.name, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    # -- placing ----------------------------------------------------------
    def set(self, x: int, y: int, z: int, block: str | BlockState | None,
            nbt_data: Mapping[str, Any] | None = None,
            **props: Any) -> "Build":
        pos = (int(x), int(y), int(z))
        if block is None:
            self.blocks.pop(pos, None)
            self.block_entities.pop(pos, None)
            return self
        state = bk.as_block(block, **props)
        if state.is_air:
            self.blocks.pop(pos, None)
            self.block_entities.pop(pos, None)
            return self
        self.blocks[pos] = state
        if nbt_data is not None:
            self.block_entities[pos] = to_nbt(nbt_data)
        return self

    # Friendly alias.
    place = set

    def set_many(self, positions: Iterable[tuple[int, int, int]],
                 block: str | BlockState, **props: Any) -> "Build":
        for x, y, z in positions:
            self.set(x, y, z, block, **props)
        return self

    def remove(self, x: int, y: int, z: int) -> "Build":
        return self.set(x, y, z, None)

    def fill(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
             block: str | BlockState, **props: Any) -> "Build":
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set(x, y, z, block, **props)
        return self

    box = fill

    def hollow_box(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                   block: str | BlockState, **props: Any) -> "Build":
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        z1, z2 = min(z1, z2), max(z1, z2)
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                for z in range(z1, z2 + 1):
                    if x in (x1, x2) or y in (y1, y2) or z in (z1, z2):
                        self.set(x, y, z, block, **props)
        return self

    def walls(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
              block: str | BlockState, **props: Any) -> "Build":
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        z1, z2 = min(z1, z2), max(z1, z2)
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.set(x, y, z1, block, **props)
                self.set(x, y, z2, block, **props)
            for z in range(z1, z2 + 1):
                self.set(x1, y, z, block, **props)
                self.set(x2, y, z, block, **props)
        return self

    def floor(self, x1: int, z1: int, x2: int, z2: int, y: int,
              block: str | BlockState, **props: Any) -> "Build":
        return self.fill(x1, y, z1, x2, y, z2, block, **props)

    def ceiling(self, x1: int, z1: int, x2: int, z2: int, y: int,
                block: str | BlockState, **props: Any) -> "Build":
        return self.fill(x1, y, z1, x2, y, z2, block, **props)

    def frame(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
              block: str | BlockState, **props: Any) -> "Build":
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        z1, z2 = min(z1, z2), max(z1, z2)
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                for z in range(z1, z2 + 1):
                    edges = ((x in (x1, x2)) + (y in (y1, y2))
                             + (z in (z1, z2)))
                    if edges >= 2:
                        self.set(x, y, z, block, **props)
        return self

    def line(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
             block: str | BlockState, **props: Any) -> "Build":
        steps = max(abs(x2 - x1), abs(y2 - y1), abs(z2 - z1))
        if steps == 0:
            return self.set(x1, y1, z1, block, **props)
        for i in range(steps + 1):
            t = i / steps
            x = round(x1 + (x2 - x1) * t)
            y = round(y1 + (y2 - y1) * t)
            z = round(z1 + (z2 - z1) * t)
            self.set(x, y, z, block, **props)
        return self

    def cylinder(self, cx: float, cy: int, cz: float, radius: float,
                 height: int, block: str | BlockState, hollow: bool = False,
                 axis: str = "y", **props: Any) -> "Build":
        r = radius
        for layer in range(height):
            for a in range(math.floor(-r), math.ceil(r) + 1):
                for b in range(math.floor(-r), math.ceil(r) + 1):
                    dist = math.hypot(a, b)
                    if dist > r + 0.5:
                        continue
                    if hollow and dist < r - 0.5:
                        continue
                    if axis == "y":
                        pos = (round(cx + a), cy + layer, round(cz + b))
                    elif axis == "x":
                        pos = (cx + layer, round(cy + a), round(cz + b))
                    else:
                        pos = (round(cx + a), round(cy + b), cz + layer)
                    self.set(*pos, block, **props)
        return self

    def sphere(self, cx: float, cy: float, cz: float, radius: float,
               block: str | BlockState, hollow: bool = False,
               **props: Any) -> "Build":
        return self.ellipsoid(cx, cy, cz, radius, radius, radius, block,
                              hollow, **props)

    def ellipsoid(self, cx: float, cy: float, cz: float, rx: float, ry: float,
                  rz: float, block: str | BlockState, hollow: bool = False,
                  **props: Any) -> "Build":
        for x in range(math.floor(cx - rx), math.ceil(cx + rx) + 1):
            for y in range(math.floor(cy - ry), math.ceil(cy + ry) + 1):
                for z in range(math.floor(cz - rz), math.ceil(cz + rz) + 1):
                    d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 \
                        + ((z - cz) / rz) ** 2
                    if d > 1.0:
                        continue
                    if hollow and d < 0.65:
                        continue
                    self.set(x, y, z, block, **props)
        return self

    def replace(self, old: str | BlockState, new: str | BlockState,
                **props: Any) -> "Build":
        old_state = bk.as_block(old)
        new_state = bk.as_block(new, **props)
        for pos, state in list(self.blocks.items()):
            if state == old_state:
                self.blocks[pos] = new_state
        return self

    def stamp_ascii(self, x: int, y: int, z: int, rows: Iterable[str],
                    palette: Mapping[str, str | BlockState],
                    plane: str = "xz", spacing: int = 1) -> "Build":
        """Place a 2D grid of blocks.  Rows are top-to-bottom.

        ``plane='xz'`` is a floor (rows advance +z, columns +x),
        ``plane='xy'`` is a wall (rows advance -y, columns +x),
        ``plane='zy'`` is a wall (rows advance -y, columns +z).
        ``palette`` maps a character to a block; unknown characters are skipped.
        """
        for row_index, row in enumerate(rows):
            for col_index, char in enumerate(row):
                if char not in palette:
                    continue
                block = palette[char]
                if plane == "xz":
                    pos = (x + col_index * spacing, y,
                           z + row_index * spacing)
                elif plane == "xy":
                    pos = (x + col_index * spacing,
                           y - row_index * spacing, z)
                elif plane == "zy":
                    pos = (x, y - row_index * spacing,
                           z + col_index * spacing)
                else:
                    raise ValueError("plane must be xz, xy or zy")
                self.set(*pos, block)
        return self

    # -- redstone helpers -------------------------------------------------
    def wire(self, x: int, y: int, z: int, power: int = 0,
             north: str = "none", east: str = "none", south: str = "none",
             west: str = "none", auto: bool = True) -> "Build":
        if auto:
            conns = bk.auto_wire_connections(self, x, y, z, north=north,
                                             east=east, south=south, west=west)
        else:
            conns = {"north": north, "east": east, "south": south,
                     "west": west}
        self.set(x, y, z, bk.redstone_wire(power=power, **conns))
        return self

    def wire_line(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                  power: int = 0) -> "Build":
        self.line(x1, y1, z1, x2, y2, z2, "minecraft:redstone_wire")
        for pos in list(self.blocks):
            if self.blocks[pos].name == "minecraft:redstone_wire":
                conns = bk.auto_wire_connections(self, *pos)
                self.blocks[pos] = bk.redstone_wire(power=power, **conns)
        return self

    def lever(self, x: int, y: int, z: int, face: str = "floor",
              facing: str = "north", powered: bool = False) -> "Build":
        self.set(x, y, z, bk.lever(face=face, facing=facing, powered=powered))
        return self

    def torch(self, x: int, y: int, z: int, wall: str | None = None,
              redstone: bool = False, lit: bool = True) -> "Build":
        block = bk.redstone_torch(lit=lit, wall=wall) if redstone \
            else bk.torch(wall=wall)
        self.set(x, y, z, block)
        return self

    def repeater(self, x: int, y: int, z: int, facing: str = "north",
                 delay: int = 1, powered: bool = False) -> "Build":
        self.set(x, y, z, bk.repeater(facing=facing, delay=delay,
                                      powered=powered))
        return self

    def comparator(self, x: int, y: int, z: int, facing: str = "north",
                   mode: str = "compare", powered: bool = False) -> "Build":
        self.set(x, y, z, bk.comparator(facing=facing, mode=mode,
                                        powered=powered))
        return self

    def observer(self, x: int, y: int, z: int, facing: str = "north",
                 powered: bool = False) -> "Build":
        self.set(x, y, z, bk.observer(facing=facing, powered=powered))
        return self

    def piston(self, x: int, y: int, z: int, facing: str = "north",
               sticky: bool = False, extended: bool = False) -> "Build":
        self.set(x, y, z, bk.piston(facing=facing, sticky=sticky,
                                    extended=extended))
        return self

    def lamp(self, x: int, y: int, z: int, lit: bool = False) -> "Build":
        self.set(x, y, z, bk.redstone_lamp(lit=lit))
        return self

    def door(self, x: int, y: int, z: int, material: str = "oak",
             facing: str = "north", hinge: str = "left", open: bool = False,
             powered: bool = False) -> "Build":
        self.set(x, y, z, bk.door(material, facing=facing, half="lower",
                                  hinge=hinge, open=open, powered=powered))
        self.set(x, y + 1, z, bk.door(material, facing=facing, half="upper",
                                      hinge=hinge, open=open,
                                      powered=powered))
        return self

    def bed(self, x: int, y: int, z: int, material: str = "red",
            facing: str = "north", occupied: bool = False) -> "Build":
        dx, _, dz = bk.OFFSET[facing]
        self.set(x, y, z, bk.bed(material, facing=facing, part="foot",
                                 occupied=occupied))
        self.set(x + dx, y, z + dz, bk.bed(material, facing=facing,
                                           part="head", occupied=occupied))
        return self

    def gable_roof(self, x1: int, z1: int, x2: int, z2: int, y: int,
                   material: str = "spruce_planks", ridge_axis: str = "x",
                   trim: str | None = None, solid_gable: bool = True,
                   stair_block: str | None = None,
                   slab_block: str | None = None) -> "Build":
        """Build a simple gable (A-frame) roof out of stairs.

        ``ridge_axis='x'`` puts the ridge along X (slopes face north/south).
        ``ridge_axis='z'`` puts the ridge along Z (slopes face east/west).
        The roof rises one block per step; odd spans get a slab ridge.
        ``material`` is used for the solid gable fill; stair/slab block names
        are derived from it unless supplied explicitly.
        """
        x1, x2 = min(x1, x2), max(x1, x2)
        z1, z2 = min(z1, z2), max(z1, z2)
        stair_name = stair_block or _derived_shape_block(material, "stairs")
        slab_name = slab_block or _derived_shape_block(material, "slab")
        if ridge_axis == "x":
            depth = z2 - z1 + 1
            layers = (depth + 1) // 2
            for i in range(layers):
                za, zb = z1 + i, z2 - i
                for x in range(x1, x2 + 1):
                    if za == zb:
                        self.set(x, y + i, za, slab_name, type="bottom",
                                 waterlogged=False)
                    else:
                        self.set(x, y + i, za, stair_name, facing="south",
                                 half="bottom", shape="straight",
                                 waterlogged=False)
                        self.set(x, y + i, zb, stair_name, facing="north",
                                 half="bottom", shape="straight",
                                 waterlogged=False)
                if solid_gable:
                    if za > z1:
                        for x in range(x1, x2 + 1):
                            self.set(x, y + i, za - 1, material)
                            self.set(x, y + i, zb + 1, material)
            if trim:
                ridge_z = (z1 + z2) // 2
                for x in range(x1, x2 + 1):
                    self.set(x, y + layers - 1, ridge_z, trim)
        else:
            width = x2 - x1 + 1
            layers = (width + 1) // 2
            for i in range(layers):
                xa, xb = x1 + i, x2 - i
                for z in range(z1, z2 + 1):
                    if xa == xb:
                        self.set(xa, y + i, z, slab_name, type="bottom",
                                 waterlogged=False)
                    else:
                        self.set(xa, y + i, z, stair_name, facing="east",
                                 half="bottom", shape="straight",
                                 waterlogged=False)
                        self.set(xb, y + i, z, stair_name, facing="west",
                                 half="bottom", shape="straight",
                                 waterlogged=False)
                if solid_gable:
                    if xa > x1:
                        for z in range(z1, z2 + 1):
                            self.set(xa - 1, y + i, z, material)
                            self.set(xb + 1, y + i, z, material)
            if trim:
                ridge_x = (x1 + x2) // 2
                for z in range(z1, z2 + 1):
                    self.set(ridge_x, y + layers - 1, z, trim)
        return self

    def tree(self, x: int, y: int, z: int, height: int = 5,
             log_material: str = "oak", leaf_material: str = "oak",
             radius: int = 2) -> "Build":
        for dy in range(height):
            self.set(x, y + dy, z, bk.log(log_material, axis="y"))
        top = y + height
        for dy in range(-1, 2):
            r = radius if dy < 1 else max(1, radius - 1)
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if dx == 0 and dz == 0 and dy < 1:
                        continue
                    if abs(dx) == r and abs(dz) == r:
                        continue
                    self.set(x + dx, top + dy, z + dz,
                             bk.leaves(leaf_material, persistent=False))
        self.set(x, top + 2, z, bk.leaves(leaf_material, persistent=False))
        return self

    # -- entities and block entities --------------------------------------
    def add_entity(self, entity_id: str, x: float, y: float, z: float,
                   data: Mapping[str, Any] | None = None,
                   **kwargs: Any) -> "Build":
        merged: dict[str, Any] = {}
        if data:
            merged.update(data)
        merged.update(kwargs)
        self.entities.append(Entity(entity_id, (float(x), float(y), float(z)),
                                    to_nbt(merged) if merged
                                    else nbt.NBTCompound()))
        return self

    def add_block_entity(self, x: int, y: int, z: int,
                         data: Mapping[str, Any]) -> "Build":
        self.block_entities[(int(x), int(y), int(z))] = to_nbt(data)
        return self

    def spawner(self, x: int, y: int, z: int, entity_id: str,
                spawn_data: Mapping[str, Any] | None = None,
                count: int = 1, min_delay: int = 200, max_delay: int = 800,
                required_player_range: int = 16, spawn_range: int = 4,
                max_nearby: int = 6) -> "Build":
        """Place a monster spawner with a configured mob.

        ``entity_id`` is a namespaced id such as ``minecraft:zombie``.
        ``spawn_data`` is merged into the spawned entity's NBT.
        """
        entity = {"id": bk.normalize_name(entity_id)}
        if spawn_data:
            entity.update(spawn_data)
        data = {
            "id": "minecraft:mob_spawner",
            "SpawnData": {"entity": entity},
            "SpawnPotentials": nbt.NBTList([
                nbt.NBTCompound({
                    "weight": nbt.NBTInt(1),
                    "data": nbt.NBTCompound({"entity": to_nbt(entity)}),
                })
            ], elem_type=nbt.TAG_COMPOUND),
            "SpawnCount": nbt.NBTShort(count),
            "SpawnRange": nbt.NBTShort(spawn_range),
            "MinSpawnDelay": nbt.NBTShort(min_delay),
            "MaxSpawnDelay": nbt.NBTShort(max_delay),
            "MaxNearbyEntities": nbt.NBTShort(max_nearby),
            "RequiredPlayerRange": nbt.NBTShort(required_player_range),
            "Delay": nbt.NBTShort(20),
        }
        self.set(x, y, z, "minecraft:spawner")
        self.add_block_entity(x, y, z, data)
        return self

    def chest_with_items(self, x: int, y: int, z: int, items: Iterable[Any],
                         facing: str = "north") -> "Build":
        """``items`` entries: dict with ``slot``, ``id``, ``count`` and
        optional ``components`` (1.20.5+) or ``tag`` (older)."""
        item_list = nbt.NBTList([], elem_type=nbt.TAG_COMPOUND)
        for item in items:
            entry = {
                "Slot": nbt.NBTByte(item.get("slot", 0)),
                "id": bk.normalize_name(item["id"]),
                "count": nbt.NBTInt(item.get("count", 1)),
            }
            if "components" in item:
                entry["components"] = to_nbt(item["components"])
            if "tag" in item:
                entry["tag"] = to_nbt(item["tag"])
            item_list.append(nbt.NBTCompound(entry))
        self.set(x, y, z, "minecraft:chest", facing=facing)
        self.add_block_entity(x, y, z, {
            "id": "minecraft:chest",
            "Items": item_list,
        })
        return self

    def sign_text(self, x: int, y: int, z: int, lines: Iterable[str],
                  material: str = "oak", facing: str | None = None,
                  rotation: int = 0, glowing: bool = False) -> "Build":
        """Place a sign and fill its four lines (1.20+ ``front_text``)."""
        if facing is None:
            self.set(x, y, z, bk.sign(material, rotation=rotation))
        else:
            self.set(x, y, z, bk.sign(material, wall=facing))
        texts = list(lines)[:4]
        while len(texts) < 4:
            texts.append("")
        messages = [json.dumps({"text": str(t)}) for t in texts]
        self.add_block_entity(x, y, z, {
            "id": "minecraft:sign",
            "is_waxed": nbt.NBTByte(1),
            "front_text": {
                "messages": nbt.NBTList(messages, elem_type=nbt.TAG_STRING),
                "color": "black",
                "has_glowing_text": nbt.NBTByte(1 if glowing else 0),
            },
            "back_text": {
                "messages": nbt.NBTList(["", "", "", ""],
                                        elem_type=nbt.TAG_STRING),
                "color": "black",
                "has_glowing_text": nbt.NBTByte(0),
            },
        })
        return self

    # -- transforms -------------------------------------------------------
    def translate(self, dx: int, dy: int, dz: int) -> "Build":
        self.blocks = {(x + dx, y + dy, z + dz): s
                       for (x, y, z), s in self.blocks.items()}
        self.block_entities = {(x + dx, y + dy, z + dz): t
                               for (x, y, z), t in self.block_entities.items()}
        self.entities = [Entity(e.id, (e.pos[0] + dx, e.pos[1] + dy,
                                       e.pos[2] + dz), e.data)
                         for e in self.entities]
        return self

    def mirror_x(self) -> "Build":
        self._mirror(axis="x")
        return self

    def mirror_z(self) -> "Build":
        self._mirror(axis="z")
        return self

    def _mirror(self, axis: str) -> None:
        b = self.bounds()
        if b is None:
            return
        if axis == "x":
            pivot = b[0] + b[3]
            self.blocks = {(pivot - x, y, z): _transform_state(s, mirror="x")
                           for (x, y, z), s in self.blocks.items()}
            self.block_entities = {(pivot - x, y, z): t
                                   for (x, y, z), t in
                                   self.block_entities.items()}
            self.entities = [Entity(e.id, (pivot - e.pos[0], e.pos[1],
                                           e.pos[2]), e.data)
                             for e in self.entities]
        else:
            pivot = b[2] + b[5]
            self.blocks = {(x, y, pivot - z): _transform_state(s, mirror="z")
                           for (x, y, z), s in self.blocks.items()}
            self.block_entities = {(x, y, pivot - z): t
                                   for (x, y, z), t in
                                   self.block_entities.items()}
            self.entities = [Entity(e.id, (e.pos[0], e.pos[1],
                                           pivot - e.pos[2]), e.data)
                             for e in self.entities]

    def rotate_y(self, quarter_turns: int = 1) -> "Build":
        turns = quarter_turns % 4
        if turns == 0:
            return self
        b = self.bounds()
        if b is None:
            return self
        x1, y1, z1, x2, y2, z2 = b
        # Rotate around the centre of the bounding box, then normalise.
        cx = (x1 + x2) / 2
        cz = (z1 + z2) / 2
        rotated: dict[tuple[int, int, int], BlockState] = {}
        for (x, y, z), state in self.blocks.items():
            rx, rz = x - cx, z - cz
            for _ in range(turns):
                rx, rz = -rz, rx  # clockwise when viewed from above
            rotated[(round(cx + rx), y, round(cz + rz))] = \
                _transform_state(state, turns=turns)
        self.blocks = rotated
        new_block_entities: dict[tuple[int, int, int], nbt.NBTCompound] = {}
        for (x, y, z), data in self.block_entities.items():
            rx, rz = x - cx, z - cz
            for _ in range(turns):
                rx, rz = -rz, rx
            new_block_entities[(round(cx + rx), y, round(cz + rz))] = data
        self.block_entities = new_block_entities
        new_entities = []
        for e in self.entities:
            rx, rz = e.pos[0] - cx, e.pos[2] - cz
            for _ in range(turns):
                rx, rz = -rz, rx
            new_entities.append(Entity(e.id, (cx + rx, e.pos[1], cz + rz),
                                       e.data))
        self.entities = new_entities
        return self

    def paste(self, other: "Build", dx: int = 0, dy: int = 0, dz: int = 0,
              replace_air: bool = False) -> "Build":
        for (x, y, z), state in other.blocks.items():
            if replace_air or (x + dx, y + dy, z + dz) not in self.blocks:
                self.blocks[(x + dx, y + dy, z + dz)] = state
        for (x, y, z), data in other.block_entities.items():
            self.block_entities[(x + dx, y + dy, z + dz)] = data
        for e in other.entities:
            self.entities.append(Entity(e.id, (e.pos[0] + dx, e.pos[1] + dy,
                                               e.pos[2] + dz), e.data))
        return self

    def clone(self) -> "Build":
        other = Build(self.name, self.author, self.description)
        other.blocks = dict(self.blocks)
        other.block_entities = {k: v for k, v in self.block_entities.items()}
        other.entities = [Entity(e.id, e.pos, e.data) for e in self.entities]
        other.meta = dict(self.meta)
        return other

    # -- output -----------------------------------------------------------
    def save(self, path: str, fmt: str | None = None, **kwargs: Any) -> str:
        from .schematic import save
        return save(self, path, fmt=fmt, **kwargs)

    def describe(self) -> str:
        b = self.bounds()
        if b is None:
            return "empty build"
        sx, sy, sz = self.size()
        return (f"{self.name}: {len(self)} blocks, {sx}x{sy}x{sz}, "
                f"{len(self.entities)} entities, "
                f"{len(self.block_entities)} block entities")


def _derived_shape_block(material: str, suffix: str) -> str:
    """Derive a stairs/slab block name from a base building material.

    ``spruce_planks`` -> ``spruce_stairs``; ``stone_bricks`` ->
    ``stone_brick_stairs``; ``deepslate_tiles`` -> ``deepslate_tile_stairs``.
    """
    if material.endswith("_" + suffix):
        return material
    base = material
    if base.endswith("_planks"):
        base = base[:-len("_planks")]
    elif base.endswith("_bricks"):
        base = base[:-len("_bricks")] + "_brick"
    elif base.endswith("_tiles"):
        base = base[:-len("_tiles")] + "_tile"
    elif base.endswith("_block"):
        base = base[:-len("_block")]
    return f"{base}_{suffix}"


def _transform_state(state: BlockState, turns: int = 0,
                     mirror: str | None = None) -> BlockState:
    """Rotate/mirror the directional properties of a block state."""
    props = dict(state.props)
    if turns:
        if "facing" in props:
            props["facing"] = bk.rotate_facing(props["facing"], turns)
        if "axis" in props:
            if turns % 2 == 1:
                props["axis"] = {"x": "z", "z": "x"}.get(props["axis"],
                                                         props["axis"])
        if "rotation" in props:
            try:
                props["rotation"] = str((int(props["rotation"])
                                         + 4 * turns) % 16)
            except ValueError:
                pass
    if mirror:
        if "facing" in props:
            props["facing"] = bk.mirror_facing(props["facing"], mirror)
        if props.get("hinge") in ("left", "right"):
            props["hinge"] = "right" if props["hinge"] == "left" else "left"
        if props.get("type") in ("left", "right"):
            props["type"] = "right" if props["type"] == "left" else "left"
        shape = props.get("shape")
        if shape in ("inner_left", "inner_right", "outer_left",
                     "outer_right"):
            side, part = shape.split("_", 1)
            part = "right" if part == "left" else "left"
            props["shape"] = f"{side}_{part}"
        if "rotation" in props:
            try:
                r = int(props["rotation"])
                props["rotation"] = str(((-r) % 16) if mirror == "x"
                                        else ((8 - r) % 16))
            except ValueError:
                pass
    if props == dict(state.props):
        return state
    return BlockState(state.name, props)
