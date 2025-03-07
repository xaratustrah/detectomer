#
# SDR2ZMQ
# 
# (2025) xaratustrah@github
#

import sys
import os
from pyqtgraph.Qt import QtWidgets

from .zmqreceiver import ZMQReceiver

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ZMQReceiver()
    window.show()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()
    