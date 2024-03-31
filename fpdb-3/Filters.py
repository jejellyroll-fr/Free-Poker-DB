#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2008-2011 Steffen Schaumburg
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# In the "official" distribution you can find the license in agpl-3.0.txt.


from __future__ import print_function
from __future__ import division
from ast import Pass

from dataclasses import replace
from past.utils import old_div
#import L10n
#_ = L10n.get_translation()
import pathlib
import os


from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QDate, QDateTime
from PyQt5.QtWidgets import (QCalendarWidget, QCheckBox, QCompleter,
                             QDateEdit, QDialog, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QRadioButton,
                             QSpinBox, QVBoxLayout, QWidget, QComboBox)

from time import gmtime, mktime, strftime, strptime
from functools import partial

import logging

import Configuration
import Database
import SQL
import Charset
import Card

if __name__ == "__main__":
    Configuration.set_logfile("fpdb-log.txt")
# logging has been set up in fpdb.py or HUD_main.py, use their settings:
log = logging.getLogger("filter")

class Filters(QWidget):
    def __init__(self, db, display = {}):
        QWidget.__init__(self, None)
        self.db = db
        self.cursor = db.cursor
        self.sql = db.sql
        self.conf = db.config
        self.display = display

        self.gameName = {"27_1draw"  : ("Single Draw 2-7 Lowball")
                        ,"27_3draw"  : ("Triple Draw 2-7 Lowball")
                        ,"a5_3draw"  : ("Triple Draw A-5 Lowball")
                        ,"5_studhi"   : ("5 Card Stud")
                        ,"badugi"    : ("Badugi")
                        ,"badacey"   : ("Badacey")
                        ,"badeucey"  : ("Badeucey")
                        ,"drawmaha"  : ("2-7 Drawmaha")
                        ,"a5_1draw"  : ("A-5 Single Draw")
                        ,"27_razz"   : ("2-7 Razz")
                        ,"fivedraw"  : ("5 Card Draw")
                        ,"holdem"    : ("Hold'em")
                        ,"6_holdem"    : ("Hold'em")
                        ,"omahahi"   : ("Omaha")
                        ,"fusion"    : ("Fusion")
                        ,"omahahilo" : ("Omaha Hi/Lo")
                        ,"razz"      : ("Razz")
                        ,"studhi"    : ("7 Card Stud")
                        ,"studhilo"  : ("7 Card Stud Hi/Lo")
                        ,"5_omahahi" : ("5 Card Omaha")
                        ,"5_omaha8"  : ("5 Card Omaha Hi/Lo")
                        ,"cour_hi"   : ("Courchevel")
                        ,"cour_hilo" : ("Courchevel Hi/Lo")
                        ,"2_holdem"  : ("Double hold'em")
                        ,"irish"     : ("Irish")
                        ,"6_omahahi" : ("6 Card Omaha")
                        }

        self.currencyName = {"USD" : ("US Dollar")
                            ,"EUR" : ("Euro")
                            ,"T$"  : ("Tournament Dollar")
                            ,"play": ("Play Money")
                            }

        # text used on screen stored here so that it can be configured
        self.filterText = {'limitsall':('All'), 'limitsnone':('None'), 'limitsshow':('Show Limits')
                          ,'gamesall':('All'), 'gamesnone':('None')
                          ,'positionsall':('All'), 'positionsnone':('None')
                          ,'currenciesall':('All'), 'currenciesnone':('None')
                          ,'seatsbetween':('Between:'), 'seatsand':('And:'), 'seatsshow':('Show Number of Players')
                          ,'playerstitle':('Hero:'), 'sitestitle':(('Sites')+':'), 'gamestitle':(('Games')+':'), 'tourneytitle':(('Tourney')+':'),'tourneycat':(('King of game')+':')
                          ,'limitstitle':('Limits:'), 'positionstitle':('Positions:'), 'seatstitle':('Number of Players:'),'tourneylim':(('Betting limit')+':')
                          ,'groupstitle':('Grouping:'), 'posnshow':('Show Position Stats'),'tourneybuyin':(('Buyin')+':')
                          ,'datestitle':('Date:'), 'currenciestitle':(('Currencies')+':')
                          ,'groupsall':('All Players'), 'cardstitle':(('Hole Cards')+':')
                          ,'limitsFL':'FL', 'limitsNL':'NL', 'limitsPL':'PL', 'limitsCN':'CAP', 'ring':('Ring'), 'tour':('Tourney'), 'limitsHP':'HP'
                          }

        gen = self.conf.get_general_params()
        self.day_start = 0

        if 'day_start' in gen:
            self.day_start = float(gen['day_start'])

        self.setLayout(QVBoxLayout())

        self.callback = {}

        self.setStyleSheet("QPushButton {padding-left:5;padding-right:5;padding-top:2;padding-bottom:2;}")
        self.make_filter()
        
    def make_filter(self):
        self.siteid = {}
        self.cards  = {}

        for site in self.conf.get_supported_sites():
            # Get db site id for filtering later
            self.cursor.execute(self.sql.query['getSiteId'], (site,))
            result = self.db.cursor.fetchall()
            if len(result) == 1:
                self.siteid[site] = result[0][0]
            else:
                log.debug(("Either 0 or more than one site matched for %s"), site)

        # For use in date ranges.
        self.start_date = QDateEdit(QDate(1970,1,1))
        self.end_date = QDateEdit(QDate(2100,1,1))

        # For use in groups etc
        self.cbGroups = {}
        self.phands = None

        playerFrame = QGroupBox(self.filterText['playerstitle'])
        self.leHeroes = {}

        self.fillPlayerFrame(playerFrame, self.display)
        self.layout().addWidget(playerFrame)

        # Sites
        sitesFrame = QGroupBox(self.filterText['sitestitle'])
        self.cbSites = {}

        self.fillSitesFrame(sitesFrame)
        self.layout().addWidget(sitesFrame)

        # Game types
        gamesFrame = QGroupBox(self.filterText['gamestitle'])
        self.layout().addWidget(gamesFrame)
        self.cbGames = {}

        self.fillGamesFrame(gamesFrame)

        # Tourney types
        tourneyFrame = QGroupBox(self.filterText['tourneytitle'])
        self.layout().addWidget(tourneyFrame)
        self.cbTourney = {}

        self.fillTourneyTypesFrame(tourneyFrame)

        # Tourney category
        tourneyCatFrame = QGroupBox(self.filterText['tourneycat'])
        self.layout().addWidget(tourneyCatFrame)
        self.cbTourneyCat = {}

        self.fillTourneyCatFrame(tourneyCatFrame)

        # Tourney limit
        tourneyLimFrame = QGroupBox(self.filterText['tourneylim'])
        self.layout().addWidget(tourneyLimFrame)
        self.cbTourneyLim = {}

        self.fillTourneyLimFrame(tourneyLimFrame)

        # Tourney buyin
        tourneyBuyinFrame = QGroupBox(self.filterText['tourneybuyin'])
        self.layout().addWidget(tourneyBuyinFrame)
        self.cbTourneyBuyin = {}

        self.fillTourneyBuyinFrame(tourneyBuyinFrame)

        # Currencies
        currenciesFrame = QGroupBox(self.filterText['currenciestitle'])
        self.layout().addWidget(currenciesFrame)
        self.cbCurrencies = {}

        self.fillCurrenciesFrame(currenciesFrame)

        # Limits
        limitsFrame = QGroupBox(self.filterText['limitstitle'])
        self.layout().addWidget(limitsFrame)
        self.cbLimits = {}
        self.rb = {}     # radio buttons for ring/tour
        self.type = None # ring/tour

        self.fillLimitsFrame(limitsFrame, self.display)
        
        # Positions
        positionsFrame = QGroupBox(self.filterText['positionstitle'])
        self.layout().addWidget(positionsFrame)
        
        self.cbPositions = {}

        self.fillPositionsFrame(positionsFrame, self.display)

        # GraphOps
        graphopsFrame = QGroupBox(("Graphing Options:"))
        self.layout().addWidget(graphopsFrame)
        self.cbGraphops = {}

        self.fillGraphOpsFrame(graphopsFrame)

        # Seats
        seatsFrame = QGroupBox(self.filterText['seatstitle'])
        self.layout().addWidget(seatsFrame)
        self.sbSeats = {}

        self.fillSeatsFrame(seatsFrame)

        # Groups
        groupsFrame = QGroupBox(self.filterText['groupstitle'])
        self.layout().addWidget(groupsFrame)

        self.fillGroupsFrame(groupsFrame, self.display)

        # Date
        dateFrame = QGroupBox(self.filterText['datestitle'])
        self.layout().addWidget(dateFrame)

        self.fillDateFrame(dateFrame)

        # Hole cards
        cardsFrame = QGroupBox(self.filterText['cardstitle'])
        self.layout().addWidget(cardsFrame)

        self.fillHoleCardsFrame(cardsFrame)

        # Buttons
        self.Button1 = QPushButton("Unnamed 1")
        self.Button2 = QPushButton("Unnamed 2")
        self.layout().addWidget(self.Button1)
        self.layout().addWidget(self.Button2)

        # Should do this cleaner
        if "Heroes" not in self.display or self.display["Heroes"] is False:
            playerFrame.hide()
        if "Sites" not in self.display or self.display["Sites"] is False:
            sitesFrame.hide()
        if "Games" not in self.display or self.display["Games"] is False:
            gamesFrame.hide()
        if "Tourney" not in self.display or self.display["Tourney"] is False:
            tourneyFrame.hide()
        if "King of game" not in self.display or self.display["King of game"] is False:
            tourneyCatFrame.hide()
        if "Betting limit" not in self.display or self.display["Betting limit"] is False:
            tourneyLimFrame.hide()
        if "Buyin" not in self.display or self.display["Buyin"] is False:
            tourneyBuyinFrame.hide()
        if "Currencies" not in self.display or self.display["Currencies"] is False:
            currenciesFrame.hide()
        if "Limits" not in self.display or self.display["Limits"] is False:
            limitsFrame.hide()
        if "Positions" not in self.display or self.display["Positions"] is False:
            positionsFrame.hide()
        if "Seats" not in self.display or self.display["Seats"] is False:
            seatsFrame.hide()
        if "Groups" not in self.display or self.display["Groups"] is False:
            groupsFrame.hide()
        if "Dates" not in self.display or self.display["Dates"] is False:
            dateFrame.hide()
        if "GraphOps" not in self.display or self.display["GraphOps"] is False:
            graphopsFrame.hide()
        if "Cards" not in self.display or self.display["Cards"] is False:
            cardsFrame.hide()
        if "Button1" not in self.display or self.display["Button1"] is False:
            self.Button1.hide()
        if "Button2" not in self.display or self.display["Button2"] is False:
            self.Button2.hide()

        # make sure any locks on db are released:
        self.db.rollback()

    def getNumHands(self):
        if self.phands:
            return self.phands.value()
        return 0

    def getNumTourneys(self):
        return 0

    

    def getSites(self):
        return [s for s in self.cbSites if self.cbSites[s].isChecked()]
    
    def getPositions(self):
        return [p for p in self.cbPositions if self.cbPositions[p].isChecked()]

    def getTourneyCat(self):
        return [g for g in self.cbTourneyCat if self.cbTourneyCat[g].isChecked()]

    def getTourneyLim(self):
        return [g for g in self.cbTourneyLim if self.cbTourneyLim[g].isChecked()]

    def getTourneyBuyin(self):
        return [g for g in self.cbTourneyBuyin if self.cbTourneyBuyin[g].isChecked()]

    def getTourneyTypes(self):
        return [g for g in self.cbTourney if self.cbTourney[g].isChecked()]

    def getGames(self):
        return [g for g in self.cbGames if self.cbGames[g].isChecked()]

    def getCards(self):
        return self.cards

    def getCurrencies(self):
        return [c for c in self.cbCurrencies if self.cbCurrencies[c].isChecked()]

    def getSiteIds(self):
        return self.siteid

    def getHeroes(self):
        #print(dict([(site, str(self.heroList.currentText())) for site in self.leHeroes]))
        
        return dict([(site, str(self.heroList.currentText())) for site in self.leHeroes])
    
    def getGraphOps(self):
        
        return [g for g in self.cbGraphops if self.cbGraphops[g].isChecked()]

    def getLimits(self):
        print([l for l in self.cbLimits if self.cbLimits[l].isChecked()])
        return [l for l in self.cbLimits if self.cbLimits[l].isChecked()]

    def getType(self):
        return(self.type)

    def getSeats(self):
        result = {}
        if 'from' in self.sbSeats:
            result['from'] = self.sbSeats['from'].value()
        if 'to' in self.sbSeats:
            result['to'] = self.sbSeats['to'].value()
        return result

    def getGroups(self):
        return [g for g in self.cbGroups if self.cbGroups[g].isChecked()]

    def getDates(self):
        # self.day_start gives user's start of day in hours
        offset = int(self.day_start * 3600)   # calc day_start in seconds

        t1 = self.start_date.date()
        t2 = self.end_date.date()

        adj_t1 = QDateTime(t1).addSecs(offset)
        adj_t2 = QDateTime(t2).addSecs(offset + 24 * 3600 - 1)

        return (adj_t1.toUTC().toString("yyyy-MM-dd HH:mm:ss"), adj_t2.toUTC().toString("yyyy-MM-dd HH:mm:ss"))

    def registerButton1Name(self, title):
        self.Button1.setText(title)

    def registerButton1Callback(self, callback):
        self.Button1.clicked.connect(callback)
        self.Button1.setEnabled(True)
        self.callback['button1'] = callback

    def registerButton2Name(self, title):
        self.Button2.setText(title)

    def registerButton2Callback(self, callback):
        self.Button2.clicked.connect(callback)
        self.Button2.setEnabled(True)
        self.callback['button2'] = callback

    def registerCardsCallback(self, callback):
        self.callback['cards'] = callback

    def __set_tourney_type_select(self, w, tourneyType):
        self.tourneyTypes[tourneyType] = w.get_active()
        log.debug("self.tourney_types[%s] set to %s", tourneyType, self.tourneyTypes[tourneyType])

    def createTourneyTypeLine(self, hbox, tourneyType):
        cb = QCheckBox(str(tourneyType))
        cb.clicked.connect(partial(self.__set_tourney_type_select, tourneyType=tourneyType))
        hbox.addWidget(cb)
        cb.setChecked(True)

    def createCardsWidget(self, grid):
        grid.setSpacing(0)
        for i in range(0,13):
            for j in range(0,13):
                abbr = Card.card_map_abbr[j][i]
                b = QPushButton("")
                import platform
                if platform.system == "Darwin":
                    b.setStyleSheet("QPushButton {border-width:0;margin:6;padding:0;}")
                else:
                    b.setStyleSheet("QPushButton {border-width:0;margin:0;padding:0;}")
                b.clicked.connect(partial(self.__toggle_card_select, widget=b, card=abbr))
                self.cards[abbr] = False # NOTE: This is flippped in __toggle_card_select below
                self.__toggle_card_select(False, widget=b, card=abbr)
                grid.addWidget(b, j, i)

    def createCardsControls(self, hbox):
        selections = ["All", "Suited", "Off Suit"]
        for s in selections:
            cb = QCheckBox(s)
            cb.clicked.connect(self.__set_cards)
            hbox.addWidget(cb)

    def __card_select_bgcolor(self, card, selected):
        s_on  = "red"
        s_off = "orange"
        o_on  = "white"
        o_off = "lightgrey"
        p_on  = "blue"
        p_off = "lightblue"
        if len(card) == 2: return p_on if selected else p_off
        if card[2] == 's': return s_on if selected else s_off
        if card[2] == 'o': return o_on if selected else o_off

    def __toggle_card_select(self, checkState, widget, card):
        font = widget.font()
        font.setPointSize(10)
        widget.setFont(font)
        widget.setText(card)

        self.cards[card] = not self.cards[card]

#        bg_color = self.__card_select_bgcolor(card, self.cards[card])

#        style = w.get_style().copy()
#        style.bg[gtk.STATE_NORMAL] = w.get_colormap().alloc(bg_color)
#        w.set_style(style)
        if 'cards' in self.callback:
            self.callback['cards'](card)

    def __set_cards(self, checkState):
        pass

    def __set_checkboxes(self, checkState, checkBoxes, setState):
        for checkbox in list(checkBoxes.values()):
            checkbox.setChecked(setState)

    def __select_limit(self, checkState, limit):
        for l, checkbox in list(self.cbLimits.items()):
            if l.endswith(limit):
                checkbox.setChecked(True)

    def fillPlayerFrame(self, frame, display):
        vbox = QVBoxLayout()
        frame.setLayout(vbox)

        self.heroList = QComboBox()
        self.heroList.setStyleSheet("background-color: #455364")
        current_directory = str(pathlib.Path(__file__).parent.absolute())
        
        for count,site in enumerate(self.conf.get_supported_sites(), start=1):
            player = self.conf.supported_sites[site].screen_name
            _pname = player
            #vbox.addWidget(QLabel(site +" id:"))

            self.leHeroes[site] = QLineEdit(_pname)
            if os.name == 'nt' :
                icoPath = os.path.dirname(__file__)
                
                icoPath = icoPath+"\\"
                print(icoPath)
            else:
                icoPath = "" 
            if site == "PokerStars":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'ps.svg'),completPlayer)
            elif site == "Full Tilt Poker":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'ft.svg'),completPlayer)
            elif site == "Everleaf":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'everleaf.png'),completPlayer)
            elif site == "Boss":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'boss.ico'),completPlayer)    
            elif site == "PartyPoker":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'party.png'),completPlayer)    
            elif site == "Merge":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'merge.png'),completPlayer)     
            elif site == "PKR":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'pkr.png'),completPlayer)  
            elif site == "iPoker":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'ipoker.png'),completPlayer)
            elif site == "Cake":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'cake.png'),completPlayer)  
            elif site == "Entraction":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'entraction.png'),completPlayer) 
            elif site == "BetOnline":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'betonline.png'),completPlayer) 
            elif site == "Microgaming":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'microgaming.png'),completPlayer)  
            elif site == "Bovada":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'bovada.png'),completPlayer) 
            elif site == "Enet":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'enet.png'),completPlayer)  
            elif site == "SealsWithClubs":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'swc.png'),completPlayer) 
            elif site == "WinningPoker":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'winning.png'),completPlayer)    
            elif site == "GGPoker":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'gg.png'),completPlayer)              
            elif site == "Pacific":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'pacific.png'),completPlayer) 
            elif site == "KingsClub":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'kingsclub.png'),completPlayer)  
            elif site == "Unibet":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'unibet.png'),completPlayer)                                                                                  
            elif site == "Winamax":  
                completPlayer = _pname  
                self.heroList.addItem(QIcon(icoPath +'wina.svg'),completPlayer)
            else:
                completPlayer = _pname+" on "+site
                self.heroList.insertItem(count,completPlayer)
            vbox.addWidget(self.heroList)

            names = self.db.get_player_names(self.conf, self.siteid[site])
            completer = QCompleter([n[0] for n in names])
            self.leHeroes[site].setCompleter(completer)

        if "GroupsAll" in display and display["GroupsAll"]:
            hbox = QHBoxLayout()
            vbox.addLayout(hbox)
            self.cbGroups['allplayers'] = QCheckBox(self.filterText['groupsall'])
            hbox.addWidget(self.cbGroups['allplayers'])

            lbl = QLabel(('Min # Hands:'))
            hbox.addWidget(lbl)

            self.phands = QSpinBox()
            self.phands.setMaximum(int(1e5))
            hbox.addWidget(self.phands)

    def fillSitesFrame(self, frame):
        vbox = QVBoxLayout()
        frame.setLayout(vbox)

        for site in self.conf.get_supported_sites():
            self.cbSites[site] = QCheckBox(site)
            self.cbSites[site].setChecked(True)
            vbox.addWidget(self.cbSites[site])

    def fillTourneyTypesFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)
        
        req = self.cursor.execute("SELECT DISTINCT tourneyName FROM Tourneys")
        result = req.fetchall()
        print(result)
        self.gameList = QComboBox()
        self.gameList.setStyleSheet("background-color: #455364")   
        for count,game in enumerate(result, start=0):
            game = str(result[count])
            if game == "(None,)":
                game = "(\"None\",)"
                game = game.replace("(","")
                game = game.replace(",","")
                game = game.replace(")","")
            else:
                game = game.replace("(","")
                game = game.replace(",","")
                game = game.replace(")","")
            
            print(game)
            if game != '"None"':
                self.gameList.insertItem(count,game)
            else:
                self.gameList.insertItem(count,game)
        #vbox1.addWidget(self.gameList)
        
        if len(result) >= 1:
            for line in result:
                if str(line) == "(None,)":
                    self.cbTourney[line[0]] = QCheckBox("None")
                    self.cbTourney[line[0]].setChecked(True)
                    vbox1.addWidget(self.cbTourney[line[0]])
                else:
                    self.cbTourney[line[0]] = QCheckBox(line[0])
                    self.cbTourney[line[0]].setChecked(True)
                    vbox1.addWidget(self.cbTourney[line[0]])


        else:
            print(("INFO: No games returned from database"))
            log.info(("No games returned from database"))

    def fillTourneyCatFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)
        
        req = self.cursor.execute("SELECT DISTINCT category FROM TourneyTypes")
        result = req.fetchall()
        print(result)
        self.gameList = QComboBox()
        self.gameList.setStyleSheet("background-color: #455364")   
        for count,game in enumerate(result, start=0):
            game = str(result[count])
            if game == "(None,)":
                game = "(\"None\",)"
                game = game.replace("(","")
                game = game.replace(",","")
                game = game.replace(")","")
            else:
                game = game.replace("(","")
                game = game.replace(",","")
                game = game.replace(")","")
            
            print(game)
            if game != '"None"':
                self.gameList.insertItem(count,game)
            else:
                self.gameList.insertItem(count,game)
        #vbox1.addWidget(self.gameList)
        
        if len(result) >= 1:
            for line in result:
                if str(line) == "(None,)":
                    self.cbTourneyCat[line[0]] = QCheckBox("None")
                    self.cbTourneyCat[line[0]].setChecked(True)
                    vbox1.addWidget(self.cbTourneyCat[line[0]])
                else:
                    self.cbTourneyCat[line[0]] = QCheckBox(line[0])
                    self.cbTourneyCat[line[0]].setChecked(True)
                    vbox1.addWidget(self.cbTourneyCat[line[0]])


        else:
            print(("INFO: No games returned from database"))
            log.info(("No games returned from database"))

    def fillTourneyLimFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)
        
        req = self.cursor.execute("SELECT DISTINCT limitType FROM TourneyTypes")
        result = req.fetchall()
        print(result)
        self.gameList = QComboBox()
        self.gameList.setStyleSheet("background-color: #455364")   
        for count,game in enumerate(result, start=0):
            game = str(result[count])
            if game == "(None,)":
                game = "(\"None\",)"
                game = game.replace("(","")
                game = game.replace(",","")
                game = game.replace(")","")
            else:
                game = game.replace("(","")
                game = game.replace(",","")
                game = game.replace(")","")
            
            print(game)
            if game != '"None"':
                self.gameList.insertItem(count,game)
            else:
                self.gameList.insertItem(count,game)
        #vbox1.addWidget(self.gameList)
        
        if len(result) >= 1:
            for line in result:
                if str(line) == "(None,)":
                    self.cbTourneyLim[line[0]] = QCheckBox("None")
                    self.cbTourneyLim[line[0]].setChecked(True)
                    vbox1.addWidget(self.cbTourneyLim[line[0]])
                else:
                    self.cbTourneyLim[line[0]] = QCheckBox(line[0])
                    self.cbTourneyLim[line[0]].setChecked(True)
                    vbox1.addWidget(self.cbTourneyLim[line[0]])


        else:
            print(("INFO: No games returned from database"))
            log.info(("No games returned from database"))

    def fillTourneyBuyinFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)
        
        req = self.cursor.execute("SELECT DISTINCT buyin FROM TourneyTypes")
        result = req.fetchall()
        print(result)
        self.gameList = QComboBox()
        self.gameList.setStyleSheet("background-color: #455364")   
        for count,game in enumerate(result, start=0):
            game = str(result[count])
            if game == "(None,)":
                game = "(\"None\",)"
                game = game.replace("(","")
                game = game.replace(",","")
                game = game.replace(")","")
            else:
                game = game.replace("(","")
                game = game.replace(",","")
                game = game.replace(")","")
            
            print(game)
            if game != '"None"':
                self.gameList.insertItem(count,game)
            else:
                self.gameList.insertItem(count,game)
        #vbox1.addWidget(self.gameList)
        
        if len(result) >= 1:
            for line in result:
                if str(line) == "(None,)":
                    self.cbTourneyBuyin[line[0]] = QCheckBox("None")
                    self.cbTourneyBuyin[line[0]].setChecked(True)
                    vbox1.addWidget(self.cbTourneyBuyin[line[0]])
                else:
                    self.cbTourneyBuyin[line[0]] = QCheckBox(str(line[0]*0.01))
                    self.cbTourneyBuyin[line[0]].setChecked(True)
                    vbox1.addWidget(self.cbTourneyBuyin[line[0]])


        else:
            print(("INFO: No games returned from database"))
            log.info(("No games returned from database"))

    def fillGamesFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)

        self.cursor.execute(self.sql.query['getGames'])
        result = self.db.cursor.fetchall()
        print(result)
        self.gameList = QComboBox()
        self.gameList.setStyleSheet("background-color: #455364")   
        for count,game in enumerate(result, start=0):
            game = str(result[count])
            game = game.replace("(","")
            game = game.replace(",","")
            game = game.replace(")","")
            print(game)
            self.gameList.insertItem(count,game)
        #vbox1.addWidget(self.gameList)

        if len(result) >= 1:
            for line in sorted(result, key = lambda game: self.gameName[game[0]]):
                self.cbGames[line[0]] = QCheckBox(self.gameName[line[0]])
                self.cbGames[line[0]].setChecked(True)
                vbox1.addWidget(self.cbGames[line[0]])

            if len(result) >= 2:
                hbox = QHBoxLayout()
                vbox1.addLayout(hbox)
                hbox.addStretch()

                btnAll = QPushButton(self.filterText['gamesall'])
                btnAll.clicked.connect(partial(self.__set_checkboxes,
                                               checkBoxes=self.cbGames,
                                               setState=True))
                hbox.addWidget(btnAll)

                btnNone = QPushButton(self.filterText['gamesnone'])
                btnNone.clicked.connect(partial(self.__set_checkboxes,
                                                checkBoxes=self.cbGames,
                                                setState=False))
                hbox.addWidget(btnNone)
                hbox.addStretch()
        else:
            print(("INFO: No games returned from database"))
            log.info(("No games returned from database"))

    def fillTourneyFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)

        self.cursor.execute(self.sql.query['getTourneyNames'])
        result = self.db.cursor.fetchall()
        print(result)
        self.gameList = QComboBox()
        self.gameList.setStyleSheet("background-color: #455364")   
        for count,game in enumerate(result, start=0):
            game = str(result[count])
            game = game.replace("(","")
            game = game.replace(",","")
            game = game.replace(")","")
            #print(game)
            self.gameList.insertItem(count,game)
            #self.cbTourney.addItem(game)
        print(type(self.cbTourney))
        #vbox1.addWidget(self.gameList)





    def fillPositionsFrame(self, frame, display):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)

        # the following is not the fastest query (as it querys a table with potentialy a lot of data), so dont execute it if not necessary
        if "Positions" not in display or display["Positions"] is False:
            return
        
        #This takes too long if there are a couple of 100k hands in the DB
        #self.cursor.execute(self.sql.query['getPositions'])
        #result = self.db.cursor.fetchall()
        result = [[0], [1], [2], [3], [4], [5], [6], [7], ['S'], ['B']]
        res_count = len(result)
        
        if res_count > 0:     
            v_count = 0
            COL_COUNT = 4           #Number of columns
            hbox = None
            for line in result:
                if v_count == 0:    #start a new line when the vertical count is 0
                    hbox = QHBoxLayout()
                    vbox1.addLayout(hbox)
                    
                line_str = str(line[0])
                self.cbPositions[line_str] = QCheckBox(line_str)
                self.cbPositions[line_str].setChecked(True)
                hbox.addWidget(self.cbPositions[line_str])
                
                v_count += 1
                if v_count == COL_COUNT:    #set the counter to 0 if the line is full
                    v_count = 0
            
            dif = res_count % COL_COUNT    
            while dif > 0:          #fill the rest of the line with empy boxes, so that every line contains COL_COUNT elements
                fillbox = QVBoxLayout()
                hbox.addLayout(fillbox)
                dif -= 1

            if res_count > 1:
                hbox = QHBoxLayout()
                vbox1.addLayout(hbox)
                hbox.addStretch()

                btnAll = QPushButton(self.filterText['positionsall'])
                btnAll.clicked.connect(partial(self.__set_checkboxes,
                                               checkBoxes=self.cbPositions,
                                               setState=True))
                hbox.addWidget(btnAll)

                btnNone = QPushButton(self.filterText['positionsnone'])
                btnNone.clicked.connect(partial(self.__set_checkboxes,
                                                checkBoxes=self.cbPositions,
                                                setState=False))
                hbox.addWidget(btnNone)
                hbox.addStretch()
        else:
            print(("INFO") + ": " + ("No positions returned from database"))
            log.info(("No positions returned from database"))

    def fillHoleCardsFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)

        grid = QGridLayout()
        vbox1.addLayout(grid)
        self.createCardsWidget(grid)

        # Additional controls for bulk changing card selection
        hbox = QHBoxLayout()
        vbox1.addLayout(hbox)
        self.createCardsControls(hbox)

    def fillCurrenciesFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)

        self.cursor.execute(self.sql.query['getCurrencies'])
        result = self.db.cursor.fetchall()
        if len(result) >= 1:
            for line in result:
                if line[0] in self.currencyName:
                    cname = self.currencyName[line[0]]
                else:
                    cname = line[0]
                self.cbCurrencies[line[0]] = QCheckBox(cname)
                self.cbCurrencies[line[0]].setChecked(True)
                vbox1.addWidget(self.cbCurrencies[line[0]])

            if len(result) >= 2:
                hbox = QHBoxLayout()
                vbox1.addLayout(hbox)
                hbox.addStretch()

                btnAll = QPushButton(self.filterText['currenciesall'])
                btnAll.clicked.connect(partial(self.__set_checkboxes,
                                                     checkBoxes=self.cbCurrencies,
                                                     setState=True))
                hbox.addWidget(btnAll)

                btnNone = QPushButton(self.filterText['currenciesnone'])
                btnNone.clicked.connect(partial(self.__set_checkboxes,
                                                     checkBoxes=self.cbCurrencies,
                                                     setState=False))
                hbox.addWidget(btnNone)
                hbox.addStretch()
            else:
                # There is only one currency. Select it, even if it's Play Money.
                self.cbCurrencies[line[0]].setChecked(True)
        else:
            log.info(("No currencies returned from database"))

    def fillLimitsFrame(self, frame, display):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)

        self.cursor.execute(self.sql.query['getCashLimits'])
        # selects  limitType, bigBlind
        result = self.db.cursor.fetchall()
        limits_found = set()
        types_found = set()

        if len(result) >= 1:
            hbox = QHBoxLayout()
            vbox1.addLayout(hbox)
            vbox2 = QVBoxLayout()
            hbox.addLayout(vbox2)
            vbox3 = QVBoxLayout()
            hbox.addLayout(vbox3)
            for i, line in enumerate(result):
                if "UseType" in self.display:
                    if line[0] != self.display["UseType"]:
                        continue
                hbox = QHBoxLayout()
                if i < old_div((len(result)+1),2):
                    vbox2.addLayout(hbox)
                else:
                    vbox3.addLayout(hbox)
                if True:  #line[0] == 'ring':
                    name = str(line[2])+line[1]
                    limits_found.add(line[1])
                    self.cbLimits[name] = QCheckBox(name)
                    self.cbLimits[name].setChecked(True)
                    hbox.addWidget(self.cbLimits[name])
                types_found.add(line[0])      # type is ring/tour
                self.type = line[0]        # if only one type, set it now
            if "LimitSep" in display and display["LimitSep"] and len(result) >= 2:
                hbox = QHBoxLayout()
                vbox1.addLayout(hbox)
                hbox.addStretch()

                btnAll = QPushButton(self.filterText['limitsall'])
                btnAll.clicked.connect(partial(self.__set_checkboxes,
                                               checkBoxes=self.cbLimits,
                                               setState=True))
                hbox.addWidget(btnAll)

                btnNone = QPushButton(self.filterText['limitsnone'])
                btnNone.clicked.connect(partial(self.__set_checkboxes,
                                                checkBoxes=self.cbLimits,
                                                setState=False))
                hbox.addWidget(btnNone)

                if "LimitType" in display and display["LimitType"] and len(limits_found) > 1:
                    for limit in limits_found:
                        btn = QPushButton(self.filterText['limits' + limit.upper()])
                        btn.clicked.connect(partial(self.__select_limit, limit=limit))
                        hbox.addWidget(btn)

                hbox.addStretch()
        else:
            print(("INFO: No games returned from database"))
            log.info(("No games returned from database"))

        if "Type" in display and display["Type"] and 'ring' in types_found and 'tour' in types_found:
            # rb1 = QRadioButton(frame, self.filterText['ring'])
            # rb1.clicked.connect(self.__set_limit_select)
            # rb2 = QRadioButton(frame, self.filterText['tour'])
            # rb2.clicked.connect(self.__set_limit_select)
            # top_hbox.addWidget(rb1)
            # top_hbox.addWidget(rb2)
            #
            # self.rb['ring'] = rb1
            # self.rb['tour'] = rb2
            # #print "about to set ring to true"
            # rb1.setChecked(True)
            # # set_active doesn't seem to call this for some reason so call manually:
            # self.__set_limit_select(rb1)
            self.type = 'ring'

    def fillGraphOpsFrame(self, frame):
        vbox1 = QVBoxLayout()
        frame.setLayout(vbox1)

        hbox1 = QHBoxLayout()
        vbox1.addLayout(hbox1)

        label = QLabel(("Show Graph In:"))
        hbox1.addWidget(label)

        self.cbGraphops['$'] = QRadioButton("$$", frame)
        hbox1.addWidget(self.cbGraphops['$'])
        self.cbGraphops['$'].setChecked(True)

        self.cbGraphops['BB'] = QRadioButton("BB", frame)
        hbox1.addWidget(self.cbGraphops['BB'])

        self.cbGraphops['showdown'] = QCheckBox(("Showdown Winnings"))
        vbox1.addWidget(self.cbGraphops['showdown'])

        self.cbGraphops['nonshowdown'] = QCheckBox(("Non-Showdown Winnings"))
        vbox1.addWidget(self.cbGraphops['nonshowdown'])

        self.cbGraphops['ev'] = QCheckBox(("EV"))
        vbox1.addWidget(self.cbGraphops['ev'])

    def fillSeatsFrame(self, frame):
        hbox = QHBoxLayout()
        frame.setLayout(hbox)

        lbl_from = QLabel(self.filterText['seatsbetween'])
        lbl_to   = QLabel(self.filterText['seatsand'])

        adj1 = QSpinBox()
        adj1.setRange(2, 10)
        adj1.setValue(2)
        adj1.valueChanged.connect(partial(self.__seats_changed, 'from'))

        adj2 = QSpinBox()
        adj2.setRange(2, 10)
        adj2.setValue(10)
        adj2.valueChanged.connect(partial(self.__seats_changed, 'to'))

        hbox.addStretch()
        hbox.addWidget(lbl_from)
        hbox.addWidget(adj1)
        hbox.addWidget(lbl_to)
        hbox.addWidget(adj2)
        hbox.addStretch()

        self.sbSeats['from'] = adj1
        self.sbSeats['to']   = adj2

    def fillGroupsFrame(self, frame, display):
        vbox = QVBoxLayout()
        frame.setLayout(vbox)

        self.cbGroups['limits'] = QCheckBox(self.filterText['limitsshow'])
        vbox.addWidget(self.cbGroups['limits'])

        self.cbGroups['posn'] = QCheckBox(self.filterText['posnshow'])
        vbox.addWidget(self.cbGroups['posn'])

        if "SeatSep" in display and display["SeatSep"]:
            self.cbGroups['seats'] = QCheckBox(self.filterText['seatsshow'])
            vbox.addWidget(self.cbGroups['seats'])

    def fillDateFrame(self, frame):
        table = QGridLayout()
        frame.setLayout(table)

        lbl_start = QLabel(('From:'))
        btn_start = QPushButton("Cal")
        btn_start.clicked.connect(partial(self.__calendar_dialog, dateEdit=self.start_date))
        clr_start = QPushButton("Reset")
        clr_start.clicked.connect(self.__clear_start_date)

        lbl_end = QLabel(('To:'))
        btn_end = QPushButton("Cal")
        btn_end.clicked.connect(partial(self.__calendar_dialog, dateEdit=self.end_date))
        clr_end = QPushButton("Reset")
        clr_end.clicked.connect(self.__clear_end_date)

        table.addWidget(lbl_start, 0, 0)
        table.addWidget(btn_start, 0, 1)
        table.addWidget(self.start_date, 0, 2)
        table.addWidget(clr_start, 0, 3)

        table.addWidget(lbl_end, 1, 0)
        table.addWidget(btn_end, 1, 1)
        table.addWidget(self.end_date, 1, 2)
        table.addWidget(clr_end, 1, 3)

        table.setColumnStretch(0, 1)

    def get_limits_where_clause(self, limits):
        """Accepts a list of limits and returns a formatted SQL where clause starting with AND.
            Sql statement MUST link to gameType table and use the alias gt for that table."""
        where = ""
        lims = [int(x[0:-2]) for x in limits if len(x) > 2 and x[-2:] == 'fl']
        potlims = [int(x[0:-2]) for x in limits if len(x) > 2 and x[-2:] == 'pl']
        nolims = [int(x[0:-2]) for x in limits if len(x) > 2 and x[-2:] == 'nl']
        capnolims = [int(x[0:-2]) for x in limits if len(x) > 2 and x[-2:] == 'cn']
        hpnolims = [int(x[0:-2]) for x in limits if len(x) > 2 and x[-2:] == 'hp']

        where          = "AND ( "

        if lims: 
            clause = "(gt.limitType = 'fl' and gt.bigBlind in (%s))" % (','.join(map(str, lims)))
        else:
            clause = "(gt.limitType = 'fl' and gt.bigBlind in (-1))"
        where = where + clause
        if potlims:
            clause = "or (gt.limitType = 'pl' and gt.bigBlind in (%s))" % (','.join(map(str, potlims)))
        else:
            clause = "or (gt.limitType = 'pl' and gt.bigBlind in (-1))"
        where = where + clause
        if nolims:
            clause = "or (gt.limitType = 'nl' and gt.bigBlind in (%s))" % (','.join(map(str, nolims)))
        else:
            clause = "or (gt.limitType = 'nl' and gt.bigBlind in (-1))"
        where = where + clause
        if hpnolims:
            clause = "or (gt.limitType = 'hp' and gt.bigBlind in (%s))" % (','.join(map(str, hpnolims)))
        else:
            clause = "or (gt.limitType = 'hp' and gt.bigBlind in (-1))"
        where = where + clause
        if capnolims:
            clause = "or (gt.limitType = 'cp' and gt.bigBlind in (%s))" % (','.join(map(str, capnolims)))
        else:
            clause = "or (gt.limitType = 'cp' and gt.bigBlind in (-1))"
        where = where + clause + ' )'

        return where
    
    def replace_placeholders_with_filter_values(self, query):
        """ Returnes given query with replaced placeholders by the filter values from self.
        
            List of Placeholders that are replaced and some infos how the statement has to look like:
            (whole clause means it starts with AND and contains the whole clause)
        
            Placeholders      table & alias or field     SQL usage          coresponding filter Name
            <player_test>     Players.Id                in <player_test>   Heroes
            <game_test>       GameType gt               whole clause       Game
            <limit_test>      GameType gt               whole clause       Limits, LimitSep, LimitType
            <position_test>   HandsPlayers hp           whole clause       Positions
        """
        
        if '<game_test>' in query:
            games = self.getGames()    

            if len(games) > 0:
                gametest = str(tuple(games))
                gametest = gametest.replace("L", "")
                gametest = gametest.replace(",)",")")
                gametest = gametest.replace("u'","'")
                gametest = "and gt.category in %s" % gametest
            else:
                gametest = "and gt.category IS NULL"
            query = query.replace('<game_test>', gametest)
            
        if '<limit_test>' in query:  #copyed from GuiGraphView
            limits = self.getLimits()
            limittest = self.get_limits_where_clause(limits)
            query = query.replace('<limit_test>', limittest)
            
        if '<player_test>' in query: #copyed from GuiGraphView
            sites = self.getSites()
            heroes = self.getHeroes()
            siteids = self.getSiteIds()
            sitenos = []
            playerids = []

            for site in sites:
                sitenos.append(siteids[site])
                _hname = Charset.to_utf8(heroes[site])
                result = self.db.get_player_id(self.conf, site, _hname)
                if result is not None:
                    playerids.append(str(result))
            
            query = query.replace('<player_test>', '(' + ','.join(playerids) + ')')
            
        if '<position_test>' in query:
            positions = self.getPositions()
            
            positiontest = "AND hp.position in ('" + "','".join(positions) + "')"   #values must be set in '' because they can be strings as well as numbers
            query = query.replace('<position_test>', positiontest)

        return query

    def __calendar_dialog(self, checkState, dateEdit):
        d = QDialog()
        d.setWindowTitle(('Pick a date'))

        vb = QVBoxLayout()
        d.setLayout(vb)
        cal = QCalendarWidget()
        vb.addWidget(cal)

        btn = QPushButton(('Done'))
        btn.clicked.connect(partial(self.__get_date, dlg=d, calendar=cal, dateEdit=dateEdit))

        vb.addWidget(btn)

        d.exec_()

    def __clear_start_date(self, checkState):
        self.start_date.setDate(QDate(1970,1,1))

    def __clear_end_date(self, checkState):
        self.end_date.setDate(QDate(2100,1,1))

    def __get_date(self, checkState, dlg, calendar, dateEdit):
        newDate = calendar.selectedDate()
        dateEdit.setDate(newDate)

        # if the opposite date is set, and now the start date is later
        # than the end date, modify the one we didn't just set to be
        # the same as the one we did just set
        if dateEdit == self.start_date:
            end = self.end_date.date()
            if newDate > end:
                self.end_date.setDate(newDate)
        else:
            start = self.start_date.date()
            if newDate < start:
                self.start_date.setDate(newDate)
        dlg.accept()

    def __seats_changed(self, value, which):
        seats_from = self.sbSeats['from'].value()
        seats_to = self.sbSeats['to'].value()
        if seats_from > seats_to:
            if which == 'from':
                self.sbSeats['to'].setValue(seats_from)
            else:
                self.sbSeats['from'].setValue(seats_to)

if __name__ == '__main__':
    config = Configuration.Config(file = "HUD_config.test.xml")
    db = Database.Database(config)

    qdict = SQL.Sql(db_server = 'sqlite')

    filters_display = { "Heroes"    : False,
                        "Sites"     : False,
                        "Games"     : False,
                        "Cards"     : True,
                        "Currencies": False,
                        "Limits"    : False,
                        "LimitSep"  : False,
                        "LimitType" : False,
                        "Type"      : False,
                        "UseType"   : 'ring',
                        "Seats"     : False,
                        "SeatSep"   : False,
                        "Dates"     : False,
                        "GraphOps"  : False,
                        "Groups"    : False,
                        "Button1"   : False,
                        "Button2"   : False
                          }

    from PyQt5.QtWidgets import QMainWindow, QApplication
    app = QApplication([])
    i = Filters(db, display = filters_display)
    main_window = QMainWindow()
    main_window.setCentralWidget(i)
    main_window.show()
    app.exec_()
