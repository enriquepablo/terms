from distutils.core import setup

VERSION = '0.1.0a1.dev5'

setup(
    name='terms.core',
    version=VERSION,
    author='Enrique Pérez Arnaud',
    author_email='enriquepablo@gmail.com',
    url = 'http://pypi.python.org/terms.core',
    packages=['terms.core',],
    license='GNU GENERAL PUBLIC LICENSE Version 3',
    description=open('README.txt').read(),
    data_files = [('etc', ['etc/terms.cfg']),
                  ('examples', ['examples/activiti.trm',
                                'examples/cms.trm',
                                'examples/cms-time.trm',
                                'examples/monads.trm',
                                'examples/person.trm',
                                'examples/person_loves.trm',
                                'examples/person_walks.trm',
                                'examples/physics.trm',
                                ])],
    scripts = ['bin/terms', 'bin/nosetests', 'bin/coverage'],
    install_requires=[
        'Nose',
        'coverage',
        'sqlalchemy == 0.7.8',
        'ply == 3.4',
    ],
)
