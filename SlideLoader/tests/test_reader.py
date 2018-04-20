from SlideLoader import Reader
# test cases for reader


print("Test reading a csv manifest")
a = Reader("example_manifest.csv").read()

print("Test reading a JSON manifest")
b = Reader("example_manifest.json", "JSON").read()

print("assert both test records loaded from csv")
assert len(a) == 2

print("assert both test records loaded from json")
assert len(b) == 2

print("assert file path read accurately from csv")
assert a[0]["file"] == "/data/img/alice1.svs"

print("assert file path read accurately from json")
assert b[0]["file"] == "/data/img/alice1.svs"
