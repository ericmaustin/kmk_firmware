import unittest

from kmk import flag


class TestFlags(unittest.TestCase):

    def test_flag_subclass(self):
        class TestFlags(bitflag.Flagged):
            FOO = flag.Flag()
            BAR = flag.Flag()
            FOO_OR_BAR = flag.Operation('FOO | BAR')
            FOO_AND_BAR = flag.Operation('FOO & BAR')
            ANY = flag.ANY
            NONE = flag.NO

        f = TestFlags()
        self.assertTrue(f.BAR in f.FOO_OR_BAR)
        self.assertTrue(f.BAR in f.ANY)
        self.assertFalse(f.BAR in f.NONE)
        self.assertFalse(f.BAR in f.FOO_AND_BAR)
        self.assertFalse(f.FOO == f.BAR)

    def test_flag_decorator(self):
        @bitflag.flagged
        class TestFlags:
            FOO = flag.Flag()
            BAR = flag.Flag()
            FOO_OR_BAR = flag.Operation('FOO | BAR')
            FOO_AND_BAR = flag.Operation('FOO & BAR')
            ANY = flag.ANY
            NONE = flag.NONE

        self.assertTrue(TestFlags.BAR in TestFlags.FOO_OR_BAR)
        self.assertTrue(TestFlags.BAR in TestFlags.ANY)
        self.assertFalse(TestFlags.BAR in TestFlags.NONE)
        self.assertFalse(TestFlags.BAR in TestFlags.FOO_AND_BAR)
        self.assertFalse(TestFlags.FOO == TestFlags.BAR)

    def test_named_flags(self):
        TestFlags = flag.named('TestFlags', ('FOO', 'BAR', ('FOO_OR_BAR', 'FOO | BAR')))
        self.assertTrue(TestFlags.FOO in TestFlags.FOO_OR_BAR)
        self.assertTrue(TestFlags.BAR in TestFlags.FOO_OR_BAR)
