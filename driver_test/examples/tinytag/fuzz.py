from pythonfuzz.main import PythonFuzz
from tinytag import TinyTag
import io

@PythonFuzz
def fuzz(buf):
	try:
		f = open('temp.mp4', "wb")
		f.write(buf)
		f.seek(0)
		tag = TinyTag.get(f.name)
	except UnicodeDecodeError:
		pass

if __name__ == '__main__':
	fuzz()


