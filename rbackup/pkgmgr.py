
import os

from rbackup import BaseClass

class PackageManager(BaseClass):
    _package_managers = [   # Yes, this is incomplete
        'dpkg',
        'aptitude',
        'yum',
        'rpm',
        'pacman',
        'pak',
        'makeinstall'
    ]
    def __init__(self, logger):
        BaseClass.__init__(self, logger)

    def is_package_manager(self, cmdline):
        for pkgmgr in self._package_managers:
            if pkgmgr in cmdline:
                return True
        return False

    def has_running_pkgmgr(self):
        pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]

        for pid in pids:
            cmdline = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()
            if self.is_package_manager(cmdline):
                return True

        return False