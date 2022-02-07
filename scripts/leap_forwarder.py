#!/usr/bin/python3

import argparse
import logging
import sys

from urllib.error import HTTPError

import re

import osc.conf
import osc.core
from osc.core import http_GET
from osc.core import makeurl
from osc.core import get_review_list
from osc.core import print_comments
from osc.core import change_review_state
from osc.core import create_submit_request
from osc import oscerr

REVIEW_GROUP = 'factory-staging'

class RequestForwarder(object):
    def __init__(self, source_project, target_project):
        self.source_project = source_project
        self.target_project = target_project
        self.apiurl = osc.conf.config['apiurl']
        self.debug = osc.conf.config['debug']

    def crawl(self):
        results = get_review_list(self.apiurl, project=self.source_project,  bygroup=REVIEW_GROUP, req_type='submit')

        for result in results:
            if result.state.name == 'new' or result.state.name == 'review':
                reviews = [r for r in result.reviews]
                group_reviews = [r for r in reviews if (r.by_group is not None
                                 and r.by_group == REVIEW_GROUP)]
                review = group_reviews[0]
                message = 'Forward to %s - new package should\'ve submit to Backports project' % self.target_project
                state = 'declined'
                change_review_state(self.apiurl, result.reqid, state, by_group=review.by_group, message=message)
                src_actions = result.get_actions('submit')
                for action in src_actions:
                    src_prj = action.src_project
                    tgt_prj = self.target_project
                    spac = action.src_package
                    tpac = action.tgt_package
                message = ('Mirrored from OBS SR#%s\n' % result.reqid) + result.description
                result = create_submit_request(self.apiurl, src_prj, spac, tgt_prj, tpac, message=message)
                print('Mirrored SR to ' + result)

def main(args):
    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    if args.source_project is None or args.target_project is None:
        print("Please pass --source-project and --target-project argument. See usage with --help.")
        quit()

    uc = RequestForwarder(args.source_project, args.target_project)
    uc.crawl()


if __name__ == '__main__':
    description = 'Overwrites NON_FTP_PACKAGES.group according to the latest sources. '\
                  'This tool only works for Leap after CtLG implemented.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print info useful for debuging')
    parser.add_argument('-s', '--source-project', dest='source_project', metavar='SOURCE_PROJECT',
                        help='openSUSE project on buildservice')
    parser.add_argument('-t', '--target-project', dest='target_project', metavar='TARGET_PROJECT',
                        help='SLE project on buildservice')

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug
                        else logging.INFO)

    sys.exit(main(args))
