from kmk.keys import Key, KC, ModifierKey, make_key
from kmk.modules import Module


class KeySwap(Module):
    # default cg swap is disabled, can be eanbled too if needed
    def __init__(self, swaps: dict[Key, Key | tuple[Key, ...]]):
        self.__swaps: dict[Key, Key] = swaps
        self.__swap_targets = tuple(swaps.keys())

    def process_key(self, keyboard, key, is_pressed, int_coord):
        if key in self.__swap_targets:
            return self.__swaps[key]
        return key

    def during_bootup(self, keyboard):
        return

    def before_matrix_scan(self, keyboard):
        return

    def before_hid_send(self, keyboard):
        return

    def after_hid_send(self, keyboard):
        return

    def on_powersave_enable(self, keyboard):
        return

    def on_powersave_disable(self, keyboard):
        return

    def after_matrix_scan(self, keyboard):
        return
