# -*- coding: utf-8 -*-

from setuptools import setup

VERSION = '0.1.0'

setup(
    name='terms',
    version=VERSION,
    author='Enrique Pérez Arnaud',
    author_email='enriquepablo@gmail.com',
    packages=['terms',],
    license='GNU GENERAL PUBLIC LICENSE Version 3',
    long_description=open('README.txt').read(),
    include_package_data = True,
    test_suite = 'nose.collector',
    test_requires=[
        'Nose',
        'coverage',
    ],
    install_requires=[
        'sqlalchemy',
        'ply',
    ]
)
