import unittest
import sys

if __name__ == '__main__':
    import xmlrunner
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir='tests')
    runner = xmlrunner.XMLTestRunner(output='test-reports')
    res = runner.run(suite)
    sys.exit(1 if len(res.errors) > 0 else 0)
