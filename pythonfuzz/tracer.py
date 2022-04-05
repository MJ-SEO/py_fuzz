import collections
import sys

prev_line = 0
prev_filename = ''

func_filename = ''
func_line_no = 0

data = collections.defaultdict(set)
crashes = set()
index = 0

def trace(frame, event, arg):
    if event != 'line':
        return trace

    global prev_line
    global prev_filename

    func_filename = frame.f_code.co_filename
    func_line_no = frame.f_lineno

 #   print(func_filename, " " ,func_line_no)

    if func_filename != prev_filename:
        # We need a way to keep track of inter-files transferts,
        # and since we don't really care about the details of the coverage,
        # concatenating the two filenames in enough.
        data[func_filename + prev_filename].add((prev_line, func_line_no))
    else:
        data[func_filename].add((prev_line, func_line_no))

    prev_line = func_line_no
    prev_filename = func_filename

    return trace


def get_coverage():

    global prev_line
    global prev_filename

    prev_line = 0
    prev_filename = ''

    a = sum(map(len, data.values()))
    return a;

def get_crash():
    return index

def set_crash():
    crashes.add(data)
    global index
    index = len(crashes)
