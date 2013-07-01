
import os
import re

from rbackup import BaseClass

class Filesystems(BaseClass):
    _re_mount = re.compile('^(/dev/.*)\ (/[a-zA-Z0-9-_\./]*)\ ([a-z0-9]*)\ .*')
    def __init__(self, output):
        BaseClass.__init__(self, output)
        self._filesystems = {}
        self.update()

    def __getitem__(self, mountpoint):
        try:
            return self._filesystems[mountpoint]
        except KeyError:
            self.error('no such filesystem {0}'.format(mountpoint))

    def keys(self):
        return self._filesystems.keys()

    def shorten_mapper_path(self, path):
        if not '/mapper/' in path:
            return path

        lvm_info = os.path.basename(path)
        (vg, lv) = lvm_info.split('-')
        return '/dev/{0}/{1}'.format(vg, lv)

    def update(self):
        filesystems = {}
        for line in open('/proc/mounts', 'r').readlines():
            match = self._re_mount.search(line)
            if not match:
                continue

            device = self.shorten_mapper_path(match.group(1))
            mountpoint = match.group(2)
            fstype = match.group(3)
            filesystems[mountpoint] = {
                'device': device,
                'fstype': fstype,
            }
        self._filesystems = filesystems
