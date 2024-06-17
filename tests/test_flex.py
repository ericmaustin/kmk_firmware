import unittest
from tests.mocks import init_circuit_python_modules_mocks

init_circuit_python_modules_mocks()

from kmk.keys import KC
from kmk.modules import flex
from tests.keyboard_test import KeyboardTest


class TestFlex(unittest.TestCase):
    def setUp(self):
        KC.clear()

    def test_flex_short_tap(self):
        flex_mod = flex.Flex()
        inside_tap_time = 2 * KeyboardTest.loop_delay_ms
        tap_time = 3 * KeyboardTest.loop_delay_ms
        outside_tap_time = 5 * KeyboardTest.loop_delay_ms
        timeout = 10 * KeyboardTest.loop_delay_ms

        flex_mod.add_key(
            'TEST',
            flex.Action(
                flex.Mode.RELEASE
                | flex.Mode.INTERRUPT,  # trigger on release or interrupt
                flex.tap(0),
                timeout=tap_time,  # timeout after 100ms
            ),
            flex.Action(
                flex.Mode.RELEASE | flex.Mode.TIMEOUT,  # trigger on release or timeout
                flex.tap(
                    0, mods=(KC.LSHIFT,), wrap_interrupt=True
                ),  # tap with left shift
                stop_on=flex.Mode.INTERRUPT | flex.Mode.RELEASE,  # abort if interrupted
                after=tap_time,  # activate after 100ms
                timeout=timeout,  # timeout after 500ms
                ignore={KC.LSFT, KC.RSFT},  # ignore if shift is pressed
            ),
        )

        keyboard = KeyboardTest(
            [flex_mod],
            [
                [
                    KC.TEST(KC.A, KC.LSFT),
                    KC.B,
                    KC.C,
                ],
                [KC.N1, KC.N2, KC.N3, KC.N4],
            ],
            debug_enabled=True,
        )

        keyboard.test(
            'flex short tap',
            [(0, True), inside_tap_time - 2, (0, False)],
            [{KC.A}, {}],
        )

        keyboard.test(
            'flex long tap',
            [(0, True), outside_tap_time, (0, False)],
            [{KC.LSHIFT, KC.A}, {}],
        )


if __name__ == '__main__':
    unittest.main()
