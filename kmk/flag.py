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
    __slots__ = ('_bits', '_name')

    def __init__(self, b: int = None, n: str = None):
        self._bits = b
        self._name = n

    def set(self, bits: int) -> Flag:
        self._bits = bits
        return self

    @property
    def name(self):
        return self._name or f"unnamed({self.bits})"

    @property
    def is_named(self) -> bool:
        return self._name is not None

    @name.setter
    def name(self, n: str):
        self._name = n

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

    def __lt__(self, other: Flag) -> bool:
        return self.bits < other.bits

    def __eq__(self, other: Flag) -> bool:
        return self.bits == other.bits

    def __and__(self, other: Flag) -> Flag:
        return Flag(self.bits & other.bits, n=f'{self.name} & {other.name}')

    def __or__(self, other: Flag) -> Flag:
        return Flag(self.bits | other.bits, n=f'{self.name} | {other.name}')

    def __xor__(self, other: Flag) -> Flag:
        return Flag(self.bits ^ other.bits, n=f'{self.name} ^ {other.name}')

    def __invert__(self) -> Flag:
        return Flag(~self.bits, n=f'~{self.name}')

    def __add__(self, other: Flag):
        return self | other

    def __sub__(self, other: Flag):
        return self & ~other

    def __repr__(self):
        return f'<Flag.{self.name}>'

    def __hash__(self):
        return hash(self.bits)


class Operation(Flag):
    __slots__ = '_operation'

    def __init__(self, o: str, n: str = None):
        super().__init__(n=n)
        self._operation = o

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
    def __init__(self, n: str = 'All'):
        super().__init__(-1, n)


class No(Flag):
    def __init__(self, n: str = 'No'):

        super().__init__(0, n)


def auto(operation: str = None):
    if operation:
        return Operation(operation)
    return Flag()


def init(flags: dict[str, Flag] | list[Flag]):
    resolved_flags = {}
    ops = []
    i = 0
    _iter = flags.items() if isinstance(flags, dict) else enumerate(flags)

    for k, flag in _iter:
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
            if not flags[k].is_named:
                flags[k].name = k
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


def named(name: str, flags: tuple[str | Flag, ...], operations: dict[str, str] = None):
    resolved_flags = {}
    for i, field in enumerate(flags):
        if isinstance(field, Flag):
            if not field.is_set:
                field.set(1 << i)
            resolved_flags[field.name] = field
        else:
            resolved_flags[field] = Flag(1 << i, field)

    for k, op in operations.items():
        _op = Operation(op, k)
        _op.load(resolved_flags)
        resolved_flags[k] = _op

    return namedtuple(name, resolved_flags.keys())(*resolved_flags.values())


ALL = All()
NO = No()
NONE = No(n='NONE')
ANY = All(n='ANY')
