#!/usr/bin/python3

import argparse
import logging
import sys
try:
    from urllib.error import HTTPError
except ImportError:
    # python 2.x
    from urllib2 import HTTPError

import re
from xml.etree import cElementTree as ET

import osc.conf
import osc.core

from osc import oscerr

OPENSUSE = 'openSUSE:Leap:15.3'
BACKPORTS = 'openSUSE:Backports:SLE-15-SP3'
SLE = 'SUSE:SLE-15-SP3:GA'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class FindBP(object):
    def __init__(self, project, verbose, wipe):
        self.project = project
        self.verbose = verbose
        self.wipe = wipe
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

    def item_exists(self, project, package=None):
        """
        Return true if the given project or package exists
        """
        if package:
            url = makeurl(self.apiurl, ['source', project, package, '_meta'])
        else:
            url = makeurl(self.apiurl, ['source', project, '_meta'])
        try:
            http_GET(url)
        except HTTPError:
            return False
        return True

    def get_filename(self, project, package, repo, arch, binary):
        query = {}
        query['view'] = 'fileinfo'
        bname = ET.parse(http_GET(makeurl(self.apiurl, ['build', project, repo, arch, package, binary], query=query))).getroot().find('name').text

        return bname

    def has_noarchrpm(self, project, package, repo, arch):
        root = ET.parse(http_GET(makeurl(self.apiurl, ['build', project, repo, arch, package]))).getroot()
        rpms = [i.get('filename') for i in root.findall('binary')]
        ignores = ['_buildenv', '_statistics', 'rpmlint.log']
        result = False
        binarylist = []

        if len(rpms) > 0:
            for r in rpms:
                if r.endswith('.rpm') and not r.endswith('.src.rpm'):
                    bname = self.get_filename(project, package, repo, arch, r)
                    binarylist.append(bname)
                if r.endswith('.noarch.rpm'):
                    result = True
                if r.startswith('::') or r in ignores:
                    continue

        if result:
            return binarylist
        else:
            return []

    def do_wipe_package(self, project, package, repository=None):
        self._wipe_package(project, package, repository)

        url = makeurl(self.apiurl, ['source', project, package], { 'view': 'getmultibuild' })
        f = http_GET(url)
        root = ET.parse(f).getroot()
        for entry in root.findall('entry'):
            self._wipe_package(project, package + ":" + entry.get('name'), repository)

    def switch_flag_in_pkg(self, project, package, flag='build', state='disable', repository=None, arch=None):
        query = { 'cmd': 'set_flag', 'flag': flag, 'status': state }
        if repository:
            query['repository'] = repository
        if arch:
            query['arch'] = arch
        url = makeurl(self.apiurl, ['source', project, package], query)
        http_POST(url)

    def crawl(self):
        """Main method"""
        # get souce packages from SLE
        sle_pkglist = self.get_source_packages(SLE, True)
        # ecl.txt including the excluded/disabled flavor package in Backports
        with open('ecl.txt') as f:
            bp_pkglist = f.read().splitlines()

        archs = ['ppc64le', 's390x', 'aarch64']
        drop_list = []

        for pkg in bp_pkglist:
            if pkg.startswith('patchinfo') or pkg.startswith('preinstallimage') or pkg.startswith('elixir') or \
                    pkg.startswith('python2'):
                continue
            opkg_name = pkg
            if ':' in pkg:
                opkg_name = pkg.split(':')[0]
            if opkg_name in sle_pkglist:
                for arch in archs:
                    binarylist = self.has_noarchrpm(BACKPORTS, pkg, 'standard', arch)
                    if len(binarylist):
                        if pkg not in drop_list:
                            drop_list.append(pkg)
                        print("=== %s/%s ===" % (pkg, arch))
                        for r in binarylist:
                            print(r)
        # dump drop_list
        print('Package need to drop or being disabled in Backports')
        for d in drop_list:
            print(d)


def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = FindBP(args.project, args.verbose, args.wipe)
    uc.crawl()

if __name__ == '__main__':
    description = 'Compare packages status between two project'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')
    parser.add_argument('-p', '--project', dest='project', metavar='PROJECT',
                        help='the project where to check (default: %s)' % OPENSUSE,
                        default=OPENSUSE)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show the diff')
    parser.add_argument('-f', '--wipe', action='store_true',
                        help='disable package and wipe binaries')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
