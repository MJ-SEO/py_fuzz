import os
from random import random, uniform
from re import S
import sys
import time
import math
import sys
import psutil
import hashlib
import logging
import functools
import multiprocessing as mp
import signal
import tempfile
from contextlib import contextmanager

class TimeoutException(Exception): pass

mp.set_start_method('fork')

from pythonfuzz import corpus, mutate, tracer

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

def _log_hangs(self, buf):
    logging.info("=================================================================")
    logging.info("timeout reached. testcase took: {}".format(self._timeout))
 #   self.write_sample(buf, prefix='timeout-')

def worker(self, child_conn):
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
                self._target(buf)
        except TimeoutException as e:
            if not self._inf_run:
                logging.exception(e)
                child_conn.send(None)
                break
            else:
                _log_hangs(self, buf)
                sys.settrace(None)
                run_coverage = tracer.get_coverage()
                child_conn.send((run_coverage, "CRASH"))
                continue
        except Exception as e:
            if not self._inf_run:
                logging.exception(e)
                child_conn.send(None)
                break
            else:
                sys.settrace(None)
                run_coverage = tracer.get_coverage()
                child_conn.send((run_coverage, "CRASH"))
        else:
            sys.settrace(None)
            run_coverage = tracer.get_coverage()
            child_conn.send((run_coverage, "GOOD"))
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
                 sched=None):
        self._target = target
        self._dirs = [] if dirs is None else dirs
        self._exact_artifact_path = exact_artifact_path
        self._rss_limit_mb = rss_limit_mb
        self._timeout = timeout
        self._regression = regression
        self._close_fd_mask = close_fd_mask
        self._dict_path = dict_path
        self._corpus = corpus.Corpus(self._dirs, max_input_size, dict_path)
        self._child_conn, self._parent_conn = mp.Pipe()
        self._p = mp.Process(target=worker, args=(self, self._child_conn))
        self._mutation = mutate.Mutator(max_input_size, 35, dict_path, self._parent_conn)
        self._total_executions = 0
        self._executions_in_sample = 0
        self._last_sample_time = time.time()
        self._total_coverage = 0
        self.runs = runs
        self._inf_run = inf_run # added
        self._crashes = 0
        self._hangs = 0
        self._run_coverage = {}
        self._n_time = 0
        self._avg_time = 0
        self._tot_time = 0
        self._sched = self._parse_sched(sched)
    
    def _parse_sched(self, sched) :

        if sched == "afl":
            return 1
        elif sched == "perf":
            return 2
        return 0 # default

    def log_stats(self, log_type):
        rss = (psutil.Process(self._p.pid).memory_info().rss + psutil.Process(os.getpid()).memory_info().rss) / 1024 / 1024

        endTime = time.time()
        execs_per_second = int(self._executions_in_sample / (endTime - self._last_sample_time))
        self._last_sample_time = time.time()
        self._executions_in_sample = 0
        self._total_coverage = len(self._corpus._total_path)

        n = self._n_time
        self._avg_time = n / (n + 1) * self._avg_time + execs_per_second / (n+1)
        self._n_time = n + 1
        
        logging.info('#{} {}     cov: {}, {} corp: {} exec/s: {} rss: {} MB Unique Crash: {} total avg exec/s: {}'.format(
            self._total_executions, log_type, len(self._corpus._favored), self._total_coverage,self._corpus.length, execs_per_second, rss, self._crashes, self._avg_time))

        with open("log.csv", "a") as log_file:
            log_file.write("%d, %d, %d\n" %(self._total_executions, len(self._corpus._favored), self._total_coverage))
        return rss

    def write_sample(self, buf, prefix='crash-'):
        m = hashlib.sha256()
        m.update(buf)
        if self._exact_artifact_path:
            crash_path = self._exact_artifact_path
        else:
            dir_path = 'crashes'
            isExist = os.path.exists(dir_path)
            if not isExist:
              os.makedirs(dir_path)
              logging.info("The crashes directory is created")

            crash_path = dir_path + "/" + prefix + m.hexdigest()
#        with open(crash_path, 'wb') as f:
#            f.write(buf)
#logging.info('sample was written to {}'.format(crash_path))
#        if len(buf) < 200:
#            logging.info('sample = {}'.format(buf.hex()))

    def exit_protocol(self, exit_code):
        self._p.join()
        sys.exit(exit_code)

    def start(self):
        logging.info("[DEBUG] #0 READ units: {}".format(self._corpus.length))
        parent_conn = self._parent_conn
        child_conn = self._child_conn
        self._p.start()

        while True:
            buf = self._corpus.generate_input()
            idx = self._corpus._seed_idx
            if not self._corpus._seed_run_finished:
                self.fuzz_loop(buf, parent_conn)
                if idx + 1 >= len(self._corpus._inputs) : 
                    self._corpus._seed_run_finished = True
            else :
#                print("Depth, idx: ", self._corpus._select_count[self._corpus._seed_idx], self._corpus._seed_idx)
                if self._corpus._passed_det[idx] is False:
                    print("[Deterministic Stage] {idx = ",  idx,"}  LEN: ", len(self._corpus._inputs[idx]))
                    self._mutation.mutate_det(buf, self.fuzz_loop)
                    self._corpus._passed_det[idx] = True
                else:            
                    if self._sched > 0: # AFL
                        score = self._corpus.calculate_score(idx, self._sched)
                    else:
                        score = 512
                    print("[Havoc Stage] {idx =" , idx, "}  LEN: ", len(self._corpus._inputs[idx]), "  Score: " , score)
                    for i in range(int(score)):
                        havoc_buf = self._mutation.mutate_havoc(buf, self._corpus)
                        self.fuzz_loop(havoc_buf, parent_conn)

    def fuzz_loop(self, buf, parent_conn):

        exit_code = 0
        if self.runs != -1 and self._total_executions >= self.runs:
            self._p.terminate()
            logging.info('did %d runs, stopping now.', self.runs)
            self.exit_protocol(exit_code)
    
        start_time = time.time()
        parent_conn.send_bytes(buf)

        self._run_coverage, crash = parent_conn.recv()
        end_time = time.time()
        if crash == "CRASH" :
            self._crashes += 1
     #       self.write_sample(buf)
            if not self._inf_run: # added
               exit_code = 76
               self.exit_protocol(exit_code)

        self._total_executions += 1
        self._executions_in_sample += 1
        rss = 0
        idx = self._corpus._seed_idx
        self._corpus._run_time[idx] = end_time - start_time
        prev_coverage = self._total_coverage

        if self._corpus._input_path[idx] is None:
            self._corpus._input_path[idx] = self._run_coverage
#            print("DEBUG ipath: ", self._corpus._input_path[idx], " len:", len(self._corpus._input_path[idx]))
        
        if self._corpus._seed_run_finished :
            if self._corpus.is_interesting(self._run_coverage):
                idx = self._corpus.put(buf, self._corpus._depth[idx])
                self._corpus.update_favored(buf, idx, end_time - start_time, self._run_coverage)
                #print("idx : %d, mutation : %d" %(buf_idx, m))
                rss = self.log_stats("NEW")
                self._corpus._energy[idx] *= 1.8 if (len(self._corpus._total_path) - prev_coverage) <= 3 else math.log2((len(self._corpus._total_path) - prev_coverage))
            else:
                self._corpus._energy[idx] *= 0.9991
                if (time.time() - self._last_sample_time) > SAMPLING_WINDOW:
                    rss = self.log_stats('PULSE')
        else:
            self._corpus._add_to_total_coverage(self._run_coverage)
            self._corpus.update_favored(buf, idx, end_time - start_time, self._run_coverage)
            rss = self.log_stats("SEED")

        if rss > self._rss_limit_mb:
            logging.info('MEMORY OOM: exceeded {} MB. Killing worker'.format(self._rss_limit_mb))
      #      self.write_sample(buf)
            self._crashes += 1
            if not self._inf_run:
                self._p.kill()
                self.exit_protocol(exit_code)
