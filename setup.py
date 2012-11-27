#!/usr/bin/env python
import os.path
import re
from setuptools import setup, find_packages

def pkg_path(*components):
    path = os.path.join(os.path.dirname(__file__), *components)
    return os.path.realpath(path)

def get_readme():
    with open(pkg_path('README.rst'), 'r') as readme:
        return readme.read()

def get_version():
    with open(pkg_path('calendartools', '__init__.py'), 'r') as init:
        contents = init.read()
        match = re.search(r'__version__ = [\'"]([.\w]+)[\'"]', contents)
        return match.group(1)

setup(
    name='django-calendartools',
    description='A synthesis of the best parts of existing Django calendaring apps.',
    long_description=get_readme(),
    version=get_version(),
    author='Chris Chambers, Ryan Kaskel <dev@ryankaskel.com>',
    url='https://github.com/ryankask/django-calendartools',
    license='BSD',
    packages=find_packages(exclude=['test_project*']),
    install_requires=[
        #'Django>=1.5', # Waiting for official release
        'django-threaded-multihost==2.0',
        'django-extensions==1.0.1',
        'django-extensions==1.0.1',
        'python-dateutil==2.1',
        'django-timezones==0.2',
        'pytz>=2012h',
        'django-model-utils==1.1.0',
    ],
    dependency_links=[
        'https://github.com/languagelab/django-threaded-multihost/tarball/master#egg=django-threaded-multihost-2.0'
    ],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business :: Scheduling'
    ]
)
