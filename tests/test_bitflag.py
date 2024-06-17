import unittest

from kmk import bitflag


class TestFlags(unittest.TestCase):

    def test_flag_subclass(self):
        class TestFlags(bitflag.Flagged):
            FOO = bitflag.Flag()
            BAR = bitflag.Flag()
            FOO_OR_BAR = bitflag.Operation('FOO | BAR')
            FOO_AND_BAR = bitflag.Operation('FOO & BAR')
            ANY = bitflag.ANY
            NONE = bitflag.NO

        f = TestFlags()
        self.assertTrue(f.BAR in f.FOO_OR_BAR)
        self.assertTrue(f.BAR in f.ANY)
        self.assertFalse(f.BAR in f.NONE)
        self.assertFalse(f.BAR in f.FOO_AND_BAR)
        self.assertFalse(f.FOO == f.BAR)

    def test_flag_decorator(self):
        @bitflag.flagged
        class TestFlags:
            FOO = bitflag.Flag()
            BAR = bitflag.Flag()
            FOO_OR_BAR = bitflag.Operation('FOO | BAR')
            FOO_AND_BAR = bitflag.Operation('FOO & BAR')
            ANY = bitflag.ANY
            NONE = bitflag.NONE

        self.assertTrue(TestFlags.BAR in TestFlags.FOO_OR_BAR)
        self.assertTrue(TestFlags.BAR in TestFlags.ANY)
        self.assertFalse(TestFlags.BAR in TestFlags.NONE)
        self.assertFalse(TestFlags.BAR in TestFlags.FOO_AND_BAR)
        self.assertFalse(TestFlags.FOO == TestFlags.BAR)

    def test_named_flags(self):
        TestFlags = bitflag.named_flags(
            'TestFlags', ('FOO', 'BAR', ('FOO_OR_BAR', 'FOO | BAR'))
        )
        self.assertTrue(TestFlags.FOO in TestFlags.FOO_OR_BAR)
        self.assertTrue(TestFlags.BAR in TestFlags.FOO_OR_BAR)
