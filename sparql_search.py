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
                             QMessageBox)
from PyQt5.QtGui import (QPixmap,
                         QIntValidator)

from SPARQLWrapper import SPARQLWrapper2, SPARQLWrapper, JSON, XML, N3, RDF


def search_dbpedia(keyword, limit=10, offset=0):
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
    return sparql.query().convert()["results"]["bindings"]

def get_dbpedia_info(uri, limit=10, offset=0, lang="en"):
    sparql.setQuery("""
        PREFIX pref: <http://xmlns.com/foaf/0.1/>
        PREFIX onto: <http://dbpedia.org/ontology/>

        SELECT ?name ?wiki ?desc
        WHERE {{
            <{}> pref:isPrimaryTopicOf ?wiki ; pref:name ?name ; onto:abstract ?desc.
            FILTER(LANG(?desc) = "{}")
        }} LIMIT {} OFFSET {}
    """.format(uri, lang, limit, offset))
    sparql.setReturnFormat(JSON)
    all_res = sparql.query().convert()["results"]["bindings"]
    if len(all_res) == 0:
        name = uri[uri.rindex("/")+1:]
        return (uri, name.replace("_", " "), "", "")
    return (uri, all_res[0]["name"]["value"], all_res[0]["desc"]["value"], all_res[0]["wiki"]["value"])

def get_all_triplets(uri, limit=10, offset=0):
    sparql.setQuery("""
        SELECT *
        WHERE {{
            <{}> ?p ?o
        }} LIMIT {} offset {}
    """.format(uri, limit, offset))
    all_res = sparql.query().convert()["results"]["bindings"]
    return [(uri, x["p"]["value"], x["o"]["value"]) for x in all_res]

def get_wiki_link(uri):
    sparql.setQuery("""
        PREFIX pref: <http://xmlns.com/foaf/0.1/>

        SELECT ?wiki {{
            <{}> pref:isPrimaryTopicOf ?wiki
        }}
    """.format(uri))
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()["results"]["bindings"][0]["wiki"]["value"]

def get_description(uri, lang="en"):
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

def get_name(uri):
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
        self.resize(width, height)
        # Center the screen
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        center = QApplication.desktop().screenGeometry(screen).center()
        self.move(center.x() - self.width() // 2, 
                  center.y() - self.height() // 2)

        # Layout
        self._layout = QVBoxLayout()
        self.top_layout = QHBoxLayout()

        # UI
        # DB select
        self.in_db = QComboBox()
        self.in_db.addItem("DBpedia")
        self.in_db.currentIndexChanged.connect(self.in_db_changed)
        self.top_layout.addWidget(self.in_db)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search term")
        self.search_box.textChanged.connect(self.search_box_changed)
        self.top_layout.addWidget(self.search_box)

        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.pressed.connect(self.search)
        self.search_button.setEnabled(False)
        self.top_layout.addWidget(self.search_button)

        self._layout.addLayout(self.top_layout)
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        wid.setLayout(self._layout)

        self.results = [QLabel("")]
        self._layout.addWidget(self.results[0])
        
        self.initUI()
        
        self.update()

    def initUI(self):
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        #self.text_browser.setObjectName("about_box")
        #self.text_browser.setStyleSheet("padding: 20px; color: red")
        self.text_browser.append("")
        #self._layout.addWidget(self.text_browser)
        self.limit = 10
        self.offset = 0
        self.show()

    def search_box_changed(self, v):
        if len(v) > 0:
            self.search_button.setEnabled(True)
        else:
            self.search_button.setEnabled(False)

    def result_clicked(self, value):

        print(value)

    def clear_results(self):
        for r in self.results:
            self._layout.removeWidget(r)
            r.setParent(None)
        self._layout = QVBoxLayout()
        self.top_layout = QHBoxLayout()
        self.top_layout.addWidget(self.in_db)
        self.top_layout.addWidget(self.search_box)
        self.top_layout.addWidget(self.search_button)

        self._layout.addLayout(self.top_layout)
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        wid.setLayout(self._layout)

        self.results = [QLabel("")]
        self._layout.addWidget(self.results[0])
        self.update()

    def search(self):
        keyword = self.search_box.text()
        db = self.in_db.currentIndex()
        print("Searching ", keyword, " in db ", db)
        self.clear_results()
        self.results = []
        if db == 0:
            # DBPedia
            results = search_dbpedia(keyword, self.limit, self.offset)
            for result in results:
                data = get_dbpedia_info(result["c1"]["value"])
                header = data[1]
                body = data[2]
                wiki = "" if len(data[3]) == 0 else "  <small><a href="+data[3]+">wiki</a></small>"
                print(wiki)
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
        self.update()

    def more_info(self, uri):
        print("More info ", uri)
        self.clear_results()
        data = get_dbpedia_info(uri)
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
        self.results.append(hlabel)
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
        results = get_all_triplets(uri)
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

    def in_db_changed(self, v):
        if v == 0:
            sparql = SPARQLWrapper("http://dbpedia.org/sparql")


if __name__ == "__main__":
    #sparql = SPARQLWrapper2("http://dbpedia.org/sparql")
    #sparql.setQuery(""" 
    #        SELECT ?label
    #        WHERE { <http://dbpedia.org/resource/Asturias> rdfs:label ?label }
    #""")
    #
    #for result in sparql.query().bindings:
    #    print('%s: %s' % (result["label"].lang, result["label"].value))

    #sparql = SPARQLWrapper("http://dbpedia.org/sparql")

    #sparql.setQuery("""
    #    DESCRIBE <http://dbpedia.org/resource/Asturias>
    #""")

    sparql = SPARQLWrapper("http://dbpedia.org/sparql")

    #keyword = "f"
    #keyword = input("Keyword: ")
    
    #all_results = search_dbpedia(keyword)
    #for result in all_results:
    #    print(get_dbpedia_info(result["c1"]["value"]))
        #try:
        #    name = get_name(result["c1"]["value"])
        #    desc = get_description(result["c1"]["value"])
        #    wiki = get_wiki_link(result["c1"]["value"])
        #    print(name, desc, wiki)
        #except Exception:
        #    ...
    app = QApplication(sys.argv)
    win = MainWindow()
    sys.exit(app.exec_())
