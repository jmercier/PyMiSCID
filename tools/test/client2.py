import codebench.log
import logging.config
logging.config.fileConfig("logging.conf")

import scipy
import ctypes
import pymiscid


class obs(object):
	def added(self, proxy, s):
		print "added"
		s.connectTo("input", proxy, "output")

	def removed(self, proxy, s):
		print "removed"


def received(msg):
	print msg

def main():
	s = pymiscid.factory.create("pytest2")
	s.addConnector("input", "this is an output", pymiscid.INPUT)
	s.input.dispatcher.receivedEvent.addObserver(received)
	sr = pymiscid.factory.createServiceRepository()
	sr.addObserver(obs(), s, filter = pymiscid.NameIs("pytest"))
	pymiscid.run()


if __name__ == "__main__":
	main()
