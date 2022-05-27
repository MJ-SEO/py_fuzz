import random
import copy
import struct

from . import dictionnary

try:
    from random import _randbelow
except ImportError:
    from random import _inst
    _randbelow = _inst._randbelow

INTERESTING8 = [-128, -1, 0, 1, 16, 32, 64, 100, 127]
INTERESTING16 = [0, 128, 255, 256, 512, 1000, 1024, 4096, 32767, 65535]
INTERESTING32 = [0, 1, 32768, 65535, 65536, 100663045, 2147483647, 4294967295]

Deterministic = 12
Havoc = 18

class Mutator:
    def __init__(self, max_size=4096, max_arith=35, dict_path = None, parent_conn = None):
        self._max_input_size = max_size
        self._max_arith = max_arith
        self._dict = dictionnary.Dictionary(dict_path)
        self._deter_nm = Deterministic
        self._havoc_nm = Havoc
        self._deter_idx = 0
        self._parent_conn = parent_conn

    @staticmethod
    def _rand(n):
        if n < 2:
            return 0
        return _randbelow(n)

    # Exp2 generates n with probability 1/2^(n+1).
    @staticmethod
    def _rand_exp():
        rand_bin = bin(random.randint(0, 2**32-1))[2:]
        rand_bin = '0'*(32 - len(rand_bin)) + rand_bin
        count = 0
        for i in rand_bin:
            if i == '0':
                count +=1
            else:
                break
        return count

    @staticmethod
    def _choose_len(n):
        x = Mutator._rand(100)
        if x < 90:
            return Mutator._rand(min(8, n)) + 1
        elif x < 99:
            return Mutator._rand(min(32, n)) + 1
        else:
            return Mutator._rand(n) + 1

    @staticmethod
    def copy(src, dst, start_source, start_dst, end_source=None, end_dst=None):
        end_source = len(src) if end_source is None else end_source
        end_dst = len(dst) if end_dst is None else end_dst
        byte_to_copy = min(end_source-start_source, end_dst-start_dst)
        dst[start_dst:start_dst+byte_to_copy] = src[start_source:start_source+byte_to_copy] 

    def cut_and_run(self, res, fuzz_loop):
        if len(res) > self._max_input_size:
            res = res[:self._max_input_size]
        
#        with open("detinp.csv", "a") as log_file:
#            log_file.write("%s\n" %(res))

        fuzz_loop(res, self._parent_conn)


    def could_be_bitflip(self, diff):
        if diff == 0 :
            return False
        
        while not (diff & 0x1):
            diff = diff >> 1

        # if 1, 2, 4 bit flip
        if diff == 0x1 or diff == 0x3 or diff == 0xf:
            return True

        # if 8bit flip
        if diff == 0xff:
            return True

        return False

    # helper function to pack as little and big endian and assign
    def assign(self, res, buf, pos, endian, n_bytes):
        for i in range(n_bytes):
            res[pos + i] = (buf[pos + i] + endian[i]) % 256
    
    # add value to res and return added value
    def add_assign(self, res, pos, n_bytes, val, positive=True):
        if positive is True:
            mult = 1
        else:
            mult = -1
        tot = 0
        for i in range(n_bytes):
            tot = (tot << 8) + res[pos + i]

        tot = tot + mult * val
        return tot

    def mutate_det(self, buf, fuzz_loop):
        if self._dict is None :
            num_mutation = self._deter_nm-2
        else:
            num_mutation = self._deter_nm

        res = copy.deepcopy(buf)
        for index in range(len(buf)):
            for x in range(num_mutation):
                #res = buf[:]
                if x == 0:
                    # Bit flip. Spooky!
                    if len(res) == 0:
                        continue
                    pos = index
                    for bit in range(8):
                        res[pos] = buf[pos] ^ (1 << bit)
                        self.cut_and_run(res, fuzz_loop)
                elif x == 1:
                    # 2 Bit flip
                    # print("2 bit flipping")
                    n_bit = 2
                    mask = 0x03
                    if len(res) == 0:
                        continue
                    pos = index
                    for bit in range(7):
                        res[pos] = buf[pos] ^ (mask << bit)
                        self.cut_and_run(res, fuzz_loop)
                elif x == 2:
                    # 4 Bit flip
                    # print("4 bit flipping")
                    n_bit = 2
                    mask = 0x0f
                    if len(res) == 0:
                        continue
                    pos = index
                    for bit in range(4):
                        res[pos] = buf[pos] ^ (mask << bit)
                        self.cut_and_run(res, fuzz_loop)
                elif x == 3:
                    # 8 Bit flip
                    # print("8 bit flipping")
                    n_bit = 2
                    mask = 0xff
                    if len(res) == 0:
                        continue
                    pos = index
                    res[pos] = buf[pos] ^ mask
                    self.cut_and_run(res, fuzz_loop)
                elif x == 4:
                    # print("replace interesting byte")
                    # Replace a byte with an interesting value.
                    if len(res) == 0:
                        continue
                    pos = index
                    for interest8 in INTERESTING8:
                        res[pos] = interest8 % 256
                        if not self.could_be_bitflip(res[pos] ^ buf[pos]) :
                            self.cut_and_run(res, fuzz_loop)
                elif x == 5:
                    # print("replace interesting 2 byte")
                    # Replace an uint16 with an interesting value.
                    if len(res) < 2 or len(res) - 2 < index:
                        continue
                    pos = index
                    for interest16 in INTERESTING16:
                        # Big endian interest16
                        big_endian = struct.pack('>H', interest16)
                        self.assign(res, buf, pos, big_endian, 2)
                        self.cut_and_run(res, fuzz_loop)

                        # Little endian interest16
                        little_endian = struct.pack('<H', interest16)
                        self.assign(res, buf, pos, little_endian, 2)
                        self.cut_and_run(res, fuzz_loop)
                    res = copy.deepcopy(buf)             
                elif x == 6:
                    # print("replace interesting 4 byte")
                    # Replace an uint32 with an interesting value.
                    if len(res) < 4 or len(res) - 4 < index:
                        continue
                    pos = index
                    for interest32 in INTERESTING32:
                        # Big endian interest32
                        big_endian = struct.pack('>I', interest32)
                        self.assign(res, buf, pos, big_endian, 4)
                        self.cut_and_run(res, fuzz_loop)

                        # Little endian interest32
                        little_endian = struct.pack('<I', interest32)
                        self.assign(res, buf, pos, little_endian, 4)
                        self.cut_and_run(res, fuzz_loop)
                    res = copy.deepcopy(buf)
                elif x == 7:
                    # Replace an ascii digit with another digit.
                    if len(res) <= index:
                        continue
                    pos = index
                    if ord('0') <= buf[pos] <= ord('9'):
                        for i in range(10):
                            if i is buf[pos] - ord('0'):
                                continue
                            res[pos] = ord('0') + i
                        
                            if not self.could_be_bitflip(res[pos] ^ buf[pos]) :
                                self.cut_and_run(res, fuzz_loop)
                elif x == 8:
                    # Add/subtract from a byte.
                    if len(res) == 0:
                        continue
                    pos = index
                    for v in range(self._max_arith):
                        # Arithmetic + MAX_ARITH big endian
                        res[pos] = (buf[pos] + v) % 256
                        if not self.could_be_bitflip(res[pos] ^ buf[pos]) :
                            self.cut_and_run(res, fuzz_loop)

                        # Arithmetic  - MAX_ARITH
                        res[pos] = (buf[pos] - v) % 256
                        if not self.could_be_bitflip(res[pos] ^ buf[pos]) :
                            self.cut_and_run(res, fuzz_loop)
                        self.cut_and_run(res, fuzz_loop)  # Why?
                elif x == 9:
                    # print("add/subtract 2 byte")
                    # Add/subtract from a uint16.
                    if len(res) < 2 or len(res) - 2 < index:
                        continue

                    pos = index
                    for v in range(self._max_arith):
                        # Add
                        val_16 = self.add_assign(buf, pos, 2, v, True) % 0xffff
                        big_endian = struct.pack('>H', val_16)
                        self.assign(res, buf, pos, big_endian, 2)
                        self.cut_and_run(res, fuzz_loop)

                        little_endian = struct.pack('<H', val_16)
                        self.assign(res, buf, pos, little_endian, 2)
                        self.cut_and_run(res, fuzz_loop)
                        
                        # Subtract
                        val_16 = self.add_assign(buf, pos, 2, v, False) % 0xffff
                        big_endian = struct.pack('>H', val_16)
                        self.assign(res, buf, pos, big_endian, 2)
                        self.cut_and_run(res, fuzz_loop)
                        
                        little_endian = struct.pack('<H', val_16)
                        self.assign(res, buf, pos, little_endian, 2)
                        self.cut_and_run(res, fuzz_loop)
                    res = copy.deepcopy(buf)
                elif x == 10:
                    # Insert Dictionary word
                    dict_word = self._dict.get_word()
                    if dict_word is None:
                        continue
                    pos = index
                    n = len(dict_word)
                    for k in range(n):
                        res.append(0)
                    self.copy(buf, res, pos, pos+n)
                    for k in range(n):
                        res[pos+k] = dict_word[k]
                    self.cut_and_run(res, fuzz_loop)
                    res = copy.deepcopy(buf)
                elif x == 11:
                    # Replace with Dictionary word
                    dict_word = self._dict.get_word()
                    
                    if(dict_word == None or len(res) < len(dict_word) or index > len(res) - len(dict_word)):
                        continue
                    
                    pos = index
                    self.copy(dict_word, res, 0, pos)
                    self.cut_and_run(res, fuzz_loop)
                    res = copy.deepcopy(buf)
                '''

                    '''
              
    
    def mutate_havoc(self, buf, corpus):
        res = buf[:]
        nm = self._rand_exp()
        for i in range(nm+1):
            x = self._rand(self._havoc_nm)
            if x == 0:
                # Remove a range of bytes
                if len(res) <= 1:
                    i -= 1
                    continue
                pos0 = self._rand(len(res))
                pos1 = pos0 + self._choose_len(len(res) - pos0)
                self.copy(res, res, pos1, pos0)
                res = res[:len(res) - (pos1-pos0)]
            elif x == 1:
                # Insert a range of random bytes.
                pos = self._rand(len(res) + 1)
                n = self._choose_len(10)
                for k in range(n):
                    res.append(0)
                self.copy(res, res, pos, pos+n)
                for k in range(n):
                    res[pos+k] = self._rand(256)
            elif x == 2:
                # Insert an Interesting8
                pos = self._rand(len(res) + 1)
                n = 1
                v = random.choice(INTERESTING8)
                res.append(0)
                self.copy(res, res, pos, pos+n)
                res[pos] = v % 256
            elif x == 3:
                # Insert an Interesting16
                pos = self._rand(len(res) + 1)
                n = 2
                v = random.choice(INTERESTING16)
                if bool(random.getrandbits(1)):
                    v = struct.pack('>H', v)
                else:
                    v = struct.pack('<H', v) 
                for k in range(n):
                    res.append(0)
                self.copy(res, res, pos, pos+n)
                for k in range(n):
                    res[pos+k] = v[k] % 256
            elif x == 4:
                # Insert an Interesting32
                pos = self._rand(len(res) + 1)
                n = 4
                v = random.choice(INTERESTING32)
                if bool(random.getrandbits(1)):
                    v = struct.pack('>I', v)
                else:
                    v = struct.pack('<I', v)
                for k in range(n):
                    res.append(0)
                self.copy(res, res, pos, pos+n)
                for k in range(n):
                    res[pos+k] = v[k] % 256
            elif x == 5:
                # Duplicate a range of bytes.
                if len(res) <= 1:
                    i -= 1
                    continue
                src = self._rand(len(res))
                dst = self._rand(len(res))
                while src == dst:
                    dst = self._rand(len(res))
                n = self._choose_len(len(res) - src)
                tmp = bytearray(n)
                self.copy(res, tmp, src, 0)
                for k in range(n):
                    res.append(0)
                self.copy(res, res, dst, dst+n)
                for k in range(n):
                    res[dst+k] = tmp[k]
            elif x == 6:
                # Copy a range of bytes.
                if len(res) <= 1:
                    i -= 1
                    continue
                src = self._rand(len(res))
                dst = self._rand(len(res))
                while src == dst:
                    dst = self._rand(len(res))
                n = self._choose_len(len(res) - src)
                self.copy(res, res, src, dst, src+n)
            elif x == 7:
                # Bit flip. Spooky!
                if len(res) == 0:
                    i -= 1
                    continue
                pos = self._rand(len(res))
                res[pos] ^= 1 << self._rand(8)
            elif x == 8:
                # Set a byte to a random value.
                if len(res) == 0:
                    i -= 1
                    continue
                pos = self._rand(len(res))
                res[pos] ^= self._rand(255) + 1
            elif x == 9:
                # Swap 2 bytes.
                if len(res) <= 1:
                    i -= 1
                    continue
                src = self._rand(len(res))
                dst = self._rand(len(res))
                while src == dst:
                    dst = self._rand(len(res))
                    res[src], res[dst] = res[dst], res[src]
            elif x == 10:
                # Byte flip. Spooky!
                if len(res) == 0:
                    i -= 1
                    continue
                pos = self._rand(len(res))
                res[pos] ^= 0xff
            elif x == 11:
                # 2 Byte flip. Spooky!
                if len(res) < 2:
                    return res
                pos = self._rand(len(res) - 1)
                res[pos] ^= 0xff
                res[pos+1] ^= 0xff
            elif x == 12:
                # Add/subtract from a byte.
                if len(res) == 0:
                    i -= 1
                    continue
                pos = self._rand(len(res))
                v = self._rand(2 ** 8)
                res[pos] = (res[pos] + v) % 256
            elif x == 13:
                # Add/subtract from a uint16.
                if len(res) < 2:
                    i -= 1
                    continue
                pos = self._rand(len(res) - 1)
                v = self._rand(2 ** 16)
                if bool(random.getrandbits(1)):
                    v = struct.pack('>H', v)
                else:
                    v = struct.pack('<H', v)
                res[pos] = (res[pos] + v[0]) % 256
                res[pos + 1] = (res[pos] + v[1]) % 256
            elif x == 14:
                # Add/subtract from a uint32.
                if len(res) < 4:
                    i -= 1
                    continue
                pos = self._rand(len(res) - 3)
                v = self._rand(2 ** 32)
                if bool(random.getrandbits(1)):
                    v = struct.pack('>I', v)
                else:
                    v = struct.pack('<I', v)
                res[pos] = (res[pos] + v[0]) % 256
                res[pos + 1] = (res[pos + 1] + v[1]) % 256
                res[pos + 2] = (res[pos + 2] + v[2]) % 256
                res[pos + 3] = (res[pos + 3] + v[3]) % 256
            elif x == 15:
                # Add/subtract from a uint64.
                if len(res) < 8:
                    i -= 1
                    continue
                pos = self._rand(len(res) - 7)
                v = self._rand(2 ** 64)
                if bool(random.getrandbits(1)):
                    v = struct.pack('>Q', v)
                else:
                    v = struct.pack('<Q', v)
                res[pos] = (res[pos] + v[0]) % 256
                res[pos + 1] = (res[pos + 1] + v[1]) % 256
                res[pos + 2] = (res[pos + 2] + v[2]) % 256
                res[pos + 3] = (res[pos + 3] + v[3]) % 256
                res[pos + 4] = (res[pos + 4] + v[4]) % 256
                res[pos + 5] = (res[pos + 5] + v[5]) % 256
                res[pos + 6] = (res[pos + 6] + v[6]) % 256
                res[pos + 7] = (res[pos + 7] + v[7]) % 256
            elif x == 16:
                # splicing(insert)
                target = corpus._inputs[self._rand(len(corpus._inputs))]
                if len(target) == 0:
                    return res
                src = self._rand(len(target))
                dst = self._rand(len(res))
                n = self._choose_len(len(target) - src)
                for k in range(n):
                    res.append(0)
                self.copy(res, res, dst, dst+n)
                for k in range(n):
                    res[dst+k] = target[src+k]
            elif x == 17:
                # splicing(replace)
                target = corpus._inputs[self._rand(len(corpus._inputs))]
                if len(target) == 0:
                    return res
                src = self._rand(len(target))
                dst = self._rand(len(res))
                short_len  = len(target) - src if len(target) - src < len(res) - dst else len(res) - dst
                n = self._choose_len(short_len)
                self.copy(target, res, src, dst, src+n)

        if len(res) > self._max_input_size:
            res = res[:self._max_input_size]
        return res 
