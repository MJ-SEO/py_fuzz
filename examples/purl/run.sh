#!/bin/bash

rm log.csv
rm -r seed
cp -r bsd seed

pip install ../..

python3 fuzz.py --inf-run --run 4000000 seed
#python3 fuzz.py --inf-run --run 4000000
