from distutils.core import setup

VERSION = '0.1.0a1.dev22'

setup(
    name='terms.core',
    version=VERSION,
    author='Enrique Pérez Arnaud',
    author_email='enriquepablo@gmail.com',
    url = 'http://pypi.python.org/terms.core',
    packages=['terms', 'terms.core',],
    license='GNU GENERAL PUBLIC LICENSE Version 3',
    description='',
    long_description=open('README.txt').read(),
    package_data = {'terms.core': ['etc/terms.cfg', 'examples/*.trm',]},
    scripts = ['bin/terms', 'bin/nosetests', 'bin/coverage'],
    install_requires=[
        'Nose',
        'coverage',
        'sqlalchemy == 0.7.8',
        'ply == 3.4',
    ],
)
