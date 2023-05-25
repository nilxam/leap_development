# Development Model

## Description

This document describles the development model of Backports project after CtLG

## Background

Backprots used to rebuild Leap sources, after CtLG, package source will go to Backprots project and be maintained in Backports project, Leap project just maintain a small amount of Leap specific packages; brandings and KMPs, tools/checkers been used in Leap is re-implementation towards Backports.

## Pre-Integration

### Source checker + Origin checker

[factory-auto](https://github.com/openSUSE/openSUSE-release-tools/blob/master/check_source.py) checks the basic rules, and according to the config bits, it will add additional review to SR if needed, other than that there are several particular rules/reactions for Backprots

* origin-reviewers will be added if submission's source origin is not from a valid project, for Backports that should be openSUSE:Factory, openSUSE:Backports:SLE-XX-SPX:Update, openSUSE:Leap:XX.X:Update, etc. This is needed because in some cases we can not reuses Factory's source but have to take patched package with specify version, origin-reviewers need to review the change since the change has not been reviewed, submission from a valid project __openSUSE:XXX__ namespace must been reviewed somehow
* devel_project/devel_pacage reivew will be added if submitter is not package maintainer
* SR will be declined if the target package does exist in SLE
* SR will be decliend if the target package does NOT exist in openSUSE:Factory
* A declined submission by factory-auto can be overriden via commenting __@factory-auto override accept__ on the SR, the override command is only valid if was project maintainer

The checker configuration bits of openSUSE:Backprots:SLE-15-SP5 like below

```
check-source-ensure-source-exist-in-baseproject: True
check-source-devel-baseproject: openSUSE:Factory
check-source-allow-source-in-sle: False
check-source-sle-project: SUSE:SLE-15-SP5:GA
check-source-allow-valid-source-origin: True
check-source-valid-source-origins: openSUSE:Leap:15.4:Update openSUSE:Backports:SLE-15-SP4:Update openSUSE:Factory openSUSE:Backports:SLE-15-SP5:SLEFork openSUSE:Backports:SLE-15-SP5:FactoryFork
check-source-add-devel-project-review: True
review-team = origin-reviewers
```

### License checker

Backports package will delivered to SLE customer via PackageHub, therefore license check must to be done on legaldb, human legal review will review the request on legaldb

### Staging project checks

New change will be staged in a staging project, package would rebuild in the staging project, new change must build successful and binary RPMs passed installcheck verification

## Tools

### Package updater for the previous Backports

[find_update.py](https://github.com/nilxam/leap_development/blob/master/scripts/find_update.py) can go through Update project of the previous Backports project, and dump a submission list with osc command
wrapped.

### Package updater for Factory origin sources

Since we don't want to submit Factory package to Backports blindly, therefore we did rebuild Factory sources on Backports in the an experiment project that called [FactoryCandidates](https://build.opensuse.org/project/show/openSUSE:Backports:SLE-15-SP5:FactoryCandidates), the build succeeded pacakge is the good candidate  to be submitted to Backports project. We have [print_factory_updates.py](https://github.com/nilxam/leap_development/blob/master/scripts/print_factory_updates.py) help to manage FactoryCandidates project, it can update project_link; creating a submit request to Backports project in case package build successfully.

Note: **find_update.py** and **print_factory_updates.py** are not just handle package updates, it handles __new package__ as well.
Note2: the project link being used in FactoryCandidates project is created by print_factory_updates.py, print_factory_updates.py has filter out SLE sources beforehand.

### find_bp_src_rpm_only.py

rpmlint-backports has a special python build handling, it removes python3-XX RPM if it conflicts to the ones from SLE, but the package build doesn't resulting to a fail, this means other RPMs are remaining like src.rpm, this issue can not be caught while staging project, find_bp_src_rpm_only.py tries to find these affecting packages, they should be deleted in Backports.

## Post-Integration

There is not much we can do for the post-integrtion check for Backports, neither image build nor openqa test are available, but a [rebuildpac report](https://build.opensuse.org/package/view_file/openSUSE:Backports:SLE-15-SP5:Staging/dashboard/rebuildpacs.openSUSE:Backports:SLE-15-SP5-standard.yaml?expand=1) was there, it can be taken as a project-wise installcheck report of Backprots project, uninstallable RPMs should be listed, however this is from __buildservice__ view, that doesn't reflect to the real status on users system, because that depending what SLE products user's had on their system, from __buildservice__ view all dependencies are perfect filled(at least that is true on x86_64) because we have almost everything from SLE pool, note that, it's binaries pool, not equals to stuff SLE released.
