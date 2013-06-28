#!/usr/bin/env python

from distutils.core import setup

setup(
    name='rbackup',
    version='1.0',
    description='Duplicity wrapper using LVM snapshots'
    author='Lex van Roon',
    author_email='r3boot@r3blog.nl',
    url='https://r3blog.nl/',
    packages=['rbackup'],
    scripts=['scripts/rbackup'],
    data_files=[
        ('/etc/rbackup', ['config/id_rsa']),
    ]
)
