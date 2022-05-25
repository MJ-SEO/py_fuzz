import collections
import sys

prev_line = 0
prev_filename = ''
#data = collections.defaultdict(set)
data = {}#collections.defaultdict(set)

coverage = collections.defaultdict(set)

prev_branch_len = 0
branch_coverage = set()

def trace(frame, event, arg):
    if event != 'line':
        return trace

    global prev_line
    global prev_filename

    func_filename = frame.f_code.co_filename
    func_line_no = frame.f_lineno

#    print(func_filename, "prev_line: ", prev_line, "curr_line: ", func_line_no)

    if func_filename != prev_filename:
        # We need a way to keep track of inter-files transferts,
        # and since we don't really care about the details of the coverage,
        # concatenating the two filenames in enough.
        #data[func_filename + prev_filename].add((prev_line, func_line_no))
        add_to_set(prev_filename + ":" + func_filename + ":" + str(prev_line) + ":" + str(func_line_no))
    else:
        #data[func_filename].add((prev_line, func_line_no))
        add_to_set(func_filename + ":" + str(prev_line) + ":" + str(func_line_no))

    prev_line = func_line_no
    prev_filename = func_filename

    return trace

def add_to_set(edge):
    branch_coverage.add(edge)
    if data.get(edge) is None :
        data[edge] = 0
    data[edge] = data[edge] + 1

def get_coverage():
    global data
    global prev_line
    global prev_filename
    global prev_branch_len
    global branch_coverage 

    for edge in data:
        if data[edge] <= 1 :
            coverage[edge].add(0)
        elif data[edge] <= 2 :
            coverage[edge].add(1)
        elif data[edge] <= 3 :
            coverage[edge].add(2)
        elif data[edge] <= 16 :
            coverage[edge].add(3)
        elif data[edge] <= 32 :
            coverage[edge].add(4)
        elif data[edge] <= 64 :
            coverage[edge].add(5)
        elif data[edge] <= 128 :
            coverage[edge].add(6)
        else : 
            coverage[edge].add(7)
    
    prev_line = 0
    prev_filename = ""
    data = {} 
    if prev_branch_len < len(branch_coverage):
        prev_branch_len = len(branch_coverage)
#    with open("log.csv", "a") as log_file:
#            log_file.write("branch_cov: %d\n" % (prev_branch_len))
    return (len(branch_coverage), sum(map(len,coverage.values())))
    #return sum(map(lencoverage)
    #return sum(map(len, data.values()))
