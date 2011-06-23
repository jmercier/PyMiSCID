
import codebench.log
import logging.config
logging.getLogger().setLevel(logging.DEBUG)


import bonjour
import rpc
import threading
import time
import proxy
import omiscid

services = {}
domains = {}

def rem(proxy, win):
    child, parent = services[proxy.peerid]
    parent.removeChild(child)
    win.treeWidget.update()

def descr(proxy, win, parent):
    child = Qt.QTreeWidgetItem([proxy.name, str(proxy.peerid)])
    services[proxy.peerid] = (child, parent)
    parent.addChild(child)
    for c in proxy.connectors:
        cview = Qt.QTreeWidgetItem([c.name, str(c.peerid)])
        child.addChild(cview)
    win.treeWidget.update()
    pass
    #c = rpc.RPCConnector()
    #c.connect(addr, port)
    #time.sleep(0.5)
    #p = proxy.ServiceProxy(c.call("get_description").wait())
    #print [a.description for a in p.connectors]
    #print (p.connectors)
    #c.close()




class TypeObserver(object):
        def __init__(self):
            self.srs = {}
            self.items = {}

        def added(self, dtype, win):
            #btd, bsd = bonjour.BonjourServiceDiscovery(dtype), ServiceObserver()
            self.srs[dtype] = osr = omiscid.ServiceRepository(dtype)
            witem = Qt.QTreeWidgetItem([dtype])
            self.items[dtype] = win.treeWidget.topLevelItemCount()
            win.treeWidget.addTopLevelItem(witem)
            win.treeWidget.update()
            osr.addedEvent.addObserver(descr, win, witem)
            osr.removedEvent.addObserver(rem, win)
            #btd.addObserver(bsd)
            #self.srs[dtype] = (btd, bsd)
            #btd.start()

        def removed(self, dtype, win):
            ic = self.items[dtype]
            win.treeWidget.takeTopLevelItem(self.items[dtype])
            for i in self.items:
                if self.items[i] > ic:
                    self.items[i] -= 1
            del self.items[dtype]
            pass
            #del self.srs[dtype]

import browser
import sys
from PyQt4 import Qt

def main():
    app = Qt.QApplication(sys.argv)
    wi = Qt.QMainWindow()

    win = browser.Ui_MainWindow()
    win.setupUi(wi)
    wi.show()

    s = bonjour.BonjourTypeDiscovery("_bip")
    s.start()
    obs = TypeObserver()
    s.addObserver(obs, win)

    import reactor
    r = reactor.Reactor()
    r.run()

if __name__ == '__main__':
    main()
