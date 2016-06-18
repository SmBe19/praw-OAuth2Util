#!/usr/bin/env python

from setuptools import setup, find_packages
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

version = '0.3.5'

setup(
    name='praw-oauth2util',
    version=version,
    install_requires=requirements,
    author='Benjamin Schmid',
    author_email='bsgame27@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/SmBe19/praw-OAuth2Util/',
    license='MIT',
    description='OAuth2 wrapper for PRAW',
    long_description=read("README_PyPi.rst"),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
)
