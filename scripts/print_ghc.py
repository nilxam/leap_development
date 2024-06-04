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

OPENSUSE = 'openSUSE:Leap:15.6'
FACTORY = 'openSUSE:Factory'
OPENSUSE_UPDATE = 'openSUSE:Leap:15.5:Update'
BACKPORTS = 'openSUSE:Backports:SLE-15-SP6'
SLEFORKS = 'openSUSE:Backports:SLE-15-SP6:SLEFork'
SLE = 'SUSE:SLE-15-SP6:GA'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class FindSLE(object):
    def __init__(self, project, verbose):
        self.project = project
        self.verbose = verbose
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
        except HTTPError as e:
            if e.code == 404:
                return False
            else:
                raise e
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

    def get_prj_results(self, prj, arch, code='failed'):
        url = makeurl(self.apiurl, ['build', prj, "_result?arch=x86_64&repository=standard&view=status"])
        results = []

        root = ET.parse(http_GET(url)).getroot()

        xmllines = root.findall("./result/status")

        for pkg in xmllines:
            if code == 'failed':
                if pkg.attrib['code'] == 'failed' or pkg.attrib['code'] == 'unresolvable':
                    if ':' not in pkg.attrib['package']:
                        results.append(pkg.attrib['package'])
            if code == 'succeeded':
                if pkg.attrib['code'] == 'succeeded':
                    if ':' not in pkg.attrib['package']:
                        results.append(pkg.attrib['package'])

        return results

    def crawl(self):
        """Main method"""
        # get souce packages from Factory
        rebuild_pkglist = self.get_source_packages('home:mlin7442:rebuild_fails_156:cinnamon')
        bp_pkglist = self.get_source_packages(BACKPORTS)
        leap_pkglist = self.get_source_packages(OPENSUSE)
        for pkg in rebuild_pkglist:
            if pkg in bp_pkglist:
                print("eval \"osc sr -m 'Package update from %s/%s' %s %s %s %s\"" %
                      (FACTORY, pkg, FACTORY, pkg, BACKPORTS, pkg))
            else:
                if pkg in leap_pkglist:
                    print("eval \"osc sr -m 'Package update from %s/%s' %s %s %s %s\"" %
                          (FACTORY, pkg, FACTORY, pkg, OPENSUSE, pkg))
                else:
                    print("eval \"osc sr -m 'New package from %s/%s' %s %s %s %s\"" %
                          (FACTORY, pkg, FACTORY, pkg, BACKPORTS, pkg))



def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    if args.project is None:
        print("Please pass --project argument. See usage with --help.")
        quit()

    uc = FindSLE(args.project, args.verbose)
    uc.crawl()

if __name__ == '__main__':
    description = 'Compare packages status between two project'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')
    parser.add_argument('-p', '--project', dest='project', metavar='PROJECT',
                        help='the target project where do submit to')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show the diff')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
