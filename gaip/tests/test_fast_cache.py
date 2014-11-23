#!/bin/env python

import os
import unittest

import gaip


class TestSsdCaching(unittest.TestCase):
    def test_no_ssd_available(self):
        data_path = os.path.abspath("./data")
        path_to_read = gaip.fast_read(data_path, ssd_env_var="ABSENT_ENV_VAR")
        assert data_path == path_to_read

    def test_no_data(self):
        data_path = "/some/path/that/does/not/exist"
        path_to_read = gaip.fast_read(data_path)
        assert data_path == path_to_read

    def test_successful_cache_copy(self):
        data_path = os.path.abspath("./data")
        env_var = "FAST_READ_CACHE"
        cache_path = "/tmp/smr/cache"

        os.environ[env_var] = cache_path
        assert os.environ[env_var] == cache_path

        path_to_read = gaip.fast_read(data_path, ssd_env_var=env_var)
        assert path_to_read != data_path


if __name__ == "__main__":
    unittest.main()
