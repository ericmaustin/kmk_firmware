from kb import KMKKeyboard

from kmk.extensions.peg_oled_display import (
    Oled,
    OledData,
    OledDisplayMode,
    OledReactionType,
)
from kmk.extensions.peg_rgb_matrix import Rgb_matrix
from kmk.keys import KC
from kmk.modules.layers import Layers
from kmk.modules.split import Split

keyboard = KMKKeyboard()
keyboard.debug_enable = True
keyboard.modules.append(Layers())
# oled
oled = Oled(
    OledData(
        corner_one={
            0: OledReactionType.STATIC,
            1: ['1 2 3 4 5 6', '', '', '', '', '', '', ''],
        },
        corner_two={
            0: OledReactionType.STATIC,
            1: [' 7 8 Layer', '', '', '', '', '', '', ' 7 8 Layer'],
        },
        corner_three={
            0: OledReactionType.LAYER,
            1: ['^', '  ^', '    ^', '      ^', '        ^', '          ^', '', ''],
        },
        corner_four={
            0: OledReactionType.LAYER,
            1: ['', '', '', '', '', '', ' ^', '   ^'],
        },
    ),
    toDisplay=OledDisplayMode.TXT,
    flip=True,
)
keyboard.extensions.append(oled)
# ledmap
rgb = Rgb_matrix(
    ledDisplay=[
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
        [255, 255, 255],
    ],
    split=True,
    rightSide=False,
    disable_auto_write=True,
)
# ledmap
keyboard.extensions.append(rgb)
split = Split(use_pio=True)
keyboard.modules.append(split)
_______ = KC.TRNS
XXXXXXX = KC.NO

LOWER = KC.MO(2)
RAISE = KC.MO(1)

# fmt:off
keyboard.keymap = [
    [  #QWERTY
        KC.Q,    KC.W,    KC.E,    KC.R,    KC.T,                           KC.Y,    KC.U,    KC.I,    KC.O,    KC.P,
        KC.A,    KC.S,    KC.D,    KC.F,    KC.G,                           KC.H,    KC.J,    KC.K,    KC.L,    KC.SCLN,
        KC.Z,    KC.X,    KC.C,    KC.V,    KC.B,                           KC.N,    KC.M,    KC.COMM, KC.DOT,  KC.SLSH,
                                   KC.LCTL, LOWER,   KC.SPC,       KC.BSPC, RAISE,   KC.ENT,
    ],
    [  #RAISE
        KC.N1,   KC.N2,   KC.N3,   KC.N4,   KC.N5,                          KC.N6,   KC.N7,   KC.N8,   KC.N9,   KC.N0,
        KC.TAB,  KC.LEFT, KC.DOWN, KC.UP,   KC.RGHT,                        XXXXXXX, KC.MINS, KC.EQL,  KC.LBRC, KC.RBRC,
        KC.LCTL, KC.GRV,  KC.LGUI, KC.LALT, XXXXXXX,                        XXXXXXX, XXXXXXX, XXXXXXX, KC.BSLS, KC.QUOT,
                                   XXXXXXX, XXXXXXX, XXXXXXX,      XXXXXXX, XXXXXXX, XXXXXXX,
    ],
    [  #LOWER
        KC.EXLM, KC.AT,   KC.HASH, KC.DLR,  KC.PERC,                        KC.CIRC, KC.AMPR, KC.ASTR, KC.LPRN, KC.RPRN,
        KC.ESC,  XXXXXXX, XXXXXXX, XXXXXXX, XXXXXXX,                        XXXXXXX, KC.UNDS, KC.PLUS, KC.LCBR, KC.RCBR,
        KC.CAPS, KC.TILD, XXXXXXX, XXXXXXX, XXXXXXX,                        XXXXXXX, XXXXXXX, XXXXXXX, KC.PIPE, KC.DQT,
                                   XXXXXXX, XXXXXXX, XXXXXXX,       KC.ENT, XXXXXXX, KC.DEL,
    ],
]
# fmt:on

if __name__ == '__main__':
    keyboard.go()
