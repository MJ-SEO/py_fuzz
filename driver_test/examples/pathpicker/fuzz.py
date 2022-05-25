from pythonfuzz.main import PythonFuzz
from pathpicker import process_input

@PythonFuzz
def fuzz(buf):
    try:
        process_input.do_program()
    except UnicodeDecodeError:
        pass

if __name__ == '__main__':
    fuzz()
