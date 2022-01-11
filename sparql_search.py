#!/usr/bin/python3
"""
SPARQL-SEArch
Interactive application for searching through SPARQL databases.
"""

__author__ = "Marek Sedlacek (xsedla1b)"
__date__ = "December 2021"
__version__ = "1.0.0"
__email__ = ("xsedla1b@fit.vutbr.cz", "mr.mareksedlacek@gmail.com")

from re import S, escape, search
import sys
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QHBoxLayout, QMainWindow,
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
                             QComboBox, QVBoxLayout,
                             QWidgetAction,
                             QSizePolicy,
                             QTextBrowser,
                             QMessageBox,
                             QScrollArea
                             )
from PyQt5.QtGui import (QPixmap,
                         QIntValidator)

from SPARQLWrapper import SPARQLWrapper, JSON


def search_dbpedia(sparql, keyword, limit=10, offset=0, timeout=100000):
    sparql.setQuery("""
        define input:ifp "IFP_OFF"  select ?s1 as ?c1, (bif:search_excerpt (bif:vector ('{0}'), ?o1)) as ?c2, ?sc, ?rank, ?g where {{
            {{
                {{ select ?s1, (?sc * 3e-1) as ?sc, ?o1, (sql:rnk_scale (<LONG::IRI_RANK> (?s1))) as ?rank, ?g where  
                    {{ 
                        quad map virtrdf:DefaultQuadMap 
                        {{ 
                            graph ?g 
                            {{ 
                                ?s1 ?s1textp ?o1 .
                                ?o1 bif:contains  '"{0}"'  option (score ?sc)  .
                            }}
                        }}
                    }}
                    order by desc (?sc * 3e-1 + sql:rnk_scale (<LONG::IRI_RANK> (?s1)))  limit {1}  offset {2} 
                }}
            }}
        }}
    """.format(keyword, limit, offset))
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(timeout)
    sparql.addExtraURITag("timeout", str(timeout))
    return sparql.query().convert()["results"]["bindings"]

def search_general_db(sparql, keyword, limit=10, offset=0, timeout=10000):
    sparql.setQuery("""
        SELECT DISTINCT ?c1 ?p1 ?o1 WHERE {{
            ?c1 ?p1 ?o1 
            filter contains(str(?c1),"{}")
        }} LIMIT {} OFFSET {}
    """.format(keyword, limit, offset))
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(timeout)
    sparql.addExtraURITag("timeout", str(timeout))
    print(sparql.query().convert()["results"])
    return sparql.query().convert()["results"]["bindings"]
    pass

def get_dbpedia_info(sparql, uri, limit=10, offset=0, lang="en"):
    sparql.setQuery("""
        PREFIX pref: <http://xmlns.com/foaf/0.1/>
        PREFIX onto: <http://dbpedia.org/ontology/>

        SELECT DISTINCT ?name ?wiki ?desc
        WHERE {{
            <{}> pref:isPrimaryTopicOf ?wiki ; pref:name ?name ; onto:abstract ?desc.
            FILTER(LANG(?desc) = "{}")
        }} LIMIT {} OFFSET {}
    """.format(uri, lang, limit, offset))
    sparql.setReturnFormat(JSON)
    all_res = sparql.query().convert()["results"]["bindings"]
    if len(all_res) == 0:
        return (uri, format_uri(uri), "", "")
    return (uri, all_res[0]["name"]["value"], all_res[0]["desc"]["value"], all_res[0]["wiki"]["value"])

def get_all_triplets(sparql, uri, limit=10, offset=0):
    sparql.setQuery("""
        SELECT DISTINCT *
        WHERE {{
            <{}> ?p ?o
        }} LIMIT {} offset {}
    """.format(uri, limit, offset))
    sparql.setReturnFormat(JSON)
    all_res = sparql.query().convert()["results"]["bindings"]
    return [(uri, x["p"]["value"], x["o"]["value"]) for x in all_res]

def format_uri(uri):
    name = uri[uri.rindex("/")+1:]
    name = name.replace("_", " ")
    name = name.replace("-", " ")
    name = name.replace("#", ": ")
    return name

def get_db_all(sparql, limit=10, offset=0):
    sparql.setQuery("""
        SELECT DISTINCT ?s
        WHERE {{
            ?s ?p ?o
        }} LIMIT {} offset {}
    """.format(limit, offset))
    sparql.setReturnFormat(JSON)
    all_res = sparql.query().convert()["results"]["bindings"]
    return [(x["s"]["value"], format_uri(x["s"]["value"])) for x in all_res]

def get_wiki_link(sparql, uri):
    sparql.setQuery("""
        PREFIX pref: <http://xmlns.com/foaf/0.1/>

        SELECT ?wiki {{
            <{}> pref:isPrimaryTopicOf ?wiki
        }}
    """.format(uri))
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()["results"]["bindings"][0]["wiki"]["value"]

def get_description(sparql, uri, lang="en"):
    sparql.setQuery("""
        PREFIX pref: <http://dbpedia.org/ontology/>

        SELECT ?res {{
            <{}> pref:abstract ?res
        }}
    """.format(uri))
    sparql.setReturnFormat(JSON)
    all_desc = sparql.query().convert()["results"]["bindings"]
    for value in all_desc:
        if value["res"]["xml:lang"] == lang:
            return value["res"]["value"]

def get_name(sparql, uri):
    sparql.setQuery("""
        PREFIX pref: <http://xmlns.com/foaf/0.1/>

        SELECT ?name {{
            <{}> pref:name ?name
        }}
    """.format(uri))
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()["results"]["bindings"][0]["name"]["value"]

class ResultLabel(QLabel):
    def __init__(self, text, uri, window, parent = None):
        super(ResultLabel, self).__init__(text, parent)
        self.window = window
        self.uri = uri

    def mousePressEvent(self, event):
        self.window.more_info(self.uri)

class MainWindow(QMainWindow):
    """
    Main application window
    """

    def __init__(self, width=1024, height=600):
        super(MainWindow, self).__init__()
        #self.setFixedSize(width, height)
        self.setWindowTitle("Sparql Search")
        self.resize(width, height)
        # Center the screen
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        center = QApplication.desktop().screenGeometry(screen).center()
        self.move(center.x() - self.width() // 2, 
                  center.y() - self.height() // 2)

        self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")

        # Adding a menu bar
        self.menuBar().clear()
        self.menu_bar = self.menuBar()

        self.button_preferences = QAction("Preferences")
        self.mb_preferences = self.menu_bar.addAction(self.button_preferences)
        self.button_preferences.triggered.connect(self.show_preferences)

        self.button_endpoint = QAction("Add custom endpoint")
        self.mb_endpoint = self.menu_bar.addAction(self.button_endpoint)
        self.button_endpoint.triggered.connect(self.show_endpoint)

        self.button_about = QAction("About")
        self.mb_about = self.menu_bar.addAction(self.button_about)
        self.button_about.triggered.connect(self.show_about)

        # Layout
        self._layout = QVBoxLayout()
        self.top_layout = QHBoxLayout()

        # UI
        # DB select
        self.in_db = QComboBox()
        self.in_db.addItem("DBpedia")
        self.in_db.addItem("NIH")
        self.in_db.addItem("Bgee")
        self.in_db.addItem("UniProt")
        self.in_db.addItem("BioOntology")
        self.in_db.addItem("URIBurner")
        self.in_db.addItem("NeXtProt")
        self.in_db.currentIndexChanged.connect(self.in_db_changed)
        self.top_layout.addWidget(self.in_db)

        # home button
        self.home_button = QPushButton("")
        self.home_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirHomeIcon))
        self.home_button.pressed.connect(self.home_pressed)
        self.top_layout.addWidget(self.home_button)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search keywords")
        self.search_box.textChanged.connect(self.search_box_changed)
        self.top_layout.addWidget(self.search_box)

        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.pressed.connect(self.search_button_pressed)
        self.search_button.setEnabled(False)
        self.top_layout.addWidget(self.search_button)

        # Page control
        self.page_layout = QHBoxLayout()

        self.left_button = QPushButton("<")
        self.left_button.setEnabled(False)
        self.left_button.pressed.connect(self.left_button_pressed)

        self.page_number = QLabel("page 0") 
        self.page_number.setStyleSheet(
                            "QLabel"
                            "{"
                            "padding : 10px;"
                            "}")
        self.page_number.setAlignment(QtCore.Qt.AlignCenter)
        self.page_number.adjustSize()

        self.right_button = QPushButton(">")
        self.right_button.setEnabled(False)
        self.right_button.pressed.connect(self.right_button_pressed)

        self.page_layout.addWidget(self.left_button)
        self.page_layout.addWidget(self.page_number)
        self.page_layout.addWidget(self.right_button)

        self.db_searched = True
        self.timeout = 10000

        # Add layout
        self._layout.addLayout(self.top_layout)
        self._layout.addLayout(self.page_layout)
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        wid.setLayout(self._layout)

        self.results = [QLabel("")]
        self._layout.addWidget(self.results[0])
        
        self.initUI()
        
        self.about_window = AboutWindow(self)
        self.preferences_window = Preferences(self)
        self.add_endpoint_window = AddCustomEndpoint(self)

        self.in_db_changed(self.in_db.currentIndex())

        self.update()

    def initUI(self):
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.append("")
        self.limit = 10
        self.offset = 0
        self.show()

    def show_preferences(self):
        """
        Shows preferences settings
        """
        self.preferences_window.show()

    def show_endpoint(self):
        """
        Shows add custom endpoint window
        """
        self.add_endpoint_window.show()

    def show_about(self):
        """
        Shows about info
        """
        self.about_window.show()

    def search_box_changed(self, v):
        if len(v) > 0:
            self.search_button.setEnabled(True)
        else:
            self.search_button.setEnabled(False)

    def home_pressed(self):
        self.search_db_changed(None)

    def left_button_pressed(self):
        if self.offset > self.limit:
            self.offset -= self.limit
        else:
            self.offset = 0
            self.left_button.setEnabled(False)
        self.right_button.show()
        if self.db_searched:
            self.search_db()
        else:
            self.search()
        self.page_number.setText("page "+str(self.offset//self.limit+1))

    def right_button_pressed(self):
        self.offset += self.limit
        self.left_button.setEnabled(True)
        if self.db_searched:
            self.search_db()
        else:
            self.search()
        self.page_number.setText("page "+str(self.offset//self.limit+1))

    def clear_results(self):
        for r in self.results:
            self._layout.removeWidget(r)
            r.setParent(None)
        self._layout = QVBoxLayout()
        self.top_layout = QHBoxLayout()
        self.top_layout.addWidget(self.in_db)
        self.top_layout.addWidget(self.home_button)
        self.top_layout.addWidget(self.search_box)
        self.top_layout.addWidget(self.search_button)

        self.page_layout = QHBoxLayout()
        self.page_layout.addWidget(self.left_button)
        self.page_layout.addWidget(self.page_number)
        self.page_layout.addWidget(self.right_button)

        self._layout.addLayout(self.top_layout)
        self._layout.addLayout(self.page_layout)
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        wid.setLayout(self._layout)

        self.results = [QLabel("")]
        self._layout.addWidget(self.results[0])
        self.update()

    def search_button_pressed(self):
        self.offset = 0
        self.db_searched = False
        self.search()

    def search_db_changed(self, _):
        self.offset = 0
        self.db_searched = True
        self.search_db()

    def search_db(self):
        print("Searching top DB at ", self.offset)
        self.right_button.show()
        self.clear_results()
        self.page_number.setText("page "+str(self.offset//self.limit+1))
        results = get_db_all(self.sparql, self.limit, self.offset)
        for result in results:
            d = ResultLabel(result[1], result[0], self)
            d.setWordWrap(True)
            d.adjustSize()
            d.setStyleSheet("QLabel::hover"
                        "{"
                        "background-color : #b365f0;"
                        "}"
                        "QLabel"
                        "{"
                        "padding : 5px;"
                        "font-size: 15px;"
                        "font-weight: bold;"
                        "}")
            self.results.append(d)
            self._layout.addWidget(d)
        if len(results) == self.limit:
            self.right_button.setEnabled(True)
        else:
            self.right_button.setEnabled(False)
        self.update()

    def search(self):
        keyword = self.search_box.text()
        db = self.in_db.currentIndex()
        print("Searching ", keyword, " in db ", db, " at ", self.offset)
        self.right_button.show()
        if self.offset == 0:
            self.left_button.setEnabled(False)
        self.page_number.setText("page "+str(self.offset//self.limit+1))
        self.clear_results()
        self.results = []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if db == 0:
            # DBPedia
            results = search_dbpedia(self.sparql, keyword, self.limit, self.offset, self.timeout)
        else:
            results = search_general_db(self.sparql, keyword, self.limit, self.offset, self.timeout)
        for result in results:
            data = get_dbpedia_info(self.sparql, result["c1"]["value"])
            header = data[1]
            body = data[2]
            wiki = "" if len(data[3]) == 0 else "  <small><a href="+data[3]+">wiki</a></small>"
            d = ResultLabel(header+body, data[0], self)
            d.setTextFormat(Qt.RichText)
            d.setText("<html><b>"+header+"</b>"+wiki+"<br>"+body+"</html>")
            d.setOpenExternalLinks(True)
            d.setWordWrap(True)
            d.adjustSize()
            d.setStyleSheet("QLabel::hover"
                        "{"
                        "background-color : #b365f0;"
                        "}"
                        "QLabel"
                        "{"
                        "padding : 5px;"
                        "font-size: 15px"
                        "}")
            self.results.append(d)
            self._layout.addWidget(d)
        if len(results) == self.limit:
            self.right_button.setEnabled(True)
        else:
            self.right_button.setEnabled(False)
        self.update()
        QApplication.restoreOverrideCursor()

    def search_as_keyword(self):
        self.search_box.setText(self.keyword)
        self.right_button.show()
        self.search_button_pressed()

    def more_info(self, uri):
        print("More info ", uri)
        self.right_button.hide()
        self.page_number.setText("")
        self.left_button.setEnabled(True)
        # Increase offset so left works correctly
        self.offset += self.limit
        self.clear_results()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        data = get_dbpedia_info(self.sparql, uri)
        search_button = QPushButton("Search as keyword")
        self.keyword = data[1]
        search_button.pressed.connect(self.search_as_keyword)
        search_button.setFixedSize(150, 30)
        header = data[1]
        body = data[2]
        wiki = "" if len(data[3]) == 0 else "<a href="+data[3]+">Wikipedia</a>"
        hlabel = QLabel()
        hlabel.setTextFormat(Qt.RichText)
        hlabel.setText("<html><h1>"+header+"</h1><br>"+wiki+"</html>")
        hlabel.setOpenExternalLinks(True)
        hlabel.setStyleSheet(
                    "QLabel"
                    "{"
                    "padding : 5px;"
                    "font-size: 15px"
                    "}")
        hlabel.adjustSize()
        self.results.append(search_button)
        self.results.append(hlabel)
        self._layout.addWidget(search_button)
        self._layout.addWidget(hlabel)
        bodylabel = QLabel(body)
        bodylabel.setWordWrap(True)
        bodylabel.setStyleSheet(
                    "QLabel"
                    "{"
                    "padding : 5px;"
                    "}")
        bodylabel.adjustSize()
        self.results.append(bodylabel)
        self._layout.addWidget(bodylabel)
        results = get_all_triplets(self.sparql, uri, 20)
        text = ""
        for _, p, o in results:
            if p[:4] == "http":
                p_form = "<a href="+p+">"+p+"</a>"
            else:
                p_form = p
            if o[:4] == "http":
                o_form = "<a href="+o+">"+o+"</a>"
            else:
                o_form = o
            text += "<i>in predicate</i> "+p_form+" <i>with</i> "+ o_form + "<br>"
        d = QLabel()
        d.setWordWrap(True)
        d.setTextFormat(Qt.RichText)
        d.setText("<html>"+text+"</html>")
        d.setOpenExternalLinks(True)
        d.adjustSize()
        d.setStyleSheet(
                    "QLabel"
                    "{"
                    "padding : 5px;"
                    "font-size: 15px"
                    "}")
        self.results.append(d)
        self._layout.addWidget(d)
        self.update()
        QApplication.restoreOverrideCursor()

    def in_db_changed(self, v):
        if v == 0:
            self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        elif v == 1:
            self.sparql = SPARQLWrapper("http://id.nlm.nih.gov/mesh")
        elif v == 2:
            self.sparql = SPARQLWrapper("https://bgee.org/sparql")
        elif v == 3:
            self.sparql = SPARQLWrapper("https://sparql.uniprot.org")
        elif v == 4:
            self.sparql = SPARQLWrapper("http://sparql.bioontology.org")
        elif v == 5:
            self.sparql = SPARQLWrapper("http://uriburner.com/sparql")
        elif v == 6:
            self.sparql = SPARQLWrapper("https://api.nextprot.org/sparql")
        else:
            try:
                self.sparql = SPARQLWrapper(self.in_db.itemText(v))
            except Exception:
                print("Could not use db ", v, file=sys.stderr)
        try:
            self.search_db_changed(v)
        except Exception:
            print("Could not use db ", v, file=sys.stderr)
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setWindowTitle("Endpoint error")
            error_msg.setText("Endpoint "+self.in_db.itemText(v)+" could not be reached!")
            error_msg.setStandardButtons(QMessageBox.Close)
            error_msg.exec()
            self.in_db.setCurrentIndex(0)
        


class AddCustomEndpoint(QMainWindow):
    """
    Window containing search parameters
    """

    def __init__(self, parent=None):
        """
        Constructor
        :param parent Window that should be this window's parent
        """
        super(AddCustomEndpoint, self).__init__(parent)
        self.parent = parent
        self.setWindowTitle("Add Custom Endpoint")
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMinimizeButtonHint)

        # Input form
        self.form_layout = QFormLayout()

        # Results
        self.custom_input = QLineEdit()
        self.form_layout.addRow("Endpoint URL", self.custom_input)

        # Save and close
        self.close_button = QPushButton("Add and close", self)
        self.close_button.pressed.connect(self.save_and_close)
        self.form_layout.addRow(self.close_button)

        # Layout and move
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        wid.setLayout(self.form_layout)
        self.move(parent.x() + parent.width()//2 - self.width(), parent.y())
        self.update()
        self.hide()

    def save_and_close(self):
        """
        Closes window
        """
        self.parent.in_db.addItem(self.custom_input.text())
        self.parent.in_db.setCurrentIndex(self.parent.in_db.count()-1)
        self.hide()


class Preferences(QMainWindow):
    """
    Window containing search parameters
    """

    def __init__(self, parent=None):
        """
        Constructor
        :param parent Window that should be this window's parent
        """
        super(Preferences, self).__init__(parent)
        self.parent = parent
        self.setWindowTitle("Preferences")
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMinimizeButtonHint)

        # Input form
        self.form_layout = QFormLayout()

        # Timeout
        self.timeout_input = QLineEdit()
        int_validator = QIntValidator()
        self.timeout_input.setValidator(int_validator)
        self.timeout_input.show()
        self.timeout_input.textChanged.connect(self.changed_timeout_input)
        self.form_layout.addRow("Search timeout [ms]", self.timeout_input)
        self.timeout_input.setText(str(parent.timeout))

        # Results
        self.results_input = QLineEdit()
        int_validator = QIntValidator()
        self.results_input.setValidator(int_validator)
        self.results_input.show()
        self.results_input.textChanged.connect(self.changed_results_input)
        self.form_layout.addRow("Results per page", self.results_input)
        self.results_input.setText(str(parent.limit))

        # Save and close
        self.close_button = QPushButton("Save and close", self)
        self.close_button.pressed.connect(self.save_and_close)
        self.form_layout.addRow(self.close_button)

        # Layout and move
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        wid.setLayout(self.form_layout)
        self.move(parent.x() + parent.width()//2 - self.width(), parent.y())
        self.update()
        self.hide()

    def changed_timeout_input(self, v):
        try:
            self.parent.timeout = int(v)
        except Exception:
            return

    def changed_results_input(self, v):
        try:
            self.parent.limit = int(v)
        except Exception:
            return

    def save_and_close(self):
        """
        Closes window
        """
        self.hide()


class AboutWindow(QMainWindow):
    """
    Displays info about the project
    """

    def __init__(self, parent=None):
        """
        Constructor
        :param parent Window that should be this window's parent
        """
        super(AboutWindow, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMinimizeButtonHint)
        # Center the screen
        self.setWindowTitle("About")
        self.setFixedSize(400, 210)
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        center = QApplication.desktop().screenGeometry(screen).center()
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)

        self.text_browser = QTextBrowser(self)
        self.text_browser.resize(self.width(), self.height())
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.append(
            """
            <div style=\"text-align:center\">
                <h3>Sparql Search</h3>
                <p>A program for searching in SPARQL databases, focused on biological data.</p><br>
                <b>Version: </b>{}<br>
                <b>Author: </b>Marek Sedlacek<br>
                Visit <a href=https://github.com/mark-sed/sparql-search>GitHub page</a> to check for a new version.</div>
                <br><br><small><i>Copyright (c) 2022 Marek Sedláček</i></small>
            """.format(__version__)
        )
        self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    sys.exit(app.exec_())
