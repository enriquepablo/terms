from distutils.core import setup

VERSION = '0.1.0'

setup(
    name='terms',
    version=VERSION,
    author='Enrique Pérez Arnaud',
    author_email='enriquepablo@gmail.com',
    packages=['terms',],
    license='GNU GENERAL PUBLIC LICENSE Version 3',
    long_description=open('README.txt').read(),
    install_requires=[
        'nose',
    ]
)
