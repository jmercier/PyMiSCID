import codebench.log
import logging.config
logging.config.fileConfig("logging.conf")
import pymiscid
from twisted.internet import task

i = 0

def callback(var, text):
    print var

class obs(object):
    def added(self, proxy):
        proxy.addVariableObserver('bonjour', callback, "bonjour")
        print "added"

    def removed(self, proxy):
        print "removed"

def main():
    sr = pymiscid.factory.createServiceRepository()
    observer = obs()
    sr.addObserver(observer, filter = pymiscid.NameIs("srv"))

    pymiscid.run()

if __name__ == '__main__':
    main()
