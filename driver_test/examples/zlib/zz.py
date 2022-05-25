import gzip
from pythonfuzz.main import PythonFuzz


@PythonFuzz
def fuzz(buf):
    try:
#      i print("[DEBUF] buf: ", len(buf))
        string = gzip.compress(buf)
#        print("[DEBUF] string: ", len(string))
        str2 = gzip.decompress(string)
#        print("[DEBUF] string: ", len(str2))
    except UnicodeError:
        pass


if __name__ == '__main__':
    fuzz()
