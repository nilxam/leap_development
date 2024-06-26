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

OPENSUSE = 'openSUSE:Leap:15.6'
OPENSUSE_UPDATE = 'openSUSE:Leap:15.5:Update'
BACKPORTS = 'openSUSE:Backports:SLE-15-SP6'
SLEFORK = 'openSUSE:Backports:SLE-15-SP6:SLEFork'
SLE = 'SUSE:SLE-15-SP6:GA'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class SLESync(object):
    def __init__(self, project, check_slefork):
        self.project = project
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

    def parse_package_link(self, project, package, reverse=False):
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
            linkinfo = linked.get('package')
            if linked.get('project') == project and linked.get('package').startswith("%s." % package):
                return linkinfo
            else:
                return None
        return False

    def crawl(self):
        """Main method"""
        # get souce packages from SLE
        sle_pkglist = self.get_source_packages(SLE, True)
        # get souce packages from backports
        bp_pkglist = self.get_source_packages(BACKPORTS)
        os_pkglist = self.get_source_packages(OPENSUSE)
        slefork_pkglist = self.get_source_packages(SLEFORK)

        # special handling for the python stack renaming, incident number 29613
        for pkg in sle_pkglist:
            if pkg.endswith('.29613') and not pkg.startswith('patchinfo'):
                old_name = re.sub('^python3','python', pkg).replace('.29613', '')
                if old_name in bp_pkglist and self.has_diff(SLE, pkg, BACKPORTS, old_name):
                    print("eval \"osc copypac -e -m 'Package update from %s/%s' %s %s %s %s\"" %
                          (SLE, pkg, SLE, pkg, BACKPORTS, old_name))
                if old_name in os_pkglist and self.has_diff(SLE, pkg, OPENSUSE, old_name):
                    print("eval \"osc copypac -e -m 'Package update from %s/%s' %s %s %s %s\"" %
                          (SLE, pkg, SLE, pkg, OPENSUSE, old_name))

        # Backports
        for pkg in bp_pkglist:
            if pkg.startswith('patchinfo'):
                continue
            if pkg in sle_pkglist:
                if self.has_diff(SLE, pkg, BACKPORTS, pkg):
                    orig_prj, orig_pkg = self.origin_metadata_get(SLE, pkg)
                    src_pkg = self.parse_package_link(orig_prj, orig_pkg)
                    # python311 stack update
                    if src_pkg and (src_pkg.endswith('.30661') or src_pkg.endswith('.30963')):
                        continue
                    if self.check_slefork and (src_pkg in slefork_pkglist or orig_pkg in slefork_pkglist):
                        continue
                    if orig_prj != SLE:
                        if src_pkg:
                            print("eval \"osc copypac -e -m 'Package update from %s/%s' %s %s %s %s\"" %
                                    (orig_prj, src_pkg, orig_prj, src_pkg, BACKPORTS, pkg))
                        if orig_prj.endswith(':GA'):
                            logging.debug("Package %s got overrided in %s %s" % (orig_pkg, BACKPORTS, pkg))
                    else:
                        print("eval \"osc copypac -e -m 'Package update from %s/%s' %s %s %s %s\"" %
                                (SLE, pkg, SLE, pkg, BACKPORTS, pkg))

        # Leap
        for pkg in os_pkglist:
            if pkg.startswith('patchinfo'):
                continue
            if pkg in sle_pkglist:
                if self.has_diff(SLE, pkg, OPENSUSE, pkg):
                    orig_prj, orig_pkg = self.origin_metadata_get(SLE, pkg)
                    if orig_prj != SLE:
                        src_pkg = self.parse_package_link(orig_prj, orig_pkg)
                        # python311 stack update
                        if src_pkg and (src_pkg.endswith('.30661') or src_pkg.endswith('.30963')):
                            continue
                        if src_pkg:
                            print("eval \"osc copypac -e -m 'Package update from %s/%s' %s %s %s %s\"" %
                                    (orig_prj, src_pkg, orig_prj, src_pkg, OPENSUSE, pkg))
                        if orig_prj.endswith(':GA'):
                            logging.debug("Package %s got overrided in %s %s" % (orig_pkg, OPENSUSE, pkg))
                    else:
                        print("eval \"osc copypac -e -m 'Package update from %s/%s' %s %s %s %s\"" %
                                (SLE, pkg, SLE, pkg, OPENSUSE, pkg))

def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = SLESync(args.project, args.check_slefork)
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
    parser.add_argument('-s', '--check-slefork', action='store_true',
                        help='check SLEFork project')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
