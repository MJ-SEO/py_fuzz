import io
import aifc
from pythonfuzz.main import PythonFuzz


@PythonFuzz
def fuzz(buf):
    try:
        f = io.BytesIO(buf)
        a = aifc.open(f)
        a.readframes(1)
        a.readframes(2)
        a.close()
    except (EOFError, aifc.Error):
        pass


if __name__ == '__main__':
    fuzz()
