from kb import KMKKeyboard

from kmk.extensions.rgb import RGB
from kmk.keys import KC
from kmk.modules.layers import Layers

from kmk.modules import flex
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
flex_mod = flex.Flex()
keyboard.modules = [layers, split, flex_mod]
# keyboard.modules = [layers, split]
#
# Cleaner key names
_______ = KC.TRNS
XXXXXXX = KC.NO


flex_mod.add_key(
    'HR',
    flex.Action(
        flex.Mode.RELEASE | flex.Mode.INTERRUPT,  # trigger on release or interrupt
        flex.tap_action(0),
        timeout=100,  # timeout after 100ms
    ),
    flex.Action(
        flex.Mode.RELEASE | flex.Mode.TIMEOUT,  # trigger on release or timeout
        flex.tap_action(0, mods=(KC.LSFT,)),  # tap with left shift
        stop_on=flex.Mode.INTERRUPT | flex.Mode.RELEASE,  # abort if interrupted
        after=100,  # activate after 100ms
        timeout=200,  # timeout after 500ms
        ignore={KC.LSFT, KC.RSFT},  # ignore if shift is pressed
    ),
    flex.Action(
        flex.Mode.INTERRUPT,
        flex.tap_action(1, wrap_interrupt=True),
        after=100,
        timeout=1000,
    ),
)


# fmt:off
keyboard.keymap = [
    [  #QWERTY
        KC.TAB,    KC.Q,    KC.W,    KC.E,    KC.R,    KC.T,                         KC.Y,    KC.U,    KC.I,    KC.O,   KC.P,  KC.BSPC,
        KC.LCTL,   KC.HR((KC.A,), (KC.LSFT,)),    KC.S,    KC.D,    KC.F,    KC.G,                         KC.H,    KC.J,    KC.K,    KC.L, KC.SCLN, KC.QUOT,
        KC.LSFT,   KC.Z,    KC.X,    KC.C,    KC.V,    KC.B,                         KC.N,    KC.M, KC.COMM,  KC.DOT, KC.SLSH, KC.RSFT,
                                            KC.LGUI,   KC.BSPC,  KC.TAB,     KC.ENT,   KC.SPC,  KC.RALT,
    ]
]
# fmt:on

if __name__ == '__main__':
    keyboard.go()
