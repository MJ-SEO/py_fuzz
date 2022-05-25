import io
import zipfile
from pythonfuzz.main import PythonFuzz

@PythonFuzz
def fuzz(buf):
    f = io.BytesIO(buf)
    try:
        z = zipfile.ZipFile(f)
#        print("aaaaaaaaa", z.filename)
        z.testzip()
    except (zipfile.BadZipFile, zipfile.LargeZipFile):
        pass


if __name__ == '__main__':
    fuzz()
