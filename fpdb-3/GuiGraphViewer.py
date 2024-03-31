#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Copyright 2008-2011 Steffen Schaumburg
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as published by
#the Free Software Foundation, version 3 of the License.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU Affero General Public License
#along with this program. If not, see <http://www.gnu.org/licenses/>.
#In the "official" distribution you can find the license in agpl-3.0.txt.

from __future__ import print_function
from __future__ import division

from past.utils import old_div
#import L10n
#_ = L10n.get_translation()

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
                             QSplitter, QVBoxLayout, QWidget, QFileDialog, QMessageBox)
import sys
import os
from time import time

import Database
import Filters
import Charset

try:
    calluse = not 'matplotlib' in sys.modules
    import matplotlib
    if calluse:
        try:
            matplotlib.use('qt5agg')
        except ValueError as e:
            print(e)
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import FigureCanvas
    from matplotlib.font_manager import FontProperties
    from numpy import cumsum
except ImportError as inst:
    print(("""Failed to load libs for graphing, graphing will not function. Please install numpy and matplotlib if you want to use graphs."""))
    print(("""This is of no consequence for other parts of the program, e.g. import and HUD are NOT affected by this problem."""))
    print("ImportError: %s" % inst.args)


class GuiGraphViewer(QSplitter):

    def __init__(self, querylist, config, parent, debug=True):
        QSplitter.__init__(self, parent)
        self.sql = querylist
        self.conf = config
        self.debug = debug
        self.parent = parent
        self.db = Database.Database(self.conf, sql=self.sql)


        filters_display = { "Heroes"    : True,
                            "Sites"     : False,
                            "Games"     : True,
                            "Currencies": True,
                            "Limits"    : True,
                            "LimitSep"  : True,
                            "LimitType" : True,
                            "Type"      : False,
                            "UseType"   : 'ring',
                            "Seats"     : False,
                            "SeatSep"   : False,
                            "Dates"     : True,
                            "GraphOps"  : True,
                            "Groups"    : False,
                            "Button1"   : True,
                            "Button2"   : True
                          }

        self.filters = Filters.Filters(self.db, display = filters_display)
        self.filters.registerButton1Name(("Refresh Graph"))
        self.filters.registerButton1Callback(self.generateGraph)
        self.filters.registerButton2Name(("Export to File"))
        self.filters.registerButton2Callback(self.exportGraph)

        scroll = QScrollArea()
        scroll.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        scroll.setWidget(self.filters)
        self.addWidget(scroll)

        frame = QFrame()
        frame.setStyleSheet('background-color: #19232D ')
        self.graphBox = QVBoxLayout()
        
        frame.setLayout(self.graphBox)
        self.addWidget(frame)
        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 1)

        self.fig = None
        #self.exportButton.set_sensitive(False)
        self.canvas = None

        self.exportFile = None

        self.db.rollback()

    def clearGraphData(self):
        try:
            if self.canvas:
                self.graphBox.removeWidget(self.canvas)
        except:
            pass

        if self.fig != None:
            self.fig.clear()
        self.fig = Figure(figsize=(5.0,4.0), dpi=100)
        self.fig.patch.set_facecolor('#19232D')
        if self.canvas is not None:
            self.canvas.destroy()

        self.canvas = FigureCanvas(self.fig)
        
        self.canvas.setParent(self)

    def generateGraph(self, widget):
        self.clearGraphData()

        sitenos = []
        playerids = []
        winnings = []
        sites   = self.filters.getSites()
        heroes  = self.filters.getHeroes()
        siteids = self.filters.getSiteIds()
        limits  = self.filters.getLimits()
        games   = self.filters.getGames()
        currencies = self.filters.getCurrencies()
        graphops = self.filters.getGraphOps()
        display_in = "$" if "$" in graphops else "BB"
        names   = ""

        # Which sites are selected?
        for site in sites:
            sitenos.append(siteids[site])
            _hname = Charset.to_utf8(heroes[site])
            result = self.db.get_player_id(self.conf, site, _hname)
            if result is not None:
                playerids.append(int(result))
                names = names + "\n"+_hname + " on "+site

        if not sitenos:
            #Should probably pop up here.
            print(("No sites selected - defaulting to PokerStars"))
            self.db.rollback()
            return

        if not playerids:
            print(("No player ids found"))
            self.db.rollback()
            return

        if not limits:
            print(("No limits found"))
            self.db.rollback()
            return

        #Set graph properties
        
        self.ax = self.fig.add_subplot(111)
        
        
        #Get graph data from DB
        starttime = time()
        (green, blue, red, orange) = self.getRingProfitGraph(playerids, sitenos, limits, games, currencies, display_in)
        
        print(("Graph generated in: %s") %(time() - starttime))

        #Set axis labels and grid overlay properites
        
        self.ax.set_xlabel(("Hands"),color='#9DA9B5')
        self.ax.set_facecolor('#19232D')
        self.ax.tick_params(axis='x', colors='#9DA9B5') 
        self.ax.tick_params(axis='y', colors='#9DA9B5') 
        self.ax.spines['left'].set_color('#9DA9B5') 
        self.ax.spines['right'].set_color('#9DA9B5')
        self.ax.spines['top'].set_color('#9DA9B5')
        self.ax.spines['bottom'].set_color('#9DA9B5')
        self.ax.spines.left.set_position(('data',0))
        self.ax.spines.top.set_color('none')
        self.ax.spines.right.set_color('none')
        self.ax.spines.bottom.set_position(('data',0))
        self.ax.xaxis.set_ticks_position('bottom')
        self.ax.yaxis.set_ticks_position('left')
        
       
        
        # SET LABEL FOR X AXIS
        self.ax.set_ylabel(display_in, color='#9DA9B5')
        self.ax.grid(color='g', linestyle=':', linewidth=0.2)
        if green is None or len(green) == 0:
            self.ax.set_title(("No Data for Player(s) Found"))
            green = ([    0.,     0.,     0.,     0.,   500.,  1000.,   900.,   800.,
                        700.,   600.,   500.,   400.,   300.,   200.,   100.,     0.,
                        500.,  1000.,  1000.,  1000.,  1000.,  1000.,  1000.,  1000.,
                        1000., 1000.,  1000.,  1000.,  1000.,  1000.,   875.,   750.,
                        625.,   500.,   375.,   250.,   125.,     0.,     0.,     0.,
                        0.,   500.,  1000.,   900.,   800.,   700.,   600.,   500.,
                        400.,   300.,   200.,   100.,     0.,   500.,  1000.,  1000.])
            red   =  ([    0.,     0.,     0.,     0.,   500.,  1000.,   900.,   800.,
                        700.,   600.,   500.,   400.,   300.,   200.,   100.,     0.,
                        0.,   0.,     0.,     0.,     0.,     0.,   125.,   250.,
                        375.,   500.,   500.,   500.,   500.,   500.,   500.,   500.,
                        500.,   500.,   375.,   250.,   125.,     0.,     0.,     0.,
                        0.,   500.,  1000.,   900.,   800.,   700.,   600.,   500.,
                        400.,   300.,   200.,   100.,     0.,   500.,  1000.,  1000.])
            blue =    ([    0.,     0.,     0.,     0.,   500.,  1000.,   900.,   800.,
                          700.,   600.,   500.,   400.,   300.,   200.,   100.,     0.,
                          0.,     0.,     0.,     0.,     0.,     0.,   125.,   250.,
                          375.,   500.,   625.,   750.,   875.,  1000.,   875.,   750.,
                          625.,   500.,   375.,   250.,   125.,     0.,     0.,     0.,
                        0.,   500.,  1000.,   900.,   800.,   700.,   600.,   500.,
                        400.,   300.,   200.,   100.,     0.,   500.,  1000.,  1000.])

        #Plot the graph
            
            
            self.ax.plot(green, color='green', linewidth = 0.5, label=('Hands') + ': %d\n' % len(green) + ('Profit') + ': %.2f' % green[-1])
            self.ax.plot(blue, color='blue', label=('Showdown') + ': $%.2f' %(blue[-1]))
            self.ax.plot(red, color='red', label=('Non-showdown') + ': $%.2f' %(red[-1]))
            self.graphBox.addWidget(self.canvas)
            self.canvas.draw()
        else:
            self.ax.set_title((("Profit graph for ring games")+names), color='#9DA9B5')

            #Draw plot
            if 'showdown' in graphops:
                print("blue max:", blue.max())
                self.ax.plot(blue, color='blue' , label=('Showdown') + ' (%s): %.2f' %(display_in, blue[-1]))
                
                
            if 'nonshowdown' in graphops:
                self.ax.plot(red, color='red', label=('Non-showdown') + ' (%s): %.2f' %(display_in, red[-1]))
            if 'ev'in graphops:
                self.ax.plot(orange, color='orange', label=('All-in EV') + ' (%s): %.2f' %(display_in, orange[-1]))
            self.ax.plot(green, color='green', label=('Hands') + ': %d\n' % len(green) + ('Profit') + ': (%s): %.2f' % (display_in, green[-1]))

            # order legend, greenline on top
            handles, labels = self.ax.get_legend_handles_labels()
            
            handles = handles[-1:]+handles[:-1]
            labels = labels[-1:]+labels[:-1]
            
            legend = self.ax.legend(handles, labels, loc='upper left', fancybox=True, shadow=True, prop=FontProperties(size='smaller'), facecolor="#19232D", labelcolor='#9DA9B5')
            #legend.draggable(True)
          

            legend.set_draggable(state= 1)
            
            self.graphBox.addWidget(self.canvas)
            self.canvas.draw()
            #self.exportButton.set_sensitive(True)


    def getRingProfitGraph(self, names, sites, limits, games, currencies, units):
#        tmp = self.sql.query['getRingProfitAllHandsPlayerIdSite']
#        print "DEBUG: getRingProfitGraph"

        if units == '$':
            tmp = self.sql.query['getRingProfitAllHandsPlayerIdSiteInDollars']
        elif units == 'BB':
            tmp = self.sql.query['getRingProfitAllHandsPlayerIdSiteInBB']


        start_date, end_date = self.filters.getDates()

        #Buggered if I can find a way to do this 'nicely' take a list of integers and longs
        # and turn it into a tuple readale by sql.
        # [5L] into (5) not (5,) and [5L, 2829L] into (5, 2829)
        nametest = str(tuple(names))
        sitetest = str(tuple(sites))
        #nametest = nametest.replace("L", "")

        for m in list(self.filters.display.items()):
            if m[0] == 'Games' and m[1]:
                if len(games) > 0:
                    gametest = str(tuple(games))
                    gametest = gametest.replace("L", "")
                    gametest = gametest.replace(",)",")")
                    gametest = gametest.replace("u'","'")
                    gametest = "and gt.category in %s" % gametest
                else:
                    gametest = "and gt.category IS NULL"
        tmp = tmp.replace("<game_test>", gametest)

        limittest = self.filters.get_limits_where_clause(limits)
        
        currencytest = str(tuple(currencies))
        currencytest = currencytest.replace(",)",")")
        currencytest = currencytest.replace("u'","'")
        currencytest = "AND gt.currency in %s" % currencytest


        if type == 'ring':
            limittest = limittest + " and gt.type = 'ring' "
        elif type == 'tour':
            limittest = limittest + " and gt.type = 'tour' "

        #Must be a nicer way to deal with tuples of size 1 ie. (2,) - which makes sql barf
        tmp = tmp.replace("<player_test>", nametest)
        tmp = tmp.replace("<site_test>", sitetest)
        tmp = tmp.replace("<startdate_test>", start_date)
        tmp = tmp.replace("<enddate_test>", end_date)
        tmp = tmp.replace("<limit_test>", limittest)
        tmp = tmp.replace("<currency_test>", currencytest)
        tmp = tmp.replace(",)", ")")

        print ("DEBUG: sql query:")
        print( tmp)
        self.db.cursor.execute(tmp)
        #returns (HandId,Winnings,Costs,Profit)
        winnings = self.db.cursor.fetchall()
        self.db.rollback()

        if len(winnings) == 0:
            return (None, None, None, None)
        green = [0]
        green.extend([float(x[1]) for x in winnings])
        #print (green)
        blue = [0]
        blue.extend([float(x[1]) if x[2] == True  else 0.0 for x in winnings])
        red = [0]
        red.extend([float(x[1]) if x[2] == False else 0.0 for x in winnings])
        orange = [0]
        orange.extend([float(x[3]) for x in winnings])
        greenline = cumsum(green)
        blueline  = cumsum(blue)
        redline   = cumsum(red)
        orangeline = cumsum(orange)
        return (old_div(greenline,100), old_div(blueline,100), old_div(redline,100), old_div(orangeline,100))

    def exportGraph (self):
        if self.fig is None:
            return # Might want to disable export button until something has been generated.
        else:
            path = os.getcwd()
            print (path)
            path = path+'/graph.png'
            print (path)
            self.fig.savefig(path) 
            msg = QMessageBox()
            msg.setWindowTitle("FPDB 3 info")
            mess = "Your graph is saved in "+path
            msg.setText(mess)
            msg.exec()
    #end of def exportGraph TO DO more if needed

if __name__ == "__main__":
    import Configuration
    config = Configuration.Config()

    settings = {}

    settings.update(config.get_db_parameters())
    settings.update(config.get_import_parameters())
    settings.update(config.get_default_paths())

    from PyQt5.QtWidgets import QApplication, QMainWindow
    app = QApplication([])
    import SQL
    sql = SQL.Sql(db_server=settings['db-server'])
    i = GuiGraphViewer(sql, config, None, None)
    main_window = QMainWindow()
    main_window.setCentralWidget(i)
    main_window.show()
    main_window.resize(1400, 800)
    app.exec_()
