import connector
import bip.protocol as protocol

class ConnectorDescription(object):
    def __init__(self, desc, addr):
        self.__dict__.update(desc)
        self.addr = addr
        self.peerid = protocol.PeerID(self.peerid)


class ServiceDescription(object):
    def __init__(self, desc):
        self.__dict__.update(desc)
        self.connectors     = [ConnectorDescription(c, self.addr) for c in desc.pop('connectors')]
        self.control        = ConnectorDescription(desc.pop('control'), self.addr)





