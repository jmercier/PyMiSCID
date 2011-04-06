import codebench.log as log
import logging.config
logging.config.fileConfig("logging.conf")

class TestListener(object):
    def received(self, *args):
        print "RECEIVED", len(args[0])

    def connected(self, *args):
        print "CONNECTED", args

    def disconnected(self, *args):
        print "DISCONNECTED", args

if __name__ == '__main__':
    import socket
    import bip.protocol
    import time
    import gobject
    import connector
    import rpc

    class obj(object):
        @rpc.remote_callable
        def method1(self, *args):
            return args

    import rpc

    f = rpc.RPCConnector()
    o = obj()
    f.bind(o)

    f.start()
    print f.tcp, f.udp

    import reactor
    reactor.Reactor().run()
    f.close()
