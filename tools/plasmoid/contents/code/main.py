# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.plasma import Plasma
from PyKDE4 import plasmascript
from PyKDE4.kdecore import i18n
from PyKDE4.kdeui import *
import pymiscid

import time
import weakref
import traceback
import socket
import os

odd_color_1 = QColor(10,10,10)
odd_color_2 = QColor(10,10,10)
even_color_1 = QColor(10,10,10)
even_color_2 = QColor(100,100,100)
    

class DomainTitleWidget(QGraphicsWidget):
         title = "Unknown Title"
         dw = None
         hover = False

         def __init__(self):
                QGraphicsWidget.__init__(self)
                font = Plasma.Theme.defaultTheme().font(Plasma.Theme.DefaultFont)
                height = QFontMetrics(font).height()

                self.setAcceptHoverEvents(True)
                self.setMinimumHeight(height)
                self.setMaximumHeight(height)

         def paint(self, painter, opt, widget):
                frame = QRectF(QPointF(0, 0), self.geometry().size())
                painter.setPen(Qt.gray)
                painter.setBrush(Qt.black)
                painter.drawRect(frame)
                painter.setPen(Qt.white)
                frame.adjust(10, 1, -10, -1)
                painter.drawText(frame, Qt.AlignCenter | Qt.AlignTop, self.title + " (%d services)" % len(self.dw().managed_services))
                QGraphicsWidget.paint(self, painter, opt, widget)

         def mousePressEvent(self, evt):
                self.dw().toggleVisible()


         def hoverEnterEvent(self, evt):
                self.hover = True
                self.update()

         def hoverLeaveEvent(self, evt):
                self.hover = False
                self.update()

class DomainWidget(QGraphicsWidget):
        open = True

        def __init__(self, domain):
                QGraphicsWidget.__init__(self)
                self.layout = QGraphicsLinearLayout(Qt.Vertical)
                self.layout.setSpacing(1)
                self.setLayout(self.layout)
                dtw = DomainTitleWidget()
                dtw.title = domain
                self.layout.addItem(dtw)
                dtw.dw = weakref.ref(self)

                self.managed_services = {}

        def toggleVisible(self):
                self.open = not self.open
                if self.open:
                    for sw in self.managed_services.itervalues():
                        self.layout.addItem(sw)
                        sw.show()
                else:
                    for sw in self.managed_services.itervalues():
                        self.layout.removeItem(sw)
                        sw.hide()
                self.update()

        def addService(self, name, sw):
                self.managed_services[name] = sw
                if self.open:
                    self.layout.addItem(sw)
                    self.update()

        def removeService(self, name):
                sw = self.managed_services.pop(name)
                if self.open:
                    self.layout.removeItem(sw)
                    self.update()


class ServiceWidget(QGraphicsWidget):
 hover = False
 data = { "name" : 'name', 'host' : 'host', 'time' : "time", 'peerid' : 'peerid', 'addr' : 'addr'}
 desc = {}
 odd = True
 def __init__(self):
     QGraphicsWidget.__init__(self)
     self.setAcceptHoverEvents(True)

     self.font = Plasma.Theme.defaultTheme().font(Plasma.Theme.DefaultFont)
     height = QFontMetrics(self.font).height()

     self.setMinimumHeight(2 * height)
     self.setMaximumHeight(2 * height)
     self.setMinimumWidth(280)

 def paint(self, painter, opt, widget):
     painter.setRenderHint(QPainter.Antialiasing)
     frame = QRectF(QPointF(0, 0), self.geometry().size())
     painter.setPen(Qt.black)
     grad = QLinearGradient(frame.topLeft(), frame.bottomLeft()) 
     grad.setColorAt(0, QColor(26, 33, 42))
     grad.setColorAt(1, QColor(20, 26, 33))
     painter.setBrush(QBrush(grad))
     painter.drawRect(frame)
     frame.adjust(10, 1, -10, -1)

     painter.setPen(Qt.white)
     self.font.setBold(True)
     painter.setFont(self.font)
     painter.drawText(frame, Qt.AlignLeft  | Qt.AlignTop, self.data['name'] )
     painter.drawText(frame, Qt.AlignRight  | Qt.AlignTop, self.data['peerid'])
     self.font.setBold(False)
     painter.setFont(self.font)
     painter.drawText(frame, Qt.AlignRight | Qt.AlignBottom, self.data['time'])
     if self.data['owner'] == os.environ['USER']:
        if (self.data['addr'] == '127.0.0.1') or (self.data['host'] == socket.gethostname()):
            painter.setPen(Qt.green)
        else:
            painter.setPen(Qt.yellow)
     else:
        painter.setPen(Qt.red)
     painter.drawText(frame, Qt.AlignLeft | Qt.AlignBottom, "%s@%s [%s]" % (self.data['owner'], self.data['host'], self.data['addr']))


 def hoverEnterEvent(self, evt):
        self.hover = True
        self.update()

 def hoverLeaveEvent(self, evt):
        self.hover = False
        self.update()

class LabelWidget(QGraphicsWidget):
        def __init__(self):
                QGraphicsWidget.__init__(self)
                self.font = Plasma.Theme.defaultTheme().font(Plasma.Theme.DefaultFont)
                self.font.setBold(True)
                height = QFontMetrics(self.font).height()
                self.setMinimumHeight(height)
                self.setMaximumHeight(height)


        def paint(self, painter, opt, widget):
                frame = QRectF(QPointF(0, 0), self.geometry().size())
                painter.setFont(self.font)
                painter.setPen(Qt.black)
                painter.drawText(frame, Qt.AlignCenter | Qt.AlignTop, "OMiSCID SWARM")


class OMiSCIDBrowserPlasmoid(plasmascript.Applet):
 def __init__(self, parent, args=None):
     plasmascript.Applet.__init__(self, parent)
     self.dwidgets = {}

 def init(self):
      self.setHasConfigurationInterface(False)
      self.setAspectRatioMode(Plasma.IgnoreAspectRatio)
      self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
      self.setMinimumWidth(425)

      self.layout = QGraphicsLinearLayout(Qt.Vertical, self.applet)
      self.layout.setSpacing(0)
      self.group = QLabel()

      self.stringlist = []
      self.setLayout(self.layout)
      self.label = LabelWidget()
      self.layout.addItem(self.label)
      self.srs = {}
      self.tds = pymiscid.bonjour.BonjourTypeDiscovery("_bip")
      self.tds.addedEvent.addObserver(self.typeAdded)
      self.tds.removedEvent.addObserver(self.typeRemoved)
      self.tds.run()

 def srvAdded(self, name, host, addr, port, txt, unknown, tname):
     try:
        data = {'peerid' : name, 'host' : host, 'addr' : addr, 'time' : str(time.ctime()), 'name' : txt['name'].strip('c/'), 'owner' : txt['owner'].strip('c/')}
        wid = ServiceWidget()
        wid.data = data
        self.dwidgets[tname].addService(name, wid)
        self.setLayout(self.layout)
        self.update()
     except Exception, err:
        traceback.print_exc()

 def srvRemoved(self, name, tname):
        self.dwidgets[tname].removeService(name)
        self.setLayout(self.layout)
        self.update()

 def typeAdded(self, tname):
     try:
        wid = DomainWidget(tname)
        self.dwidgets[tname] = wid
        self.layout.addItem(wid)

        sr = pymiscid.bonjour.BonjourServiceDiscovery(tname)
        id1 = sr.addedEvent.addObserver(self.srvAdded, tname)
        id2 = sr.removedEvent.addObserver(self.srvRemoved, tname)

        self.srs[tname] = (sr, id1, id2)
        sr.run()
        self.update()
     except Exception, err:
        traceback.print_exc()

 def typeRemoved(self, tname):
    try:
        wid = self.dwidgets.pop(tname)
        self.layout.removeItem(wid)
        sr, id1, id2 = self.srs.pop(tname)
        sr.addedEvent.removeObserver(id1)
        sr.removedEvent.removeObserver(id2)
        self.update()
    except Exception, err:
        traceback.print_exc()

def CreateApplet(parent):
 return OMiSCIDBrowserPlasmoid(parent)
