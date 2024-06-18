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

from kmk import bitflag as bf
from kmk.keys import Key, KC, ModifierKey, make_argumented_key
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

# if _debug.enabled:
#
#     def debug(msg: str):
#         _debug("[Flex] " + msg)
#
# else:
#
#     def debug(_: str):
#         pass


def debug(msg: str):
    _debug("[Flex] " + msg)


@bf.flagged
class Mode:
    NONE = bf.NONE
    PRESS = bf.Flag()  # press key
    RELEASE = bf.Flag()  # release key
    TIMEOUT = bf.Flag()
    INTERRUPT = bf.Flag()
    TAP = bf.Operation('PRESS | RELEASE')  # tap key

    @staticmethod
    def flag_to_str(flag: bf.Flag) -> str:
        return {
            Mode.PRESS: 'PRESS',
            Mode.RELEASE: 'RELEASE',
            Mode.TIMEOUT: 'TIMEOUT',
            Mode.INTERRUPT: 'INTERRUPT',
            Mode.TAP: 'TAP',
        }[flag]


@bf.flagged
class _KeyStatus:
    NONE = bf.NONE
    PRESSED = bf.Flag()
    RELEASED = bf.Flag()


def noop(*_, **__):
    pass


def add_mods(key: Key, mods: set[ModifierKey]) -> Key:
    for mod in mods:
        key = mod(key)
    return key


def press_action(ikey: int) -> KeyAction:
    return lambda key_map, keyboard, *_, **__: keyboard.add_key(key_map[ikey])


def release_action(ikey: int) -> KeyAction:
    return lambda key_map, keyboard, *_, **__: keyboard.remove_key(key_map[ikey])


def tap_action(
    ikey: int,
    mods: set[ModifierKey] | int = None,
    wrap_interrupt: bool = False,
) -> KeyAction:
    mods = mods or ()

    def f(
        key_map: tuple[Key, ...], keyboard: KMKKeyboard, interrupt: Key = None
    ) -> None:
        rel_keys = []

        if isinstance(mods, int):
            mod_keys = key_map[mods]
        else:
            mod_keys = mods

        debug(f"tap_action mods: {mod_keys}")

        keyboard.add_key(add_mods(key_map[ikey], mods))

        if wrap_interrupt and interrupt:
            if isinstance(interrupt.meta, _KeyMeta):
                keyboard.tap_key(add_mods(interrupt.meta.key_map[0]))
            else:
                keyboard.tap_key(add_mods(interrupt, mod_keys))

        # keyboard._send_hid()

        def cb(keys):
            for _k in reversed(keys):
                keyboard.remove_key(_k)
            # keyboard._send_hid()

        keyboard.set_timeout(0, lambda keys=tuple(rel_keys): cb(keys))

    return lambda key_map, keyboard, interrupt: f(key_map, keyboard, interrupt)


def mod_interrupt_action(mods: set[ModifierKey]) -> KeyAction:

    def f(_, keyboard: KMKKeyboard, interrupt: Key = None) -> None:
        if isinstance(interrupt.meta, _KeyMeta):
            debug(
                f"mod_interrupt_action: interrupting with {interrupt.meta.key_map[0]} mods: {mods}"
            )
            modded_key = add_mods(interrupt.meta.key_map[0], mods)
            debug(f"mod_interrupt_action: modded_key: {modded_key}")
            keyboard.tap_key(modded_key)
            return

        keyboard.tap_key(add_mods(interrupt, mods))

    return f


class Action:
    __slots__ = (
        'on',
        'do',
        'after',
        'timeout',
        'stop_on',
        'ignore',
        'requires',
        'interrupt_requires',
        'interrupt_ignore',
        'replace_interrupt',
        'id',
    )

    def __init__(
        self,
        on: bf.Flag,
        do: KeyAction,
        after: int = -1,
        timeout: int = -1,
        stop_on: bf.Flag = Mode.RELEASE,
        ignore: set[Key] = None,
        requires: set[Key] = None,
        interrupt_ignore: set[Key] = None,
        interrupt_requires: set[Key] = None,
    ):
        self.on = on
        self.do = do
        self.after = after
        self.timeout = timeout
        self.stop_on = stop_on
        self.requires = requires or set()
        self.ignore = ignore or set()
        self.interrupt_requires = interrupt_requires or set()
        self.interrupt_ignore = interrupt_ignore or set()


class _KeyMeta:
    __slots__ = ('key_map',)

    def __init__(self, *key_map: tuple[Key, ...]):
        self.key_map = key_map


class _KeyState:
    __slots__ = (
        'status',
        'interrupt',
        'actions',
        '__key_map',
        '__tasks',
        'actions_active',
        'actions_running',
        'actions_delayed',
    )

    def __init__(
        self,
        key_map: tuple[Key, ...],
        status: _KeyStatus.NONE,
    ):
        self.status = status
        self.interrupt: Key = None
        self.__key_map = key_map
        self.actions_active: set[int] = set()
        self.actions_delayed: set[int] = set()
        self.actions: dict[int, Action] = {}
        self.__tasks: dict[int, list[int]] = {}

    @property
    def all_tasks(self):
        return (t for ts in self.__tasks.values() for t in ts)

    @property
    def key_map(self) -> tuple[Key, ...]:
        return self.__key_map

    @property
    def actions_cnt(self):
        return len(self.actions)

    def action_tasks(self, i: int) -> list[int]:
        return self.__tasks[i]

    def add_task(self, action_idx, task):
        self.__tasks.get(action_idx, []).append(task)


class FlexKey:
    __slots__ = (
        'name',
        'actions',
    )

    def __init__(self, name: tuple[str, ...] | str, *actions: Action):
        self.name: tuple[str, ...] = name if isinstance(name, tuple) else (name,)
        self.actions: tuple[Action, ...] = actions

    def __repr__(self):
        return f'<FlexKey {self.name}>'


class Flex(Module):
    __key_states: dict[Key, _KeyState] = {}

    def __init__(self, *keys: FlexKey):
        self.add_key(*keys)

    def add_key(self, *args: FlexKey):
        for k in args:
            debug(f'adding {k}')
            make_argumented_key(
                validator=_KeyMeta,
                names=k.name,
                on_press=lambda key, keyboard, *arg, **kwargs: self.on_press(
                    key, k.actions, keyboard
                ),
                on_release=self.on_release,
            )

    def process_key(
        self, keyboard: KMKKeyboard, current_key: Key, is_pressed: bool, int_coord: int
    ):
        if not is_pressed:
            # ignore key if already in state or key is released
            return current_key

        captured = False

        for key in tuple(self.__key_states.keys()):
            if key == current_key:
                # ignore THIS key
                continue

            state = self.__key_states[key]

            for i in tuple(state.actions_active):
                action = state.actions[i]
                if (
                    action.interrupt_requires
                    and action.interrupt_requires - keyboard.keys_pressed
                ):
                    debug(f'key {current_key} does not meet interrupt requirements')
                    continue

                if (
                    action.interrupt_ignore
                    and action.interrupt_ignore & keyboard.keys_pressed
                ):
                    debug(f'key {current_key} is ignored by interrupt_ignore')
                    continue

                self.do_action(i, Mode.INTERRUPT, key, keyboard, current_key)
                # check if action was executed
                if i not in state.actions_active:
                    captured = True

        return current_key if not captured else None

    def on_press(
        self,
        key: Key,
        actions: tuple[Action, ...],
        keyboard: KMKKeyboard,
    ):
        if key in tuple(self.__key_states.keys()):
            debug(f'key {key} already in state, clearing')
            self.__remove_key_from_state(key, keyboard)

        debug(f'key {key} pressed')
        state = _KeyState(key_map=key.meta.key_map, status=_KeyStatus.PRESSED)

        self.__key_states[key] = state

        for i, act in enumerate(actions):
            state.actions[i] = act
            if act.after > -1:
                state.actions_delayed.add(i)
                state.add_task(
                    i,
                    keyboard.set_timeout(
                        act.after,
                        lambda action_idx=i: self.on_delay_expires(
                            action_idx, key, keyboard
                        ),
                    ),
                )
                continue

            state.actions_active.add(i)
            self.do_action(i, Mode.PRESS, key, keyboard)
            if act.timeout > -1:
                _idx = i
                state.add_task(
                    _idx,
                    keyboard.set_timeout(
                        act.timeout,
                        lambda action_idx=i: self.do_action(
                            action_idx, Mode.TIMEOUT, key, keyboard
                        ),
                    ),
                )

    def on_delay_expires(self, action_idx: int, key: Key, keyboard: KMKKeyboard):
        try:
            state = self.__key_states[key]
        except KeyError:
            debug(f'on_delay_expires: key {key} not in state')
            return

        try:
            state.actions_delayed.remove(action_idx)
        except KeyError:
            # action already removed
            debug(
                f'on_delay_expires: action {action_idx} already removed from key {key}'
            )
            return

        state.actions_active.add(action_idx)

        # attempt PRESS action
        self.do_action(action_idx, Mode.PRESS, key, keyboard)

        action = state.actions[action_idx]
        if action.timeout > -1:
            state.add_task(
                action_idx,
                keyboard.set_timeout(
                    action.timeout,
                    lambda _action_idx=action_idx: self.do_action(
                        _action_idx, Mode.TIMEOUT, key, keyboard
                    ),
                ),
            )

    def do_action(
        self,
        action_idx: int,
        key_mode: bf.Flag,
        key: Key,
        keyboard: KMKKeyboard,
        interrupt: Key = None,
    ):
        if key not in self.__key_states.keys():
            debug(
                f'do_action: key_mode={Mode.flag_to_str(key_mode)} key {key} not in state'
            )
            return

        state = self.__key_states[key]

        try:
            action = state.actions[action_idx]
        except KeyError:
            return

        completed = False

        if key_mode in action.on:
            if (action.ignore and action.ignore & keyboard.keys_pressed) or (
                action.requires and action.requires - keyboard.keys_pressed
            ):
                debug(f'do_action: ignoring action {action_idx} on key {key}')
            else:
                debug(
                    f'do_action: key_mode={Mode.flag_to_str(key_mode)} executing action {action_idx} on key {key}'
                )
                action.do(state.key_map, keyboard, interrupt)
                completed = True

        elif key_mode in action.stop_on:
            completed = True

        if completed:
            # remove action from state
            state.actions_active.discard(action_idx)
            state.actions_delayed.discard(action_idx)

            del state.actions[action_idx]
            if not state.actions_cnt:
                self.__remove_key_from_state(key, keyboard)

    def on_release(self, key: Key, keyboard: KMKKeyboard, *args, **kwargs):
        debug(f'key {key} released')
        if key not in self.__key_states.keys():
            return

        state = self.__key_states[key]
        state.status = _KeyStatus.RELEASED
        for i in tuple(state.actions_active):
            self.do_action(i, Mode.RELEASE, key, keyboard)
        # always a remove
        self.__remove_key_from_state(key, keyboard)

    def __remove_key_from_state(self, key: Key, keyboard: KMKKeyboard):
        try:
            state = self.__key_states[key]
        except KeyError:
            # key already removed
            return

        for task in state.all_tasks:
            keyboard.cancel_timeout(task)
        del self.__key_states[key]

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


def one_shot(
    key_idx: int,
    timeout: int = DEFAULT_TIMEOUT,
    ignore: set[Key] = None,
    requires: set[Key] = None,
) -> Action:
    return Action(
        Mode.INTERRUPT,
        tap_action(key_idx, wrap_interrupt=True),
        timeout=timeout,
        stop_on=Mode.INTERRUPT | Mode.TIMEOUT,
        interrupt_ignore=ignore,
        interrupt_requires=requires,
    )


def tap_on_release(
    key_idx: int,
    tap_time: int = DEFAULT_TAP_TIME,
    delay: int = -1,
    mods: tuple[ModifierKey, ...] = None,
) -> Action:
    mods = mods or ()
    return Action(
        Mode.RELEASE | Mode.INTERRUPT,
        tap_action(key_idx, mods=mods),
        after=delay,
        timeout=tap_time,
        stop_on=Mode.INTERRUPT | Mode.RELEASE | Mode.TIMEOUT,
        ignore=set(mods),
    )


def hold_auto_mod(
    key_idx: int,
    mods: set[ModifierKey],
    timeout: int = DEFAULT_TIMEOUT,
    delay: int = 0,
) -> Action:
    mods = mods or ()
    # default ignore mods
    return Action(
        Mode.TIMEOUT | Mode.RELEASE,
        tap_action(key_idx, mods=mods, wrap_interrupt=False),
        after=delay,
        stop_on=Mode.INTERRUPT | Mode.RELEASE,
        ignore=set(mods),
        timeout=timeout,
    )


def auto_shift(key_idx: int, timeout: int = DEFAULT_TIMEOUT, delay: int = 0) -> Action:
    return hold_auto_mod(key_idx, {KC.LSHIFT}, timeout=timeout, delay=delay)


def mod_interrupt(
    mods: set[ModifierKey],
    timeout: int = -1,
    delay: int = 0,
    ignore: set[Key] = None,
) -> Action:
    return Action(
        Mode.INTERRUPT,
        mod_interrupt_action(mods),
        after=delay,
        timeout=timeout,
        stop_on=Mode.RELEASE,
        ignore=(ignore or set()) | set(mods),
    )
