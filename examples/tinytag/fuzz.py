from pythonfuzz.main import PythonFuzz
from tinytag import TinyTag
import tempfile
import random
def suffix():
	randnum = random.randint(0, 4)
	if(randnum == 0):
		return ".mp4"
	elif(randnum == 1):
		return ".mp3"
	elif(randnum == 2):
		return ".WMA"
	elif(randnum == 3):
		return ".riff"
	elif(randnum == 4):
		return ".ogg"		

@PythonFuzz
def fuzz(buf):
	try:
		f = tempfile.NamedTemporaryFile('wb', suffix=suffix())
		f.write(buf) 
		tag = TinyTag.get(f.name)
		tag.filesize 
		f.close()
	except UnicodeDecodeError:
		pass

if __name__ == '__main__':
	fuzz()


