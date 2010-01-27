import time
import pymiscid
import thread
import weakref
from codebench.overlay import ubigraph

import time 


graph = ubigraph.UbiGraph()
old_build_fct = pymiscid.service.ServiceProxy.__build__

include_cloacked = True
interval = 2.0

interval = 2

snstyle = { "shape" : 'dodecahedron',
            "color" : '#ffff00',
            "size"  : '2', }

sestyle = { "strength" : '2.0',
            "width"    : '2.0',
            "color"    : '#ffffff',}

clnstyle = { "color" : "#ffffff" }


cnstyle = {}

cestyle = { "strength" : '0.1',
            "spline"   : 'true',
            "stroke"   : 'dotted',
            "width"    : '15.0',
            "color"    : '#ffffff'}

clsnstyle = snstyle.copy()
clsnstyle['color'] = '#ffffff'
clsestyle = sestyle.copy()
clsestyle['color'] = '#ffffff'
clcnstyle = cnstyle.copy()
clcnstyle['color'] = "#ffffff"

ccolor = { pymiscid.OUTPUT   : '#ff0000',
           pymiscid.INPUT    : '#00ff00',
           pymiscid.INOUTPUT : '#0000ff', }



def update_fct(wproxy, nodes):
    i = 0
    pnodes = []
    try:
        while True:
            proxy = None
            time.sleep(interval)
            proxy = wproxy()
            if proxy is None:
                break
            seen_node = []
            for c in proxy.connectors:
                for peer in proxy.getConnectedPeers(c):
                    if include_cloacked:
                        seen_node.append(peer)
                        seen_node.append(peer.base())
                        if peer not in graph:
                            graph.add_node(peer.base(), label = 'Cloacked Service [%d]' % peer.base(), **clsnstyle)
                            graph.add_node(peer, **clnstyle)
                            graph.add_edge(peer.base(), peer, **clsestyle)
                            pnodes += [peer, peer.base()]
                    if (peer in graph) and (peer not in graph.neighbors(proxy[c].peerid)):
                            graph.add_edge(proxy[c].peerid, peer, **cestyle)

                if len(graph.neighbors(proxy[c].peerid)) > 1:
                    graph.set_node_attr(proxy[c].peerid, visible = "true")
                else:
                    graph.set_node_attr(proxy[c].peerid, visible = "false")
            for p in pnodes:
                if p not in seen_node:
                    pnodes.remove(p)
                    graph.remove_node(p)
    except Exception,err:
        pass
    finally:
        for n in nodes + pnodes:
            graph.remove_node(n)




def __build_replacement__(self, *args, **kwargs):
    old_build_fct(self, *args, **kwargs)
    try:
        self.supervisor.acquire()
    except:
        pass
    nodes = [self.peerid]
    if self.peerid in graph:
        graph.remove_node(self.peerid)
    graph.add_node(self.peerid, label = self.name.value + ' [' + str(self.peerid) + ']', **snstyle)
    for c in self.connectors:
        if self[c].peerid in graph:
            graph.remove_node(self[c].peerid)
        nodes.append(self[c].peerid)
        graph.add_node(self[c].peerid, label = c, color = ccolor[self[c].type], **cnstyle)
        graph.add_edge(self.peerid, self[c].peerid, **sestyle)

    thread.start_new_thread(update_fct, (weakref.ref(self),nodes))


pymiscid.service.ServiceProxy.__build__ = __build_replacement__

sr = pymiscid.factory.createServiceRepository()

