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

    def crawl(self):
        """Main method"""
        #root = http_GET(makeurl(self.apiurl, ['source', OPENSUSE, '000package-groups', 'NON_FTP_PACKAGES.group'])).read()
        filter_file = http_GET(makeurl(self.apiurl, ['source', OPENSUSE, '000product', 'NON_FTP_PACKAGES.group'])).read().decode('utf-8')
        endindex = filter_file.index("</group>")
        filter_list = filter_file[:endindex+8]
        root = ET.fromstring(filter_list)
        obsoleted_pkglist = [i.get('name') for i in root.findall('packagelist/package')]
        for arch in ['aarch64', 'ppc64le', 's390x', 'x86_64']:
            print("====== %s =====" % arch)
            filename = 'Leap-dvd5-dvd-' + arch + '.kiwi'
            root = ET.parse(http_GET(makeurl(self.apiurl, ['source', OPENSUSE, '000product', filename]))).getroot()
            shiping_pkglist = [i.get('name') for i in root.findall('instsource/repopackages/repopackage')]
            for p in shiping_pkglist:
                if p in obsoleted_pkglist:
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
