from __future__ import annotations

try:
    from ucollections import namedtuple
except ImportError:
    from collections import namedtuple

try:
    from typing import NamedTuple
except ImportError:
    NamedTuple = object


class Flag:
    __slots__ = ('_bits',)

    def __init__(self, bits: int = None):
        self._bits = bits

    def set(self, bits: int) -> Flag:
        self._bits = bits
        return self

    @property
    def is_set(self) -> bool:
        return self._bits is not None

    @property
    def bits(self) -> int:
        if self._bits is None:
            raise ValueError(f"{self.__class__.__name__} is not set")
        return self._bits

    def __contains__(self, item: Flag) -> bool:
        return self._bits & item.bits == item.bits

    def __lt__(self, other: Flag) -> Flag:
        return Flag(self.bits < other.bits)

    def __eq__(self, other: Flag) -> bool:
        return self.bits == other.bits

    def __and__(self, other: Flag) -> Flag:
        return Flag(self.bits & other.bits)

    def __or__(self, other: Flag) -> Flag:
        return Flag(self.bits | other.bits)

    def __xor__(self, other: Flag) -> Flag:
        return Flag(self.bits ^ other.bits)

    def __invert__(self) -> Flag:
        return Flag(~self.bits)

    def __repr__(self):
        return f'<{self.__class__.__name__} bits={self.bits} bin={bin(self.bits)}>'


class Operation(Flag):
    __slots__ = '_operation'

    def __init__(self, operation: str):
        super().__init__()
        self._operation = operation

    @property
    def operation(self) -> str:
        return self._operation

    def load(self, resolved_flags: dict[str, Flag]):
        operation = (' ' + self.operation + ' ').replace('  ', ' ')
        resolved_flags |= {
            'ALL': ALL,
            'ANY': ALL,
            'NO': NO,
            'NONE': NO,
        }
        for k, v in resolved_flags.items():
            operation = operation.replace(' ' + k + ' ', ' ' + str(v.bits) + ' ')
        self._bits = eval(operation.strip())


class All(Flag):
    def __init__(self):
        super().__init__()
        self._bits = -1


class No(Flag):
    def __init__(self):
        super().__init__()
        self._bits = 0


def init(flags: dict[str, Flag]):
    resolved_flags = {}
    ops = []
    i = 0
    for k, flag in flags.items():
        if isinstance(flag, Operation):
            ops.append(flag)
        else:
            if not flag.is_set:
                flag.set(1 << i)
                i += 1
            resolved_flags[k] = flag

    for op in ops:
        op.load(resolved_flags)


def _init_flagged(cls):
    flags = {}
    for k in dir(cls):
        attr = getattr(cls, k)
        if isinstance(attr, Flag):
            flags[k] = attr
    init(flags)


class Flagged:
    def __init__(self):
        _init_flagged(self)


def flagged(cls):
    """decorator to initialize flags in class properties"""

    class Wrapped(cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            _init_flagged(self)

    _init_flagged(Wrapped)
    return Wrapped


def named_flags(name: str, fields: tuple[str | tuple, ...]):
    resolved_flags = {}
    ops = {}
    for i, field in enumerate(fields):
        if isinstance(field, tuple):
            ops[field[0]] = Operation(field[1])
            continue
        resolved_flags[field] = Flag(1 << i)

    for k, op in ops.items():
        op.load(resolved_flags)
        resolved_flags[k] = op

    return namedtuple(name, resolved_flags.keys())(*resolved_flags.values())


ALL = All()
ANY = ALL
NO = No()
NONE = NO
