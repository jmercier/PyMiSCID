import log
import logging.config
logging.config.fileConfig("logging.conf")

from codebench.ctypes import rt

import scipy
import pymiscid
import ctypes
import time

from twisted.internet import task

i = 0

class SharedArrayServer(object):
	def __init__(self, arr):
		self.arr = arr
		self.sems = {}

	def connected(self, peerid, conn):
		conn(self.arr.name)
		self.sems[peerid] = None 

	def disconnected(self, peerid, conn):
		del self.sems[peerid]


def main():
	shmem = rt.NamedArray('B', 512 * 512 * 3)
	srv = pymiscid.factory.create("pytest")
	srv.addConnector("output", "this is an output", pymiscid.OUTPUT)
	srv.output.dispatcher.addObserver(SharedArrayServer(shmem), srv.output)
	srv.start()
	pymiscid.run()


if __name__ == "__main__":
	main()
