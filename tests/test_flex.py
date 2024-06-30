import unittest

try:
    import micropython
except ImportError:
    from tests.mocks import init_circuit_python_modules_mocks

    init_circuit_python_modules_mocks()

from kmk.keys import KC
from kmk.modules.flex import Flex, FlexMeta, flex_key
from tests.keyboard_test import KeyboardTest


class TestFlex(unittest.TestCase):
    def setUp(self):
        KC.clear()
        self.short_tap_time = 2 * KeyboardTest.loop_delay_ms
        self.tap_timeout_time = 3 * KeyboardTest.loop_delay_ms
        self.outside_tap_time = 5 * KeyboardTest.loop_delay_ms
        self.hold_delay_time = 2 * KeyboardTest.loop_delay_ms
        self.hold_timeout = 10 * KeyboardTest.loop_delay_ms
        self.long_hold_time = 20 * KeyboardTest.loop_delay_ms
        self.after = 10 * KeyboardTest.loop_delay_ms

    def test_flex_with_overrides(self):
        mod = Flex(
            {
                KC.A: FlexMeta(
                    tap=KC.A,
                    tap_timeout=self.tap_timeout_time,
                    hold=[
                        KC.B,
                    ],
                    hold_timeout=self.hold_timeout,
                    hold_interrupt={KC.LSFT},
                )
            }
        )

        keyboard = KeyboardTest(
            [mod],
            [
                [
                    KC.A,
                    KC.B,
                    KC.C,
                ],
            ],
            debug_enabled=True,
        )

        keyboard.test(
            'short tap KC.A -> KC.A',
            [(0, True), self.short_tap_time, (0, False), self.after],
            [{KC.A}, {}],
        )

        # keyboard.keyboard.keys_pressed.clear()

        keyboard.test(
            'long tap KC.A -> KC.B',
            [(0, True), self.long_hold_time, (0, False), self.after],
            [{KC.B}, {}],
        )

        # keyboard.keyboard.keys_pressed.clear()

        keyboard.test(
            'hold KC.A then tap KC.B to add KC.A\'s mod',
            [
                (0, True),
                self.outside_tap_time,
                (1, True),
                (1, False),
                (0, False),
                self.after,
            ],
            [{KC.LSFT, KC.B}, {}],
        )

    def test_flex_key_factory(self):
        mod = Flex()

        AS = flex_key(
            hold_mod={KC.LSFT},
            tap_timeout=self.tap_timeout_time,
            hold_timeout=self.hold_timeout,
        )

        keyboard = KeyboardTest(
            [mod],
            [
                [
                    AS(KC.A),
                    KC.B,
                    KC.C,
                ],
            ],
            debug_enabled=True,
        )

        keyboard.test(
            'short tap AS -> KC.A',
            [(0, True), self.short_tap_time, (0, False), self.after],
            [{KC.A}, {}],
        )

        keyboard.test(
            'long tap AS -> LSFT + A',
            [(0, True), self.long_hold_time, (0, False), self.after],
            [{KC.LSFT, KC.A}, {}],
        )

    def test_flex_key(self):
        mod = Flex()

        keyboard = KeyboardTest(
            [mod],
            [
                [
                    KC.FX(
                        KC.A,
                        KC.B,
                        KC.LSFT,
                        tap_timeout=self.tap_timeout_time,
                        hold_timeout=self.hold_timeout,
                    ),
                    KC.B,
                    KC.C,
                ],
            ],
            debug_enabled=True,
        )

        keyboard.test(
            'short tap FLEX -> KC.A',
            [(0, True), self.short_tap_time, (0, False), self.after],
            [{KC.A}, {}],
        )

        # keyboard.keyboard.keys_pressed.clear()

        keyboard.test(
            'long tap FLEX -> KC.B',
            [(0, True), self.long_hold_time, (0, False), self.after],
            [{KC.B}, {}],
        )

        # keyboard.keyboard.keys_pressed.clear()

        keyboard.test(
            'hold FLEX then tap KC.B to add FLEX\'s mod',
            [
                (0, True),
                self.outside_tap_time,
                (1, True),
                (1, False),
                (0, False),
                self.after,
            ],
            [{KC.LSFT, KC.B}, {}],
        )


if __name__ == '__main__':
    unittest.main()
