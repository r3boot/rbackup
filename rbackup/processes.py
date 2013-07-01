
import os

from rbackup import BaseClass

class PackageManagers(BaseClass):
    _package_managers = [   # Yes, this is incomplete
        'dpkg',
        'aptitude',
        'yum',
        'rpm',
        'pacman',
        'pak',
        'make install'
    ]
    def __init__(self, logger):
        BaseClass.__init__(self, logger)

    def has_running_pkgmgr(self):
        pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]

        for pid in pids:
            cmdline = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()
            if 'make install' in cmdline:
                cmd = 'make install'
            else:
                cmd = os.path.basename(cmdline.split()[0])

            if cmd in self._package_managers:
                return True

        return False
