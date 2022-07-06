#!/usr/bin/python3

import repomd

# Get Leap released packages
repo = repomd.load('http://download.opensuse.org/distribution/leap/15.4/repo/oss/')
bp_repo = repomd.load('http://download.opensuse.org/repositories/openSUSE:/Backports:/SLE-15-SP3/standard/')

packages = {}
bp_packages = {}

for p in repo:
    if p.arch not in packages:
        packages[p.arch] = []
    if p.name not in packages[p.arch] and '-bp154.' not in p.nevr and '-lp154.' not in p.nevr:
        packages[p.arch].append(p.name)

for p in bp_repo:
    if p.arch not in bp_packages:
        bp_packages[p.arch] = []
    # Ignore package if Leap no longer ships
    if p.name not in bp_packages[p.arch] and p.arch in packages and p.name in packages[p.arch]:
        bp_packages[p.arch].append(p.name)

# SLE released packages database from rpmlint-backports-data
FILES = ['sle-product-packages-x86_64', 'sle-product-packages-aarch64',
        'sle-product-packages-ppc64le', 'sle-product-packages-s390x']

for file in FILES:
    finput = open(file, 'r')

    while True:
        line = finput.readline()

        if not line:
            break
        if line.strip() in bp_packages[file.split('-')[3]]:
            bp_packages[file.split('-')[3]].remove(line.strip())
        if line.strip() in bp_packages['noarch']:
            bp_packages['noarch'].remove(line.strip())

    finput.close()

for arch in bp_packages:
    print("=== %s ===" % arch)
    for pkg in sorted(bp_packages[arch]):
        print(pkg)
    print("\n")

