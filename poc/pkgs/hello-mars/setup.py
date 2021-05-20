#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="hello-mars",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    install_requires=[
        "random-word-generator==1.2",
        "hello-world==0.0.12"
    ],
    include_package_data=True,
)