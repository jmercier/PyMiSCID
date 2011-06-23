import browser
import sys
from PyQt4 import Qt

#import reactor

if __name__ == '__main__':
    app = Qt.QApplication(sys.argv)
    wi = Qt.QMainWindow()

    win = browser.Ui_MainWindow()
    win.setupUi(wi)
    wi.show()
    #reactor.Reactor().run()
    #app.exec_()

