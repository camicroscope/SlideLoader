import glob
import json
import subprocess
import sys
# from os.path import expanduser
import argparse

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-s", "--slide_dir", help="Upload svs from directory. Example: /home/user/slides/")
ap.add_argument("-u", "--url", help="Base url. Example: http://www.example.com:4010")
args = vars(ap.parse_args())
# print(args)

if not len(sys.argv) > 1:
    program_name = sys.argv[0]
    lst = ['python', program_name, '-h']
    subprocess.call(lst)  # Show help
    exit(1)

DIR = args["slide_dir"]
URL = args["url"]
# home = expanduser("~")
ff = glob.glob(DIR + "*.svs")

for f in ff:
    f = f.replace(DIR, '')
    print(f)
    bytes_value = subprocess.check_output(
        "curl -f -s -S -k " + DIR + "/load/Slide/info/" + f,
        shell=True)
    my_json = bytes_value.decode('utf8').replace("'", '"')
    obj = json.loads(my_json)
    print(obj['filename'], obj['height'])
    exit(0)  # Temporary.

exit(0)
