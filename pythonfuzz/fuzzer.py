from ast import Pass
from cgi import print_form
import os
import sys
import time
import sys
from tracemalloc import Trace
from isort import file
from numpy import convolve, cov
import psutil
import hashlib
import logging
import functools
import multiprocessing as mp
import signal
import tempfile
from contextlib import contextmanager
from multiprocessing import Manager

class TimeoutException(Exception): pass

mp.set_start_method('fork')

from pythonfuzz import corpus, dictionnary, tracer

logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
logging.getLogger().setLevel(logging.DEBUG)

SAMPLING_WINDOW = 5 # IN SECONDS

try:
    lru_cache = functools.lru_cache
except:
    import functools32
    lru_cache = functools32.lru_cache

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def worker(self, child_conn, coverage):
    # Silence the fuzzee's noise
    class DummyFile:
        """No-op to trash stdout away."""
        def write(self, x):
            pass
    logging.captureWarnings(True)
    logging.getLogger().setLevel(logging.ERROR)
    if self._close_fd_mask & 1:
        sys.stdout = DummyFile()
    if self._close_fd_mask & 2:
        sys.stderr = DummyFile()
    
#    sys.settrace(tracer.trace)
    while True:
        buf = child_conn.recv_bytes()
        try:
            with time_limit(self._timeout):
                sys.settrace(tracer.trace)
                print("DEBUG buf: ", buf)
                self._target(buf)
        except (Exception, TimeoutException) as e:
                tracer.set_crash()
                if not self._inf_run:
                    logging.exception(e)
                    child_conn.send(e)
                    break
                else:
                    sys.settrace(None)
                    if(tracer.get_crash() > self._crashes):
                        print("New crash ", self._crashes)
                        self._crashes += 1
                        logging.exception(e)
                        child_conn.send(e)
                    else:
                        coverage = tracer.get_coverage(coverage)
                        print("Outtttttter :", sum(map(len, coverage.values())))
                        child_conn.send_bytes(b'%d' % tracer.get_crash())
     #                  sys.settrace(tracer.trace)

        else:
            sys.settrace(None)
            coverage = tracer.get_coverage(coverage)
            print("Outtttttter :", sum(map(len, coverage.values())))
            child_conn.send_bytes(b'%d' % tracer.get_crash())
#           sys.settrace(tracer.trace)


class Fuzzer(object):
    def __init__(self,
                 target,
                 dirs=None,
                 exact_artifact_path=None,
                 rss_limit_mb=2048,
                 timeout=120,
                 regression=False,
                 max_input_size=4096,
                 close_fd_mask=0,
                 runs=-1,
                 dict_path=None,
				 inf_run=False,
                 file_fuzz=False,
                 file_extension=None):
        self._target = target
        self._dirs = [] if dirs is None else dirs
        self._exact_artifact_path = exact_artifact_path
        self._rss_limit_mb = rss_limit_mb
        self._timeout = timeout
        self._regression = regression
        self._close_fd_mask = close_fd_mask
        self._corpus = corpus.Corpus(self._dirs, max_input_size, dict_path)
        self._total_executions = 0
        self._executions_in_sample = 0
        self._last_sample_time = time.time()
        self._total_coverage = 0
        self._p = None
        self.runs = runs
        self._inf_run = inf_run # added
        self._crashes = 0
        self._hangs = 0
        self._file_fuzz = file_fuzz # added
        self._file_extension = file_extension # added

    def log_stats(self, log_type):
        rss = (psutil.Process(self._p.pid).memory_info().rss + psutil.Process(os.getpid()).memory_info().rss) / 1024 / 1024

        endTime = time.time()
        execs_per_second = int(self._executions_in_sample / (endTime - self._last_sample_time))
        self._last_sample_time = time.time()
        self._executions_in_sample = 0
        logging.info('#{} {}     cov: {} corp: {} exec/s: {} rss: {} MB Unique Crash: {}'.format(
            self._total_executions, log_type, self._total_coverage, self._corpus.length, execs_per_second, rss, self._crashes))
        with open("log.csv", "a") as log_file:
            log_file.write("%d, %d\n" %(self._total_executions, self._total_coverage))
        return rss

    def write_sample(self, buf, prefix='crash-'):
        m = hashlib.sha256()
        m.update(buf) # TODO: TypeError: object supporting the buffer API required
        if self._exact_artifact_path:
            crash_path = self._exact_artifact_path
        else:
            dir_path = 'crashes'
            isExist = os.path.exists(dir_path)
            if not isExist:
              os.makedirs(dir_path)
              logging.info("The crashes directory is created")

            crash_path = dir_path + "/" + prefix + m.hexdigest()
        with open(crash_path, 'wb') as f:
            f.write(buf)
        logging.info('sample was written to {}'.format(crash_path))
        if len(buf) < 200:
            logging.info('sample = {}'.format(buf.hex()))

    def initLopp(initSeed):
        print(initSeed)

    def start(self):
        logging.info("[DEBUG] #0 READ units: {}".format(self._corpus.length))
        exit_code = 0
        parent_conn, child_conn = mp.Pipe()
        manager = Manager()
        coverage = manager.dict()

        self._p = mp.Process(target=worker, args=(self, child_conn, coverage)) #added
        self._p.start()
        
        for i in (self._corpus._inputs):
            buf = self._corpus.generate_input()
            print("DEBUG INIT buf: ", buf)
            parent_conn.send_bytes(buf)
            if not parent_conn.poll(self._timeout):
                logging.info("=================================================================")
                logging.info("timeout reached. testcase took: {}".format(self._timeout))
                self.write_sample(buf, prefix='timeout-')
                if not self._inf_run:
                    self._p_kill()
                    break
                else:
                    self._hangs += 1
                    continue
            try:
                a = int(parent_conn.recv_bytes()) # total_coverage >> C(input), time
                print("OUTER INIT coverage: ", sum(map(len, coverage.values())))
            except ValueError:
                print("ff")

        while True:
            if self.runs != -1 and self._total_executions >= self.runs:
                self._p.terminate()
                logging.info('did %d runs, stopping now.', self.runs)
                break

            buf = self._corpus.generate_input()
            parent_conn.send_bytes(buf)
            
            if not parent_conn.poll(self._timeout):
                logging.info("=================================================================")
                logging.info("timeout reached. testcase took: {}".format(self._timeout))
                self.write_sample(buf, prefix='timeout-')
                if not self._inf_run:
                    self._p_kill()
                    break
                else:
                    self._hangs += 1
                    continue

            try:
                total_coverage = int(parent_conn.recv_bytes()) # total_coverage >> C(input), time
                print("OUTER coverage: ", sum(map(len, coverage.values())))
                # coverage, time = tracer.get_coverage()
                # corpus update
            except ValueError:
                self._crashes += 1
                self.write_sample(buf)
                if not self._inf_run: # added
                   exit_code = 76
                   break

            self._total_executions += 1
            self._executions_in_sample += 1
            rss = 0

            if total_coverage > self._total_coverage:  # TODO Isinteresting(path, Queue)
                rss = self.log_stats("NEW")
                self._total_coverage = total_coverage
                self._corpus.put(buf)
                    # UpdateFavored
            else:
                if (time.time() - self._last_sample_time) > SAMPLING_WINDOW:
                    rss = self.log_stats('PULSE')

            if rss > self._rss_limit_mb:
                logging.info('MEMORY OOM: exceeded {} MB. Killing worker'.format(self._rss_limit_mb))
                self.write_sample(buf)
                self._crashes += 1
                if not self._inf_run:
                    self._p.kill()
                    break

        self._p.join()
        sys.exit(exit_code)
