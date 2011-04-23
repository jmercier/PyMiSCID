from __future__ import print_function

import threading

class TimeoutError(Exception): pass

class DeferredResult(object):
    def __init__(self):
        self.__recv_evt__ = threading.Event()
        self.__results__ = []

    def __set_result__(self, result):
        self.__results__.append(result)
        self.__recv_evt__.set()
        self.__recv_evt__ = threading.Event()

    result = property(fset = __set_result__)


    def __call__(self, timeout = 10):
        if len(self.__results__) > 0:
            return self.__results__.pop()

        if self.__recv_evt__.wait(timeout = timeout):
            return self.__results__.pop()

        raise TimeoutError("Deferred Result Timeout Reached")



class ProxyObject(object):
    __active__ = False

    def __init__(self, connector, peerid = None):
        self.peerid = peerid
        connector.dispatcher.addObserver(self)

    def connected(self, *args):
        print(args)

    def disconnected(self, *args):
        print(args)

    def received(self, *args):
        print(args)


    def call(self, method, *args):
        self.connector



