import zlib
from pythonfuzz.main import PythonFuzz


@PythonFuzz
def fuzz(buf):
    try:
#        print("[DEBUF] buf: ", len(buf))
        string = zlib.compress(buf, level=-1)
#        print("[DEBUF] Compressed string: ", len(string))
        str2 = zlib.decompress(string)
#        print("[DEBUF] Original string: ", len(str2))
    except zlib.error:
        pass


if __name__ == '__main__':
    fuzz()
