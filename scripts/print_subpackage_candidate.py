#!/usr/bin/python3

import repomd

# Get Leap released binary packages
repo = repomd.load('http://download.opensuse.org/distribution/leap/15.6/repo/oss/')

packages = {}

for p in repo:
    if p.arch not in packages:
        packages[p.arch] = []
    if p.name not in packages[p.arch] and '-bp156.' not in p.nevr and '-lp156.' not in p.nevr:
        packages[p.arch].append(p.name)

# The extracted SLE15 released packages from rpmlint-backports-data
FILES = ['sle-product-packages-x86_64', 'sle-product-packages-aarch64',
        'sle-product-packages-ppc64le', 'sle-product-packages-s390x']

for file in FILES:
    finput = open(file, 'r')

    while True:
        line = finput.readline()

        if not line:
            break
        if line.strip() in packages[file.split('-')[3]]:
            packages[file.split('-')[3]].remove(line.strip())
        if line.strip() in packages['noarch']:
            packages['noarch'].remove(line.strip())

    finput.close()

for arch in packages:
    print("=== %s ===" % arch)
    for pkg in sorted(packages[arch]):
        print(pkg)
    print("\n")

