import socket
import threading
import time
import signal
import gobject

try:
    from ..codebench import events
except Exception, err:
    from codebench import events

import logging
logger = logging.getLogger(__name__)

class GTKReactor(object):
    """
    This class represent the connection event loop. It uses a GTK event async
    loop to accept connection on a socket.
    """
    __sock_timeout__ = 0.01
    __sleep_interval__ = 0.1
    __backlog__ = 5
    loop = None
    __active__ = False

    def __init__(self):
        self.__socketbuilders       = {}
        self.lock                   = threading.Lock()
        self.__factories            = set()

    def __set_active__(self, value):
        running = "Started" if value else "Stopped";
        if logger.isEnabledFor(logging.INFO):
            logger.info("BIP Reactor [%s]" % running)
        self.__active__ = value


    def __get_active__(self):
        return self.__active__

    active = property(__get_active__, __set_active__)


    def stop(self, join = True):
        if self.loop is None:
            return
        else:
            self.loop.quit()

    def run(self, install_signal_handler = True, clearafter = True):
        self.active = True

        gobject.threads_init()
        if install_signal_handler:
            signal.signal(signal.SIGINT, self.__signal_handler__)
        if self.loop is None:
            self.loop = gobject.MainLoop()

            self.loop.run()
            if clearafter:
                with self.lock:
                    while len(self.__factories) != 0:
                        self.__factories.pop().close()


        else:
            # Should probably raise an exception
            pass


        self.active = False


    def __onconnect__(self, s, *args):
        with self.lock:
            proto = self.__socketbuilders[s].build(*s.accept())
        return True

    def __create_server_socket__(self, port, stype):
        s = socket.socket(socket.AF_INET, stype)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((socket.gethostname(), port))

        addr, port = s.getsockname()
        if logger.isEnabledFor(logging.INFO):
            logger.info("Server Socket Started on [port : %d]" % (port))

        return s

    def __create_client_socket__(self, address, port, stype, timeout = 5):
        """
        """
        s = socket.socket(socket.AF_INET, stype)
        s.settimeout(timeout)
        s.connect((address, port))
        return s


    def listenTCP(self, port, factory):
        """
        """
        s = self.__create_server_socket__(port, socket.SOCK_STREAM)

        with self.lock:
            self.__socketbuilders[s] = factory
            self.__factories.add(factory)

        s.listen(self.__backlog__)
        gobject.io_add_watch(s, gobject.IO_IN, self.__onconnect__)

        return s

    def callLater(self, callback, time):
        gobject.timeout_add_seconds(int(time), callback)

    def listenUDP(self, port, factory):
        """
        """
        with self.lock:
            self.__factories.add(factory)

        s = self.__create_server_socket__(port, socket.SOCK_DGRAM)
        proto = factory.build(s, 'localhost')
        return s

    def connectTCP(self, addr, port, factory):
        """
        """
        with self.lock:
            self.__factories.add(factory)

        s = self.__create_client_socket__(addr, port, socket.SOCK_STREAM)
        proto = factory.build(s, addr)
        with self.lock:
            self.__socketbuilders[s] = factory

    def connectUDP(self, addr, port, factory):
        """
        """
        with self.lock:
            self.__factories.add(factory)

        s = self.__create_client_socket__(addr, port, socket.SOCK_DGRAM)
        return factory.build(s, addr)

    def __signal_handler__(self, *args):
        self.loop.quit()





def Install():
    import reactor.session
    gtkreactor = GTKReactor()

    reactor.session.reactor = gtkreactor
