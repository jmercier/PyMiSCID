
import codebench.log
import logging.config
logging.getLogger().setLevel(logging.DEBUG)


import bonjour
import rpc
import threading
import time
import omiscid
import proxy

c = rpc.RPCConnector()

class Observer(object):
    def __init__(self):
        self.proxys = {}

    def added(self, description):
        self.proxys[description.control.peerid] = proxy.VariableConnectorProxy(c, description.control, callback = self.proxy)

    def proxy(self, proxy):
        for v in proxy.variables:
            proxy.variables[v].addObserver(self.var_changed,v)
        self.callback = proxy.get_peers(callback = self.peers)

    def var_changed(self, value, vname):
        print (value, vname)

    def peers(self, peers):
        print "PEERS :", peers



def main():
        import omiscid
        import reactor

        sr = omiscid.ServiceRepository("_bip._tcp")
        o = Observer()
        sr.addObserver(o)
        c.addObserver(o)
        r = reactor.Reactor()
        r.run()

if __name__ == '__main__':
    main()
