from kb import KMKKeyboard

from kmk.extensions.rgb import RGB
from kmk.keys import KC
from kmk.modules.layers import Layers

from kmk.modules.key_swap import KeySwap
from kmk.modules.flex import flex_key, Flex
from kmk.modules.split import Split, SplitSide, SplitType

keyboard = KMKKeyboard()
#
# TODO Comment one of these on each side
split_side = SplitSide.LEFT
# split_side = SplitSide.RIGHT
split = Split(
    split_flip=True,
    split_type=SplitType.UART,
    split_side=split_side,
    uart_flip=True,
    data_pin=keyboard.data_pin,
    data_pin2=keyboard.data_pin2,
    use_pio=True,
    debug_enabled=True,
)
#
layers = Layers()
flex = Flex()
key_swap = KeySwap(
    {
        KC.N1: KC.N2,
        KC.N2: KC.N1,
        KC.LSFT(KC.N1): KC.LSFT(KC.N2),
    }
)
keyboard.modules = [layers, split, flex, key_swap]
# keyboard.modules = [layers, split]
#
# Cleaner key names
_______ = KC.TRNS
XXXXXXX = KC.NO

AS = flex_key(
    hold_mod=KC.LSFT,
    hold_timeout=200,
)

AS_SFT = flex_key(
    hold_mod=KC.LSFT,
    tap_time=100,
    hold_timeout=200,
)


# fmt:off
keyboard.keymap = [
    [  #QWERTY
        KC.TAB,    AS(KC.Q),    KC.W,    KC.E,    KC.R,    KC.T,                         KC.Y,    KC.U,    KC.I,    KC.O,   KC.P,  KC.BSPC,
        KC.LCTL,   KC.HR((KC.A,), (KC.LSFT,)),    KC.S,    KC.D,    KC.F,    KC.G,                         KC.H,    KC.J,    KC.K,    KC.L, KC.SCLN, KC.QUOT,
        KC.LSFT,   KC.Z,    KC.X,    KC.C,    KC.V,    KC.B,                         KC.N,    KC.M, KC.COMM,  KC.DOT, KC.SLSH, KC.RSFT,
                                            KC.LGUI,   KC.BSPC,  KC.TAB,     KC.ENT,   KC.SPC,  KC.RALT,
    ]
]
# fmt:on

if __name__ == '__main__':
    keyboard.go()
