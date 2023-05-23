# Development Model

## Description

This document describles the development model of Backports project after CtLG

## Pre-Integration

## Potential removal candidates
### Package does exist in SLE. Package build successed in Backports.

* ghc-bootstrap (got forked because of the default llvm version issue)

## Tooling for the source management

### Package updater for the previous Backports

[find_update.py](https://github.com/nilxam/leap_development/blob/master/scripts/find_update.py) can go
through Update project of the previous Backports project, and dump a submission list with osc command
wrapped.

### Package updater for Factory origin sources

Since we don't want to submit Factory package to Backports blindly, therefore we did rebuild Factory sources
on Backports in the an experiment project that called [FactoryCandidates](https://build.opensuse.org/project/show/openSUSE:Backports:SLE-15-SP5:FactoryCandidates)

We have [print_factory_updates.py](https://github.com/nilxam/leap_development/blob/master/scripts/print_factory_updates.py) 
