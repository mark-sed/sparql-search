#!/usr/bin/python3
"""
SPARQL-SEArch
Interactive application for searching through SPARQL databases.
"""

__author__ = "Marek Sedlacek (xsedla1b)"
__date__ = "December 2021"
__version__ = "0.0.1"
__email__ = ("xsedla1b@fit.vutbr.cz", "mr.mareksedlacek@gmail.com")

import sys
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMainWindow,
                             QApplication,
                             QAction,
                             QPushButton,
                             QFileDialog,
                             QLabel,
                             QLineEdit,
                             QFormLayout,
                             QSlider, 
                             QCheckBox,
                             QProgressBar,
                             QComboBox,
                             QWidgetAction,
                             QSizePolicy,
                             QTextBrowser,
                             QMessageBox)
from PyQt5.QtGui import (QPixmap,
                         QIntValidator)

from SPARQLWrapper import SPARQLWrapper2, JSON, XML


class MainWindow(QMainWindow):
    """
    Main application window
    """

    def __init__(self, width=1024, height=600):
        super(MainWindow, self).__init__()
        self.setFixedSize(width, height)
        # Center the screen
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        center = QApplication.desktop().screenGeometry(screen).center()
        self.move(center.x() - self.width() // 2, 
                  center.y() - self.height() // 2)
        self.initUI()

    def initUI(self):

        self.show()

if __name__ == "__main__":
    #sparql = SPARQLWrapper2("http://dbpedia.org/sparql")
    #sparql.setQuery(""" 
    #        SELECT ?label
    #        WHERE { <http://dbpedia.org/resource/Asturias> rdfs:label ?label }
    #""")
    #
    #for result in sparql.query().bindings:
    #    print('%s: %s' % (result["label"].lang, result["label"].value))

    app = QApplication(sys.argv)

    win = MainWindow()

    sys.exit(app.exec_())
