#!/usr/bin/env python

from setuptools import setup
setup(
    name = "PyMiSCID",
    version = open("VERSION").read(),
    packages = ["pymiscid", 
                "pymiscid.bip", 
                "pymiscid.bonjour",
                "pymiscid.xsd",
                "pymiscid.codebench"],
    package_data = {"pymiscid.xsd" : ["*.xsd"]},
)
