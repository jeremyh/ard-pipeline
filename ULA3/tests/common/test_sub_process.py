import os
import pprint
import unittest

from ULA3.utils import execute


class test_Subproc(unittest.TestCase):
    def print_result(self, result):
        print
        pprint.pprint(result)

    def test_true(self):
        result = execute("/bin/true")
        # self.print_result(result)
        assert result["returncode"] == 0
        assert result["stdout"] == ""
        assert result["stderr"] == ""

    def test_false(self):
        result = execute("/bin/false")
        # self.print_result(result)
        assert result["returncode"] == 1
        assert result["stdout"] == ""
        assert result["stderr"] == ""

    def test_ls(self):
        result = execute("ls -l")
        # self.print_result(result)
        assert result["returncode"] == 0
        assert result["stdout"] != ""
        assert result["stderr"] == ""

    def test_ls_wdir(self):
        tdir = os.getcwd()
        xdir = "/tmp"
        assert os.path.isdir(xdir)
        result = execute("ls -l", cwd=xdir)
        assert result["returncode"] == 0
        assert result["stdout"] != ""
        assert result["stderr"] == ""
        assert result["caller_wd"] == tdir
        assert result["stdout"] != execute("ls -l")["stdout"]
