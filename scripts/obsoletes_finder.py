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
from collections import namedtuple

OPENSUSE = 'openSUSE:Leap:15.4'
SLE = 'SUSE:SLE-15-SP4:GA'
SUPPORTED_ARCHS = ['x86_64', 'i586', 'aarch64', 'ppc64le', 's390x']
DEFAULT_REPOSITORY = 'standard'
BINARY_REGEX = r'(?:.*::)?(?P<filename>(?P<name>.*)-(?P<version>[^-]+)-(?P<release>[^-]+)\.(?P<arch>[^-\.]+))'
RPM_REGEX = BINARY_REGEX + r'\.rpm'

makeurl = osc.core.makeurl
http_GET = osc.core.http_GET
http_POST = osc.core.http_POST
http_PUT = osc.core.http_PUT

class ObsoletesFinder(object):
    def __init__(self, project, verbose):
        self.project = project
        self.verbose = verbose
        self.apiurl = osc.conf.config['apiurl']
        self.debug = osc.conf.config['debug']

    def get_packageinfo(self, project, expand=False):
        """Return the list of packages in a project."""
        pkglist = {}
        packageinfo = {}
        query = {}
        if expand:
            query['expand'] = 1
        root = ET.parse(http_GET(makeurl(self.apiurl, ['source', project],
                                 query=query))).getroot()
        for i in root.findall('entry'):
            pkgname = i.get('name')
            orig_project = i.get('originproject')
            is_incidentpkg = False
            if pkgname.startswith('00') or pkgname.startswith('_') or \
                    pkgname.startswith('patchinfo.'):
                continue
            # ugly hack for go1.x incidents as the name would be go1.x.xxx
            if '.' in pkgname and re.match(r'[0-9]+$', pkgname.split('.')[-1]) and \
                    orig_project.startswith('SUSE:') and orig_project.endswith(':Update'):
                is_incidentpkg = True
                if pkgname.startswith('go1') or pkgname.startswith('bazel0') or \
                        pkgname.startswith('dotnet') or pkgname.startswith('ruby2'):
                    if not (pkgname.count('.') > 1):
                        is_incidentpkg = False

            # If is an incident then update the package origin info
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

        for pkg in pkglist.keys():
            if pkglist[pkg]['Project'] not in packageinfo:
                packageinfo[pkglist[pkg]['Project']] = []
            if pkglist[pkg]['Package'] not in packageinfo[pkglist[pkg]['Project']]:
                packageinfo[pkglist[pkg]['Project']].append(pkglist[pkg]['Package'])

        return packageinfo

    def get_project_binary_list(self, project, repository, arch, package_binaries = {}):
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
        meta = ET.fromstringlist(osc.core.show_package_meta(self.apiurl, project, package))
        if meta is not None:
            return meta.get('project'), meta.get('name')

        return None, None

    def get_linkinfo(self, project, package):
        query = {'withlinked': 1}
        u = makeurl(self.apiurl, ['source', project, package], query=query)
        root = ET.parse(http_GET(u)).getroot()
        linkinfo = root.find('linkinfo')
        if linkinfo is not None:
            return linkinfo.get('package')

        return package

    def exception_list(self, package):
        if package.startswith('python2') or package.startswith('python3') or \
                package.startswith('preinstallimage-'):
            return True
        if package.endswith('-bootstrap'):
            return True
        if 'Tumbleweed' in package or 'metis' in package:
            return True
        return False

    def crawl(self):
        """Main method"""
        leap_pkglist = self.get_packageinfo(OPENSUSE, expand=1)
        # the selected_binarylist from the latest sources
        # these binary RPMs need to be presented in ftp eventually
        # no more binary RPM than this list
        selected_binarylist = []
        # any existed binary RPM
        fullbinarylist = []
        # package_binaries is a pre-formated binarylist per each package
        package_binaries = {}
        # empty binarylist of a packagelist
        # some are build failed SLE fork
        empty_binarylist_packages = []
        # extra multibuild packages
        extra_multibuilds = ["python-numpy", "openblas", "openmpi", "openmpi2",
                "openmpi3", "mpich", "mvapich2", "scalapack",
                "libappindicator", "timescaledb", "pgaudit", "petsc",
                "lua-lmod", "adios", "gnu-compilers-hpc", "hdf5", "hypre",
                "imb", "mumps", "netcdf-cxx4", "netcdf-fortran", "netcdf",
                "ocr", "scotch", "superlu", "trilinos"]
        for arch in SUPPORTED_ARCHS:
            for prj in leap_pkglist.keys():
                package_binaries = self.get_project_binary_list(prj, DEFAULT_REPOSITORY, arch, package_binaries)

        for pkg in package_binaries.keys():
            fullbinarylist += package_binaries[pkg]

        for prj in leap_pkglist.keys():
            for pkg in leap_pkglist[prj]:
                index = prj + "_" + pkg
                if index in package_binaries:
                    selected_binarylist += package_binaries[index]
                else:
                    if 'Backports' in prj:
                        empty_binarylist_packages.append(pkg)
                    logging.info("Can not find binary of %s/%s" % (prj, pkg))
        # the additional binary RPMs
        extra_multibuilds += empty_binarylist_packages
        for pkg in extra_multibuilds:
            if (not self.exception_list(pkg) and self.item_exists(SLE, pkg)):
                oproject, opackage = self.origin_metadata_get(SLE, pkg)
                opackage = self.get_linkinfo(oproject, opackage)
                index = oproject + "_" + opackage
                if index in package_binaries:
                    selected_binarylist += package_binaries[index]

        unneeded = []
        for pkg in fullbinarylist:
            if pkg not in selected_binarylist and pkg not in unneeded:
                if not self.exception_list(pkg):
                    unneeded.append(pkg)
                    if self.verbose:
                        print(pkg)

def main(args):
    # Configure OSC
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    uc = ObsoletesFinder(args.project, args.verbose)
    uc.crawl()

if __name__ == '__main__':
    description = 'Find obsoleted binary RPM according to the latest sources'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')
    parser.add_argument('-p', '--project', dest='project', metavar='PROJECT',
                        help='the project where to check (default: %s)' % OPENSUSE,
                        default=OPENSUSE)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show the diff')

    args = parser.parse_args()

    # Set logging configuration
    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
