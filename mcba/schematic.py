"""Export and import Minecraft schematics: ``.litematic`` and ``.schem``.

Both formats are gzip-compressed NBT.  The writers here are dependency free
and follow the published Litematica and Sponge schematic specifications.

Supported Sponge versions: 2 (default, best tool support) and 3.
"""

from __future__ import annotations

import math
import os
import time
from typing import Any, Iterable

from . import nbt
from .blocks import BlockState
from .builder import Build, Entity, to_nbt

DEFAULT_DATA_VERSION = 3955  # Minecraft 1.21.1

MASK64 = (1 << 64) - 1


def schematic_version_for_data_version(data_version: int) -> tuple[int, int | None]:
    """Return ``(Version, SubVersion)`` that Litematica writes for a data version."""
    if data_version < 1631:      # before 1.13.2
        return 4, None
    if data_version < 2860:      # 1.13.2 .. 1.17.x
        return 5, None
    if data_version < 3837:      # 1.18 .. 1.20.4
        return 6, (1 if data_version >= 3120 else None)
    return 7, 1                  # 1.20.5+


def _local_blocks(build: Build):
    """Return ``(min_pos, size, getter)`` enclosing blocks, block entities,
    and entities (so nothing is stored outside the region)."""
    minx = miny = minz = None
    maxx = maxy = maxz = None

    def include(x: int, y: int, z: int) -> None:
        nonlocal minx, miny, minz, maxx, maxy, maxz
        minx = x if minx is None else min(minx, x)
        miny = y if miny is None else min(miny, y)
        minz = z if minz is None else min(minz, z)
        maxx = x if maxx is None else max(maxx, x)
        maxy = y if maxy is None else max(maxy, y)
        maxz = z if maxz is None else max(maxz, z)

    for x, y, z in build.blocks:
        include(x, y, z)
    for x, y, z in build.block_entities:
        include(x, y, z)
    for entity in build.entities:
        include(math.floor(entity.pos[0]), math.floor(entity.pos[1]),
                math.floor(entity.pos[2]))

    if minx is None:
        return (0, 0, 0), (1, 1, 1), (lambda x, y, z: None)
    size = (maxx - minx + 1, maxy - miny + 1, maxz - minz + 1)

    def getter(x: int, y: int, z: int):
        return build.blocks.get((minx + x, miny + y, minz + z))

    return (minx, miny, minz), size, getter


def _make_palette(size, getter):
    """Build a palette with air at index 0 and a dense index array."""
    states = set()
    sx, sy, sz = size
    for y in range(sy):
        for z in range(sz):
            for x in range(sx):
                state = getter(x, y, z)
                if state is not None and not state.is_air:
                    states.add(state)
    ordered = sorted(states, key=str)
    palette = [BlockState("minecraft:air")] + ordered
    index_of = {state: i for i, state in enumerate(palette)}
    ids = []
    for y in range(sy):
        for z in range(sz):
            for x in range(sx):
                state = getter(x, y, z)
                if state is None or state.is_air:
                    ids.append(0)
                else:
                    ids.append(index_of[state])
    return palette, index_of, ids


# ---------------------------------------------------------------------------
# Litematica bit packing (LSB first, values may cross a long boundary)
# ---------------------------------------------------------------------------

def pack_litematica(ids: Iterable[int], bits: int) -> list[int]:
    ids = list(ids)
    longs = [0] * ((len(ids) * bits + 63) // 64)
    for index, value in enumerate(ids):
        start = index * bits
        long_index = start >> 6
        offset = start & 63
        longs[long_index] = (longs[long_index]
                             | ((value << offset) & MASK64)) & MASK64
        if offset + bits > 64:
            longs[long_index + 1] = (longs[long_index + 1]
                                     | (value >> (64 - offset))) & MASK64
    return longs


def unpack_litematica(longs: Iterable[int], bits: int, count: int) -> list[int]:
    longs = [int(v) & MASK64 for v in longs]
    mask = (1 << bits) - 1
    result = []
    for index in range(count):
        start = index * bits
        long_index = start >> 6
        offset = start & 63
        value = longs[long_index] >> offset
        if offset + bits > 64:
            value |= longs[long_index + 1] << (64 - offset)
        result.append(value & mask)
    return result


def _bits_for_palette(palette_size: int) -> int:
    return max(2, max(0, palette_size - 1).bit_length())


def _palette_to_nbt(palette: list[BlockState]) -> nbt.NBTList:
    return nbt.NBTList([state.to_nbt() for state in palette],
                       elem_type=nbt.TAG_COMPOUND)


def _palette_from_nbt(tag: nbt.NBTList) -> list[BlockState]:
    result = []
    for entry in tag:
        name = str(entry.get("Name", "minecraft:air"))
        props = entry.get("Properties") or {}
        result.append(BlockState(name, {str(k): str(v)
                                        for k, v in props.items()}))
    return result


# ---------------------------------------------------------------------------
# Litematica writer / reader
# ---------------------------------------------------------------------------

def save_litematic(build: Build, path: str, *, data_version: int | None = None,
                   region_name: str | None = None, name: str | None = None,
                   author: str | None = None,
                   description: str | None = None,
                   origin: tuple[int, int, int] | None = None) -> str:
    data_version = DEFAULT_DATA_VERSION if data_version is None else data_version
    name = build.name if name is None else name
    author = build.author if author is None else author
    description = build.description if description is None else description
    region_name = (build.name or "Main") if region_name is None else region_name
    version, sub_version = schematic_version_for_data_version(data_version)

    min_pos, size, getter = _local_blocks(build)
    if origin is None:
        origin = min_pos
    sx, sy, sz = size
    palette, index_of, ids = _make_palette(size, getter)
    bits = _bits_for_palette(len(palette))
    longs = pack_litematica(ids, bits)

    region = nbt.NBTCompound({
        "Position": nbt.NBTCompound({
            "x": nbt.NBTInt(origin[0]),
            "y": nbt.NBTInt(origin[1]),
            "z": nbt.NBTInt(origin[2]),
        }),
        "Size": nbt.NBTCompound({
            "x": nbt.NBTInt(sx),
            "y": nbt.NBTInt(sy),
            "z": nbt.NBTInt(sz),
        }),
        "BlockStatePalette": _palette_to_nbt(palette),
        "BlockStates": nbt.NBTLongArray(longs),
        "TileEntities": _tile_entities_nbt(build, min_pos),
        "Entities": _entities_nbt(build, min_pos),
        "PendingBlockTicks": nbt.NBTList([], elem_type=nbt.TAG_END),
        "PendingFluidTicks": nbt.NBTList([], elem_type=nbt.TAG_END),
    })

    now = int(time.time() * 1000)
    metadata = nbt.NBTCompound({
        "Name": name,
        "Author": author,
        "Description": description,
        "RegionCount": nbt.NBTInt(1),
        "TotalBlocks": nbt.NBTInt(build.non_air_count()),
        "TotalVolume": nbt.NBTInt(sx * sy * sz),
        "TimeCreated": nbt.NBTLong(now),
        "TimeModified": nbt.NBTLong(now),
        "EnclosingSize": nbt.NBTCompound({
            "x": nbt.NBTInt(sx),
            "y": nbt.NBTInt(sy),
            "z": nbt.NBTInt(sz),
        }),
    })

    root = nbt.NBTCompound({
        "Version": nbt.NBTInt(version),
        "MinecraftDataVersion": nbt.NBTInt(data_version),
        "Metadata": metadata,
        "Regions": nbt.NBTCompound({region_name: region}),
    })
    if sub_version is not None:
        root["SubVersion"] = nbt.NBTInt(sub_version)

    data = nbt.dumps(root, gzipped=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def _tile_entities_nbt(build: Build, min_pos) -> nbt.NBTList:
    ox, oy, oz = min_pos
    result = nbt.NBTList([], elem_type=nbt.TAG_COMPOUND)
    for (x, y, z), data in sorted(build.block_entities.items()):
        entry = nbt.NBTCompound(data)
        entry["x"] = nbt.NBTInt(x - ox)
        entry["y"] = nbt.NBTInt(y - oy)
        entry["z"] = nbt.NBTInt(z - oz)
        result.append(entry)
    return result


def _entities_nbt(build: Build, min_pos) -> nbt.NBTList:
    ox, oy, oz = min_pos
    result = nbt.NBTList([], elem_type=nbt.TAG_COMPOUND)
    for entity in build.entities:
        entry = nbt.NBTCompound(entity.data)
        entry["id"] = entity.id
        entry["Pos"] = nbt.NBTList([
            nbt.NBTDouble(entity.pos[0] - ox),
            nbt.NBTDouble(entity.pos[1] - oy),
            nbt.NBTDouble(entity.pos[2] - oz),
        ], elem_type=nbt.TAG_DOUBLE)
        result.append(entry)
    return result


def load_litematic(path: str) -> Build:
    root = nbt.load_file(path)
    metadata = root.get("Metadata", {})
    build = Build(
        name=str(metadata.get("Name", os.path.splitext(os.path.basename(path))[0])),
        author=str(metadata.get("Author", "")),
        description=str(metadata.get("Description", "")),
    )
    build.meta["data_version"] = int(root.get("MinecraftDataVersion", 0))
    build.meta["format"] = "litematic"
    build.meta["version"] = int(root.get("Version", 0))

    regions = root.get("Regions", {})
    for region in regions.values():
        pos = region.get("Position", {})
        ox = int(pos.get("x", 0))
        oy = int(pos.get("y", 0))
        oz = int(pos.get("z", 0))
        # Litematica stores entity ``Pos`` relative to the region's original
        # Position anchor, while blocks/tile entities are stored relative to
        # the (normalized) minimum corner. Keep the anchor before normalizing
        # so entities in negative-size regions are not shifted.
        anchor_x, anchor_y, anchor_z = ox, oy, oz
        size_tag = region.get("Size", {})
        sx = int(size_tag.get("x", 0))
        sy = int(size_tag.get("y", 0))
        sz = int(size_tag.get("z", 0))
        if sx < 0:
            ox += sx + 1
            sx = -sx
        if sy < 0:
            oy += sy + 1
            sy = -sy
        if sz < 0:
            oz += sz + 1
            sz = -sz
        palette = _palette_from_nbt(region.get("BlockStatePalette", []))
        bits = _bits_for_palette(len(palette))
        count = sx * sy * sz
        ids = unpack_litematica(region.get("BlockStates", []), bits, count)
        index = 0
        for y in range(sy):
            for z in range(sz):
                for x in range(sx):
                    state = palette[ids[index]] if ids[index] < len(palette) \
                        else BlockState("minecraft:air")
                    index += 1
                    if not state.is_air:
                        build.blocks[(ox + x, oy + y, oz + z)] = state
        for entry in region.get("TileEntities", []):
            x = ox + int(entry.get("x", 0))
            y = oy + int(entry.get("y", 0))
            z = oz + int(entry.get("z", 0))
            data = nbt.NBTCompound(entry)
            data.pop("x", None)
            data.pop("y", None)
            data.pop("z", None)
            build.block_entities[(x, y, z)] = data
        for entry in region.get("Entities", []):
            pos_list = entry.get("Pos", [])
            if len(pos_list) != 3:
                continue
            ex = anchor_x + float(pos_list[0])
            ey = anchor_y + float(pos_list[1])
            ez = anchor_z + float(pos_list[2])
            data = nbt.NBTCompound(entry)
            data.pop("Pos", None)
            entity_id = str(data.pop("id", "minecraft:pig"))
            build.entities.append(Entity(entity_id, (ex, ey, ez), data))
    return build


# ---------------------------------------------------------------------------
# Sponge .schem writer / reader
# ---------------------------------------------------------------------------

def encode_varints(values: Iterable[int]) -> bytes:
    out = bytearray()
    for value in values:
        v = int(value) & 0xFFFFFFFF
        while True:
            byte = v & 0x7F
            v >>= 7
            if v:
                out.append(byte | 0x80)
            else:
                out.append(byte)
                break
    return bytes(out)


def decode_varints(data: Iterable[int]) -> list[int]:
    values = []
    value = 0
    shift = 0
    for byte in data:
        byte = int(byte) & 0xFF
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
        else:
            values.append(value)
            value = 0
            shift = 0
    if shift:
        values.append(value)
    return values


def _sponge_palette(build: Build, size, getter):
    palette, index_of, ids = _make_palette(size, getter)
    # Sponge uses a string -> index compound and does not require air at 0,
    # but keeping it is harmless and keeps both writers identical.
    string_palette = {str(state): i for i, state in enumerate(palette)}
    return string_palette, ids


def _sponge_block_entities(build: Build, min_pos) -> nbt.NBTList:
    ox, oy, oz = min_pos
    result = nbt.NBTList([], elem_type=nbt.TAG_COMPOUND)
    for (x, y, z), data in sorted(build.block_entities.items()):
        entry = nbt.NBTCompound(data)
        entry.pop("x", None)
        entry.pop("y", None)
        entry.pop("z", None)
        entity_id = str(entry.pop("id", "minecraft:chest"))
        entry["Id"] = entity_id
        entry["Pos"] = nbt.NBTIntArray([x - ox, y - oy, z - oz])
        result.append(entry)
    return result


def _sponge_entities(build: Build, min_pos) -> nbt.NBTList:
    ox, oy, oz = min_pos
    result = nbt.NBTList([], elem_type=nbt.TAG_COMPOUND)
    for entity in build.entities:
        entry = nbt.NBTCompound(entity.data)
        entry.pop("Pos", None)
        entity_id = str(entry.pop("id", entity.id))
        entry["Id"] = entity_id
        entry["Pos"] = nbt.NBTList([
            nbt.NBTDouble(entity.pos[0] - ox),
            nbt.NBTDouble(entity.pos[1] - oy),
            nbt.NBTDouble(entity.pos[2] - oz),
        ], elem_type=nbt.TAG_DOUBLE)
        result.append(entry)
    return result


def save_sponge(build: Build, path: str, *, version: int = 2,
                data_version: int | None = None, name: str | None = None,
                author: str | None = None,
                description: str | None = None,
                offset: tuple[int, int, int] | None = None) -> str:
    data_version = DEFAULT_DATA_VERSION if data_version is None else data_version
    name = build.name if name is None else name
    author = build.author if author is None else author
    description = build.description if description is None else description

    min_pos, size, getter = _local_blocks(build)
    if offset is None:
        offset = min_pos
    sx, sy, sz = size
    palette, ids = _sponge_palette(build, size, getter)
    block_data = nbt.NBTByteArray(encode_varints(ids))

    metadata = nbt.NBTCompound({
        "Name": name,
        "Author": author,
        "Description": description,
    })

    def block_entities():
        return _sponge_block_entities(build, min_pos)

    if version == 2:
        root = nbt.NBTCompound({
            "Version": nbt.NBTInt(2),
            "DataVersion": nbt.NBTInt(data_version),
            "Metadata": metadata,
            "Width": nbt.NBTShort(sx),
            "Height": nbt.NBTShort(sy),
            "Length": nbt.NBTShort(sz),
            "Offset": nbt.NBTIntArray(list(offset)),
            "PaletteMax": nbt.NBTInt(len(palette)),
            "Palette": nbt.NBTCompound(
                {key: nbt.NBTInt(value) for key, value in palette.items()}),
            "BlockData": block_data,
            "BlockEntities": block_entities(),
            "Entities": _sponge_entities(build, min_pos),
        })
        data = nbt.dumps(root, root_name="Schematic", gzipped=True)
    elif version == 3:
        schematic = nbt.NBTCompound({
            "Version": nbt.NBTInt(3),
            "DataVersion": nbt.NBTInt(data_version),
            "Metadata": metadata,
            "Width": nbt.NBTShort(sx),
            "Height": nbt.NBTShort(sy),
            "Length": nbt.NBTShort(sz),
            "Offset": nbt.NBTIntArray(list(offset)),
            "Blocks": nbt.NBTCompound({
                "Palette": nbt.NBTCompound(
                    {key: nbt.NBTInt(value) for key, value in palette.items()}),
                "Data": block_data,
                "BlockEntities": block_entities(),
            }),
            "Entities": _sponge_entities(build, min_pos),
        })
        data = nbt.dumps(nbt.NBTCompound({"Schematic": schematic}),
                         root_name="", gzipped=True)
    else:
        raise ValueError("Sponge schematic version must be 2 or 3")

    with open(path, "wb") as fh:
        fh.write(data)
    return path


def load_sponge(path: str) -> Build:
    root_name, root = nbt.load_file_named(path)
    if root_name == "" and "Schematic" in root:
        schematic = root["Schematic"]
        version = int(schematic.get("Version", 3))
        blocks_tag = schematic.get("Blocks", {})
        palette_tag = blocks_tag.get("Palette", {})
        data_tag = blocks_tag.get("Data", [])
        block_entities_tag = blocks_tag.get("BlockEntities", [])
        entities_tag = schematic.get("Entities", [])
    else:
        schematic = root
        version = int(schematic.get("Version", 2))
        palette_tag = schematic.get("Palette", {})
        data_tag = schematic.get("BlockData", [])
        block_entities_tag = schematic.get("BlockEntities", [])
        entities_tag = schematic.get("Entities", [])

    metadata = schematic.get("Metadata", {})
    build = Build(
        name=str(metadata.get("Name", os.path.splitext(os.path.basename(path))[0])),
        author=str(metadata.get("Author", "")),
        description=str(metadata.get("Description", "")),
    )
    build.meta["data_version"] = int(schematic.get("DataVersion", 0))
    build.meta["format"] = "schem"
    build.meta["version"] = version

    sx = int(schematic.get("Width", 0))
    sy = int(schematic.get("Height", 0))
    sz = int(schematic.get("Length", 0))
    offset_tag = schematic.get("Offset", [0, 0, 0])
    ox, oy, oz = (int(offset_tag[0]), int(offset_tag[1]), int(offset_tag[2])) \
        if len(offset_tag) == 3 else (0, 0, 0)

    palette: dict[int, BlockState] = {}
    for key, value in palette_tag.items():
        palette[int(value)] = BlockState.parse(str(key))
    ids = decode_varints(data_tag)
    index = 0
    for y in range(sy):
        for z in range(sz):
            for x in range(sx):
                state = palette.get(ids[index] if index < len(ids) else 0)
                index += 1
                if state is not None and not state.is_air:
                    build.blocks[(ox + x, oy + y, oz + z)] = state

    for entry in block_entities_tag:
        pos = entry.get("Pos", [0, 0, 0])
        if len(pos) != 3:
            continue
        x, y, z = (ox + int(pos[0]), oy + int(pos[1]), oz + int(pos[2]))
        data = nbt.NBTCompound(entry)
        data.pop("Pos", None)
        entity_id = data.pop("Id", None)
        if entity_id is not None:
            data["id"] = entity_id
        build.block_entities[(x, y, z)] = data

    for entry in entities_tag:
        pos = entry.get("Pos", [])
        if len(pos) != 3:
            continue
        data = nbt.NBTCompound(entry)
        data.pop("Pos", None)
        entity_id = str(data.pop("Id", "minecraft:pig"))
        build.entities.append(Entity(entity_id,
                                     (ox + float(pos[0]), oy + float(pos[1]),
                                      oz + float(pos[2])), data))
    return build


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------

def _detect_format(path: str, fmt: str | None) -> str:
    if fmt:
        fmt = fmt.lower().lstrip(".")
        if fmt in ("litematic", "litematica", "litematics"):
            return "litematic"
        if fmt in ("schem", "sponge"):
            return "schem"
        raise ValueError(f"unknown schematic format {fmt!r}")
    ext = os.path.splitext(path)[1].lower()
    if ext in (".litematic", ".litematica"):
        return "litematic"
    if ext in (".schem", ".schematic"):
        return "schem"
    return "litematic"


def save(build: Build, path: str, fmt: str | None = None, **kwargs: Any) -> str:
    """Save ``build`` to ``path``; format inferred from the extension."""
    chosen = _detect_format(path, fmt)
    if chosen == "litematic":
        return save_litematic(build, path, **kwargs)
    return save_sponge(build, path, **kwargs)


def load(path: str) -> Build:
    """Load a ``.litematic`` or ``.schem`` file into a :class:`Build`."""
    _, root = nbt.load_file_named(path)
    if "Regions" in root and "Metadata" in root:
        return load_litematic(path)
    return load_sponge(path)


def info(path: str) -> dict[str, Any]:
    build = load(path)
    bounds = build.bounds()
    sx, sy, sz = build.size()
    return {
        "path": path,
        "format": build.meta.get("format"),
        "version": build.meta.get("version"),
        "data_version": build.meta.get("data_version"),
        "name": build.name,
        "author": build.author,
        "description": build.description,
        "size": (sx, sy, sz),
        "blocks": len(build.blocks),
        "block_types": build.block_counts(),
        "entities": len(build.entities),
        "block_entities": len(build.block_entities),
        "bounds": bounds,
    }
