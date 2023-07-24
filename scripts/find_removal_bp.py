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

OPENSUSE = 'openSUSE:Leap:15.5'
OPENSUSE_UPDATE = 'openSUSE:Leap:15.4:Update'
BACKPORTS = 'openSUSE:Backports:SLE-15-SP5'
SLEFORK = 'openSUSE:Backports:SLE-15-SP5:SLEFork'
SLE = 'SUSE:SLE-15-SP5:GA'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class FindSLE(object):
    def __init__(self, project, verbose, check_slefork):
        self.project = project
        self.verbose = verbose
        self.check_slefork = check_slefork
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

    def has_diff(self, project, package, target_prj, target_pkg):
        changes_file = package + ".changes"
        query = {'cmd': 'diff',
                 'view': 'xml',
                 'file': changes_file,
                 'oproject': project,
                 'opackage': package}
        u = makeurl(self.apiurl, ['source', target_prj, target_pkg], query=query)
        root = ET.parse(http_POST(u)).getroot()
        if root:
            # check if it has diff element
            diffs = root.findall('files/file/diff')
            if diffs:
                return True
        return False

    def get_filelist_for_package(self, pkgname, project, expand=None, extension=None):
        filelist = []
        query = {}
        if extension:
            query['extension'] = extension
        if expand:
            query['expand'] = expand

        if len(query):
            url = makeurl(self.apiurl, ['source', project, pkgname], query=query)
        else:
            url = makeurl(self.apiurl, ['source', project, pkgname])
        try:
            content = http_GET(url).read()
            for entry in ET.fromstring(content).findall('entry'):
                filelist.append(entry.attrib['name'])
        except HTTPError as err:
            if err.code == 404 or err.code == 400:
                # The package we were supposed to query does not exist
                # or the sources are broken (as we link into branches it can happen)
                # we can pass this up and return the empty filelist
                return []
            raise err
        return filelist

    def crawl(self):
        """Main method"""
        # get souce packages from SLE
        sle_pkglist = self.get_source_packages(SLE, True)
        # get souce packages from backports
        bp_pkglist = self.get_source_packages(BACKPORTS)
        slefork_pkglist = self.get_source_packages(SLEFORK)
        ignored_multibuilds = []

        # Backports
        for pkg in bp_pkglist:
            if pkg not in sle_pkglist:
                continue
            if pkg in slefork_pkglist:
                continue
            filelist = self.get_filelist_for_package(pkgname=pkg, project=BACKPORTS, expand='1')
            if '_multibuild' in filelist:
                ignored_multibuilds.append(pkg)
                continue

            print("eval \"osc rebuildpac -r standard %s %s\"" % (BACKPORTS, pkg))
            #print("eval \"osc dr -m 'Package %s does exist in SLE' %s %s\"" % (pkg, BACKPORTS, pkg))

        print("\nIgnored Multibuilds:")
        for p in ignored_multibuilds:
            print(p)


def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = FindSLE(args.project, args.verbose, args.check_slefork)
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
    parser.add_argument('-s', '--check-slefork', action='store_true',
                        help='check SLEFork project')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
