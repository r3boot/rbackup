import os
import re
import shlex
import socket

from rbackup import BaseClass

class DuplicityWrapper(BaseClass):
    _re_identityfile = re.compile('.*IdentityFile[\ \t]+(/.*)')

    def __init__(self, logger, remote, max_incrementals=5,
            cfg_dir='~/.config/backup', cache_dir='~/.cache/duplicity'):
        BaseClass.__init__(self, logger)
        self.__cfg_dir = cfg_dir
        self.__cache_dir = os.path.expanduser(cache_dir)
        self.__hostname = socket.gethostname().split('.')[0]
        (self.__host, self.__path) = remote.split(':')
        self.__destination = 'rsync://{0}/{1}'.format(self.__host, self.__path)
        self.__max_incrementals = max_incrementals

        self.__ssh_config = os.path.expanduser('{0}/{1}_ssh_config'.format(
            self.__cfg_dir, self.__hostname))
        self.validate_ssh_config()

    def _ssh(self, options):
        cmd = ['ssh', '-F', self.__ssh_config, self.__host]
        options = shlex.split(options)
        return self.run(cmd + options)

    def _duplicity(self, options):
        cmd = ['duplicity']
        options = shlex.split(options)
        return self.run(cmd + options)

    def validate_ssh_config(self):
        if not os.path.exists(self.__ssh_config):
            self.error('{0} does not exist'.format(self.__ssh_config))

        identity_file = None
        for line in open(self.__ssh_config, 'r').readlines():
            match = self._re_identityfile.search(line)
            if match:
                identity_file = match.group(1)

        if not identity_file:
            self.error('no IdentityFile specified in {0}'.format(
                self.__ssh_config))

        if not os.path.exists(identity_file):
            self.error('{0} does not exist'.format(identity_file))

    def has_backup_dir(self, backup_name):
        cmd = 'ls -d {0}/{1} 2>&1'.format(self.__path, backup_name)
        result = self._ssh(cmd)
        return 'not found' not in result

    def create_backup_dir(self, backup_name):
        cmd = 'mkdir -p {0}/{1}'.format(self.__path, backup_name)
        return self._ssh(cmd)

    def has_backups(self, backup_name):
        cmd = 'ls {0}/{1} 2>/dev/null'.format(self.__path, backup_name)
        result = self._ssh(cmd)
        if not result or len(result) == 0:
            return False
        return True

    def get_number_of_incrementals(self, backup_name):
        cmd = 'ls {0}/{1}/*-inc*.manifest 2>/dev/null | wc -l'.format(
            self.__path, backup_name)
        result = self._ssh(cmd)
        return int(result)

    def get_excludes_file(self, backup_name):
        return os.path.expanduser('{0}/{1}_excluded.list'.format(
            self.__cfg_dir, backup_name))

    def has_excludes(self, backup_name):
        excludes_file = self.get_excludes_file(backup_name)
        return os.path.exists(excludes_file)

    def run_duplicity_backup(self, backup_type, backup_name, path):
        exclude_list_option = ''
        if self.has_excludes(backup_name):
            excludes_file = self.get_excludes_file(backup_name)
            exclude_list_option = ' --exclude-filelist={0}'.format(
                excludes_file)

        rsync_options = ' --rsync-options=\"-e \'ssh -F {0}\'\"'.format(
            self.__ssh_config)

        duplicity_cmdline = backup_type \
                    + ' --exclude-device-files' \
                    + exclude_list_option \
                    + ' --no-encryption' \
                    + rsync_options \
                    + ' {0}'.format(path) \
                    + ' {0}/{1}'.format(self.__destination, backup_name)

        result = self._duplicity(duplicity_cmdline)

    def run_duplicity_cleanup(self, backup_name):
        rsync_options = ' --rsync-options=\"-e \'ssh -F {0}\'\"'.format(
            self.__ssh_config)

        duplicity_cmdline = 'remove-all-but-n-full 1' \
            + ' --force' \
            + ' --no-encryption' \
            + rsync_options \
            + ' {0}/{1}'.format(self.__destination, backup_name)
        result = self._duplicity(duplicity_cmdline)

        duplicity_cmdline = 'cleanup' \
            + ' --force' \
            + ' --no-encryption' \
            + rsync_options \
            + ' {0}/{1}'.format(self.__destination, backup_name)
        result = self._duplicity(duplicity_cmdline)

    def full_backup(self, backup_name, path):
        self.info('starting full backup')
        self.run_duplicity_backup('full', backup_name, path)

    def incremental_backup(self, backup_name, path):
        self.info('starting incremental backup')
        self.run_duplicity_backup('incr', backup_name, path)

    def backup(self, path=None):
        if not path:
            self.warning('backup_directory requires an argument')
            return

        if not os.path.exists(path):
            self.warning('{0} does not exist'.format(path))
            return

        backup_name = 'laptop'
        num_incrementals = self.get_number_of_incrementals(backup_name)

        if not self.has_backup_dir(backup_name):
            self.create_backup_dir(backup_name)
            self.full_backup(backup_name, path)

        elif not self.has_backups(backup_name):
            self.full_backup(backup_name, path)

        elif num_incrementals >= self.__max_incrementals:
            self.full_backup(backup_name, path)
            self.run_duplicity_cleanup(backup_name)

        else:
            self.incremental_backup(backup_name, path)

        self.info('backup completed')
