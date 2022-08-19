#!/usr/bin/python3

import argparse
import logging
import sys
import subprocess
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
BACKPORTS_UPDATE = 'openSUSE:Backports:SLE-15-SP4:Update'
SLE = 'SUSE:SLE-15-SP5:GA'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class UpdateFinder(object):
    def __init__(self, project, bp_only, submit):
        self.project = project
        self.bp_only = bp_only
        self.submit = submit
        self.apiurl = osc.conf.config['apiurl']
        self.debug = osc.conf.config['debug']

    def get_source_packages(self, project, expand=False, deleted=False, with_project_name=False):
        """Return the list of packages in a project."""
        query = {}
        if expand:
            query['expand'] = 1
        if deleted:
            query['deleted'] = 1
        root = ET.parse(http_GET(makeurl(self.apiurl, ['source', project],
                                 query=query))).getroot()
        if with_project_name:
            packages = [[project, i.get('name')] for i in root.findall('entry')]
        else:
            packages = [i.get('name') for i in root.findall('entry')]

        return packages

    def get_request_list(self, project, package):
        return osc.core.get_request_list(self.apiurl, project, package, req_state=('new', 'review'))

    def has_package_modified(self, project, package):
        return osc.core.get_request_list(self.apiurl, project, package, req_state=('accepted', ))

    def package_version(self, project, package):
        try:
            url = makeurl(self.apiurl, ['source', project, package, '_history'], {'limit': 1})
            root = ET.parse(http_GET(url)).getroot()
        except HTTPError as e:
            if e.code == 404:
                return False

            raise e

        return str(root.find('./revision/version').text)

    def package_vercmp(self, ver1, ver2):
        cmd = "rpmdev-vercmp %s %s" % (ver1, ver2)
        prun = subprocess.run(cmd, shell=True, capture_output=True, encoding='utf-8')
        vcmp = prun.stdout.strip()
        if '>' in vcmp:
            return 1
        elif '<' in vcmp:
            return -1
        return 0

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
        return False

    def do_check(self, project, update_project, package, sle_pkglist, deleted_pkglist, cmp_pkglist):
        if package.startswith('patchinfo') or package.count('.') > 1:
            return
        if package in sle_pkglist:
            logging.debug("%s exist in SLE" % package)
            return
        if package.startswith('rubygem') or package.startswith('Leap-release'):
            return
        target_pkg = self.parse_package_link(update_project, package)
        if package in cmp_pkglist:
            req_record = self.has_package_modified(project, package)
            if req_record and (req_record[len(req_record)-1].actions[0].src_project != update_project and \
                               req_record[len(req_record)-1].actions[0].src_package != target_pkg):
                logging.debug("%s has got updated from other place, skip!" % package)
                return
            if target_pkg and not self.parse_package_link(update_project, target_pkg, True) and\
                    self.has_diff(project, package, update_project, target_pkg):
                if self.get_request_list(project, target_pkg):
                    logging.debug("There is a request to %s / %s already or it has been revoked, skip!" % (project, target_pkg))
                else:
                    new_ver = self.package_version(update_project, target_pkg)
                    old_ver = self.package_version(project, package)
                    if self.package_vercmp(new_ver, old_ver) >= 0:
                        if self.submit:
                            print("Submitting %s/%s to %s/%s" %
                                    (update_project, target_pkg, project, package))
                            self.do_submit(update_project, target_pkg, project, package)
                        else:
                            print("eval \"osc sr -m '%s has different source in %s/%s' %s %s %s %s\"" %
                                    (package, update_project, target_pkg, update_project, target_pkg, project, package))
        else:
            if target_pkg and package not in deleted_pkglist:
                if self.submit:
                    print("Submitting %s/%s to %s/%s" %
                            (update_project, update_project, target_pkg, project, package))
                    self.do_submit(update_project, target_pkg, project, package)
                else:
                    print("eval \"osc sr -m 'New package in %s' %s %s %s %s\"" %
                            (update_project, update_project, target_pkg, project, package))

    def do_submit(self, src_project, src_package, dst_project, dst_package):
        """Create a submit request."""

        msg = "Automatically create request by update submitter. \
               This is going to update package to %s from %s. \
               Please review this change and decline it if Leap do not need it." % (dst_project, src_project)
        res = osc.core.create_submit_request(self.apiurl,
                                             src_project,
                                             src_package,
                                             dst_project,
                                             dst_package,
                                             message=msg)
        return res

    def crawl(self):
        """Main method"""
        # get souce packages from Leap/Backports update
        os_update_pkglist = self.get_source_packages(OPENSUSE_UPDATE, with_project_name=True)
        bp_update_pkglist = self.get_source_packages(BACKPORTS_UPDATE, with_project_name=True)
        # get souce packages from SLE
        sle_pkglist = self.get_source_packages(SLE, True)
        # get souce packages from Leap
        os_pkglist = self.get_source_packages(OPENSUSE)
        os_deleted_pkglist = self.get_source_packages(OPENSUSE, deleted=True)
        # get souce packages from Backports
        bp_pkglist = self.get_source_packages(BACKPORTS)
        bp_deleted_pkglist = self.get_source_packages(BACKPORTS, deleted=True)

        if not self.bp_only:
            for pkg in os_update_pkglist:
                if pkg[1] in bp_pkglist:
                    bp_update_pkglist.append([OPENSUSE_UPDATE, pkg[1]])
                    continue
                self.do_check(OPENSUSE, pkg[0], pkg[1], sle_pkglist, os_deleted_pkglist, os_pkglist)

        for pkg in bp_update_pkglist:
            self.do_check(BACKPORTS, pkg[0], pkg[1], sle_pkglist, bp_deleted_pkglist, bp_pkglist)

def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = UpdateFinder(args.project, args.bp_only, args.submit)
    uc.crawl()

if __name__ == '__main__':
    description = 'Find update candidates from the last SP Update'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')
    parser.add_argument('-p', '--project', dest='project', metavar='PROJECT',
                        help='the project where to check (default: %s)' % OPENSUSE,
                        default=OPENSUSE)
    parser.add_argument('-b', '--bp-only', action='store_true',
                        help='Check Backports project only')
    parser.add_argument('-s', '--submit', dest='submit', action='store_true',
                        help='Submit updates to Backports project')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    sys.exit(main(args))
