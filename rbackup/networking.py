
import os
import re
import shlex
import socket

from ipcalc import IPCalc

from rbackup import BaseClass

class Networking(BaseClass):
    """/sys/class/net/eno1"""
    _re_ipv4_address = re.compile('^[0-9]: [A-Za-z0-9-_]* +inet\ ([0-9./]*) .* scope global')
    _re_ipv6_address = re.compile('^[0-9]: [A-Za-z0-9-_]* +inet6\ ([0-9a-f:/]*) scope global')

    def __init__(self, logger, config):
        BaseClass.__init__(self, logger)
        self._cfg = config
        self._ipcalc = IPCalc()

    def getaddrinfo(self, fqdn):
        addresses = []
        try:
            for addrinfo in socket.getaddrinfo(fqdn, 22):
                addr = addrinfo[4][0]
                if addr not in addresses:
                    addresses.append(addr)
        except socket.gaierror, errmsg:
            self.warning('getaddrinfo({0}): {1}'.format(fqdn, errmsg))

        return addresses

    def connect(self, addr, af):
        if af == 6:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
            t = (addr, 22, 0, 0)
        elif af == 4:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            t = (addr, 22)
        else:
            self.warning('unknown address family')
            return False

        try:
            s.connect(t)
        except socket.error, errmsg:
            self.warning('connect({0}): {1}'.format(addr, errmsg))
            return False
        except socket.gaierror, errmsg:
            self.warning('connect({0}): {1}'.format(addr, errmsg))
            return False

        return True

    def server_is_alive(self):
        result = {'ipv4': False, 'ipv6': False}
        addresses = self.getaddrinfo(self._cfg['remote_host'])
        for address in addresses:
            if ':' in address:
                result['ipv6'] = self.connect(address, 6)
            else:
                result['ipv4'] = self.connect(address, 4)
        return result

    def get_ipaddresses(self):
        addresses = []
        command_line = '/sbin/ip -o address show'
        output = self.run(shlex.split(command_line))
        if not output:
            return []

        for line in output.split('\n'):
            match = self._re_ipv4_address.search(line)
            if match:
                address = match.group(1)
                if address not in addresses:
                    addresses.append(address)
                continue
            match = self._re_ipv6_address.search(line)
            if match:
                address = match.group(1)
                if address not in addresses:
                    addresses.append(address)

        addresses.sort()
        return addresses

    def on_runon_network(self):
        addresses = self.get_ipaddresses()
        for network in self._cfg['runon_networks']:
            for address in addresses:
                if self._ipcalc.in_network(address, network):
                    return True
        return False
