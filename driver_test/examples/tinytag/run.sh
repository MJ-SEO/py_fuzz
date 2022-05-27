#!/bin/bash

rm log.csv
rm -r seed
cp -r bsd seed

pip uninstall -y pythonfuzz
pip install ../..

python fuzzbp.py --inf-run seed 
#python3 fuzz.py --inf-run --run 4000000
