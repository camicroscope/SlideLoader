import pytest
from SlideLoader import Config
# unit test cases for the config submodule

# test script
print("Fails if no config passed.")
with pytest.raises(IOError):
    cnf0 = Config("")
    # config object
print("Successfully creates from a file. ")
cnf = Config("example_config.yml")

print ("Reads the file without incident.")
config = cnf.read()

print ("api_key translates ok from example")
assert config['api_key'] == "ABC123"

print ("reads globals ok")
assert config['global']['study'] == "TEST01"
