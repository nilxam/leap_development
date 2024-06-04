#!/usr/bin/python3

import argparse
import logging
import sys
import time

from urllib.error import HTTPError, URLError

import random
import re
from xml.etree import cElementTree as ET

import osc.conf
import osc.core
from osclib.core import devel_project_get
from osclib.core import project_pseudometa_package

from osc import oscerr
from osclib.memoize import memoize

BACKPORTS = 'openSUSE:Backports:SLE-15-SP6'
OPENSUSE = 'openSUSE:Leap:15.6'
SLE = 'SUSE:SLE-15-SP6:GA'
REBUILD_PROJECT = '{}:FactoryCandidates'.format(BACKPORTS)
FACTORYFORK = '{}:FactoryFork'.format(BACKPORTS)
SUPPORTED_ARCHS = ['x86_64']
FACTORY = 'openSUSE:Factory'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class FccFreezer(object):
    def __init__(self, freeze_rebuild):
        self.apiurl = osc.conf.config['apiurl']
        self.debug = osc.conf.config['debug']
        self.freeze_rebuild = freeze_rebuild

    def list_packages(self, project):
        url = makeurl(self.apiurl, ['source', project])
        pkglist = []

        root = ET.parse(http_GET(url)).getroot()
        xmllines = root.findall("./entry")
        for pkg in xmllines:
            pkglist.append(pkg.attrib['name'])

        return set(pkglist)

    def get_source_packages(self, project, expand=False):
        """Return the list of packages in a project."""
        query = {}
        if expand:
            query['expand'] = 1
        root = ET.parse(http_GET(makeurl(self.apiurl, ['source', project],
                                 query=query))).getroot()
        packages = [i.get('name') for i in root.findall('entry')]

        return packages

    def check_one_source(self, flink, si, pkglist, os_pkglist, ignored_pkgs, sle_pkglist, bp_pkglist, factory_srcmd5, bp_srcmd5, factoryfork_pkglist):
        """
        Insert package information to the temporary frozenlinks.
        Return package name if the package can not fit the condition
        add to the frozenlinks, can be the ignored package.
        """
        package = si.get('package')
        logging.debug("Processing %s" % (package))

        # If the package is an internal one (e.g _product)
        if package.startswith('_') or package.startswith('Test-DVD') or package.startswith('000') or package.startswith('preinstallimage'):
            return None

        if 'tumbleweed' in package or 'branding' in package:
            return package

        if package in ignored_pkgs:
            return package

        # filter out multibuild package
        for originpackage in si.findall('originpackage'):
            if ':' in package and package.split(':')[0] == originpackage.text:
                return package

        if self.freeze_rebuild:
            if package in sle_pkglist:
                return package
            #if package in factoryfork_pkglist:
            #    return package
            if package in bp_srcmd5 and factory_srcmd5[package] == bp_srcmd5[package]:
                return package

        for linked in si.findall('linked'):
            if linked.get('project') == FACTORY:
                url = makeurl(self.apiurl, ['source', FACTORY, package], {'view': 'info', 'nofilename': '1'})
                f = http_GET(url)
                proot = ET.parse(f).getroot()
                lsrcmd5 = proot.get('lsrcmd5')
                if lsrcmd5 is None:
                    raise Exception("{}/{} is not a link but we expected one".format(FACTORY, package))
                ET.SubElement(flink, 'package', {'name': package, 'srcmd5': lsrcmd5, 'vrev': si.get('vrev')})
                return None

        if package in ['rpmlint-mini-AGGR']:
            # we should not freeze aggregates
            return None

        ET.SubElement(flink, 'package', {'name': package, 'srcmd5': si.get('srcmd5'), 'vrev': si.get('vrev')})
        return None

    def sources_to_ignore(self, flink):
        ignored_sources = []
        os_pkglist = self.get_source_packages(OPENSUSE, True)
        pkglist = self.get_source_packages(FACTORY)
        sle_pkglist = self.get_source_packages(SLE, True)
        bp_pkglist = self.get_source_packages(BACKPORTS)
        factoryfork_pkglist = self.get_source_packages(FACTORYFORK)
        factory_srcmd5 = {}
        bp_srcmd5 = {}

        url = makeurl(self.apiurl, ['source', FACTORY], {'view': 'info', 'nofilename': '1'})
        f = http_GET(url)
        root = ET.parse(f).getroot()

        for si in root.findall('sourceinfo'):
            factory_srcmd5[si.get('package')] = [si.get('verifymd5')]

        url = makeurl(self.apiurl, ['source', BACKPORTS], {'view': 'info', 'nofilename': '1'})
        f = http_GET(url)
        root2 = ET.parse(f).getroot()
        for si in root2.findall('sourceinfo'):
            bp_srcmd5[si.get('package')] = [si.get('verifymd5')]

        ignored_pkgs = []
        ignored_develprjs = ['KDE:Applications', 'KDE:Qt5', 'devel:languages:haskell', 'devel:kubic', 'KDE:Frameworks5', 'mozilla:Factory', 'KDE:Qt:5.15', 'devel:languages:ruby:extensions', 'security:SELinux', 'devel:languages:rust', 'science:HPC', 'devel:tools:building', 'server:php:extensions', 'devel:CaaSP', 'devel:CaaSP:Head:ControllerNode', 'system:install:head', 'mobile:synchronization:FACTORY', 'Java:Factory', 'devel:languages:javascript', 'devel:languages:ruby', 'Base:System', 'windows:mingw:win32', 'Java:packages', 'Virtualization:containers:images', 'X11:Pantheon', 'Virtualization:Appliances:Images:openSUSE-Tumbleweed', 'Application:ERP:GNUHealth:Factory', 'devel:languages:python:jupyter', 'devel:languages:python:azure', 'devel:languages:python:aws', 'Cloud:OpenStack:Factory', 'devel:languages:python:flask', 'devel:languages:python:avocado', 'devel:languages:python:django', 'devel:languages:python:aliyun', 'devel:languages:python:pytest', 'devel:languages:python:pyramid', 'server:monitoring', 'server:monitoring:zabbix','server:monitoring:thruk','server:monitoring:gearman', 'windows:mingw:win64', 'Application:Dochazka', 'devel:languages:python:numeric', 'science:machinelearning', 'Emulators', 'devel:openQA:tested', 'electronics', 'Publishing:TeXLive', 'devel:languages:python', 'devel:languages:lua', 'devel:languages:ocaml', 'X11:Cinnamon:Factory', 'devel:gcc']

        for prj in ignored_develprjs:
            ignored_pkgs = ignored_pkgs + self.get_source_packages(prj)

        for si in root.findall('sourceinfo'):
            package = self.check_one_source(flink, si, pkglist, os_pkglist, ignored_pkgs, sle_pkglist, bp_pkglist, factory_srcmd5, bp_srcmd5, factoryfork_pkglist)
            if package is not None:
                ignored_sources.append(str(package))
        return ignored_sources

    def freeze(self, project):
        """Main method"""
        print('freezing {}'.format(project))
        flink = ET.Element('frozenlinks')

        fl = ET.SubElement(flink, 'frozenlink', {'project': FACTORY})
        ignored_sources = self.sources_to_ignore(fl)
        if self.debug:
            logging.debug("Dump ignored source")
            for source in ignored_sources:
                logging.debug("Ignored source: %s" % source)

        url = makeurl(self.apiurl, ['source', project, '_project', '_frozenlinks'], {'meta': '1'})
        l = ET.tostring(flink)

        try:
            http_PUT(url, data=l)
        except HTTPError as e:
            raise e

    def has_diff(self, project, package, target_prj, target_pkg):                                                                                 
        # if package does not exist in taget project return True
        if not self.item_exists(target_prj, target_pkg):
            return True
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

    def create_submitrequest(self, src_project, package, dst_project):
        """Create a submit request using the osc.commandline.Osc class."""

        if not self.has_diff(src_project, package, dst_project, package):
            return None

        msg = ("Automatically create request by update submitter."
               "This is going to update package to %s from %s."
               "Please review this change and decline it if Leap do not need it." % (dst_project, src_project))
        res = osc.core.create_submit_request(self.apiurl,
                                             src_project,
                                             package,
                                             dst_project,
                                             package,
                                             message=msg)
        return res

    def get_request_list(self, project):
        return osc.core.get_request_list(self.apiurl, project, req_state=('new', 'review', 'declined', 'revoked'))

    def check_multiple_specfiles(self, project, package):
        try:
            url = makeurl(self.apiurl, ['source', project, package], { 'expand': '1' } )
        except HTTPError as e:
            if e.code == 404:
                return None
            raise e
        root = ET.fromstring(http_GET(url).read())
        data = {}
        linkinfo = root.find('linkinfo')
        if linkinfo is not None:
            data['linkinfo'] = linkinfo.attrib['package']
        else:
            data['linkinfo'] = None

        files = [ entry.get('name').replace('.spec', '') for entry in root.findall('entry') if entry.get('name').endswith('.spec') ]
        data['specs'] = files

        if len(files) > 1:
            return data
        else:
            return False

    def get_build_succeeded_packages(self, project, arch):
        """Get the build succeeded packages from `from_prj` project.
        """
        buildresult = osc.core.show_prj_results_meta(self.apiurl, REBUILD_PROJECT)
        root = ET.fromstringlist(buildresult)
        failed_multibuild_pacs = []
        pacs = []
        for node in root.findall('result'):
            if node.get('repository') == 'standard' and node.get('arch') == arch:
                for pacnode in node.findall('status'):
                    if ':' in pacnode.get('package'):
                        mainpac = pacnode.get('package').split(':')[0]
                        if pacnode.get('code') not in ['succeeded', 'excluded']:
                            failed_multibuild_pacs.append(pacnode.get('package'))
                            if mainpac not in failed_multibuild_pacs:
                                failed_multibuild_pacs.append(mainpac)
                            if mainpac in pacs:
                                pacs.remove(mainpac)
                        else:
                            if mainpac in failed_multibuild_pacs:
                                failed_multibuild_pacs.append(pacnode.get('package'))
                            elif mainpac not in pacs:
                                pacs.append(mainpac)
                        continue
                    if pacnode.get('code') == 'succeeded':
                        pacs.append(pacnode.get('package'))
                    else:
                        failed_multibuild_pacs.append(pacnode.get('package'))

        return pacs

    def list_pkgs(self):
        """List build succeeded packages"""
        for arch in SUPPORTED_ARCHS:
            succeeded_packages = self.get_build_succeeded_packages(REBUILD_PROJECT, arch)
            if not len(succeeded_packages) > 0:
                logging.info('No build succeeded package in %s/%s' % (REBUILD_PROJECT,arch))
                return

            print('Build succeeded packages for %s:' % arch)
            print('-------------------------------------')
            for pkg in sorted(succeeded_packages):
                print(pkg)

            print('-------------------------------------')
            print("Found {} build succeded packages for {}".format(len(succeeded_packages), arch))

    def send_updates(self):
        pending_requests = [r.actions[0].tgt_package for r in self.get_request_list(BACKPORTS)]
        ms_packages = []
        succeeded_packages = self.get_build_succeeded_packages(REBUILD_PROJECT, 'x86_64')
        for package in sorted(succeeded_packages):
            to_submit = True

            multi_specs = self.check_multiple_specfiles(FACTORY, package)
            if multi_specs is None:
                logging.debug('%s does not exist in %s' % (package, 'openSUSE:Factory'))
                to_submit = False

            if multi_specs:
                if multi_specs['linkinfo']:
                    logging.debug('%s in %s is sub-package of %s, skip it!' % (package, 'openSUSE:Factory', multi_specs['linkinfo']))
                    ms_packages.append(package)
                    to_submit = False

                for spec in multi_specs['specs']:
                    if spec not in succeeded_packages:
                        logging.debug('%s is sub-pacakge of %s but build failed, skip it!' % (spec, package))
                        to_submit = False

            if not to_submit:
                continue

            if package not in pending_requests:
                res = self.create_submitrequest(FACTORY, package, BACKPORTS)
                if res and res is not None:
                    logging.info('Created request %s for %s' % (res, package))
                else:
                    logging.error('Error occurred when creating submit request for %s' % package)
            else:
                logging.info('%s has a pending submission on %s or it has been declined/revoked, skip!' % (package, BACKPORTS))
            time.sleep(5)

        # dump multi specs packages
        print("Multi-specfile packages:")
        if len(ms_packages) > 0:
            for pkg in ms_packages:
                print(pkg)
        else:
            print('None')


def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    freezer = FccFreezer(args.freeze_rebuild)
    if args.list_packages:
        freezer.list_pkgs()
    elif args.submit:
        freezer.send_updates()
    elif args.freeze_rebuild:
        freezer.freeze(REBUILD_PROJECT)

if __name__ == '__main__':
    description = 'Backports FactoryCandidates/SLECandidates freezer'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')
    parser.add_argument('-l', '--list', dest='list_packages', action='store_true', help='list build succeeded packages')
    parser.add_argument('-f', '--freeze', dest='freeze_rebuild', action='store_true', help='update frozenlinks of RebuildFactoryCandidates')
    parser.add_argument('-s', '--submit', dest='submit', action='store_true', help='submit updates from Factory to Backports')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
