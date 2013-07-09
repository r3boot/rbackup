import os
import re
import shlex
import socket
import subprocess
import tempfile
import time

import pprint

from rbackup import BaseClass

class Duplicity(BaseClass):
    _re_identityfile = re.compile('.*IdentityFile[\ \t]+(/.*)')

    _re_duplicity_error = re.compile('duplicity: error: (.*)$')
    _re_duplicity = {
        'last_full':        re.compile('^Last full backup date: (.*)'),
        'start_time':       re.compile('^StartTime ([0-9\.]+) .*$'),
        'end_time':         re.compile('^EndTime ([0-9\.]+) .*$'),
        'elapsed_time':     re.compile('^ElapsedTime ([0-9\.]+) .*$'),
        'source_files':     re.compile('^SourceFiles ([0-9]+)$'),
        'source_file_s':    re.compile('^SourceFileSize ([0-9]+) .*$'),
        'new_files':        re.compile('^NewFiles ([0-9]+)$'),
        'new_files_s':      re.compile('^NewFileSize ([0-9]+) .*$'),
        'deleted_files':    re.compile('^DeletedFiles ([0-9]+)$'),
        'changed_files':    re.compile('^ChangedFiles ([0-9]+)$'),
        'changed_file_s':   re.compile('^ChangedFileSize ([0-9]+) .*$'),
        'changed_delta_s':  re.compile('^ChangedDeltaSize ([0-9]+) .*$'),
        'delta_entries':    re.compile('^DeltaEntries ([0-9]+)$'),
        'raw_delta_s':      re.compile('^RawDeltaSize ([0-9]+) .*$'),
        'dest_size_change': re.compile('^TotalDestinationSizeChange ([0-9]+) .*$'),
        'errors':           re.compile('^Errors ([0-9]+)$'),
    }

    def __init__(self, output, config):
        BaseClass.__init__(self, output)
        self._cfg = config
        self._destination = 'rsync://{0}/{1}'.format(
                self._cfg['remote_host'], self._cfg['remote_path'])

    def _ssh(self, options):
        cmd = 'ssh -F {0} {1} '.format(self._cfg['ssh_config'],
                self._cfg['remote_host'])
        return self.run(cmd + options)


    def _duplicity(self, options):
        cmd = 'duplicity' + options
        self.debug(cmd)

        proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,
                stdout=subprocess.PIPE)

        output = []
        for raw_line in proc.communicate():
            if len(raw_line) == 0:
                continue
            for line in raw_line.split('\n'):
                if len(line) == 0:
                    continue
                output.append(line)

        stats = {}
        if proc.returncode == 0:
            for key, regexp in self._re_duplicity.items():
                if key in stats.keys():
                    continue
                for line in output:
                    match = regexp.search(line)
                    if match:
                        if key in ['elapsed_time', 'end_time', 'start_time']:
                            value = float(match.group(1))
                        elif key in ['last_full']:
                            struct_t = time.strptime(match.group(1),
                                    '%a %b %d %H:%M:%S %Y')
                            value = time.mktime(struct_t)
                        else:
                            value = int(match.group(1))

                        stats[key] = value
        else:
            for line in output:
                match = self._re_duplicity_error.search(line)
                if match:
                    self.critical('Backup failed', match.group(1))

        return stats

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
        (retcode, output) = self._ssh(cmd)
        return int(output[0])

    def run_duplicity_backup(self, backup_type, path):
        stats = {}
        duplicity_options = ''
        excluded_options = ''
        if len(self._cfg['excluded']) > 0:
            (f, fname) = tempfile.mkstemp(prefix='rbackup-', text=True)
            fd = os.fdopen(f, 'w')
            for excluded_path in self._cfg['excluded']:
                fd.write('.{0}\n'.format(excluded_path))
            fd.close()
            excluded_options = '--exclude-filelist={0}'.format(fname)

        rsync_options = '--rsync-options=\"-e \'ssh -F {0}\'\"'.format(
            self._cfg['ssh_config'])

        duplicity_options =  ' {0}'.format(backup_type)
        duplicity_options += ' --exclude-device-files'
        duplicity_options += ' --no-encryption'
        duplicity_options += ' {0}'.format(excluded_options)
        duplicity_options += ' {0}'.format(rsync_options)
        duplicity_options += ' {0}'.format(path)
        duplicity_options += ' {0}'.format(self._destination)

        stats = self._duplicity(duplicity_options)

        if len(excluded_options) > 0:
            os.unlink(fname)

        return stats

    def run_duplicity_cleanup(self):
        rsync_options = ' --rsync-options=\"-e \'ssh -F {0}\'\"'.format(
            self._cfg['ssh_config'])

        duplicity_options = ' remove-all-but-n-full 1' \
            + ' --force' \
            + ' --no-encryption' \
            + rsync_options \
            + ' {0}'.format(self._destination)
        result = self._duplicity(duplicity_options)

        duplicity_options = ' cleanup' \
            + ' --force' \
            + ' --no-encryption' \
            + rsync_options \
            + ' {0}'.format(self._destination)
        result = self._duplicity(duplicity_options)

    def full_backup(self, path):
        self.normal('Starting full backup')
        return self.run_duplicity_backup('full', path)

    def incremental_backup(self, path):
        self.normal('Starting incremental backup')
        return self.run_duplicity_backup('incr', path)

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
            stats = self.full_backup(path)

        elif num_incrementals >= self._cfg['max_incrementals']:
            self.full_backup(path)
            stats = self.run_duplicity_cleanup()

        else:
            stats = self.incremental_backup(path)

        pprint.pprint(stats)
        output = 'E:{0}, T:{1}, S:{2}, C:{3}, D:{4}, N:{5}'.format(
            stats['errors'],
            time.strftime('%H:%M:%S', time.gmtime(stats['elapsed_time'])),
            stats['dest_size_change'],
            stats['changed_files'],
            stats['deleted_files'],
            stats['new_files'],
        )

        if stats['errors'] > 0:
            self.critical('Backup completed', output)
        else:
            self.normal('Backup completed', output)

def _duplicity(options):
    cmd = options

    proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    output = []
    for raw_line in proc.communicate():
        if len(raw_line) == 0:
            continue
        for line in raw_line.split('\n'):
            if len(line) == 0:
                continue
            output.append(line)

    return((proc.returncode, output))
