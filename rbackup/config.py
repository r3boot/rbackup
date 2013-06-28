
import os
import re
import shlex
import socket

import yaml

from rbackup import BaseClass

class Configuration(BaseClass):
    _config_version = 1
    _re_identity = re.compile('.*IdentityFile (/.*)$')
    _ssh_config_template = """Host %HOST%
  User %USER%
  GSSAPIAuthentication no
  ControlMaster no
  ServerAliveInterval 15
  IdentityFile %IDENTITY%
  Ciphers blowfish-cbc,aes256-cbc"""
    _config_template = """---
version: 1
remote_host: %HOST%
remote_user: %USER%
remote_path: %PATH%
ssh_config: /etc/rbackup/ssh_config
use_snapshots: auto
excluded:
 - /dev
 - /sys
 - /proc
 - /run
 - /net
 - /tmp
 - /media
 - /mnt
 - /var/tmp
 """

    def __init__(self, logger, cfg_dir='/etc/rbackup'):
        BaseClass.__init__(self, logger)
        self._cfg_dir = cfg_dir
        self._cfg_file = cfg_dir + '/config.yaml'
        self._identity = cfg_dir + '/id_rsa'
        self._config = {}

    def __getitem__(self, cfgitem):
        try:
            return self._config[cfgitem]
        except KeyError:
            self.error('no such configuration item')

    def update(self):
        self._config = self.verify_all()

    def verify_all(self):
        self.verify_config_paths()
        config = self.verify_yaml()
        self.verify_ssh_config(config)

    def verify_config_paths(self):
        if not os.path.exists(self._cfg_dir):
            self.error('{0} does not exist'.format(self._cfg_dir))

        if not os.path.exists(self._cfg_file):
            self.error('{0} does not exist'.format(self._cfg_file))

    def verify_yaml(self):
        raw_yaml = open(self._cfg_file, 'r').read()
        config = yaml.load(raw_yaml)
        if config['version'] is not self._config_version:
            self.error('config version mismatch, want {0}, got {0}'.format(
                self._config_version, config['version']))
        return config

    def verify_ssh_config(self, config):
        ssh_config_file = config['ssh_config']
        if not os.path.exists(ssh_config_file):
            self.error('{0} does not exist'.format(ssh_config_file))

        identity_file = None
        for line in open(ssh_config_file, 'r').readlines():
            match = self._re_identity.search(line)
            if match:
                identity_file = match.group(1)
                break

        if not identity_file:
            self.error('no identity specified in {0}'.format(ssh_config_file))
        elif not os.path.exists(identity_file):
            self.error('identity {0} does not exist'.format(identity_file))

    def create_config(self, host, user, path):
        if not host:
            self.error('no host specified')
        elif not user:
            self.error('no user specified')
        elif not path:
            self.error('no path specified')

        if not os.path.exists(self._cfg_file):
            self.info('generating configuration file')
            cfg = self._config_template.replace('%HOST%', host)
            cfg = cfg.replace('%USER%', user)
            cfg = cfg.replace('%PATH%', path)
            open(self._cfg_file, 'w').write(cfg)
        else:
            self.warning('{0} already exists, not overwriting'.format(
                self._cfg_file))
        config = self.verify_yaml()

        if not os.path.exists(self._identity):
            self.info('generating ssh key')
            cmd = 'ssh-keygen -q -b 4096 -t rsa' \
                  + ' -C "rbackup@{0}"'.format(socket.gethostname()) \
                  + ' -f {0}'.format(self._identity) \
                  + ' -N ""'
            self.run(shlex.split(cmd))

            self.info('copying ssh key to {0}@{1}'.format(user, host))
            cmd = 'ssh-copy-id -i /etc/rbackup/id_rsa {0}@{1}'.format(
                    user, host)
            self.run(shlex.split(cmd))
        else:
            self.warning('{0} already exists, not overwriting'.format(
                self._identity))

        if not os.path.exists(config['ssh_config']):
            ssh_config = self._ssh_config_template.replace('%HOST%', host)
            ssh_config = ssh_config.replace('%USER%', user)
            ssh_config = ssh_config.replace('%IDENTITY%', self._identity)
            open(config['ssh_config'], 'w').write(ssh_config)
        else:
            self.warning('{0} already exists, not overwriting'.format(
                config['ssh_config']))
