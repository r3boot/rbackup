
import sys
import subprocess

#import pynotify

class BaseClass:
    def __init__(self, output):
        setattr(self, 'info', output.info)
        setattr(self, 'debug', output.debug)
        setattr(self, 'warning', output.warning)
        setattr(self, 'error', output.error)

    def path_to_name(self, path=None):
        if not path:
            return

        if path == '/':
            return 'slash'
        elif path.startswith('/'):
            path = path[1:]
        return path.replace('/', '_')

    def run(self, cmdline):
        self.debug(' '.join(cmdline))
        proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        proc.wait()
        output = proc.stdout.readlines()
        if len(output) > 0:
            return ''.join(output)
