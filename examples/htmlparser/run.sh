#!/bin/bash

rm log.csv
rm -r seed
cp -r bsd seed

pip3 uninstall -y pythonfuzz
pip3 install ../..

python3 fuzz.py --inf-run seed
#python3 fuzz.py --inf-run --run 4000000
