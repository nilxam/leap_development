#!/usr/bin/python3

import argparse
import logging
import sys

adi = []
bp = []

file1 = open('/tmp/rebuild_deepin', 'r')
count = 0

while True:
    count += 1

    line = file1.readline()

    if not line:
        break
    adi.append(line.strip())

file1.close()

file2 = open('/tmp/devel_deepin', 'r')
count = 0

while True:
    count += 1

    line = file2.readline()

    if not line:
        break
    bp.append(line.strip())

file2.close()

diff = set(bp) - set(adi)
for i in sorted(list(diff)):
    print(i)
