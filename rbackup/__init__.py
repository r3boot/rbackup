
import math
import sys
import subprocess

class BaseClass:
    _unit_list = zip(['B', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 2, 2, 2])

    def __init__(self, output):
        setattr(self, 'info', output.info)
        setattr(self, 'debug', output.debug)
        setattr(self, 'warning', output.warning)
        setattr(self, 'error', output.error)
        setattr(self, 'low', output.low)
        setattr(self, 'normal', output.normal)
        setattr(self, 'critical', output.critical)


    def path_to_name(self, path=None):
        if not path:
            return

        if path == '/':
            return 'slash'
        elif path.startswith('/'):
            path = path[1:]
        return path.replace('/', '_')

    def run(self, cmdline):
        self.debug(cmdline)

        proc = subprocess.Popen(cmdline, shell=True, stderr=subprocess.PIPE,
                stdout=subprocess.PIPE)

        output = []
        for raw_line in proc.communicate():
            if len(raw_line) == 0:
                continue
            for line in raw_line.split('\n'):
                if len(line) == 0:
                    continue
                output.append(line)

        return (proc.returncode, output)

    def human_byte(self, num):
        """Human friendly file size"""
        if num > 1:
            exponent = min(int(math.log(num, 1024)), len(self._unit_list) - 1)
            quotient = float(num) / 1024**exponent
            unit, num_decimals = self._unit_list[exponent]
            format_string = '{:.%sf}{}' % (num_decimals)
            return format_string.format(quotient, unit)
        if num == 0:
            return '0B'
        if num == 1:
            return '1B'
