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

BINARY_REGEX = r'(?:.*::)?(?P<filename>(?P<name>.*)-(?P<version>[^-]+)-(?P<release>[^-]+)\.(?P<arch>[^-\.]+))'
RPM_REGEX = BINARY_REGEX + r'\.rpm'

class SLEMover(object):
    def __init__(self, opensuse_project, sle_project, print_full):
        self.upload_project = opensuse_project
        self.opensuse_project = opensuse_project
        self.sle_project = sle_project
        self.print_full = print_full
        self.apiurl = osc.conf.config['apiurl']
        self.debug = osc.conf.config['debug']

    def get_source_packages(self, project, expand=False):
        """Return the list of packages in a project."""
        query = {}
        if expand:
            query['expand'] = 1
        root = ET.parse(http_GET(makeurl(self.apiurl, ['source', project],
                                 query=query))).getroot()
        packages = [i.get('name') for i in root.findall('entry')]

        return packages

    def get_project_binary_list(self, project, repository, arch, package_binaries={}):
        """
        Returns binarylist of a project
        """

        # Use pool repository for SUSE namespace project.
        # Because RPMs were injected to pool repository on OBS rather than
        # standard repository.
        if project.startswith('SUSE:'):
            repository = 'pool'

        path = ['build', project, repository, arch]
        url = makeurl(self.apiurl, path, {'view': 'binaryversions'})
        root = ET.parse(http_GET(url)).getroot()

        for binary_list in root:
            package = binary_list.get('package')
            package = package.split(':', 1)[0]
            index = package + "_" + arch

            if index not in package_binaries:
                package_binaries[index] = []
            for binary in binary_list:
                filename = binary.get('name')
                result = re.match(RPM_REGEX, filename)
                if not result:
                    continue

                if not self.print_full:
                    if result.group('arch') == 'src' or result.group('arch') == 'nosrc':
                        continue
                    if result.group('name').endswith('-debuginfo') or result.group('name').endswith('-debuginfo-32bit'):
                        continue
                    if result.group('name').endswith('-debugsource'):
                        continue

                if result.group('name') not in package_binaries[index]:
                    package_binaries[index].append(result.group('name'))

        return package_binaries

    def crawl(self):
        """Main method"""

        leap_pkglist = self.get_source_packages(self.opensuse_project)
        sle_pkglist = self.get_source_packages(self.sle_project, True)
        package_binaries = {}

        inter_pkglist = set(leap_pkglist) & set(sle_pkglist)

        # Inject binarylist to a list per package name no matter what archtectures was
        for arch in SUPPORTED_ARCHS:
            package_binaries = self.get_project_binary_list(self.opensuse_project, DEFAULT_REPOSITORY, arch, package_binaries)

        for pkg in sorted(inter_pkglist):
            print("Name: %s" % pkg)
            for arch in SUPPORTED_ARCHS:
                if pkg + "_" + arch in package_binaries:
                    print("--- %s ---" % arch)
                    print("\n".join(package_binaries[pkg + "_" + arch]))
            print("\n")

def main(args):
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    if args.opensuse_project is None or args.sle_project is None:
        print("Please pass --opensuse-project and --sle-project argument. See usage with --help.")
        quit()

    uc = SLEMover(args.opensuse_project, args.sle_project, args.print_full)
    uc.crawl()


if __name__ == '__main__':
    description = 'Lists overlap package between Backports and SLE, and its binaries.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')
    parser.add_argument('-o', '--opensuse-project', dest='opensuse_project', metavar='OPENSUSE_PROJECT',
                        help='openSUSE project on buildservice')
    parser.add_argument('-s', '--sle-project', dest='sle_project', metavar='SLE_PROJECT',
                        help='SLE project on buildservice')
    parser.add_argument('-f', '--print-full', action='store_true',
                        help='show full RPMs including src, debuginfo and debugsource')

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
