from pythonfuzz.main import PythonFuzz
from pybuilder.errors import PyBuilderException
from pybuilder.core import *
from pybuilder.scaffolding import * 
import tempfile

@PythonFuzz
def fuzz(buf):
	try:
		p_name = buf.decode("ascii")
		with tempfile.TemporaryDirectory() as tempDir:
			pass
		project = Project(basedir= tempDir, name = p_name)
		project.validate()

		scaffold = PythonProjectScaffolding(project)
		scaffold.build_initializer()

	except (PyBuilderException, UnicodeDecodeError):
		pass

if __name__ == '__main__':
	fuzz()
