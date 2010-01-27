#import codebench.twisted.internet.qt4reactor
#codebench.twisted.internet.qt4reactor.install()

import codebench.log
import logging.config
logging.config.fileConfig("logging.conf")
import pymiscid


class TypeObserver(object):
        def __init__(self):
                self.srs = {}

        def added(self, type):
                self.srs[type] = pymiscid.factory.createServiceRepository(domain = type)

        def removed(self, type):
                del self.srs[type]

def main():
        s = pymiscid.factory.create("test")
        dr = pymiscid.factory.createDomainRepository()
        obs = TypeObserver()
        dr.addObserver(obs)
        s.start()
        pymiscid.run()

if __name__ == '__main__':
    main()
