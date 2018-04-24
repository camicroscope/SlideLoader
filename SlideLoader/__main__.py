import SlideLoader
import sys

if __name__ == "__main__":
    print("this should run")
    print(sys.argv)
    if len(sys.argv[1]) < 4:
        raise RuntimeError("Requires a mode, a config file and a manifest")
    mode = cnf_file = sys.argv[1]
    cnf_file = sys.argv[2]
    manifest_file = sys.argv[3]
    a = SlideLoader.Controller(cnf_file, manifest_file)
    if mode.lower() == "run":
        a.run()
    elif mode.lower() == "thumbnail":
        a.thumbnails()
    else:
        raise RuntimeError("Unrecognized mode")
