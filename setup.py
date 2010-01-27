from setuptools import setup
setup(
    name = "PyMiSCID",
    version = open("VERSION").read(),
    packages = ["pymiscid", 
                "pymiscid.bip", 
                "pymiscid.bonjour",
                "pymiscid.xsd",
                "codebench",
                "codebench.opencv",
                "codebench.graphics"],
    package_data = {"pymiscid.xsd" : ["*.xsd"]},
)
