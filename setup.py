#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    'appdirs>=1.4',
    'pygubu>=0.9.7.4',
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='ptsync',
    version='0.1.0',
    description="Personal tube sync app",
    long_description=readme + '\n\n' + history,
    author="Alejandro Autalán",
    author_email='alejandroautalan@gmail.com',
    url='https://github.com/alejandroautalan/ptsync',
    packages=[
        'ptsync',
    ],
    package_dir={'ptsync':
                 'ptsync'},
    include_package_data=True,
    install_requires=requirements,
    license="GPL-3",
    zip_safe=False,
    keywords='ptsync',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
