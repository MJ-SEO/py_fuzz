import collections
from random import random
import sys
from time import sleep, time

start = time()

mydic = collections.defaultdict(set)
mydic['one'] = 1
mydic['one'] = 2

#mydic['one'].insert(1)

#mydic['one'] += 1
#mydic['one'].add(('fname1,3'))
#mydic['one'].add(('fname1,2'))
#mydic['one'].add(('fname2,1,2'))

print(list(mydic))
print(len(mydic))
print(mydic['one'])


cdic = dict()
cdic['1'] = 0 #[] # key - coverage
cdic['2'] = 0 #[] # key - coverage
#cdic['3'] = [] # key - coverage

#cdic['1'].append("zz") #
#cdic['1'].append("zz") #
#cdic['2'].append("zz") #
#cdic['3'].append("zz") #
#cdic['1'].append("zz")

cdic['1'] = cdic['1'] + 1
cdic['1'] = cdic['1'] + 1
cdic['1'] = cdic['1'] + 1
cdic['2'] = cdic['2'] + 1

#len(cdic['1']) # hit count
#.append(mydic['one'])

print("=================")

print(cdic['1'])
print(cdic.keys())
print(cdic.values())
#print(cdic['2'].count('zz'))
#print(cdic['1'].index('zz'))
#print(sum(map(len, cdic.values())))


#print(a['one'].pop)

#sleep(1)

end = time()

t = end - start

print(end - start)

print(random())

numbers = ['one', 'two', 'three', 'four', 'five']

for n in numbers:
    print(n)

print("========================")

while True:
    for i in range(10):
        for j in range(10):
            print(i+j)
            if i + j == 18:
                break
        else:
            continue
        break
    else:
        continue
    break

    