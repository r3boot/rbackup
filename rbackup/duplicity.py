import os
import re
import shlex
import socket
import tempfile

from rbackup import BaseClass

class Duplicity(BaseClass):
    _re_identityfile = re.compile('.*IdentityFile[\ \t]+(/.*)')

    def __init__(self, logger, config):
        BaseClass.__init__(self, logger)
        self._cfg = config
        self._destination = 'rsync://{0}/{1}'.format(
                self._cfg['remote_host'], self._cfg['remote_path'])

    def _ssh(self, options):
        cmd = 'ssh -F {0} {1}'.format(self._cfg['ssh_config'],
                self._cfg['remote_host'])
        cmd = shlex.split(cmd)
        options = shlex.split(options)
        return self.run(cmd + options)

    def _duplicity(self, options):
        cmd = ['duplicity']
        options = shlex.split(options)
        return self.run(cmd + options)

    def has_backup_dir(self):
        cmd = 'ls -d {0} 2>&1'.format(self._cfg['remote_path'])
        result = self._ssh(cmd)
        return 'not found' not in result

    def has_backups(self):
        cmd = 'ls {0} 2>/dev/null'.format(self._cfg['remote_path'])
        result = self._ssh(cmd)
        if not result or len(result) == 0:
            return False
        return True

    def get_number_of_incrementals(self):
        cmd = 'ls {0}/*-inc*.manifest 2>/dev/null | wc -l'.format(
                self._cfg['remote_path'])
        result = self._ssh(cmd)
        return int(result)

    def run_duplicity_backup(self, backup_type, path):
        excluded_paths = ''
        if len(self._cfg['excluded']) > 0:
            for excluded_path in self._cfg['excluded']:
                excluded_paths += ' --exclude="{0}"'.format(excluded_path)

        rsync_options = ' --rsync-options=\"-e \'ssh -F {0}\'\"'.format(
            self._cfg['ssh_config'])

        duplicity_cmdline = backup_type \
                    + ' --exclude-device-files' \
                    + excluded_paths \
                    + ' --no-encryption' \
                    + rsync_options \
                    + ' {0}'.format(path) \
                    + ' {0}'.format(self._destination)

        result = self._duplicity(duplicity_cmdline)

    def run_duplicity_cleanup(self):
        rsync_options = ' --rsync-options=\"-e \'ssh -F {0}\'\"'.format(
            self.__ssh_config)

        duplicity_cmdline = 'remove-all-but-n-full 1' \
            + ' --force' \
            + ' --no-encryption' \
            + rsync_options \
            + ' {0}'.format(self.__destination)
        result = self._duplicity(duplicity_cmdline)

        duplicity_cmdline = 'cleanup' \
            + ' --force' \
            + ' --no-encryption' \
            + rsync_options \
            + ' {0}'.format(self.__destination)
        result = self._duplicity(duplicity_cmdline)

    def full_backup(self, path):
        self.info('starting full backup')
        self.run_duplicity_backup('full', path)

    def incremental_backup(self, path):
        self.info('starting incremental backup')
        self.run_duplicity_backup('incr', path)

    def backup(self, path=None):
        if not path:
            self.warning('backup_directory requires an argument')
            return

        if not os.path.exists(path):
            self.warning('{0} does not exist'.format(path))
            return

        num_incrementals = self.get_number_of_incrementals()

        if not self.has_backup_dir():
            self.error('{0}:{1} does not exist'.format(
                self._cfg['remote_host'], self._cfg['remote_path']))

        elif not self.has_backups():
            self.full_backup(path)

        elif num_incrementals >= self._cfg['max_incrementals']:
            self.full_backup(path)
            self.run_duplicity_cleanup()

        else:
            self.incremental_backup(path)

        self.info('backup completed')
