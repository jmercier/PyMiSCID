import codebench.log
import logging.config
logging.getLogger().setLevel(logging.INFO)

import connector
import time

c1 = connector.Connector()
c2 = connector.Connector()

c1.start()

c2.connect(('localhost', c1.tcp))

import threading

n = 1000

sending_times = [0] * n
receiving_times = [0] * n

i = 0
j = 0

def received(msg):
    t = time.time()
    global i
    if i != 0:
        receiving_times[i - 1] = t
        #print i, t, sending_times[i - 1]
    i += 1

c2.receivedEvent.addObserver(received)
size = int(1e7)
msg = bytearray(size)

def send():
    global j
    if j == (n):
        #reactor.Reactor().stop(join = False)
        return False
    t = time.time()
    c1.send(msg, udp = False)
    if j != 0:
        sending_times[j - 1] = t
    j += 1
    return 1

import reactor
r = reactor.Reactor()
r.callLater(send, 0.05)
r.run()

#import numpy as np
#diff = np.array(receiving_times) - np.array(sending_times)
#print np.average(diff), np.std(diff)
