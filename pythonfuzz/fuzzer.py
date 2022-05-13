import os
from random import random, uniform
import sys
import time
import sys
import psutil
import hashlib
import logging
import functools
import multiprocessing as mp
import signal
import statistics
import tempfile
from contextlib import contextmanager
from multiprocessing import Manager

from pyrsistent import mutant

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
 #           with time_limit(self._timeout):
            sys.settrace(tracer.trace)
            self._target(buf)
        except (Exception, TimeoutException) as e:
                tracer.set_crash()
                if not self._inf_run:
                    logging.exception(e)
                    child_conn.send(None)
                    break
                else:
                    sys.settrace(None)
                    if(tracer.get_crash() > self._crashes):
                        print("New crash ", self._crashes)
                        self._crashes += 1
                        logging.exception(e)
                        child_conn.send(None)
                    else:
                        run_coverage = tracer.get_coverage()
    #                    print("Outtttttter11111 :", sum(map(len, coverage.values())))
                        child_conn.send(run_coverage)
     #                  sys.settrace(tracer.trace)

        else:
            sys.settrace(None)
            run_coverage = tracer.get_coverage()
            child_conn.send(run_coverage)
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
                 sched=None,
                 ):
        self._target = target
        self._dirs = [] if dirs is None else dirs
        self._exact_artifact_path = exact_artifact_path
        self._rss_limit_mb = rss_limit_mb
        self._timeout = timeout
        self._regression = regression
        self._close_fd_mask = close_fd_mask
        self._dict_path = dict_path
        self._corpus = corpus.Corpus(self._dirs, max_input_size, dict_path)
        self._mutation = mutate.Mutator(max_input_size, dict_path)
        self._total_executions = 0
        self._executions_in_sample = 0
        self._last_sample_time = time.time()
        self._total_coverage = 0
        self._p = None
        self.runs = runs
        self._inf_run = inf_run # added
        self._crashes = 0
        self._hangs = 0
        self._run_coverage = {}
        self._n_time = 0
        self._avg_time = 0
        self._tot_time = 0
        self._sched = sched

    def log_stats(self, log_type):
        rss = (psutil.Process(self._p.pid).memory_info().rss + psutil.Process(os.getpid()).memory_info().rss) / 1024 / 1024

        endTime = time.time()
        execs_per_second = int(self._executions_in_sample / (endTime - self._last_sample_time))
        self._last_sample_time = time.time()
        self._executions_in_sample = 0
        ### ADDED
        n = self._n_time
        self._avg_time = n / (n + 1) * self._avg_time + execs_per_second / (n+1)
        self._n_time = n + 1
        
        #self._tot_time += execs_per_second
        #print(self._tot_time / (n + 1))
        logging.info('#{} {}     cov: {} corp: {} exec/s: {} rss: {} MB Unique Crash: {} total avg exec/s: {}'.format(
            self._total_executions, log_type, self._total_coverage, self._corpus.length, execs_per_second, rss, self._crashes, self._avg_time))
        '''
        print("idx : %d" % (self._corpus._seed_idx))
        print("favored : %d" %  len(self._corpus._favored))
        print("run path : %d" % len(self._run_coverage))
        print("total path : %d" % len(self._corpus._total_path))
        print("time : %d " % len(self._corpus._time))
        print("num(mutated) : %d" % len(self._corpus._mutated))
        print("num(inputs) : %d" % len(self._corpus._inputs))
        for i, inp in enumerate(self._corpus._inputs):
            print("inputs: ", inp, "hex: ", inp.hex() , " refcount", self._corpus._refcount[i])
        print("---")
        '''
        with open("log.csv", "a") as log_file:
            log_file.write("%d, %d\n" %(self._total_executions, self._total_coverage))
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
        with open(crash_path, 'wb') as f:
            f.write(buf)
        logging.info('sample was written to {}'.format(crash_path))
        if len(buf) < 200:
            logging.info('sample = {}'.format(buf.hex()))

    def exit_protocol(self, exit_code):
        self._p.join()
        sys.exit(exit_code)

    def calculate_score(self, input_idx, sched):
        HAVOC_CYCLE = 256
        avg_exec_time = statistics.mean(self._corpus._run_time)
        avg_coveage = 10 # coverage
        perf_score = 100
        
        curr_exec_time = self._corpus._run_time[input_idx]
        curr_coverage = 10 

        # Adjust score based on execution speed of this input, compared to the global average.
        # Fast inpust are less expensive to fuzz
        if curr_exec_time * 0.1 > avg_exec_time:
            perf_score = 10
        elif curr_exec_time * 0.25 > avg_exec_time:
            perf_score = 25 
        elif curr_exec_time* 0.5 > avg_exec_time:
            perf_score = 50
        elif curr_exec_time * 0.75 > avg_exec_time:
            perf_score = 70
        elif curr_exec_time * 4 < avg_exec_time:
            perf_score = 300
        elif curr_exec_time * 3 < avg_exec_time:
            perf_score = 200
        elif curr_exec_time * 2 < avg_exec_time:
            perf_score = 150

        # Adjust score based pn bitmap size. 
        # The working theory is that better coverate translates to better targets 
        if curr_coverage * 0.3 > avg_coveage:
            perf_score *= 3
        elif curr_coverage * 0.5 > avg_coveage:
            perf_score *= 2 
        elif curr_coverage * 0.75 > avg_coveage:
            perf_score *= 1.5
        elif curr_coverage * 3 < avg_coveage:
            perf_score * 0.25
        elif curr_coverage * 2 < avg_coveage:
            perf_score = 0.5
        elif curr_coverage * 1.5 < avg_coveage:
            perf_score = 0.75

        # Adjust score based on handicap
        # TODO Latecomers are allowed to run for a bit longer
        

        ## TODO Chage depth to level
        if self._corpus._depth[input_idx] < 3:
            pass
        elif self._corpus._depth[input_idx] < 7:
            perf_score *= 2
        elif self._corpus._depth[input_idx] < 13:
            perf_score *= 3
        elif self._corpus._depth[input_idx] < 24:
            perf_score *= 4
        else:
            perf_score *= 5         
        

        print("DEBUG perf_score: ", perf_score)

        perf_score = HAVOC_CYCLE * perf_score / 100 / 1 # TODO havoc div

        return perf_score

# afl->stage_max = (doing_det ? HAVOC_CYCLES_INIT : HAVOC_CYCLES) *
#             perf_score / afl->havoc_div / 100;

    def start(self):
        logging.info("[DEBUG] #0 READ units: {}".format(self._corpus.length))
        parent_conn, child_conn = mp.Pipe()
        self._p = mp.Process(target=worker, args=(self, child_conn)) #added
        self._p.start()

        while True:
            buf = self._corpus.generate_input()
            if not self._corpus._seed_run_finished:
                self.fuzz_loop(buf, parent_conn)
                if self._corpus._seed_idx + 1 >= len(self._corpus._inputs) : 
                    self._corpus._seed_run_finished = True
            else :
#                print("Depth, idx: ", self._corpus._depth[self._corpus._seed_idx], self._corpus._seed_idx)
                if self._corpus._depth[self._corpus._seed_idx] == 1:
                    for buf_idx in range(len(buf)):
                        for m in range(self._mutation._deterministics):
                            mutated_buf = self._mutation.mutate_det(buf, buf_idx, m)
                            self.fuzz_loop(mutated_buf, parent_conn)
                else:
                    if self._sched:
                        score = self.calculate_score(self._corpus._seed_idx, self._sched)
                    else:
                        score = 500
                    for i in range(int(score)):
                        havoc_buf = self._mutation.mutate_havoc(buf, self._dict_path)
                        self.fuzz_loop(havoc_buf, parent_conn)

    def fuzz_loop(self, buf, parent_conn):

        exit_code = 0
        if self.runs != -1 and self._total_executions >= self.runs:
            self._p.terminate()
            logging.info('did %d runs, stopping now.', self.runs)
            self.exit_protocol(exit_code)
    
        start_time = time.time()
        parent_conn.send_bytes(buf)
        if not parent_conn.poll(self._timeout):
            logging.info("=================================================================")
            logging.info("timeout reached. testcase took: {}".format(self._timeout))
            self.write_sample(buf, prefix='timeout-')
            if self._inf_run:
                self._hangs += 1
            else:
                self._p.kill()
                self.exit_protocol(exit_code)

        self._run_coverage = parent_conn.recv()
        end_time = time.time()
        if self._run_coverage is None :
            self._crashes += 1
            self.write_sample(buf)
            if not self._inf_run: # added
               exit_code = 76
               self.exit_protocol(exit_code)
            return

        self._total_coverage = len(self._corpus._total_path)
        self._total_executions += 1
        self._executions_in_sample += 1
        rss = 0
        idx = self._corpus._seed_idx
        self._corpus._run_time[idx] = end_time - start_time

        if self._corpus._seed_run_finished :
            if self._corpus.Isinteresting(self._run_coverage):
                idx = self._corpus.put(buf)
                self._corpus.UpdatedFavored(buf, idx, end_time - start_time, self._run_coverage)
                #print("idx : %d, mutation : %d" %(buf_idx, m))
                rss = self.log_stats("NEW")
            else:
                if (time.time() - self._last_sample_time) > SAMPLING_WINDOW:
                    rss = self.log_stats('PULSE')
                    for i, inp in enumerate(self._corpus._inputs):
                        print("iNPUTS: " , inp, " refcount:", self._corpus._is_favored[i], "Time: ", self._corpus._run_time[i]
                        , "Depth: ", self._corpus._depth[i])


        else:
            self._corpus._add_to_total_coverage(self._run_coverage)
            self._corpus.UpdatedFavored(buf, idx, end_time - start_time, self._run_coverage)
            rss = self.log_stats("SEED")

        if rss > self._rss_limit_mb:
            logging.info('MEMORY OOM: exceeded {} MB. Killing worker'.format(self._rss_limit_mb))
            self.write_sample(buf)
            self._crashes += 1
            if not self._inf_run:
                self._p.kill()
                self.exit_protocol(exit_code)