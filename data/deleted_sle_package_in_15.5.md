# Deleted SLE package list in Backports 15.5

## Description

Tracking package got deleted in openSUSE:Backports:SLE-15-SP5 in case the reason is about the package does exist in SLE.

## Tables

**F**: failed

**S**: succeeded


| Name  | Build result | Shipped in SLE product | Addtional info |
| ------------- |:-------------:|:-------------:|:-------------:|
| abseil-cpp | **F** | Yes | x86_64 failed only|
| amavisd-milter | **F** | Yes | |
| capstone | **F** | Yes | |
| duktape | **F** | Yes | |
| helm | **F** | Yes | Coming from container module |
| ignition | **S** | No | Added to SLE15 SP5 but it seem not exist in any product
| iio-sensor-proxy | **F** | Yes | |
| iniparser | **F** | Yes | |
| pcm | **F** | Yes | |
| python-apipkg | **S** | Yes | rpmlink-backports removed all binary but src.rpm left only|

## Blocks of code

To get some more removal information

```
osc log -D openSUSE:Backports:SLE-15-SP5 PACKAGE_NAME
```
