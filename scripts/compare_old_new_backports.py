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

OPENSUSE = 'openSUSE:Leap:15.4'
OPENSUSE_UPDATE = 'openSUSE:Leap:15.3:Update'
NEW_BACKPORTS = 'openSUSE:Backports:SLE-15-SP4'
OLD_BACKPORTS = 'openSUSE:Backports:SLE-15-SP3'
SLE = 'SUSE:SLE-15-SP4:GA'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class FindBP(object):
    def __init__(self, project, verbose, identical):
        self.project = project
        self.verbose = verbose
        self.identical = identical
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

    def origin_metadata_get(self, project, package):
        meta = ET.fromstringlist(osc.core.show_package_meta(self.apiurl, project, package))
        if meta is not None:
            return meta.get('project'), meta.get('name')

        return None, None

    def is_links(self, project, package, reverse=False):
        query = {'withlinked': 1}
        u = makeurl(self.apiurl, ['source', project, package], query=query)
        root = ET.parse(http_GET(u)).getroot()
        links = root.findall('linkinfo/linked')
        linkinfo = None
        if reverse and links:
            return True
        if not links:
            return False

        for linked in links:
            if linked.get('project') == project:
                return True
        return False

    def crawl(self):
        """Main method"""
        # get souce packages from SLE
        sle_pkglist = self.get_source_packages(SLE, True)
        # get souce packages from backports
        new_bp_pkglist = self.get_source_packages(NEW_BACKPORTS)
        old_bp_pkglist = self.get_source_packages(OLD_BACKPORTS)
        newadded_pkglist = []
        deleted_pkglist = []

        for pkg in old_bp_pkglist:
            if pkg.startswith('patchinfo') or pkg.startswith('00'):
                continue
            if pkg not in new_bp_pkglist:
                if pkg in sle_pkglist:
                    continue
                deleted_pkglist.append(pkg)
                print("%s got deleted" % (pkg))

        print("==============================")

        for pkg in new_bp_pkglist:
            if pkg.startswith('patchinfo') or pkg.startswith('00'):
                continue
            if pkg not in old_bp_pkglist:
                newadded_pkglist.append(pkg)
                print("%s got added" % (pkg))


def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = FindBP(args.project, args.verbose, args.identical)
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
    parser.add_argument('-i', '--identical', action='store_true',
                        help='show identical package')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show the diff')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
