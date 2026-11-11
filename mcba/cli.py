"""Command line interface for mcba.

    python -m mcba run build_script.py --out house.litematic
    python -m mcba info house.litematic
    python -m mcba convert house.litematic house.schem
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import builder, blocks, nbt, schematic
from .builder import Build
from .schematic import load, save


def _run(args: argparse.Namespace) -> int:
    path = args.script
    if not os.path.isfile(path):
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": os.path.abspath(path),
        "Build": Build,
        "BlockState": blocks.BlockState,
        "nbt": nbt,
        "save": save,
        "load": load,
        "b": None,
        "build": None,
    }
    for name in getattr(blocks, "__all__", []):
        namespace[name] = getattr(blocks, name)
    for name in ("stairs", "slab", "wall", "fence", "pane", "log", "leaves",
                 "piston", "observer", "repeater", "comparator",
                 "redstone_wire", "redstone_torch", "torch", "redstone_lamp",
                 "lever", "button", "door", "trapdoor", "fence_gate", "rail",
                 "hopper", "dropper", "dispenser", "chest", "furnace",
                 "lantern", "campfire", "sign", "banner", "bed", "candle"):
        namespace[name] = getattr(blocks, name)
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    code = compile(source, os.path.abspath(path), "exec")
    exec(code, namespace)

    out = args.out
    if out:
        target = namespace.get("build")
        if target is None:
            target = namespace.get("b")
        if not isinstance(target, Build):
            candidates = [v for v in namespace.values() if isinstance(v, Build)]
            if not candidates:
                print("error: the script did not leave a Build in 'build' or 'b'",
                      file=sys.stderr)
                return 3
            target = candidates[-1]
        kwargs: dict[str, Any] = {}
        if args.data_version is not None:
            kwargs["data_version"] = args.data_version
        if args.format == "schem":
            kwargs["version"] = args.schem_version
        save(target, out, fmt=args.format, **kwargs)
        print(f"wrote {out} ({target.describe()})")
    return 0


def _info(args: argparse.Namespace) -> int:
    data = schematic.info(args.file)
    if args.json:
        data["size"] = list(data["size"])
        data["bounds"] = list(data["bounds"]) if data["bounds"] else None
        print(json.dumps(data, indent=2, default=str))
    else:
        sx, sy, sz = data["size"]
        print(f"file:           {data['path']}")
        print(f"format:         {data['format']} v{data['version']} "
              f"(data version {data['data_version']})")
        print(f"name:           {data['name']}")
        print(f"author:         {data['author']}")
        print(f"size:           {sx} x {sy} x {sz}")
        print(f"blocks:         {data['blocks']}")
        print(f"entities:       {data['entities']}")
        print(f"block entities: {data['block_entities']}")
        print("top block types:")
        for name, count in list(data["block_types"].items())[:20]:
            print(f"  {count:8d}  {name}")
    return 0


def _convert(args: argparse.Namespace) -> int:
    build = load(args.input)
    kwargs: dict[str, Any] = {}
    if args.data_version is not None:
        kwargs["data_version"] = args.data_version
    if args.format == "schem":
        kwargs["version"] = args.schem_version
    save(build, args.output, fmt=args.format, **kwargs)
    print(f"wrote {args.output} ({build.describe()})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcba",
        description="Author Minecraft builds and export .litematic / .schem")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a Python build script")
    run.add_argument("script")
    run.add_argument("--out", "-o", help="output schematic path")
    run.add_argument("--format", choices=["litematic", "schem"])
    run.add_argument("--data-version", type=int,
                     help="Minecraft data version (default 3955 / 1.21.1)")
    run.add_argument("--schem-version", type=int, choices=[2, 3], default=2,
                     help="Sponge schematic version (default 2)")
    run.set_defaults(func=_run)

    info = sub.add_parser("info", help="inspect a schematic")
    info.add_argument("file")
    info.add_argument("--json", action="store_true")
    info.set_defaults(func=_info)

    convert = sub.add_parser("convert", help="convert between formats")
    convert.add_argument("input")
    convert.add_argument("output")
    convert.add_argument("--format", choices=["litematic", "schem"])
    convert.add_argument("--data-version", type=int)
    convert.add_argument("--schem-version", type=int, choices=[2, 3], default=2)
    convert.set_defaults(func=_convert)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
