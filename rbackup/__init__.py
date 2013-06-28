
import sys
import subprocess

#import pynotify

class BaseClass:
    def __init__(self, logger):
        self.__logger = logger
        #pynotify.init('backup')

    #def _notification(self, urgency, title, msg):
    #    if urgency not in ['low', 'normal', 'critical']:
    #        urgency = 'normal'

    #    msg = pynotify.Notification(title, msg)
    #    msg.set_urgency(urgency)
    #    msg.show()

    def info(self, msg):
        self.__logger.info(msg)
        #self._notification('normal', msg, '')

    def debug(self, msg):
        self.__logger.debug(msg)

    def warning(self, msg):
        self.__logger.warning(msg)
        #self._notification('critical', 'Error during backup', msg)

    def error(self, msg):
        self.__logger.error(msg)
        #self._notification('critical', 'Error during backup', msg)
        sys.exit(1)

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
