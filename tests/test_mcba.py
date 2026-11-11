"""Tests for mcba.  Run with ``python -m unittest discover -s tests``."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

from mcba import Build, info, load, nbt
from mcba.schematic import (load_litematic, load_sponge, save_litematic,
                            save_sponge, schematic_version_for_data_version)


def sample_build() -> Build:
    b = Build("sample", author="tester", description="round trip")
    b.fill(0, 0, 0, 6, 0, 6, "stone_bricks")
    b.walls(0, 1, 0, 6, 3, 6, "oak_planks")
    b.gable_roof(0, 0, 6, 6, 4, "spruce_planks")
    b.door(3, 1, 0, "oak", facing="north")
    b.set(2, 1, 0, "glass_pane")
    b.set(1, 2, 0, "oak_stairs", facing="north")
    b.set(4, 2, 0, "oak_log", axis="x")
    b.set(5, 2, 0, "redstone_wire", power=7)
    b.set(0, 1, 1, "chest", facing="north")
    b.chest_with_items(0, 1, 1, [
        {"slot": 0, "id": "diamond", "count": 3},
        {"slot": 4, "id": "minecraft:bread", "count": 16,
         "components": {"minecraft:custom_name": "Lunch"}},
    ])
    b.spawner(5, 1, 5, "minecraft:zombie")
    b.sign_text(2, 1, 1, ["Welcome", "to the", "sample"])
    b.add_entity("minecraft:armor_stand", 2.5, 1.0, 2.5,
                 {"NoGravity": True, "Invisible": True})
    return b


class NBTTest(unittest.TestCase):
    def test_round_trip_all_types(self):
        root = nbt.NBTCompound({
            "byte": nbt.B(-3),
            "short": nbt.S(300),
            "int": nbt.I(-7),
            "long": nbt.L(2 ** 40),
            "float": nbt.F(1.5),
            "double": nbt.D(2.5),
            "string": "héllo",
            "byte_array": nbt.NBTByteArray([1, 2, 255]),
            "int_array": nbt.NBTIntArray([1, -2, 3]),
            "long_array": nbt.NBTLongArray([2 ** 33]),
            "list": nbt.NBTList([nbt.I(1), nbt.I(2)], elem_type=nbt.TAG_INT),
            "compound": {"a": nbt.B(1)},
        })
        for gzipped in (True, False):
            back = nbt.loads(nbt.dumps(root, gzipped=gzipped),
                             gzipped=gzipped)
            self.assertIs(type(back["byte"]), nbt.NBTByte)
            self.assertIs(type(back["short"]), nbt.NBTShort)
            self.assertIs(type(back["int"]), nbt.NBTInt)
            self.assertIs(type(back["long"]), nbt.NBTLong)
            self.assertIs(type(back["float"]), nbt.NBTFloat)
            self.assertIs(type(back["double"]), nbt.NBTDouble)
            self.assertEqual(back["string"], "héllo")
            self.assertEqual(list(back["byte_array"]), [1, 2, 255])
            self.assertEqual(list(back["int_array"]), [1, -2, 3])
            self.assertEqual(list(back["long_array"]), [2 ** 33])
            self.assertEqual(back["list"].elem_type, nbt.TAG_INT)
            self.assertEqual(list(back["list"]), [1, 2])
            self.assertEqual(back["compound"]["a"], 1)

    def test_empty_list_keeps_end_type(self):
        root = nbt.NBTCompound({"empty": nbt.NBTList([], elem_type=nbt.TAG_END)})
        back = nbt.loads(nbt.dumps(root))
        self.assertEqual(len(back["empty"]), 0)
        self.assertEqual(back["empty"].elem_type, nbt.TAG_END)


class BuildTest(unittest.TestCase):
    def test_basic_shapes(self):
        b = Build("shapes")
        b.fill(0, 0, 0, 2, 2, 2, "stone")
        self.assertEqual(len(b), 27)
        self.assertEqual(b.size(), (3, 3, 3))
        b.hollow_box(0, 0, 0, 2, 2, 2, "glass")
        self.assertEqual(len(b), 27)
        b.set(1, 1, 1, None)
        self.assertEqual(len(b), 26)
        b.remove(0, 0, 0)
        self.assertEqual(len(b), 25)

    def test_replace(self):
        b = Build("replace")
        b.fill(0, 0, 0, 3, 0, 3, "stone")
        b.replace("stone", "stone_bricks")
        self.assertTrue(all(s.name == "minecraft:stone_bricks"
                            for s in b.blocks.values()))

    def test_transforms(self):
        b = Build("transform")
        b.set(0, 0, 0, "oak_stairs", facing="north")
        b.set(1, 0, 0, "oak_log", axis="x")
        b.set(2, 0, 0, "oak_sign", rotation="4")
        b.rotate_y(1)
        self.assertEqual(b.get(1, 0, -1).get("facing"), "east")
        self.assertEqual(b.get(1, 0, 0).get("axis"), "z")
        self.assertEqual(b.get(1, 0, 1).get("rotation"), "8")
        b.mirror_x()
        self.assertEqual(b.get(1, 0, -1).get("facing"), "west")
        self.assertEqual(b.get(1, 0, 0).get("axis"), "z")
        self.assertEqual(b.get(1, 0, 1).get("rotation"), "8")

    def test_roof_uses_valid_shape_names(self):
        b = Build("roof")
        b.gable_roof(0, 0, 6, 6, 4, "spruce_planks")
        names = {s.name for s in b.blocks.values()}
        self.assertIn("minecraft:spruce_stairs", names)
        self.assertIn("minecraft:spruce_slab", names)
        self.assertNotIn("minecraft:spruce_planks_stairs", names)

    def test_empty_build_exports(self):
        b = Build("empty")
        with tempfile.TemporaryDirectory() as tmp:
            for ext in (".litematic", ".schem"):
                path = os.path.join(tmp, "empty" + ext)
                b.save(path)
                back = load(path)
                self.assertEqual(len(back), 0)


class LitematicTest(unittest.TestCase):
    def test_round_trip(self):
        b = sample_build()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sample.litematic")
            save_litematic(b, path)
            back = load_litematic(path)
            self.assertEqual(back.blocks, b.blocks)
            self.assertEqual(back.name, b.name)
            self.assertEqual(back.author, b.author)
            self.assertEqual(back.description, b.description)
            self.assertEqual(back.block_entities, b.block_entities)
            self.assertEqual([(e.id, e.pos) for e in back.entities],
                             [(e.id, e.pos) for e in b.entities])
            self.assertEqual(back.entities[0].data["NoGravity"], 1)
            self.assertEqual(back.meta["format"], "litematic")

    def test_negative_coordinates_and_origin(self):
        b = Build("negative")
        b.fill(-4, 2, -3, -1, 4, 0, "stone")
        b.add_entity("minecraft:pig", -2.5, 3.0, -1.5)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "neg.litematic")
            save_litematic(b, path)
            back = load_litematic(path)
            self.assertEqual(back.blocks, b.blocks)
            self.assertEqual(back.entities[0].pos, (-2.5, 3.0, -1.5))

    def test_explicit_origin_translates_blocks_and_entities(self):
        b = Build("origin")
        b.set(10, 0, 10, "stone")
        b.chest_with_items(11, 0, 10, [
            {"slot": 0, "id": "stone", "count": 1}])
        b.add_entity("minecraft:pig", 11.5, 1.0, 10.5)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "origin.litematic")
            save_litematic(b, path, origin=(100, 5, 100))
            back = load_litematic(path)
            self.assertEqual(set(back.blocks), {(100, 5, 100), (101, 5, 100)})
            self.assertEqual(back.block_entities[(101, 5, 100)]["id"],
                             "minecraft:chest")
            self.assertEqual(back.entities[0].pos, (101.5, 6.0, 100.5))

    def test_entity_only_build_keeps_position(self):
        b = Build("entity-only")
        b.add_entity("minecraft:pig", 5.5, 2.0, -3.5)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "entity.litematic")
            save_litematic(b, path)
            back = load_litematic(path)
            self.assertEqual(back.blocks, {})
            self.assertEqual(back.entities[0].pos, (5.5, 2.0, -3.5))

    def test_negative_size_region_entity_uses_position_anchor(self):
        # Litematica stores entity Pos relative to the region Position, while
        # blocks are relative to the normalized minimum corner.  A negative
        # size must not shift the entity by the region size.
        from mcba.schematic import _bits_for_palette, pack_litematica
        palette = nbt.NBTList([
            nbt.NBTCompound({"Name": "minecraft:air"}),
            nbt.NBTCompound({"Name": "minecraft:stone"}),
        ], elem_type=nbt.TAG_COMPOUND)
        longs = pack_litematica([1, 1], _bits_for_palette(len(palette)))
        region = nbt.NBTCompound({
            "Position": nbt.NBTCompound({
                "x": nbt.NBTInt(5), "y": nbt.NBTInt(0), "z": nbt.NBTInt(0)}),
            "Size": nbt.NBTCompound({
                "x": nbt.NBTInt(-2), "y": nbt.NBTInt(1), "z": nbt.NBTInt(1)}),
            "BlockStatePalette": palette,
            "BlockStates": nbt.NBTLongArray(longs),
            "TileEntities": nbt.NBTList([], elem_type=nbt.TAG_COMPOUND),
            "Entities": nbt.NBTList([nbt.NBTCompound({
                "id": "minecraft:pig",
                "Pos": nbt.NBTList([
                    nbt.NBTDouble(-0.5), nbt.NBTDouble(0.0),
                    nbt.NBTDouble(0.5)], elem_type=nbt.TAG_DOUBLE),
            })], elem_type=nbt.TAG_COMPOUND),
        })
        root = nbt.NBTCompound({
            "Version": nbt.NBTInt(6),
            "MinecraftDataVersion": nbt.NBTInt(3955),
            "Metadata": nbt.NBTCompound({"Name": "neg-size"}),
            "Regions": nbt.NBTCompound({"main": region}),
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "neg-size.litematic")
            with open(path, "wb") as fh:
                fh.write(nbt.dumps(root, gzipped=True))
            back = load_litematic(path)
        self.assertEqual(set(back.blocks), {(4, 0, 0), (5, 0, 0)})
        self.assertEqual(back.entities[0].pos, (4.5, 0.0, 0.5))

    def test_many_palette_entries_cross_long_boundary(self):
        b = Build("palette")
        instruments = ["harp", "basedrum", "snare", "hat", "bass", "flute",
                       "bell", "guitar", "chime", "xylophone"]
        states = []
        for inst in instruments:
            for note in range(25):
                states.append(
                    f"minecraft:note_block[instrument={inst},note={note},"
                    f"powered=false]")
        for i, state in enumerate(states):
            b.set(i % 50, 0, i // 50, state)
        self.assertGreater(len(states), 128)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "palette.litematic")
            save_litematic(b, path)
            back = load_litematic(path)
            self.assertEqual(back.blocks, b.blocks)

    def test_version_mapping(self):
        self.assertEqual(schematic_version_for_data_version(1000), (4, None))
        self.assertEqual(schematic_version_for_data_version(2000), (5, None))
        self.assertEqual(schematic_version_for_data_version(3000), (6, None))
        self.assertEqual(schematic_version_for_data_version(3200), (6, 1))
        self.assertEqual(schematic_version_for_data_version(3955), (7, 1))


class SpongeTest(unittest.TestCase):
    def test_v2_round_trip(self):
        b = sample_build()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sample.schem")
            save_sponge(b, path, version=2)
            back = load_sponge(path)
            self.assertEqual(back.blocks, b.blocks)
            self.assertEqual(back.block_entities, b.block_entities)
            self.assertEqual([(e.id, e.pos) for e in back.entities],
                             [(e.id, e.pos) for e in b.entities])
            self.assertEqual(back.meta["version"], 2)
            self.assertEqual(back.meta["format"], "schem")

    def test_explicit_offset_translates_blocks_and_entities(self):
        b = Build("offset")
        b.set(10, 0, 10, "stone")
        b.chest_with_items(11, 0, 10, [
            {"slot": 0, "id": "stone", "count": 1}])
        b.add_entity("minecraft:pig", 11.5, 1.0, 10.5)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "offset.schem")
            save_sponge(b, path, offset=(100, 5, 100))
            back = load_sponge(path)
            self.assertEqual(set(back.blocks), {(100, 5, 100), (101, 5, 100)})
            self.assertEqual(back.block_entities[(101, 5, 100)]["id"],
                             "minecraft:chest")
            self.assertEqual(back.entities[0].pos, (101.5, 6.0, 100.5))

    def test_v3_round_trip(self):
        b = sample_build()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sample_v3.schem")
            save_sponge(b, path, version=3)
            back = load_sponge(path)
            self.assertEqual(back.blocks, b.blocks)
            self.assertEqual(back.block_entities, b.block_entities)
            self.assertEqual([(e.id, e.pos) for e in back.entities],
                             [(e.id, e.pos) for e in b.entities])
            self.assertEqual(back.meta["version"], 3)

    def test_v3_root_name_is_empty(self):
        b = Build("root")
        b.set(0, 0, 0, "stone")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "root.schem")
            save_sponge(b, path, version=3)
            name, root = nbt.load_file_named(path)
            self.assertEqual(name, "")
            self.assertIn("Schematic", root)


class DispatchTest(unittest.TestCase):
    def test_save_and_load_infer_from_extension(self):
        b = Build("dispatch")
        b.set(0, 0, 0, "stone")
        with tempfile.TemporaryDirectory() as tmp:
            for ext in (".litematic", ".schem"):
                path = os.path.join(tmp, "d" + ext)
                b.save(path)
                self.assertEqual(load(path).blocks, b.blocks)
                data = info(path)
                self.assertEqual(data["blocks"], 1)
                self.assertEqual(data["size"], (1, 1, 1))

    def test_cli_run_and_info(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "build.py")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write(
                    "b = Build('cli')\n"
                    "b.fill(0, 0, 0, 1, 0, 1, 'stone')\n"
                )
            out = os.path.join(tmp, "cli.litematic")
            result = subprocess.run(
                [sys.executable, "-m", "mcba", "run", script, "--out", out],
                cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(os.path.isfile(out))
            result = subprocess.run(
                [sys.executable, "-m", "mcba", "info", out, "--json"],
                cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"blocks": 4', result.stdout)


if __name__ == "__main__":
    unittest.main()
