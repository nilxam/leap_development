#!/usr/bin/python3

import argparse
import logging
import sys

from urllib.error import HTTPError

import re
from lxml import etree as ET
from collections import namedtuple

import osc.conf
import osc.core
from osc.core import http_GET
from osc.core import makeurl
from osc import oscerr

SUPPORTED_ARCHS = ['x86_64', 'aarch64', 'ppc64le', 's390x']
DEFAULT_REPOSITORY = 'standard'
BACKPORTS = "openSUSE:Backports:SLE-16.1"

BINARY_REGEX = r'(?:.*::)?(?P<filename>(?P<name>.*)-(?P<version>[^-]+)-(?P<release>[^-]+)\.(?P<arch>[^-\.]+))'
RPM_REGEX = BINARY_REGEX + r'\.rpm'

class Mover(object):
    def __init__(self):
        self.apiurl = osc.conf.config['apiurl']
        self.debug = osc.conf.config['debug']

    def get_project_binary_list(self, project, repository, arch, package_binaries={}):
        """
        Returns binarylist of a project
        """
        path = ['build', project, repository, arch]
        url = makeurl(self.apiurl, path, {'view': 'binaryversions'})
        root = ET.parse(http_GET(url)).getroot()

        for binary_list in root:
            package = binary_list.get('package')
            for binary in binary_list:
                index = package
                if index not in package_binaries:
                    package_binaries[index] = []

                filename = binary.get('name')
                result = re.match(RPM_REGEX, filename)
                if not result:
                    continue

                if result.group('arch') == 'src' or result.group('arch') == 'nosrc':
                    continue
                if result.group('name').endswith('-debuginfo') or result.group('name').endswith('-debuginfo-32bit'):
                    continue
                if result.group('name').endswith('-debugsource'):
                    continue

                if result.group('name') and result.group('name') not in package_binaries[index]:
                    package_binaries[index].append(result.group('name'))

        return package_binaries

    def crawl(self):
        """Main method"""

        package_binaries = {}
        # Inject binarylist to a list per package name no matter what archtectures was
        for arch in SUPPORTED_ARCHS:
            package_binaries = self.get_project_binary_list(BACKPORTS, DEFAULT_REPOSITORY, arch, package_binaries)

            for pkg in package_binaries:
                if pkg.startswith('mozc'):
                    print(pkg + "-" + arch)
                    print("==========")
                    for p in package_binaries[pkg]:
                        print(p)
                    print()
                if pkg.startswith('openblas'):
                    print(pkg + "-" + arch)
                    print("==========")
                    for p in package_binaries[pkg]:
                        print(p)
                    print()
                if pkg.startswith('lapack'):
                    print(pkg + "-" + arch)
                    print("==========")
                    for p in package_binaries[pkg]:
                        print(p)
                    print()

def main(args):
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = Mover()
    uc.crawl()


if __name__ == '__main__':
    description = 'Simple script'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
