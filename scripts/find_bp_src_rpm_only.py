#!/usr/bin/python3

import argparse
import logging
import sys
from urllib.error import HTTPError

import re
from xml.etree import cElementTree as ET

import osc.conf
import osc.core

from osc import oscerr

OPENSUSE = 'openSUSE:Leap:15.3'
OPENSUSE_UPDATE = 'openSUSE:Leap:15.2:Update'
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

    def src_rpm_only(self, project, package, repo, arch):
        try:
            root = ET.parse(http_GET(makeurl(self.apiurl, ['build', project, repo, arch, package]))).getroot()
        except HTTPError as e:
            if e.code == 404:
                print("No build result found: %s" % package)
                return False

            raise e

        rpms = [i.get('filename') for i in root.findall('binary')]
        result = True

        if len(rpms) > 0:
            for r in rpms:
                if not r.endswith('.rpm') or r.startswith('::'):
                    continue
                else:
                    if not (r.endswith('.src.rpm') or '-doc' in r or '-lang' in r or r.startswith('python2')):
                        result = False
        else:
            result = False

        return result

    def _wipe_package(self, project, package, repository):
        url = makeurl(self.apiurl, ['build', project], {'cmd': 'wipe', 'package': package, 'repository': repository})
        try:
            http_POST(url)
        except HTTPError as e:
            print(e.read())
            raise e

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
        # get souce packages from backports
        bp_pkglist = self.get_source_packages(BACKPORTS)

        for pkg in bp_pkglist:
            if pkg.startswith('patchinfo') or pkg.startswith('preinstallimage') or pkg.startswith('elixir') or \
                    pkg.startswith('python2'):
                continue
            if pkg in sle_pkglist:
                if self.src_rpm_only(BACKPORTS, pkg, 'standard', 'x86_64') and \
                        self.src_rpm_only(BACKPORTS, pkg, 'standard', 'aarch64'):
                    if self.wipe:
                        self.switch_flag_in_pkg(BACKPORTS, pkg, flag='build', state='disable', repository='standard')
                        self.do_wipe_package(BACKPORTS, pkg, repository='standard')
                    print("Package exists in SLE and was produced src.rpm only in %s %s" % (BACKPORTS, pkg))


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
    parser.add_argument('-w', '--wipe', action='store_true',
                        help='disable package and wipe binaries')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
