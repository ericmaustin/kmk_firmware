try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False
    pass

from micropython import const

from kmk.keys import (
    KC,
    ModifierKey,
    Key,
    make_key,
)
from kmk.modules import Module
from kmk.scheduler import cancel_task, create_task
from kmk.utils import Debug
from kmk.kmk_keyboard import KMKKeyboard

_debug = Debug(__name__)


def debug(msg: str):
    if _debug.enabled:
        _debug(msg)


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


DEFAULT_TAP_TIME = const(200)


class AutoMod(Module):
    _active_key: Key | None = None
    _active_mods: set[ModifierKey] | None = None
    _enabled: bool = True
    _task: int | None = None

    def __init__(
        self,
        mods: set[ModifierKey] = None,
        tap_time: int = DEFAULT_TAP_TIME,
        targets: set[Key] = None,
        on_release: bool = False,
    ):
        self.tap_time: int = tap_time or DEFAULT_TAP_TIME
        self.mods = mods
        self._target_key_codes: set[int] = {k.code for k in targets}
        self._on_release: bool = on_release

        if KC.get('AM_TOGG') == KC.NO:
            make_key(names=('AM_TOGG',))

        self._am_togg_code = KC.AM_TOGG.code

    def during_bootup(self, keyboard):
        pass

    def before_matrix_scan(self, keyboard):
        pass

    def after_matrix_scan(self, keyboard):
        pass

    def process_key(
        self, keyboard: KMKKeyboard, current_key: Key, is_pressed: bool, int_coord: int
    ):
        # active_key = self._active_key
        has_task = self._task is not None

        if not self._enabled:
            return current_key

        if is_pressed:
            if self._task:
                cancel_task(self._task)
                self._task = None

            if current_key.code == self._am_togg_code:
                self._enabled = not self._enabled
                return None

            if self._active_key and has_task:
                keyboard.resume_process_key(self, self._active_key, True)

            if self._active_mods:
                maybe_rm_keys(self._active_mods, keyboard)
                self._active_mods = None

            if current_key.code in self._target_key_codes:
                self._task = create_task(
                    lambda: self._on_timeout(keyboard), after_ms=self.tap_time
                )
                self._active_key = current_key
            else:
                keyboard.resume_process_key(self, current_key, True)
            return None

        if current_key is self._active_key:
            if self._task:
                cancel_task(self._task)
                self._task = None

            if has_task:
                keyboard.resume_process_key(self, self._active_key, True)

            elif self._on_release:
                self._active_mods = maybe_add_keys(self.mods, keyboard)
                keyboard.resume_process_key(self, self._active_key, True)

            keyboard.resume_process_key(self, self._active_key, False)
            self._active_key = None
            r_key = None
        else:
            r_key = current_key

        maybe_rm_keys(self._active_mods, keyboard)
        self._active_mods = None

        return r_key

    def before_hid_send(self, keyboard):
        pass

    def after_hid_send(self, keyboard):
        pass

    def on_powersave_enable(self, keyboard):
        pass

    def on_powersave_disable(self, keyboard):
        pass

    def _on_timeout(self, keyboard: KMKKeyboard):
        self._task = None

        if not self._active_key:
            return

        if not self._on_release:
            self._active_mods = maybe_add_keys(self.mods, keyboard)
            # press the modded key now
            keyboard.resume_process_key(self, self._active_key, True)
