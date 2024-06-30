from __future__ import annotations

try:
    from typing import TYPE_CHECKING, Callable
except ImportError:
    TYPE_CHECKING = False
    pass

from micropython import const

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC, Key, ModifierKey, make_argumented_key
from kmk.scheduler import cancel_task, create_task
from kmk.modules import Module
from kmk.utils import Debug


_debug = Debug(__name__)


def debug(msg: str):
    if _debug.enabled:
        _debug("[Flex] " + msg)


# default value constants
DEFAULT_TIMEOUT = const(300)
DEFAULT_TAP_TIME = const(100)
DEFAULT_TAP_DELAY = const(10)

MOD_KEYS = {
    KC.LCTRL,
    KC.LSHIFT,
    KC.LALT,
    KC.LGUI,
    KC.RCTRL,
    KC.RSHIFT,
    KC.RALT,
    KC.RGUI,
}


class KeyStatus:
    NONE = const(0)
    PRESSED = const(1)
    # HELD = const(2)
    INTERRUPTED = const(3)
    RELEASED = const(5)


# todo: use the below methods to add mods on hold timeout!
def maybe_add_keys(keys: set[ModifierKey], keyboard: KMKKeyboard) -> set[ModifierKey]:
    if keys:
        keys_added = keys - keyboard.keys_pressed
        keyboard.keys_pressed = keyboard.keys_pressed | keys_added
        return keys_added


def maybe_rm_keys(keys: set[ModifierKey], keyboard: KMKKeyboard) -> set[ModifierKey]:
    if keys:
        keys_removed = keys & keyboard.keys_pressed
        keyboard.keys_pressed = keyboard.keys_pressed - keys_removed
        return keys_removed


def tap_key(mod: Module, keyboard: KMKKeyboard, key: Key):
    keyboard.resume_process_key(mod, key, True)
    keyboard.resume_process_key(mod, key, False)


class FlexMeta:
    def __init__(
        self,
        tap: tuple[Key, ...] | Key | None,
        hold: tuple[Key | int, ...] | Key | int | None = None,
        mod_interrupt: set[ModifierKey] | ModifierKey = None,
        tap_time: int = DEFAULT_TAP_TIME,
        hold_timeout: int = DEFAULT_TIMEOUT,
        hold_delay: int = -1,
        mod_interrupt_targets: set[Key] | None = None,
    ):
        self.tap: tuple[Key, ...] = (
            tap if isinstance(tap, tuple) else ((tap,) if tap else None)
        )
        self.hold: tuple[Key | int, ...] | None = (
            hold if isinstance(hold, tuple) else ((hold,) if hold else None)
        )
        self.mod_interrupt: set[ModifierKey] | None = (
            mod_interrupt
            if isinstance(mod_interrupt, set)
            else ({mod_interrupt} if mod_interrupt else None)
        )
        self.tap_time = tap_time
        self.hold_timeout = hold_timeout
        self.hold_delay = hold_delay
        self.mod_interrupt_target_codes: set[int] = (
            set([k.code for k in mod_interrupt_targets])
            if mod_interrupt_targets
            else set()
        )


class FlexKeyState:
    def __init__(
        self,
        key: Key,
        key_id: int,
    ):
        self.key: Key = key
        self.__id: int = key_id
        self.__status_log: list[int] = []
        self.__tap_task: int | None = None
        self.__hold_task: int | None = None
        self.__delay_task: int | None = None
        self.__hold_idx: int = 0
        self.__buffer: list[Key] = []
        self.__pressed: set[Key] = set()

    @property
    def id(self) -> int:
        return self.__id

    @property
    def meta(self) -> FlexMeta:
        return self.key.meta

    @property
    def interrupted(self) -> bool:
        return KeyStatus.INTERRUPTED in self.__status_log

    @property
    def held_continuously(self) -> bool:
        return (
            KeyStatus.INTERRUPTED not in self.__status_log
            and KeyStatus.RELEASED not in self.__status_log
        )

    @property
    def status(self) -> int:
        try:
            return self.__status_log[-1]
        except IndexError:
            return KeyStatus.NONE

    @status.setter
    def status(self, value: int):
        self.__status_log.append(value)

    @property
    def tap_idx(self) -> int:
        c = 0
        for s in self.__status_log:
            if s == KeyStatus.PRESSED:
                c += 1

        return round((9 / c % 1) * c)

    @property
    def hold_target(self):
        return self.meta.hold[self.__hold_idx]

    def press(self, mod: Module, keyboard: KMKKeyboard):
        self.status = KeyStatus.PRESSED
        if self.__tap_task:
            # tap task is still running, do nothing...
            return

        self.__tap_task = create_task(
            lambda: self.__tap_timeout(mod, keyboard), after_ms=self.meta.tap_time
        )

    def release(self, mod: Module, keyboard: KMKKeyboard):
        self.status = KeyStatus.RELEASED
        self.__release_keys(mod, keyboard)

        if self.__tap_task is not None:
            # tap task is still running...
            return

        if self.__hold_task is not None:
            # cancel the hold
            cancel_task(self.__hold_task)
            self.__hold_task = None

        if self.__delay_task is not None:
            # cancel the delay
            cancel_task(self.__delay_task)
            self.__delay_task = None

        self.__hold_idx = 0
        self.__status_log.clear()
        self.__buffer.clear()

    def interrupt(self, interrupt_key: Key, mod: Module, keyboard: KMKKeyboard):
        last_status = self.status
        if self.__tap_task:
            self.status = KeyStatus.INTERRUPTED
            # interrupted before tap timeout
            cancel_task(self.__tap_task)
            self.__tap_task = None
            self.__press_key(self.meta.tap[self.tap_idx], mod, keyboard)
            return

        if last_status in (KeyStatus.RELEASED, KeyStatus.INTERRUPTED):
            return

        self.status = KeyStatus.INTERRUPTED
        # key is being held
        if self.__hold_task:
            cancel_task(self.__hold_task)
            self.__hold_task = None
        # cancel the delay task
        if self.__delay_task:
            cancel_task(self.__delay_task)
            self.__delay_task = None
        if (
            not self.meta.mod_interrupt_target_codes
            or interrupt_key.code in self.meta.mod_interrupt_target_codes
        ):
            for key in self.meta.mod_interrupt:
                self.__press_key(key, mod, keyboard)
        else:
            self.__press_key(self.meta.tap[self.tap_idx], mod, keyboard)

        self.__hold_idx = 0
        self.__buffer.clear()

    def __press_key(self, key: Key, mod: Module, keyboard: KMKKeyboard):
        if key in self.__pressed:
            return

        self.__pressed.add(key)
        keyboard.resume_process_key(mod, key, True)

    def __release_keys(self, mod: Module, keyboard: KMKKeyboard):
        for key in self.__pressed:
            keyboard.resume_process_key(mod, key, False)
        self.__pressed.clear()

    def __tap_timeout(self, mod: Module, keyboard: KMKKeyboard):
        self.__tap_task = None
        if not self.held_continuously:
            if not self.interrupted:
                self.__press_key(self.meta.tap[self.tap_idx], mod, keyboard)
            return

        if self.meta.hold_delay > 0:
            # hold delay is set, add a delay task
            self.__delay_task = create_task(
                lambda: self.__delay_timeout(mod, keyboard),
                after_ms=self.meta.hold_delay,
            )
        # process hold on the next loop
        self.__hold_task = create_task(
            lambda: self.__process_hold(mod, keyboard),
            after_ms=0,
        )

    def __process_hold(self, mod: Module, keyboard: KMKKeyboard):
        try:
            v = self.meta.hold[self.__hold_idx]
        except IndexError:
            # no more keys to tap
            self.__hold_task = None
            return

        if not self.held_continuously:
            # key wasn't continuously held, stop processing
            self.__hold_task = None
            return

        self.__hold_idx += 1

        if isinstance(v, int):
            # process hold after delay provived as in int
            self.__hold_task = create_task(
                lambda: self.__process_hold(mod, keyboard),
                after_ms=v,
            )
            return

        if self.__delay_task or self.meta.hold_delay < 0:
            # delay is running, or delay is inf (-1), add to buffer
            self.__buffer.append(v)
        else:
            tap_key(mod, keyboard, v)

        if self.__hold_idx >= len(self.meta.hold):
            # no more keys to tap
            self.__hold_task = None
            return

        self.__hold_task = create_task(
            lambda: self.__process_hold(mod, keyboard),
            after_ms=0,
        )

    def __delay_timeout(self, mod: Module, keyboard: KMKKeyboard):
        self.__delay_task = None
        for key in self.__buffer.copy():
            tap_key(mod, keyboard, key)
            keyboard._process_resume_buffer()  # force process resume buffer

    def __hash__(self) -> int:
        return self.__id

    def __repr__(self):
        return f"<{self.__class__.__name__}(Key={self.key.code} Status={self.status})>"


class Flex(Module):
    _buffer: dict[int, FlexKeyState] = {}

    def __init__(self):
        if KC.get('FX') == KC.NO:
            make_argumented_key(validator=FlexMeta, names=('FX', 'FLEX'))

    @property
    def buffer(self) -> tuple[FlexKeyState, ...]:
        # return a frozen state of the buffer as a list
        return tuple(self._buffer.values())

    def process_key(
        self, keyboard: KMKKeyboard, current_key: Key, is_pressed: bool, int_coord: int
    ):
        key_id = hash((current_key.code, int_coord))

        if isinstance(current_key.meta, FlexMeta):
            key_state = self._buffer.get(key_id) or FlexKeyState(
                key=current_key,
                key_id=key_id,
            )
        else:
            key_state = None

        if is_pressed:

        else:
            pass

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
