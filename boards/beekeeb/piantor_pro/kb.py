import board

from kmk.kmk_keyboard import KMKKeyboard as _KMKKeyboard
from kmk.scanners import DiodeOrientation


class KMKKeyboard(_KMKKeyboard):
    col_pins = (
        board.GP11,
        board.GP12,
        board.GP13,
        board.GP14,
        board.GP15,
        board.GP16,
    )
    row_pins = (
        board.GP7,
        board.GP8,
        board.GP9,
        board.GP10,
    )
    data_pin2 = board.GP0
    data_pin = board.GP1
    diode_orientation = DiodeOrientation.COL2ROW

    # fmt: off
    coord_mapping = [
         0,  1,  2,  3,  4,  5,  29, 28, 27, 26, 25, 24,
         6,  7,  8,  9, 10, 11,  35, 34, 33, 32, 31, 30,
        12, 13, 14, 15, 16, 17,  41, 40, 39, 38, 37, 36,
                    21, 22, 23,  47, 46, 45,
    ]
    # fmt:on
