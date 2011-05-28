from __future__ import print_function

import socket
import thread
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s2 = []

def handler(*args):
    print ("Thread Start")
    try:
        s.bind(('localhost', 5000))
        s.listen(2)
        s3, addr = s.accept()
        s2.append(s3)
        result = s3.recv(100)
        print ("EUH", result)
    except (Exception, e):
        print (e)
    print ("Thread Stop")

thread.start_new_thread(handler, ())
