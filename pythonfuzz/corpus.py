
import hashlib
import os
from random import random
import numpy as np

INTERESTING8 = [-128, -1, 0, 1, 16, 32, 64, 100, 127]
INTERESTING16 = [0, 128, 255, 256, 512, 1000, 1024, 4096, 32767, 65535]
INTERESTING32 = [0, 1, 32768, 65535, 65536, 100663045, 2147483647, 4294967295]


class Corpus(object):
    def __init__(self, dirs=None, max_input_size=4096, dict_path=None):
        self._inputs = []

        self._input_path = []
        self._refcount = [] # favored or not
        self._run_time = [] # running time of inputs
        self._mutated = [] # Mutated or not
        self._select_count = []
        self._depth = []
        self._passed_det = []
        self._energy = []
        
        self._queue_cycle = 0
        
        self._favored = {} 
        self._total_path = set()
        
        self._dirs = dirs if dirs else []
        for i, path in enumerate(dirs):
            if i == 0 and not os.path.exists(path):
                os.mkdir(path)

            if os.path.isfile(path):
                self._add_file(path)
            else:
                for i in os.listdir(path):
                    fname = os.path.join(path, i)
                    if os.path.isfile(fname):
                        self._add_file(fname)

        self._seed_run_finished = False
        self._seed_idx = -1
        self._save_corpus = dirs and os.path.isdir(dirs[0])
        #self._mutation = mutate.Mutator(max_input_size, dict_path)
        self._put_inputs(bytearray(0))

    @property
    def length(self):
        return len(self._inputs)

    def _put_inputs(self, buf):
        self._inputs.append(buf)
        idx = len(self._inputs) - 1
        self._refcount.append(0)
        self._run_time.append(0)
        self._mutated.append(False)
        self._select_count.append(0)
        self._depth.append(0)
        self._passed_det.append(False)
        self._input_path.append(None)
        self._energy.append(20)
        return idx

    def _add_file(self, path):
        with open(path, 'rb') as f:
            self._put_inputs(bytearray(f.read()))
   
    def put(self, buf, depth):
        if self._save_corpus:
            m = hashlib.sha256()
            m.update(buf)
            fname = os.path.join(self._dirs[0], m.hexdigest())
            #fileExist = os.path.exists(fname)
            with open(fname, 'wb') as f:
                f.write(buf)
        idx = self._put_inputs(buf)
        self._depth[idx] = depth

        return idx

    def _add_to_total_coverage(self, path):
        for edge in path:
            self._total_path.add((edge, path[edge]))
 #           print("[DEBUG] ", edge, " ", hitcount)

    def is_interesting(self, path):
        orig_len = len(self._total_path)
        self._add_to_total_coverage(path)
        if orig_len < len(self._total_path):
            return True
        else:
            return False

            
    def update_favored(self, buf, index, time, coverage):
        for edge in coverage:
            if self._favored.get(edge) is None: 
                self._favored[edge] = buf
                self._refcount[index] += 1
            else:
                favored_idx = self._inputs.index(self._favored[edge]) 
                if (len(buf) * time < (len(self._favored[edge]) * self._run_time[favored_idx])):
                    self._favored[edge] = buf
                    self._refcount[favored_idx] -= 1
                    self._refcount[index] += 1
    
    def is_there_uumutated_favored(self):
        for i in range(len(self._inputs)):
            if self._refcount[i] > 0 and self._mutated[i] == 0 :
               return True
        return False

    def seed_selection(self):
        unmutated_favored_in_queue = self.is_there_uumutated_favored()
        while True:
            self._seed_idx += 1
            if self._seed_idx >= len(self._inputs):
                self._queue_cycle += 1
                self._seed_idx = 0
       
            if(self._refcount[self._seed_idx] == 0) :
                if unmutated_favored_in_queue:
                    if random() >= 0.01 :
                        continue
                elif self._mutated[self._seed_idx] == 1:
                    if random() >= 0.05 :
                        continue
                else :
                    if random() >= 0.25 :
                        continue
            break

        return self._seed_idx


    def generate_input(self):
        if self._seed_run_finished is True:
            buf_idx = self.seed_selection()
            buf = self._inputs[buf_idx]
            self._mutated[buf_idx] = True
            self._select_count[buf_idx] += 1
            return buf
        else:
            self._seed_idx += 1
            if(self._seed_idx >= len(self._inputs)):
                self._seed_idx = 0
            buf_idx = self._seed_idx
            buf = self._inputs[buf_idx]
            return buf
    
    def calculate_score(self, idx, sched):
        if sched == 1 : # AFL
            HVCOV_CYCLE = 256
            perf_score = 100
            t = np.array(self._run_time)
            avg_exec_time = t[np.nonzero(t)].mean()
            avg_coverage = np.mean(len(self._input_path))

            cur_exec_time = self._run_time[idx]
            cur_coverage = len(self._input_path[idx])

            # Adjust score via execution time
            if cur_exec_time * 0.1 > avg_exec_time:
                perf_score = 10
            elif cur_exec_time * 0.25 > avg_exec_time:
                perf_score = 25 
            elif cur_exec_time* 0.5 > avg_exec_time:
                perf_score = 50
            elif cur_exec_time * 0.75 > avg_exec_time:
                perf_score = 70
            elif cur_exec_time * 4 < avg_exec_time:
                perf_score = 450
            elif cur_exec_time * 3 < avg_exec_time:
                perf_score = 300
            elif cur_exec_time * 2 < avg_exec_time:
                perf_score = 225

            # Adjust score via coverage
            if cur_coverage * 0.3 > avg_coverage:
                perf_score *= 4
            elif cur_coverage * 0.5 > avg_coverage:
                perf_score *= 3 
            elif cur_coverage * 0.75 > avg_coverage:
                perf_score *= 2.5
            elif cur_coverage * 3 < avg_coverage:
                perf_score * 0.25
            elif cur_coverage * 2 < avg_coverage:
                perf_score = 0.5
            elif cur_coverage * 1.5 < avg_coverage:
                perf_score = 0.75

            # TODO handicap
            perf_score *= 1.5

            if self._select_count[idx] < 2:
                perf_score *= 3
            elif self._select_count[idx] < 10:
                perf_score *= 2
            elif self._select_count[idx] < 20:
                perf_score *= 1
            elif self._select_count[idx] < 30:
                perf_score *= 0.8
            else:
                perf_score *= 0.5

            # Adjust score via input depth
            if self._depth[idx] < 3:
                pass
            elif self._depth[idx] < 7:
                perf_score *= 2
            elif self._depth[idx] < 13:
                perf_score *= 3
            elif self._depth[idx] < 24:
                perf_score *= 4
            else:
                perf_score *= 5        

    #        print("RUNS: , Score: ", HVCOV_CYCLE * perf_score / 100 / 1, " ", perf_score)

            if perf_score < 1:
                perf_score = 1
            
            if perf_score > 6400:
                perf_score = 6400

            perf_score = HVCOV_CYCLE * perf_score / 100 / 1 # TODO havoc div
            return perf_score

        elif sched == 2 : # perf_fuzz
            iter = 100 * self._energy[idx]
            if iter < 12:
                iter = 12
            elif iter > 16000:
                iter = 16000

            print("Iter, Energy: ", iter, " ", self._energy[idx])
            return iter
        else: # default score
            return 1000 
