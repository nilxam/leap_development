# Deleted SLE package list in Backports 15.5

## Description

Tracking package got deleted in openSUSE:Backports:SLE-15-SP5 in case the reason is about the package does exist in SLE.

## Tables

**F**: failed

**S**: succeeded


| Name  | Build result | Shipped in SLE product | Addtional info |
| ------------- |:-------------:|:-------------:|:-------------:|
| DirectX-Headers | **F** | Yes | |
| abseil-cpp | **F** | Yes | x86_64 failed only|
| amavisd-milter | **F** | Yes | |
| capstone | **F** | Yes | |
| docker-distribution | **F** | Yes | renamed to distribution, SLE does have distribution package|
| duktape | **F** | Yes | |
| helm | **F** | Yes | Coming from container module |
| ignition | **S** | No | Added to SLE15 SP5 but it seem not exist in any product
| iio-sensor-proxy | **F** | Yes | |
| iniparser | **F** | Yes | |
| ipxe | **F** | Yes | |
| libqrtr-glib | **F** | Yes | |
| pcm | **F** | Yes | |
| python-apipkg | **S** | Yes | rpmlink-backports removed all binary but src.rpm left only|
| source-highlight | **F** | Yes | |
| warewulf4 | **F** | Yes | |
| zypper-changelog-plugin | **F** | Yes | |

## Potential removal candidates
# Package does exist in SLE. Package build successed in Backports.

* dragonbox
* flashrom
* ghc
* ghc-Glob
* ghc-HsYAML
* ghc-JuicyPixels
* ghc-OneTuple
* ghc-QuickCheck
* ghc-SHA
* ghc-aeson
* ghc-aeson-pretty
* ghc-ansi-terminal
* ghc-appar
* ghc-asn1-encoding
* ghc-asn1-parse
* ghc-asn1-types
* ghc-assoc
* ghc-async
* ghc-attoparsec
* ghc-base-compat
* ghc-base-compat-batteries
* ghc-base-orphans
* ghc-base16-bytestring
* ghc-base64-bytestring
* ghc-basement
* ghc-bifunctors
* ghc-blaze-builder
* ghc-blaze-html
* ghc-blaze-markup
* ghc-bootstrap
* ghc-bootstrap-helpers
* ghc-byteorder
* ghc-cabal-doctest
* ghc-case-insensitive
* ghc-cereal
* ghc-citeproc
* ghc-colour
* ghc-commonmark
* ghc-commonmark-extensions
* ghc-commonmark-pandoc
* ghc-comonad
* ghc-conduit
* ghc-conduit-extra
* ghc-connection
* ghc-cookie
* ghc-cryptonite
* ghc-data-default
* ghc-data-default-class
* ghc-data-default-instances-containers
* ghc-data-default-instances-dlist
* ghc-data-default-instances-old-locale
* ghc-data-fix
* ghc-digest
* ghc-distributive
* ghc-dlist
* ghc-doclayout
* ghc-doctemplates
* ghc-emojis
* ghc-file-embed
* ghc-haddock-library
* ghc-hashable
* ghc-haskell-lexer
* ghc-hourglass
* ghc-hslua
* ghc-hslua-aeson
* ghc-hslua-classes
* ghc-hslua-core
* ghc-hslua-marshalling
* ghc-hslua-module-path
* ghc-hslua-module-system
* ghc-hslua-module-text
* ghc-hslua-module-version
* ghc-hslua-objectorientation
* ghc-hslua-packaging
* ghc-http-client
* ghc-http-client-tls
* ghc-http-types
* ghc-indexed-traversable
* ghc-integer-logarithms
* ghc-iproute
* ghc-ipynb
* ghc-jira-wiki-markup
* ghc-libyaml
* ghc-lpeg
* ghc-lua
* ghc-memory
* ghc-mime-types
* ghc-mono-traversable
* ghc-network
* ghc-network-uri
* ghc-old-locale
* ghc-pandoc-lua-marshal
* ghc-pandoc-types
* ghc-pem
* ghc-pretty-show
* ghc-primitive
* ghc-random
* ghc-resourcet
* ghc-rpm-macros
* ghc-safe
* ghc-scientific
* ghc-skylighting
* ghc-skylighting-core
* ghc-socks
* ghc-split
* ghc-splitmix
* ghc-streaming-commons
* ghc-strict
* ghc-syb
* ghc-tagged
* ghc-tagsoup
* ghc-temporary
* ghc-text-conversions
* ghc-th-abstraction
* ghc-th-compat
* ghc-th-lift
* ghc-th-lift-instances
* ghc-these
* ghc-time-compat
* ghc-tls
* ghc-transformers-compat
* ghc-typed-process
* ghc-unicode-collation
* ghc-unicode-data
* ghc-unicode-transforms
* ghc-uniplate
* ghc-unliftio-core
* ghc-unordered-containers
* ghc-utf8-string
* ghc-uuid-types
* ghc-vector
* ghc-vector-algorithms
* ghc-x509
* ghc-x509-store
* ghc-x509-system
* ghc-x509-validation
* ghc-xml
* ghc-xml-conduit
* ghc-xml-types
* ghc-yaml
* ghc-zip-archive
* ghc-zlib
* golang-github-prometheus-promu
* happy
* httpcomponents-project
* kio
* libcuckoo
* libjaylink
* pandoc
* perl-Text-Markdown
* plasma-wayland-protocols
* python-ansi2html
* python-cached-property
* python-docker-pycreds
* python-osc-tiny
* python-pefile
* python-pytest-html
* python-pytest-metadata
* python-pytest-rerunfailures
* python-readthedocs-sphinx-ext
* python-semver
* python-tomli
* python-unittest-mixins
* sevctl
* texmath
* xxhash
* yq

## Blocks of code

To get some more removal information

```
osc log -D openSUSE:Backports:SLE-15-SP5 PACKAGE_NAME
```
