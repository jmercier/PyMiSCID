import connector
import bip.protocol as protocol

class ConnectorProxy(object):
    def __init__(self, desc, addr):
        self.__dict__.update(desc)
        self.addr = addr
        self.peerid = protocol.PeerID(self.peerid)


class ServiceProxy(object):
    def __init__(self, desc):
        addr = '127.0.0.1'
        self.connectors     = [ConnectorProxy(c, addr) for c in desc.pop('connectors')]
        self.control        = ConnectorProxy(desc.pop('control'), addr)
        self.__dict__.update(desc)





