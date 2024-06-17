import unittest

try:
    import micropython
except ImportError:
    from tests.mocks import init_circuit_python_modules_mocks

    init_circuit_python_modules_mocks()

from kmk.keys import KC
from kmk.modules.key_swap import KeySwap
from tests.keyboard_test import KeyboardTest


class TestKeySwap(unittest.TestCase):
    def setUp(self):
        KC.clear()
        self.swap = KeySwap(
            {KC.N1: KC.N2, KC.N2: KC.N1, KC.LSFT(KC.N1): KC.LSFT(KC.N2)}
        )
        self.tap_time = 3 * KeyboardTest.loop_delay_ms

    def test_swap(self):
        keyboard = KeyboardTest(
            [self.swap],
            [
                [
                    KC.N1,
                    KC.N2,
                    KC.LSFT,
                ],
            ],
            debug_enabled=True,
        )

        keyboard.test(
            'flex N1 -> N2',
            [(0, True), self.tap_time, (0, False)],
            [{KC.N2}, {}],
        )

        keyboard.test(
            'flex LSFT(N1) -> LSFT(N2)',
            [(2, True), (0, True), self.tap_time, (0, False), (2, False)],
            [{KC.LSFT, KC.N2}, {KC.N2}, {}],
        )


if __name__ == '__main__':
    unittest.main()
