import codebench.log
import logging.config
logging.config.fileConfig("logging.conf")
import pymiscid
from twisted.internet import task

i = 0

def main():
    srv = pymiscid.factory.create('srv')
    srv.addVariable("bonjour", "Int:", "Int:", pymiscid.READ_WRITE, value = 12)
    srv.addConnector("conn1", "this is a connector", pymiscid.INOUTPUT)
    srv.start()
    def upd_var():
        global i
        i += 1
        srv.setVariableValue("bonjour", i)

    tsk = task.LoopingCall(upd_var)
    tsk.start(1)
    pymiscid.run()

if __name__ == '__main__':
    main()
