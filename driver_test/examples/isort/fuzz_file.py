from pythonfuzz.main import PythonFuzz
import tempfile
import isort

@PythonFuzz
def fuzz(buf):
	try:
		string = buf.decode("ascii")
		f = tempfile.NamedTemporaryFile('w+')
		f.write(string)
		
		f.seek(0)
		isort.file(f.name)
		f.close()
	except UnicodeDecodeError:
		pass

if __name__ == '__main__':
	fuzz()
