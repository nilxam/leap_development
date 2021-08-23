#!/usr/bin/python3

import argparse
import logging
import sys

from urllib.error import HTTPError

import re
from lxml import etree as ET

import osc.conf
import osc.core

from osc import oscerr
from collections import namedtuple

from osc.util.helper import decode_it

OPENSUSE = 'openSUSE:Leap:15.4'
SLE = 'SUSE:SLE-15-SP4:GA'
SUPPORTED_ARCHS = ['x86_64', 'i586', 'aarch64', 'ppc64le', 's390x']
DEFAULT_REPOSITORY = 'standard'
BINARY_REGEX = r'(?:.*::)?(?P<filename>(?P<name>.*)-(?P<version>[^-]+)-(?P<release>[^-]+)\.(?P<arch>[^-\.]+))'
RPM_REGEX = BINARY_REGEX + r'\.rpm'

META_PACKAGE = '000package-groups'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT


class ObsoletesFinder(object):
    def __init__(self, project, print_only, verbose):
        self.project = project
        self.print_only = print_only
        self.verbose = verbose
        self.apiurl = osc.conf.config['apiurl']
        self.debug = osc.conf.config['debug']

    def is_sle_specific(self, package):
        pkg = package.lower()
        if pkg.startswith('skelcd') or pkg.startswith('release-notes') or\
                pkg.startswith('sle-') or pkg.startswith('sle_'):
            return True
        if 'sles' in pkg or 'sled' in pkg:
            return True
        if 'sap-' in pkg or '-sap' in pkg or pkg.startswith('sap'):
            return True
        if 'eula' in pkg:
            return True
        if pkg.startswith('sle15') or\
                pkg.startswith('sles15') or\
                pkg.startswith('suse-migration') or\
                pkg.startswith('migrate') or\
                pkg.startswith('kernel-livepatch') or\
                pkg.startswith('patterns') or\
                pkg.startswith('supportutils-plugin') or\
                pkg.startswith('lifecycle-data-sle') or\
                pkg.startswith('sca-patterns') or\
                pkg.startswith('susemanager-') or\
                pkg.startswith('desktop-data'):
            return True
        if pkg.endswith('bootstrap') or pkg.endswith('-caasp') or\
                pkg.endswith('-sle'):
            return True
        if pkg == 'suse-build-key' or pkg == 'suse-hpc' or\
                pkg == 'zypper-search-packages-plugin' or\
                pkg == 'python-ibus':
            return True
        return False

    def get_packagelist(self, project, by_project=True):
        """
        Return the list of package's info of a project.
        If the latest package is from an incident then returns incident
        package.
        """

        pkglist = {}
        packageinfo = {}
        query = {'expand': 1}
        root = ET.parse(http_GET(makeurl(self.apiurl, ['source', project],
                                 query=query))).getroot()
        for i in root.findall('entry'):
            pkgname = i.get('name')
            orig_project = i.get('originproject')
            is_incidentpkg = False
            if pkgname.startswith('000') or\
                    pkgname.startswith('_') or\
                    pkgname.startswith('patchinfo.') or\
                    pkgname.startswith('skelcd-') or\
                    pkgname.startswith('installation-images') or\
                    pkgname.endswith('-mini'):
                continue
            # ugly hack for go1.x incidents as the name would be go1.x.xxx
            if '.' in pkgname and re.match(r'[0-9]+$', pkgname.split('.')[-1]) and \
                    orig_project.startswith('SUSE:') and orig_project.endswith(':Update'):
                is_incidentpkg = True
                if pkgname.startswith('go1') or pkgname.startswith('bazel0') or \
                        pkgname.startswith('dotnet') or pkgname.startswith('ruby2'):
                    if not (pkgname.count('.') > 1):
                        is_incidentpkg = False

            # if an incident then update the package origin info
            if is_incidentpkg:
                orig_name = re.sub(r'\.[0-9]+$', '', pkgname)
                incident_number = int(pkgname.split('.')[-1])
                if orig_name in pkglist and pkglist[orig_name]['Project'] == orig_project:
                    if re.match(r'[0-9]+$', pkglist[orig_name]['Package'].split('.')[-1]):
                        old_incident_number = int(pkglist[orig_name]['Package'].split('.')[-1])
                        if incident_number > old_incident_number:
                            pkglist[orig_name]['Package'] = pkgname
                    else:
                        pkglist[orig_name]['Package'] = pkgname
            else:
                pkglist[pkgname] = {'Project': orig_project, 'Package': pkgname}

        if by_project:
            for pkg in pkglist.keys():
                if pkglist[pkg]['Project'].startswith('SUSE:') and self.is_sle_specific(pkg):
                    continue
                if pkglist[pkg]['Project'] not in packageinfo:
                    packageinfo[pkglist[pkg]['Project']] = []
                if pkglist[pkg]['Package'] not in packageinfo[pkglist[pkg]['Project']]:
                    packageinfo[pkglist[pkg]['Project']].append(pkglist[pkg]['Package'])
            return packageinfo

        return pkglist

    def get_project_binary_list(self, project, repository, arch, package_binaries={}):
        """
        Returns binarylist of a project
        """

        if project.startswith('SUSE:'):
            repository = 'pool'

        path = ['build', project, repository, arch]
        url = makeurl(self.apiurl, path, {'view': 'binaryversions'})
        root = ET.parse(http_GET(url)).getroot()

        for binary_list in root:
            package = binary_list.get('package')
            package = package.split(':', 1)[0]
            index = project + "_" + package

            if index not in package_binaries:
                package_binaries[index] = []
            for binary in binary_list:
                filename = binary.get('name')
                result = re.match(RPM_REGEX, filename)
                if not result:
                    continue

                if result.group('arch') == 'src' or result.group('arch') == 'nosrc':
                    continue
                if result.group('name').endswith('-debuginfo') or result.group('name').endswith('-debuginfo-32bit'):
                    continue
                if result.group('name').endswith('-debugsource'):
                    continue

                if result.group('name') not in package_binaries[index]:
                    package_binaries[index].append(result.group('name'))

        return package_binaries

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

    def origin_metadata_get(self, project, package):
        """
        Returns origin infomration
        """

        meta = ET.fromstringlist(osc.core.show_package_meta(self.apiurl, project, package))
        if meta is not None:
            return meta.get('project'), meta.get('name')

        return None, None

    def get_linkinfo(self, project, package):
        """
        Returns package links if it does exist
        """

        query = {'withlinked': 1}
        u = makeurl(self.apiurl, ['source', project, package], query=query)
        root = ET.parse(http_GET(u)).getroot()
        linkinfo = root.find('linkinfo')
        if linkinfo is not None:
            return linkinfo.get('package')

        return package

    def exceptions(self, package):
        """
        Do not skip the package if marches the condition
        """

        if package.startswith('python2') or package.startswith('python3') or \
                package.startswith('preinstallimage-'):
            return True
        if package.endswith('-bootstrap'):
            return True
        if 'Tumbleweed' in package or 'metis' in package:
            return True
        return False

    def source_file_load(self, project, package, filename):
        query = {'expand': 1}
        url = makeurl(self.apiurl, ['source', project, package, filename], query)
        try:
            return decode_it(http_GET(url).read())
        except HTTPError:
            return None

    def source_file_save(self, project, package, filename, content, comment=None):
        url = makeurl(self.apiurl, ['source', project, package, filename], {'comment': comment})
        http_PUT(url, data=content)

    def upload_skip_list(self, project, package, filename, content, comment=None):
        if content != self.source_file_load(project, package, filename):
            self.source_file_save(project, package, filename, content, comment)

    def crawl(self):
        """Main method"""

        leap_pkglist = self.get_packagelist(OPENSUSE)
        sle_pkglist = self.get_packagelist(SLE, by_project=False)
        # the selected_binarylist including the latest sourcepackage list
        # binary RPMs from the latest sources need to be presented in ftp eventually
        selected_binarylist = []
        # all existed binary RPMs from any SPx/Leap/Backports
        fullbinarylist = []
        # package_binaries is a pre-formated binarylist per each package
        package_binaries = {}
        # a packagelist of no build result's package
        # some are SLE fork but build failed
        empty_binarylist_packages = []
        # the extra multibuild packages
        # TODO: this is a ugly hack since multibuild flavor has different
        # capacity on openSUSE and SLE
        extra_multibuilds = ["python-numpy", "openblas", "openmpi", "openmpi2",
                             "openmpi3", "mpich", "mvapich2", "scalapack",
                             "libappindicator", "timescaledb", "pgaudit", "petsc",
                             "lua-lmod", "adios", "gnu-compilers-hpc", "hdf5", "hypre",
                             "imb", "mumps", "netcdf-cxx4", "netcdf-fortran", "netcdf",
                             "ocr", "scotch", "superlu", "trilinos"]
        # inject binarylist to a list per package name no matter what archtectures was
        for arch in SUPPORTED_ARCHS:
            for prj in leap_pkglist.keys():
                package_binaries = self.get_project_binary_list(prj, DEFAULT_REPOSITORY, arch, package_binaries)

        for pkg in package_binaries.keys():
            fullbinarylist += package_binaries[pkg]

        for prj in leap_pkglist.keys():
            for pkg in leap_pkglist[prj]:
                cands = [prj + "_" + pkg]
                if prj.startswith('openSUSE:') and pkg in sle_pkglist and\
                        not 'branding' in pkg:
                    cands.append(sle_pkglist[pkg]['Project'] + "_" + sle_pkglist[pkg]['Package'])
                logging.debug(cands)
                for index in cands:
                    if index in package_binaries:
                        selected_binarylist += package_binaries[index]
                    else:
                        # we only cares empty binarylist in Backports
                        if 'Backports' in prj:
                            empty_binarylist_packages.append(pkg)
                        logging.info("Can not find binary of %s/%s" % (prj, pkg))
        # the additional binary RPMs should be included in ftp
        extra_multibuilds += empty_binarylist_packages
        for pkg in extra_multibuilds:
            if (not self.exceptions(pkg) and self.item_exists(SLE, pkg)):
                oproject, opackage = self.origin_metadata_get(SLE, pkg)
                opackage = self.get_linkinfo(oproject, opackage)
                index = oproject + "_" + opackage
                if index in package_binaries:
                    selected_binarylist += package_binaries[index]

        # a list of binary RPM should filter out from ftp
        obsoleted = []
        for pkg in fullbinarylist:
            if pkg not in selected_binarylist and pkg not in obsoleted and not self.exceptions(pkg):
                # special handling for -release package
                if pkg == 'openSUSE-release' or pkg == 'openSUSE-release-ftp' or\
                        pkg == 'openSUSE-Addon-NonOss-release':
                    continue
                obsoleted.append(pkg)

        # another ugly hack for -32bit and -64bit binary RPM for the obsoleted list
        unneeded = obsoleted.copy()
        for pkg in unneeded:
            if pkg.endswith('-32bit') or pkg.endswith('-64bit'):
                main_filename = re.sub('-[36][24]bit', '', pkg)
                if main_filename not in obsoleted:
                    obsoleted.remove(pkg)

        skip_list = ET.Element('group', {'name': 'NON_FTP_PACKAGES'})
        ET.SubElement(skip_list, 'conditional', {'name': 'drop_from_ftp'})
        packagelist = ET.SubElement(skip_list, 'packagelist', {'relationship': 'requires'})
        for pkg in sorted(obsoleted):
            if self.verbose:
                print(pkg)
            attr = {'name': pkg}
            ET.SubElement(packagelist, 'package', attr)
        if not self.print_only:
            self.upload_skip_list(OPENSUSE, META_PACKAGE, 'NON_FTP_PACKAGES.group',
                                  ET.tostring(skip_list, pretty_print=True, encoding='unicode'),
                                  'Update the skip list')


def main(args):
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = ObsoletesFinder(args.project, args.print_only, args.verbose)
    uc.crawl()


if __name__ == '__main__':
    description = 'Find the obsoleted binary RPMs according to the latest sources'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')
    parser.add_argument('-p', '--project', dest='project', metavar='PROJECT',
                        help='the project where to check (default: %s)' % OPENSUSE,
                        default=OPENSUSE)
    parser.add_argument('-t', '--print-only', action='store_true',
                        help='show the diff')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show the diff')

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
