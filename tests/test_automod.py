import unittest

try:
    import micropython
except ImportError:
    from tests.mocks import init_circuit_python_modules_mocks

    init_circuit_python_modules_mocks()

from kmk.keys import KC, ModifierKey
from kmk.modules.automod import AutoMod
from tests.keyboard_test import KeyboardTest
from kmk.utils import Debug

Debug.enabled = True


class TestAutoMod(unittest.TestCase):
    def setUp(self):
        self.tap_time = 3 * KeyboardTest.loop_delay_ms
        self.t_after = 4 * KeyboardTest.loop_delay_ms
        auto_mod = AutoMod(
            tap_time=self.tap_time,
            mods={KC.LSHIFT},
            targets={KC.A},
        )

        self.kb = KeyboardTest(
            [auto_mod],
            [
                [
                    KC.A,
                    KC.N1,
                    KC.HASH,
                    KC.NO,
                ]
            ],
            debug_enabled=True,
        )

    def test_auto_mod(self):
        self.kb.test(
            'test_tap_alpha',
            [(0, True), (0, False)],
            [{KC.A}, {}],
        )

        self.kb.test(
            'test_hold_alpha',
            [(0, True), self.t_after, (0, False), self.t_after],
            [{KC.A, KC.LSHIFT}, {}],
        )

        self.kb.test(
            'test_hold_num',
            [(1, True), self.t_after, (1, False)],
            [{KC.N1}, {}],
        )

        self.kb.test(
            'test nested hold_alpha',
            [(0, True), (1, True), self.t_after, (1, False), (0, False)],
            [{KC.A}, {KC.A, KC.N1}, {KC.A}, {}],
        )

        self.kb.test(
            'test_hold_alpha_tap_num_after',
            [(0, True), self.t_after, (1, True), (1, False), (0, False)],
            [{KC.A, KC.LSHIFT}, {KC.A, KC.N1}, {KC.A}, {}],
        )

        self.kb.test(
            '',
            [(1, True), (0, True), self.t_after, (0, False), (1, False)],
            [{KC.N1}, {KC.N1, KC.A, KC.LSHIFT}, {KC.N1}, {}],
        )

        self.kb.test(
            '',
            [(1, True), (0, True), (1, False), self.t_after, (0, False)],
            [{KC.N1}, {}, {KC.A, KC.LSHIFT}, {}],
        )

        self.kb.test(
            '',
            [(2, True), (0, True), self.t_after, (2, False), (0, False)],
            [{KC.LSHIFT, KC.HASH}, {KC.LSHIFT, KC.HASH, KC.A}, {KC.A}, {}],
        )

        self.kb.test(
            '',
            [(3, True), self.t_after, (3, False)],
            [],
        )


if __name__ == '__main__':
    unittest.main()
