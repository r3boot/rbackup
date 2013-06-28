
import os
import re
import shlex
import time

from rbackup import BaseClass

class LVM(BaseClass):
    _re_lv_path = re.compile('\ +LV Path\ .*\ (/.*)')
    _re_lv_path = re.compile('\ +LV Name\ .*\ (/.*)')
    _re_no_such_vg = re.compile('\ +Volume group .* not found')
    _re_vg_pe_size = re.compile('.*PE Size.*\ ([0-9\.]+) MiB')
    _re_vg_free_pe = re.compile('\ +Free  PE / Size.*\ ([0-9]+)\ .*')
    _re_lvs_snapshot = re.compile('\ +([a-zA-Z0-9]+)_([0-9]+)\ .*')

    def __init__(self, logger, filesystems, use_snapshots='auto', snap_size=1,
            vg_name=None, snap_dir='/.snapshot'):
        BaseClass.__init__(self, logger)
        self._filesystems = filesystems
        self._vg_name = vg_name
        self._snap_size = snap_size
        self._snap_dir = snap_dir
        self.setup_snapshots(use_snapshots)

    def setup_snapshots(self, use_snapshots):
        if use_snapshots == 'auto':
            all_vgs = self.get_vgs()
            all_vgs_len = len(all_vgs)
            if all_vgs_len == 0:
                self.error('no volume groups found')
            elif all_vgs_len > 0 and not self._vg_name:
                self.error('multiple volume groups found')
            self._vg_name = all_vgs[0]

        elif use_snapshots:
            all_vgs = self.get_vgs()
            if not self._vg_name:
                self.error('no volume group specified')
            elif self._vg_name not in all_vgs:
                self.error('volume group {0} does not exist')

    def get_vgs(self):
        vgs = []
        results = self.run(['vgs'])
        for line in results.split('\n')[1:]:
            try:
                vgs.append(line.split()[0])
            except IndexError:
                continue
        return vgs

    def get_lvs(self, vg):
        lvs = []
        results = self.run(['lvs'])
        for line in results.split('\n')[1:]:
            try:
                lvs.append(line.split()[0])
            except IndexError:
                continue
        return lvs

    def shorten_mapper_path(self, path):
        lvm_info = os.path.basename(path)
        (vg, lv) = lvm_info.split('-')
        return '/dev/{0}/{1}'.format(vg, lv)

    def is_lv(self, name):
        if '/mapper/' in name:
            name = self.shorten_mapper_path(name)

        cmd = ['lvdisplay', name]
        result = self.run(cmd)
        return len(result.split('\n')) > 3

    def list_snapshots(self):
        snapshot_timestamps = []
        for line in self.run(['lvs']).split('\n'):
            match = self._re_lvs_snapshot.search(line)
            if match:
                timestamp = match.group(2)
                if timestamp not in snapshot_timestamps:
                    snapshot_timestamps.append(timestamp)
        snapshot_timestamps.sort()
        return snapshot_timestamps

    def get_free_vg_space(self, vg_name):
        cmd = ['vgdisplay', vg_name]
        result = self.run(cmd)
        pe_size = 0
        free_pe = -1
        for line in result.split('\n'):
            match = self._re_no_such_vg.search(line)
            if match:
                self.error('no such VG: {0}'.format(vg_name))

            match = self._re_vg_pe_size.search(line)
            if match:
                pe_size = float(match.group(1))

            match = self._re_vg_free_pe.search(line)
            if match:
                free_pe = float(match.group(1))

        if pe_size == 0:
            self.error('PE size of VG is 0')

        return int(round(pe_size * free_pe))

    def get_mounts(self):
        mounts = {}
        for line in open('/proc/mounts', 'r').readlines():
            match = self._re_mount.search(line)
            if match:
                device = match.group(1)
                mountpoint = match.group(2)
                filesystem = match.group(3)

                mounts[mountpoint] = {
                    'device':       device,
                    'filesystem':   filesystem,
                }

        return mounts

    def mksnapshot(self, mountpoint, mount_data, timestamp):
        lvm_info = os.path.basename(mount_data['device'])
        (vg_name, lv_name) = lvm_info.split('-')

        snap_lv_name = '{0}_{1}'.format(lv_name, timestamp)
        snap_lv_device = '/dev/{0}/{1}'.format(self._vg_name, snap_lv_name)

        if not os.path.exists(mountpoint):
            self.error('{0} not found'.format(mountpoint))

        if self.is_lv(snap_lv_device):
            self.warning('snapshot already exists')
            return

        cmd = shlex.split('lvcreate -L {0}G -s -n {1} {2}'.format(
            self._snap_size,
            snap_lv_name,
            mount_data['device']))
        self.run(cmd)

        if mount_data['filesystem'] == 'xfs':
            cmd = 'mount -o ro,nouuid {0} {1}'.format(snap_lv_device,
                    mountpoint)
        else:
            cmd = 'mount -o ro {0} {1}'.format(snap_lv_device, mountpoint)
        self.run(shlex.split(cmd))

    def do_bind_mount(self, mountpoint, snap_mountpoint):
        cmd = 'mount --bind -o ro {0} {1}'.format(mountpoint, snap_mountpoint)
        self.run(shlex.split(cmd))

    def create_snapshots(self):
        mounts = self.get_mounts()
        mountpoints = mounts.keys()
        mountpoints.sort()

        free_vg_space = self.get_free_vg_space(self._vg_name)

        if (len(mounts.keys()) * self._snap_size) > (free_vg_space / 1024):
            self.error('not enough free space in VG {0}'.format(self._vg_name))

        if not os.path.exists(self._snap_dir):
            os.mkdir(self._snap_dir)

        if '/' not in mountpoints:
            self.error('root filesystem not found')

        timestamp = int(time.time())
        for mountpoint in mountpoints:
            device = mounts[mountpoint]['device']
            snap_mountpoint = self._snap_dir + mountpoint

            if self.is_lv(device):
                self.mksnapshot(snap_mountpoint, mounts[mountpoint], timestamp)
            else:
                self.do_bind_mount(mountpoint, snap_mountpoint)

        return timestamp

    def remove_snapshots(self, timestamp):
        mounts = self.get_mounts()
        mountpoints = mounts.keys()
        mountpoints.sort(reverse=True)

        for mountpoint in mountpoints:
            if not mountpoint.startswith('/.snapshot'):
                continue

            device = mounts[mountpoint]['device']

            if mountpoint.endswith('/'):
                mountpoint = mountpoint[:len(mountpoint)-1]

            cmd = 'umount -f {0}'.format(mountpoint)
            result = self.run(shlex.split(cmd))

            if self.is_lv(device):
                lvm_info = os.path.basename(mountpoint)

                cmd = 'lvremove -f {0}'.format(device)
                self.run(shlex.split(cmd))

        os.rmdir(self._snap_dir)

    def cleanup_snapshots(self):
        mounts = self.get_mounts()
        mountpoints = mounts.keys()
        mountpoints.sort(reverse=True)

        for mountpoint in mountpoints:
            if mountpoint.startswith('/.snapshot'):
                if mountpoint.endswith('/'):
                    mountpoint = mountpoint[:len(mountpoint)-1]
                cmd = 'umount -f {0}'.format(mountpoint)
                self.run(shlex.split(cmd))

        mounts = self.get_mounts()
        mountpoints = mounts.keys()
        mountpoints.sort(reverse=True)

        snapshot_timestamps = self.list_snapshots()
        for mountpoint in mountpoints:
            device = mounts[mountpoint]['device']
            for timestamp in snapshot_timestamps:
                snap_device = '{0}_{1}'.format(device, timestamp)
                if self.is_lv(snap_device):
                    cmd = 'lvremove -f {0}'.format(snap_device)
                    self.run(shlex.split(cmd))
