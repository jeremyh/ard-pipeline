import unittest

from gaip import Spacecraft


class SpacecraftTest(unittest.TestCase):
    def test_type(self):
        sat = Spacecraft.LS5
        assert isinstance(sat, Spacecraft)

    def test_name(self):
        # the 'name' property derives from being an enumeration member
        sat = Spacecraft.LS5
        assert isinstance(sat.name, str)
        assert sat.name == "LS5"
        assert str(sat) == "Spacecraft.LS5"
        assert repr(sat) == "Spacecraft.LS5 (Sensors: ['TM', 'MSS'])"

    def test_properties(self):
        sat = Spacecraft.LS8
        assert sat.omega == 0.001059
        assert sat.tag == "LS8"

    def test_iteration(self):
        names = ""
        for sat in Spacecraft:
            names = names + sat.name + ","

        assert names == "LS5,LS7,LS8,"

    def test_access(self):
        craft_a = Spacecraft.LS7
        craft_b = Spacecraft["LS7"]

        assert craft_a == craft_b

    def no_test_immutable(self):
        """TODO: make Spacecraft members immutable."""
        sat = Spacecraft.LS8

        assert sat.altitude == 705000.0
        try:
            sat.altitude = 710000.0
            self.fail("Spacecraft is immutable, should have raised a TypeError")
        except TypeError:
            pass  # expected a TypeError trying to change immutable Spacecraft object


if __name__ == "__main__":
    unittest.main()
