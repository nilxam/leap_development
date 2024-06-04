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

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class Checks(object):
    def __init__(self, project, verbose, identical):
        self.project = project
        self.verbose = verbose
        self.identical = identical
        self.apiurl = osc.conf.config['apiurl']
        self.debug = osc.conf.config['debug']

    def get_project_binarylist(self, project, repository, arch):
        query = {'view': 'binaryversions'}
        root = ET.parse(http_GET(makeurl(self.apiurl, ['build', project, repository, arch],
                                         query=query))).getroot()
        return root

    def process_project_binarylist(self, project, repository, arch):
        prj_binarylist = self.get_project_binarylist(project, repository, arch)
        files = []
        for package in prj_binarylist.findall('./binaryversionlist'):
            for binary in package.findall('binary'):
                result = re.match(r'(.*)-([^-]*)-([^-]*)\.([^-\.]+)\.rpm', binary.attrib['name'])
                if not result:
                    continue
                bname = result.group(1)
                if bname.endswith('-debuginfo') or bname.endswith('-debuginfo-32bit'):
                    continue
                if bname.endswith('-debugsource'):
                    continue
                if bname.startswith('::import::'):
                    continue
                if result.group(4) == 'src':
                    continue
                files.append(package.attrib['package'].split(':', 1)[0])

        return files

    def crawl(self):
        """Main method"""
        #blist = self.process_project_binarylist('openSUSE:Backports:SLE-15-SP4', 'standard', 'x86_64')
        blist = self.process_project_binarylist('openSUSE:Leap:15.6', 'standard', 'x86_64')
        #root = ET.parse(http_GET(makeurl(self.apiurl, ['source', OPENSUSE, '000package-groups', 'NON_FTP_PACKAGES.group']))).getroot()
        ll = http_GET(makeurl(self.apiurl, ['source', OPENSUSE, '000package-groups', 'NON_FTP_PACKAGES.group'])).read().decode('utf-8')
        x = ll.index("</group>")
        aa = ll[:x+8]
        root = ET.fromstring(aa)
        obsoleted_pkglist = [i.get('name') for i in root.findall('packagelist/package')]

        for p in obsoleted_pkglist:
            print(p)

def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = Checks(args.project, args.verbose, args.identical)
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
