from pythonfuzz.main import PythonFuzz
from pybuilder.errors import PyBuilderException
from pybuilder.core import *
from pybuilder.scaffolding import * 
import tempfile

@PythonFuzz
def fuzz(buf):
	try:
		p_name = buf.decode("ascii") # pass to stdin
		collect_project_information()

	except (PyBuilderException, UnicodeDecodeError):
		pass

if __name__ == '__main__':
	fuzz()
