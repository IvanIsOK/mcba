"""Dependency-free NBT (Named Binary Tag) reader and writer.

Only what Minecraft schematic formats need: every standard tag type,
big-endian encoding and optional gzip wrapping.

Values are represented with small wrapper types so the exact tag type is
preserved.  Plain Python ``int`` / ``float`` / ``str`` / ``dict`` / ``list``
also work when writing (they are mapped to int / double / string / compound /
list).  Reading always returns the wrapper types so a value can be written
back unchanged.
"""

from __future__ import annotations

import gzip
import io
import struct
from typing import Any, Iterable

# Tag ids from the NBT specification.
TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12

TAG_NAMES = {
    TAG_END: "End",
    TAG_BYTE: "Byte",
    TAG_SHORT: "Short",
    TAG_INT: "Int",
    TAG_LONG: "Long",
    TAG_FLOAT: "Float",
    TAG_DOUBLE: "Double",
    TAG_BYTE_ARRAY: "ByteArray",
    TAG_STRING: "String",
    TAG_LIST: "List",
    TAG_COMPOUND: "Compound",
    TAG_INT_ARRAY: "IntArray",
    TAG_LONG_ARRAY: "LongArray",
}


class NBTByte(int):
    pass


class NBTShort(int):
    pass


class NBTInt(int):
    pass


class NBTLong(int):
    pass


class NBTFloat(float):
    pass


class NBTDouble(float):
    pass


class NBTByteArray(list):
    """A byte array.  Accepts ``bytes`` or an iterable of ints."""

    def __init__(self, data: Iterable[int] | bytes = b""):
        if isinstance(data, (bytes, bytearray, memoryview)):
            data = list(bytes(data))
        super().__init__(data)


class NBTIntArray(list):
    pass


class NBTLongArray(list):
    pass


class NBTList(list):
    """A list tag.  ``elem_type`` is required for empty lists."""

    def __init__(self, items: Iterable[Any] = (), elem_type: int | None = None):
        super().__init__(items)
        self.elem_type = elem_type


class NBTCompound(dict):
    """A compound tag (a dict with a marker type)."""


def tag_id(value: Any) -> int:
    """Return the NBT tag id for a Python value."""
    if isinstance(value, bool):
        return TAG_BYTE
    if isinstance(value, NBTByte):
        return TAG_BYTE
    if isinstance(value, NBTShort):
        return TAG_SHORT
    if isinstance(value, NBTInt):
        return TAG_INT
    if isinstance(value, NBTLong):
        return TAG_LONG
    if isinstance(value, NBTFloat):
        return TAG_FLOAT
    if isinstance(value, NBTDouble):
        return TAG_DOUBLE
    if isinstance(value, NBTByteArray):
        return TAG_BYTE_ARRAY
    if isinstance(value, NBTIntArray):
        return TAG_INT_ARRAY
    if isinstance(value, NBTLongArray):
        return TAG_LONG_ARRAY
    if isinstance(value, NBTList):
        return TAG_LIST
    if isinstance(value, NBTCompound):
        return TAG_COMPOUND
    if isinstance(value, str):
        return TAG_STRING
    if isinstance(value, int):
        return TAG_INT
    if isinstance(value, float):
        return TAG_DOUBLE
    if isinstance(value, dict):
        return TAG_COMPOUND
    if isinstance(value, (list, tuple)):
        return TAG_LIST
    if isinstance(value, (bytes, bytearray, memoryview)):
        return TAG_BYTE_ARRAY
    raise TypeError(f"cannot convert {type(value)!r} to an NBT tag")


def _infer_list_type(items: Iterable[Any]) -> int:
    for item in items:
        return tag_id(item)
    return TAG_END


def _to_signed(value: int, bits: int) -> int:
    mask = (1 << bits) - 1
    value &= mask
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value


def _write_string(out: io.BytesIO, value: str) -> None:
    data = value.encode("utf-8")
    if len(data) > 0xFFFF:
        raise ValueError("NBT string is too long")
    out.write(struct.pack(">H", len(data)))
    out.write(data)


def _write_payload(out: io.BytesIO, tag: int, value: Any) -> None:
    if tag == TAG_BYTE:
        out.write(struct.pack(">b", _to_signed(int(value), 8)))
    elif tag == TAG_SHORT:
        out.write(struct.pack(">h", _to_signed(int(value), 16)))
    elif tag == TAG_INT:
        out.write(struct.pack(">i", _to_signed(int(value), 32)))
    elif tag == TAG_LONG:
        out.write(struct.pack(">q", _to_signed(int(value), 64)))
    elif tag == TAG_FLOAT:
        out.write(struct.pack(">f", float(value)))
    elif tag == TAG_DOUBLE:
        out.write(struct.pack(">d", float(value)))
    elif tag == TAG_BYTE_ARRAY:
        data = bytes(int(v) & 0xFF for v in value)
        out.write(struct.pack(">i", len(data)))
        out.write(data)
    elif tag == TAG_STRING:
        _write_string(out, str(value))
    elif tag == TAG_LIST:
        if isinstance(value, NBTList) and value.elem_type is not None:
            elem_type = value.elem_type
        else:
            elem_type = _infer_list_type(value)
        if len(value) == 0 and elem_type == TAG_END:
            out.write(struct.pack(">bi", TAG_END, 0))
            return
        out.write(struct.pack(">bi", elem_type, len(value)))
        for item in value:
            _write_payload(out, elem_type, item)
    elif tag == TAG_COMPOUND:
        for key, item in value.items():
            item_tag = tag_id(item)
            if item_tag == TAG_END:
                raise ValueError(f"cannot write an End tag (key {key!r})")
            out.write(struct.pack(">b", item_tag))
            _write_string(out, str(key))
            _write_payload(out, item_tag, item)
        out.write(struct.pack(">b", TAG_END))
    elif tag == TAG_INT_ARRAY:
        out.write(struct.pack(">i", len(value)))
        for item in value:
            out.write(struct.pack(">i", _to_signed(int(item), 32)))
    elif tag == TAG_LONG_ARRAY:
        out.write(struct.pack(">i", len(value)))
        for item in value:
            out.write(struct.pack(">q", _to_signed(int(item), 64)))
    else:
        raise ValueError(f"unknown tag id {tag}")


def dumps(value: Any, root_name: str = "", gzipped: bool = True,
          compression_level: int = 6) -> bytes:
    """Serialize a compound to NBT bytes (gzip wrapped by default)."""
    tag = tag_id(value)
    if tag != TAG_COMPOUND:
        raise TypeError("the NBT root must be a compound (dict)")
    out = io.BytesIO()
    out.write(struct.pack(">b", TAG_COMPOUND))
    _write_string(out, root_name)
    _write_payload(out, TAG_COMPOUND, value)
    data = out.getvalue()
    if gzipped:
        return gzip.compress(data, compresslevel=compression_level, mtime=0)
    return data


class _Reader:
    def __init__(self, data: bytes):
        self.f = io.BytesIO(data)

    def _read(self, n: int) -> bytes:
        data = self.f.read(n)
        if len(data) != n:
            raise EOFError("unexpected end of NBT data")
        return data

    def _unpack(self, fmt: str) -> Any:
        return struct.unpack(fmt, self._read(struct.calcsize(fmt)))[0]

    def _read_string(self) -> str:
        length = self._unpack(">H")
        return self._read(length).decode("utf-8")

    def _read_payload(self, tag: int) -> Any:
        if tag == TAG_BYTE:
            return NBTByte(self._unpack(">b"))
        if tag == TAG_SHORT:
            return NBTShort(self._unpack(">h"))
        if tag == TAG_INT:
            return NBTInt(self._unpack(">i"))
        if tag == TAG_LONG:
            return NBTLong(self._unpack(">q"))
        if tag == TAG_FLOAT:
            return NBTFloat(self._unpack(">f"))
        if tag == TAG_DOUBLE:
            return NBTDouble(self._unpack(">d"))
        if tag == TAG_BYTE_ARRAY:
            length = self._unpack(">i")
            return NBTByteArray(self._read(length))
        if tag == TAG_STRING:
            return self._read_string()
        if tag == TAG_LIST:
            elem_type = self._unpack(">b")
            length = self._unpack(">i")
            if elem_type == TAG_END:
                return NBTList([], elem_type=TAG_END)
            return NBTList([self._read_payload(elem_type) for _ in range(length)],
                           elem_type=elem_type)
        if tag == TAG_COMPOUND:
            result = NBTCompound()
            while True:
                item_tag = self._unpack(">b")
                if item_tag == TAG_END:
                    return result
                key = self._read_string()
                result[key] = self._read_payload(item_tag)
        if tag == TAG_INT_ARRAY:
            length = self._unpack(">i")
            return NBTIntArray(self._unpack(">i") for _ in range(length))
        if tag == TAG_LONG_ARRAY:
            length = self._unpack(">i")
            return NBTLongArray(self._unpack(">q") for _ in range(length))
        raise ValueError(f"unknown tag id {tag}")

    def read_root(self) -> tuple[str, Any]:
        tag = self._unpack(">b")
        if tag != TAG_COMPOUND:
            raise ValueError("the NBT root is not a compound")
        name = self._read_string()
        return name, self._read_payload(TAG_COMPOUND)


def loads(data: bytes, gzipped: bool | None = None) -> Any:
    """Parse NBT bytes and return the root compound value."""
    if gzipped is None:
        gzipped = data[:2] == b"\x1f\x8b"
    if gzipped:
        data = gzip.decompress(data)
    return _Reader(data).read_root()[1]


def loads_named(data: bytes, gzipped: bool | None = None) -> tuple[str, Any]:
    """Parse NBT bytes and return ``(root_name, root_value)``."""
    if gzipped is None:
        gzipped = data[:2] == b"\x1f\x8b"
    if gzipped:
        data = gzip.decompress(data)
    return _Reader(data).read_root()


def load_file(path: str, gzipped: bool | None = None) -> Any:
    with open(path, "rb") as fh:
        return loads(fh.read(), gzipped=gzipped)


def load_file_named(path: str, gzipped: bool | None = None) -> tuple[str, Any]:
    with open(path, "rb") as fh:
        return loads_named(fh.read(), gzipped=gzipped)


def save_file(path: str, value: Any, root_name: str = "",
              gzipped: bool = True) -> None:
    with open(path, "wb") as fh:
        fh.write(dumps(value, root_name=root_name, gzipped=gzipped))


# Short aliases used by the rest of the package.
def B(v: int) -> NBTByte:
    return NBTByte(v)


def S(v: int) -> NBTShort:
    return NBTShort(v)


def I(v: int) -> NBTInt:
    return NBTInt(v)


def L(v: int) -> NBTLong:
    return NBTLong(v)


def F(v: float) -> NBTFloat:
    return NBTFloat(v)


def D(v: float) -> NBTDouble:
    return NBTDouble(v)
