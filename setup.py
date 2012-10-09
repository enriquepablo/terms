import distribute_setup
distribute_setup.use_setuptools()
from setuptools import setup

VERSION = '0.1.0a1'

setup(
    name = 'terms.core',
    version = VERSION,
    author = 'Enrique Pérez Arnaud',
    author_email = 'enriquepablo@gmail.com',
    url = 'http://pypi.python.org/terms.core',
    license = 'GNU GENERAL PUBLIC LICENSE Version 3',
    description = '',
    long_description = open('INSTALL.txt').read() + open('README.txt').read(),

    zip_safe = False,
    packages=['terms', 'terms.core',],
    namespace_packages=['terms'],
    include_package_data = True,
    scripts = ['bin/terms', 'bin/nosetests', 'bin/coverage'],

    test_suite = 'nose.collector',

    entry_points = {
        'console_scripts': [
            'terms = terms.core.repl:repl',
#            'initterms = terms.core.initialize:initterms',
        ],
    }
    tests_require=[
        'Nose',
        'coverage',
    ],
    install_requires=[
        'psycopg2',
        'sqlalchemy == 0.7.8',
        'ply == 3.4',
    ],
)
