
import socket

from rbackup import BaseClass

class Networking(BaseClass):
    def __init__(self, logger):
        BaseClass.__init__(self, logger)

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

    def server_is_alive(self, fqdn):
        result = {'ipv4': False, 'ipv6': False}
        addresses = self.getaddrinfo(fqdn)
        for address in addresses:
            if ':' in address:
                result['ipv6'] = self.connect(address, 6)
            else:
                result['ipv4'] = self.connect(address, 4)
        return result
