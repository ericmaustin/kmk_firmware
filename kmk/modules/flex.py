from __future__ import annotations

try:
    from typing import (
        Tuple,
        Dict,
        List,
        TYPE_CHECKING,
        NamedTuple,
        Callable,
        Mapping,
        Generator,
        Any,
    )
except ImportError:
    TYPE_CHECKING = False
    pass

from micropython import const

from kmk import bitflag as bf
from kmk.keys import Key, ModifierKey, make_argumented_key
from kmk.modules import Module
from kmk.utils import Debug
from kmk.kmk_keyboard import KMKKeyboard

_debug = Debug(__name__)

# default value constants
DEFAULT_TIMEOUT = const(300)
DEFAULT_TAP_TIME = const(100)
DEFAULT_TAP_DELAY = const(10)


def debug(msg: str):
    # if _debug.enabled:
    _debug("[Flex] " + msg)


@bf.flagged
class Mode:
    NONE = bf.NONE
    PRESS = bf.Flag()  # press key
    RELEASE = bf.Flag()  # release key
    TIMEOUT = bf.Flag()
    INTERRUPT = bf.Flag()
    TAP = bf.Operation('PRESS | RELEASE')  # tap key


@bf.flagged
class _KeyStatus:
    NONE = bf.NONE
    PRESSED = bf.Flag()
    RELEASED = bf.Flag()


def noop(*_, **__):
    pass


def press(ikey: int) -> KeyAction:
    def f(key_map: KeyMap, keyboard: KMKKeyboard, *_, **__) -> None:
        for k in key_map[ikey]:
            keyboard.add_key(k)

    return f


def release(ikey: int, reverse: bool = False) -> KeyAction:
    def f(key_map: KeyMap, keyboard: KMKKeyboard, *_, **__) -> None:
        for k in key_map[ikey] if not reverse else reversed(key_map[ikey]):
            keyboard.remove_key(k)

    return f


def add_mods(key: Key, mods: tuple[ModifierKey, ...]) -> Key:
    for mod in mods:
        key = mod(key)
    return key


def tap(
    ikey: int,
    mods: tuple[ModifierKey, ...] = None,
    wrap_interrupt: bool = False,
) -> KeyAction:
    mods = mods or ()

    def f(key_map: KeyMap, keyboard: KMKKeyboard, interrupt: Key = None) -> None:
        rel_keys = []

        for key in key_map[ikey]:
            modded_key = add_mods(key, mods)
            rel_keys.append(modded_key)
            keyboard.add_key(modded_key)

        if wrap_interrupt and interrupt:
            keyboard.tap_key(add_mods(interrupt, mods))

        def cb(keys):
            for _k in reversed(keys):
                keyboard.remove_key(_k)

        keyboard.set_timeout(0, lambda keys=tuple(rel_keys): cb(keys))

    return f


def mod_interrupt(mods: tuple[ModifierKey, ...]) -> KeyAction:
    def f(_, keyboard: KMKKeyboard, interrupt: Key = None) -> None:
        if interrupt:
            for mod in mods:
                keyboard.add_key(mod(interrupt))

    return f


def chain(*args: KeyAction, delay=0, abort_on: bf.Flag = bf.NONE):
    def gen() -> Generator[KeyAction]:
        ops = list(args)
        while ops:
            yield ops.pop(0)

    def wrapped(key_map: KeyMap, keyboard: KMKKeyboard, interrupt: None = None) -> None:
        _sequence_with_delay(gen(), key_map, keyboard, interrupt, delay, abort_on)

    return wrapped


def _sequence_with_delay(
    iterator: Generator[KeyAction],
    key_map: KeyMap,
    keyboard: KMKKeyboard,
    interrupt: Key | None,
    delay: int,
    abort_on: bf.Flag,
    __count__: int = 0,
):
    try:
        op = next(iterator)
    except StopIteration:
        # no more operations
        return

    def f():
        op(key_map, keyboard, interrupt)
        _sequence_with_delay(
            iterator, key_map, keyboard, interrupt, delay, abort_on, __count__ + 1
        )

    if __count__ == 0:
        # first operation, execute immediately
        f()
        return

    # delay execution on subsequent operations
    keyboard.set_timeout(delay, f)


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

    def __init__(
        self,
        *key_map: KeyMap,
    ):
        _key_map = []
        for k in key_map:
            if not isinstance(k, tuple):
                _key_map.append((k,))
            else:
                _key_map.append(k)

        self.key_map = tuple(_key_map)


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
        key_map: KeyMap,
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
    def key_map(self):
        return self.__key_map

    @property
    def actions_cnt(self):
        return len(self.actions)

    def action_tasks(self, i: int) -> list[int]:
        return self.__tasks[i]

    def add_task(self, action_idx, task):
        self.__tasks.get(action_idx, []).append(task)


class Flex(Module):
    __slots__ = ('__key_states',)

    def __init__(self):
        self.__key_states: dict[Key, _KeyState] = {}

    def add_key(self, name: tuple[str, ...] | str, *actions: Action):
        name = name if isinstance(name, tuple) else (name,)
        debug(f'adding key {name} with actions {actions}')
        make_argumented_key(
            validator=_KeyMeta,
            names=name,
            on_press=lambda key, keyboard, *arg, **kwargs: self.on_press(
                key, actions, keyboard
            ),
            on_release=self.on_release,
        )

    def process_key(
        self, keyboard: KMKKeyboard, current_key: Key, is_pressed: bool, int_coord: int
    ):
        if current_key in self.__key_states.keys() or not is_pressed:
            # ignore key if already in state or key is released
            debug(f'ignoring key {current_key}')
            return current_key

        captured = False

        for key, state in self.__key_states.items():
            if not state.status & _KeyStatus.PRESSED:
                continue

            for i in state.actions_active:
                action = state.actions[i]
                if (
                    action.interrupt_requires
                    and action.interrupt_requires - keyboard.keys_pressed
                ):
                    continue

                if (
                    action.interrupt_ignore
                    and action.interrupt_ignore & keyboard.keys_pressed
                ):
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
        if key in self.__key_states.keys():
            debug(f'key {key} already in state, clearing')
            self.__remove_key_from_state(key, keyboard)

        debug(f'key {key} pressed')
        state = _KeyState(key_map=key.meta.key_map, status=_KeyStatus.PRESSED)

        self.__key_states[key] = state

        for i, act in enumerate(actions):
            state.actions[i] = act
            if act.after > -1:
                debug(f'key {key} has delay for action {i}')
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
        debug(f"delay expired for action {action_idx} on key {key}")
        if key not in self.__key_states.keys():
            debug(f'on_delay_expires: key {key} not in state')
            return

        state = self.__key_states[key]

        try:
            state.actions_delayed.remove(action_idx)
        except KeyError:
            # action already removed
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
            debug(f'do_action: key {key} not in state')
            return

        state = self.__key_states[key]

        try:
            action = state.actions[action_idx]
        except KeyError:
            return

        activated = False

        if key_mode in action.on:
            if (action.ignore and action.ignore & keyboard.keys_pressed) or (
                action.requires and action.requires - keyboard.keys_pressed
            ):
                debug(f'do_action: ignoring action {action_idx} on key {key}')
            else:
                debug(
                    f'do_action: key_mode={key_mode} executing action {action_idx} on key {key}'
                )
                action.do(state.key_map, keyboard, interrupt)
                self.__remove_action(action_idx, key, keyboard)
                activated = True

        if not activated and key_mode in action.stop_on:
            self.__remove_action(action_idx, key, keyboard)

    def on_release(self, key: Key, keyboard: KMKKeyboard, *args, **kwargs):
        if key not in self.__key_states.keys():
            return

        state = self.__key_states[key]
        state.status = _KeyStatus.RELEASED

        for i in tuple(state.actions_active):
            self.do_action(i, Mode.RELEASE, key, keyboard)

    def __remove_action(self, action_idx: int, key: Key, keyboard: KMKKeyboard):
        try:
            state = self.__key_states[key]
        except KeyError:
            # key already removed
            return

        try:
            tasks = state.action_tasks(action_idx)
            for t in tasks:
                keyboard.cancel_timeout(t)
        except KeyError:
            # action already removed
            debug(f'action {action_idx} already removed from key {key}')

        # remove action from state
        state.actions_active.discard(action_idx)
        state.actions_delayed.discard(action_idx)
        del state.actions[action_idx]

        if not state.actions_cnt:
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


if TYPE_CHECKING:
    KeyMap = tuple[tuple[Key, ...]]
    KeyAction = Callable[[KeyMap, KMKKeyboard, Key | None], None]
