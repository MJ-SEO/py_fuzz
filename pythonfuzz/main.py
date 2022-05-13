import argparse
from re import S
from pythonfuzz import fuzzer

class PythonFuzz(object):
    def __init__(self, func):
        self.function = func
        self._fname = None

    def __call__(self, *args, **kwargs):
        parser = argparse.ArgumentParser(description='Coverage-guided fuzzer for python packages')
        parser.add_argument('dirs', type=str, nargs='*',
                            help="one or more directories/files to use as seed corpus. the first directory will be used to save the generated test-cases")
        parser.add_argument('--exact-artifact-path', type=str, help='set exact artifact path for crashes/ooms')
        parser.add_argument('--regression',
                            type=bool,
                            default=False,
                            help='run the fuzzer through set of files for regression or reproduction')
        parser.add_argument('--rss-limit-mb', type=int, default=4096, help='Memory usage in MB')
        parser.add_argument('--max-input-size', type=int, default=4096, help='Max input size in bytes')
        parser.add_argument('--dict', type=str, help='dictionary file')
        parser.add_argument('--close-fd-mask', type=int, default=0, help='Indicate output streams to close at startup')
        parser.add_argument('--runs', type=int, default=-1, help='Number of individual test runs, -1 (the default) to run indefinitely.')
        parser.add_argument('--timeout', type=int, default=5,
                            help='If input takes longer then this timeout the process is treated as failure case')
        parser.add_argument('--inf-run', default=False, action='store_true', help='Decide the fuzzing wherter stop or keep runing after it finds a failure') # added
        parser.add_argument('--sched', type=str, default=None, help='Choose the fuzzing power schduling stratgy') # added
        parser.add_argument('--fname', type=str, default=None, help='Specific file name for PythonfuzzFile driver') # added

        args = parser.parse_args()
        f = fuzzer.Fuzzer(self.function, args.dirs, args.exact_artifact_path,
                          args.rss_limit_mb, args.timeout, args.regression, args.max_input_size,
                          args.close_fd_mask, args.runs, args.dict, args.inf_run, args.sched) #, self._fname)

        f.start()

class PythonFuzzFile(object):
    def __init__(self, func):
        self.function = func
        self._fname = "tempfile"

    def _fuzzfile(self):
        return self._fname

    def __call__(self, *args, **kwargs):
        parser = argparse.ArgumentParser(description='Coverage-guided fuzzer for python packages')
        parser.add_argument('dirs', type=str, nargs='*',
                            help="one or more directories/files to use as seed corpus. the first directory will be used to save the generated test-cases")
        parser.add_argument('--exact-artifact-path', type=str, help='set exact artifact path for crashes/ooms')
        parser.add_argument('--regression',
                            type=bool,
                            default=False,
                            help='run the fuzzer through set of files for regression or reproduction')
        parser.add_argument('--rss-limit-mb', type=int, default=4096, help='Memory usage in MB')
        parser.add_argument('--max-input-size', type=int, default=4096, help='Max input size in bytes')
        parser.add_argument('--dict', type=str, help='dictionary file')
        parser.add_argument('--close-fd-mask', type=int, default=0, help='Indicate output streams to close at startup')
        parser.add_argument('--runs', type=int, default=-1, help='Number of individual test runs, -1 (the default) to run indefinitely.')
        parser.add_argument('--timeout', type=int, default=5,
                            help='If input takes longer then this timeout the process is treated as failure case')
        parser.add_argument('--inf-run', default=False, action='store_true', help='Decide the fuzzing wherter stop or keep runing after it finds a failure') # added
        parser.add_argument('--fname', type=str, default=None, help='Specific file name for PythonfuzzFile driver') # added

        args = parser.parse_args()

        if args.fname:
            self._fname = args.fname

        print("MAIN fname: ", self._fname)
        
        f = fuzzer.Fuzzer(self.function, args.dirs, args.exact_artifact_path,
                          args.rss_limit_mb, args.timeout, args.regression, args.max_input_size,
                          args.close_fd_mask, args.runs, args.dict, args.inf_run, self._fname)

        f.start()

'''
@PythonFuzz
def PythonfuzzFile():
    pass
'''

if __name__ == '__main__':
    PythonFuzz()
