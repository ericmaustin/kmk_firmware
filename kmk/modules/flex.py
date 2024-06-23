from __future__ import annotations

try:
    from typing import (
        TYPE_CHECKING,
        Tuple,
        Dict,
        List,
        NamedTuple,
        Mapping,
        Generator,
        Callable,
    )
except ImportError:
    TYPE_CHECKING = False
    pass

from micropython import const

from kmk.keys import KC, Key, ModifierKey, make_argumented_key
from kmk.modules import Module
from kmk.utils import Debug
from kmk.kmk_keyboard import KMKKeyboard


if TYPE_CHECKING:
    KeyAction = Callable[[tuple[Key, ...], KMKKeyboard, Key | None], None]

_debug = Debug(__name__)

# default value constants
DEFAULT_TIMEOUT = const(300)
DEFAULT_TAP_TIME = const(100)
DEFAULT_TAP_DELAY = const(10)

if _debug.enabled:

    def debug(msg: str):
        _debug("[Flex] " + msg)

else:

    def debug(_: str):
        pass


def add_mods(key: Key, mods: set[ModifierKey]) -> Key:
    for mod in mods:
        key = mod(key)
    return key


def maybe_add_mods(key: Key, mods: set[ModifierKey], keyboard: KMKKeyboard) -> Key:
    for mod in mods - keyboard.keys_pressed:
        key = mod(key, keyboard)
    return key


def tap_key(
    key: Key,
    keyboard: KMKKeyboard,
    send_hid_after_add: bool = False,
    send_hid_after_remove: bool = False,
):
    keyboard.add_key(key)
    if send_hid_after_add:
        keyboard._send_hid()
    keyboard.remove_key(key)
    if send_hid_after_remove:
        keyboard._send_hid()


class KeyStatus:
    NONE = const(0)
    TAP = const(1)
    HELD = const(2)
    HOLD_TIMEOUT = const(3)
    RELEASED = const(4)


class FlexMeta:
    def __init__(
        self,
        tap: Key,
        hold: list[Key] | Key | None = None,
        mod: set[ModifierKey] | ModifierKey = None,
        mod_targets: set[Key] | None = None,
        tap_timeout: int = DEFAULT_TAP_TIME,
        hold_timeout: int = DEFAULT_TIMEOUT,
        hold_delay: int = DEFAULT_TAP_DELAY,
    ):
        self.tap: Key = tap
        self.tap_timeout: int = tap_timeout
        self.hold = hold if not isinstance(hold, Key) else [hold]
        self.hold_delay: int = hold_delay
        self.hold_timeout: int = hold_timeout
        self.mod: set[ModifierKey] = mod if isinstance(mod, set) else {mod}
        self.mod_targets: set[Key] = mod_targets

    def __eq__(self, other):
        return self.tap == other.key


def flex_key(
    tap: Key | None = None,
    hold: list[Key] | Key | None = None,
    mod: set[ModifierKey] | ModifierKey = None,
    hold_mod: set[ModifierKey] | ModifierKey = None,
    mod_targets: set[Key] | None = None,
    tap_timeout: int = DEFAULT_TAP_TIME,
    hold_timeout: int = DEFAULT_TIMEOUT,
    hold_delay: int = DEFAULT_TAP_DELAY,
    mod_replace: dict[tuple[ModifierKey] | ModifierKey, Key] = None,
) -> Callable[..., Key]:
    def factory(*args, **kwargs) -> Key:
        arg_iter = iter(args)
        tap_key = next(arg_iter, None) or kwargs.pop('tap_key', None) or tap
        hold_keys = next(arg_iter, None) or kwargs.pop('hold_keys', None) or hold
        if hold_keys:
            hold_keys = hold_keys if isinstance(hold_keys, list) else [hold_keys]
        if hold_mod:
            if not hold_keys:
                hold_keys = [tap_key]
            hold_mods = hold_mod if isinstance(hold_mod, set) else {hold_mod}
            for i, k in enumerate(hold_keys):
                hold_keys[i] = add_mods(k, hold_mods)

        factory_kwargs = {
            k: v
            for k, v in {
                'tap': tap_key,
                'hold': hold_keys,
                'mod': mod,
                'mod_targets': mod_targets,
                'tap_timeout': tap_timeout,
                'hold_timeout': hold_timeout,
                'hold_delay': hold_delay,
                'mod_replace': mod_replace,
            }.items()
            if v is not None
        }
        factory_kwargs |= kwargs

        return KC.FLEX(
            *list(arg_iter),
            **factory_kwargs,
        )

    return factory


class _KeyState:
    def __init__(
        self,
        key: Key,
        state: int,
        int_coord: int,
        config: FlexMeta | None = None,
    ):
        self.key: Key = key
        self.config: FlexMeta = config
        self.int_coord: int = int_coord
        self.status: int = state
        self.interrupted = False
        self.hold_idx = 0
        # pre-calculate hash
        self.__hash = hash((self.key, self.int_coord))

    @property
    def has_config(self) -> bool:
        return self.config is not None

    @property
    def hash(self):
        return self.__hash

    def set_status(self, status: int):
        self.status = status

    def __hash__(self) -> int:
        return self.__hash

    def __eq__(self, other):
        return (self.key == other.key) and (self.int_coord == other.int_coord)

    def __repr__(self):
        return f"<HrmKeyState(state={self.status}, int_coord{self.int_coord})>"


class Flex(Module):
    def __init__(
        self,
        overrides: dict[Key, FlexMeta] = None,
    ):

        self._map = overrides or {}
        self._key_buffer: dict[int, _KeyState] = {}
        self._tap_tasks: dict[int, int] = {}
        self._hold_tasks: dict[int, int] = {}

        make_argumented_key(
            validator=FlexMeta,
            names=('FX', 'FLX', 'FLEX'),
        )

    def process_key(
        self, keyboard: KMKKeyboard, current_key: Key, is_pressed: bool, int_coord: int
    ):
        key = _KeyState(
            key=current_key,
            state=KeyStatus.TAP if is_pressed else KeyStatus.RELEASED,
            int_coord=int_coord,
        )

        if key.key in self._map.keys():
            key.config = self._map[key.key]
            # key.key = key.config.tap_key

        elif isinstance(key.key.meta, FlexMeta):
            # flexmeta argumented key
            key.config = key.key.meta
            # key.key = key.config.tap_key

        if is_pressed:
            return self.handle_press(key, keyboard)

        return self.handle_release(key, keyboard)

    def handle_press(self, key: _KeyState, keyboard: KMKKeyboard) -> Key | None:
        # remove key from buffer if it's already there (re-press)
        self.remove_key(key.hash, keyboard)
        # process interrupt for all held keys
        for k in tuple(self._key_buffer.values()):
            # cancel any active hold tasks on interrupt
            k.interrupted = True
            if k.status == KeyStatus.TAP:
                # if we're within that TAP window then just tap the key now
                # ... this is a better experience when rolling keysa
                self.remove_key(k.hash, keyboard)
                k.status = KeyStatus.RELEASED
                tap_key(k.config.tap, keyboard, send_hid_after_add=True)

            if (
                k.status in (KeyStatus.HELD, KeyStatus.HOLD_TIMEOUT)
                and k.config.mod
                # only add mods if the key is in the mod_targets
                and (not k.config.mod_targets or key.key in k.config.mod_targets)
            ):
                # add mods from any held keys with mods
                key.key = maybe_add_mods(key.key, k.config.mod, keyboard)

        if key.config:
            if key.config.hold or key.config.mod:
                debug(f"handle_press({key.key}) captured key hash = {key.hash}")
                # add key to buffer only if we are delaying tap
                self._key_buffer[key.hash] = key
                if key.config.tap_timeout > 0:
                    self._tap_tasks[key.hash] = keyboard.set_timeout(
                        key.config.tap_timeout,
                        lambda _k=key.hash: self.handle_tap_timeout(_k, keyboard),
                    )
                else:
                    self._hold_tasks[key.hash] = keyboard.set_timeout(
                        key.config.hold_timeout,
                        lambda _k=key.hash: self.handle_hold_timeout(_k, keyboard),
                    )
                return None

        return key.key

    def handle_release(self, key: _KeyState, keyboard: KMKKeyboard) -> Key | None:
        if key.config:
            if key.hash in self._key_buffer.keys():
                key = self._key_buffer[key.hash]

                if key.status == KeyStatus.TAP or (
                    not key.interrupted
                    and (not key.config.hold or key.status == KeyStatus.HELD)
                ):
                    # still in tap mode, so tap the key
                    tap_key(key.config.tap, keyboard, send_hid_after_add=True)

                debug(f"handle_release({key.key}) removing key from buffer")
                self.remove_key(key.hash, keyboard)

        return key.key

    def remove_key(self, key_hash: int, keyboard):
        self.cancel_all_tasks(key_hash, keyboard)
        if key_hash in self._key_buffer.keys():
            del self._key_buffer[key_hash]

    def handle_tap_timeout(self, key_hash: int, keyboard: KMKKeyboard):
        del self._tap_tasks[key_hash]
        if key_hash not in self._key_buffer.keys():
            return

        key = self._key_buffer[key_hash]

        if key.status != KeyStatus.TAP:
            return

        debug(f"handle_tap_timeout({key.key}) tap timeout, setting key to HELD")
        key.status = KeyStatus.HELD
        if key.config.hold:
            self._hold_tasks[key_hash] = keyboard.set_timeout(
                key.config.hold_timeout,
                lambda _k=key_hash: self.handle_hold_timeout(key_hash, keyboard),
            )

    def handle_hold_timeout(self, key_hash: int, keyboard: KMKKeyboard):
        del self._hold_tasks[key_hash]
        if key_hash not in self._key_buffer.keys():
            debug(f"handle_hold_timeout({key_hash}) key not in buffer")
            return

        key = self._key_buffer[key_hash]
        key.status = KeyStatus.HOLD_TIMEOUT
        debug(
            f"handle_hold_timeout({key.key}) tapping hold key {key.config.hold[key.hold_idx]}"
        )
        hold_key = key.config.hold[key.hold_idx]
        tap_key(hold_key, keyboard, send_hid_after_add=True)
        key.hold_idx += 1
        if key.hold_idx < len(key.config.hold):
            self._hold_tasks[key_hash] = keyboard.set_timeout(
                key.config.hold_delay,
                lambda _k=key_hash: self.handle_hold_timeout(_k, keyboard),
            )

    def cancel_all_tasks(self, key_hash: int, keyboard: KMKKeyboard):
        self.cancel_tap_task(key_hash, keyboard)
        self.cancel_hold_task(key_hash, keyboard)

    def cancel_tap_task(self, key_hash: int, keyboard: KMKKeyboard):
        if key_hash in self._tap_tasks:
            keyboard.cancel_timeout(self._tap_tasks[key_hash])
            del self._tap_tasks[key_hash]

    def cancel_hold_task(self, key_hash: int, keyboard: KMKKeyboard):
        if key_hash in self._hold_tasks:
            debug(f"cancel_hold_task({key_hash})")
            keyboard.cancel_timeout(self._hold_tasks[key_hash])
            del self._hold_tasks[key_hash]

    def before_hid_send(self, keyboard):
        return

    def after_hid_send(self, keyboard):
        return

    def on_powersave_enable(self, keyboard):
        return

    def on_powersave_disable(self, keyboard):
        return

    def during_bootup(self, keyboard):
        return

    def before_matrix_scan(self, keyboard):
        return

    def after_matrix_scan(self, keyboard):
        return
