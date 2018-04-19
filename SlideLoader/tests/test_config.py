from SlideLoader import Config
# unit test cases for the config submodule

class TestConfig(unittest.TestCase):
    # Read a config file
    # fail (gracefully? not so gracefully?) if file absent
    # output a dictionary for usage
    # complain if an important setting missing
    # complain loudly if config file malformed
