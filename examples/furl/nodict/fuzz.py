from pythonfuzz.main import PythonFuzz
from furl import furl

@PythonFuzz
def fuzz(buf):
	try:
		string = buf.decode("ascii")
		f = furl(string)
		f.path.segments
		f.path.normalize()
	except (UnicodeDecodeError, ValueError, SyntaxError):
		pass

if __name__ == '__main__':
	fuzz()
