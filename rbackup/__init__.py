
import sys
import subprocess

#import pynotify

class BaseClass:
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
