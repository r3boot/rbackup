
import logging
import sys

import dbus

class Output:
    _bus_name = 'net.as65342.notifications'
    _bus_path = '/net/as65342/notifications'

    _logformat = '%(asctime)s [%(levelname)s]: %(message)s'

    def __init__(self, log_level):
        self._logger = None
        self._notificationd = None
        self._log_level = log_level
        self.setup_output()

    def setup_output(self):
        self.setup_main_logger()
        self.setup_console_logger()

        self._bus = dbus.SystemBus()
        self._notificationd = self._bus.get_object(self._bus_name, self._bus_path)

    def setup_main_logger(self):
        self._logger = logging.getLogger('main')
        self._logger.setLevel(self._log_level)

    def setup_console_logger(self):
        console_logger = logging.StreamHandler()
        console_logger.setLevel(self._log_level)
        formatter = logging.Formatter(self._logformat)
        console_logger.setFormatter(formatter)
        self._logger.addHandler(console_logger)

    def info(self, msg):
        self._logger.info(msg)

    def debug(self, msg):
        self._logger.debug(msg)

    def warning(self, msg):
        self._logger.warning(msg)

    def error(self, msg):
        self._logger.error(msg)
        sys.exit(1)

    def low(self, title, msg=''):
        self._notificationd.low(title, msg)
        if len(msg) > 0:
            self.debug('{0}: {1}'.format(title, msg))
        else:
            self.debug('{0}'.format(title))

    def normal(self, title, msg=''):
        self._notificationd.normal(title, msg)
        if len(msg) > 0:
            self.info('{0}: {1}'.format(title, msg))
        else:
            self.info('{0}'.format(title))

    def critical(self, title, msg=''):
        self._notificationd.critical(title, msg)
        if len(msg) > 0:
            self.error('{0}: {1}'.format(title, msg))
        else:
            self.error('{0}'.format(title))
