import os
import unittest

if __name__ == "__main__":
    unittest.main(module=None,
                  failfast=False,
                  buffer=False,
                  catchbreak=False,
                  argv=["", "discover", "-p", "*test*.py"])  # search for all test files having test_ prefix
