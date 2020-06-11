#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read().replace(':class:`~', '`')

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'django_otp',
]

setup(
    author="Harm Geerts",
    author_email='hgeerts@osso.nl',
    python_requires='>=3.5, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Environment :: Web Environment',
        'Natural Language :: English',
        'Framework :: Django',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        ('Topic :: System :: Systems Administration :: '
         'Authentication/Directory'),
    ],
    description="Interface components to configure and manage multi factor "
                "authentication",
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='kleides_mfa',
    name='kleides_mfa',
    packages=find_packages(include=['kleides_mfa', 'kleides_mfa.*']),
    version='0.1.11',
    zip_safe=False,
)
