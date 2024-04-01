#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2008-2013 Steffen Schaumburg
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


import os
import sys
import re
import queue
import qdarkstyle
import multiprocessing
import threading

if os.name == 'nt':
    import win32api
    import win32con

import codecs
import traceback
import Options
import string
from functools import partial

cl_options = '.'.join(sys.argv[1:])
(options, argv) = Options.fpdb_options()
from L10n import set_locale_translation
import logging

from PyQt5.QtCore import (QCoreApplication, QDate, Qt)
from PyQt5.QtGui import (QScreen, QIcon)
from PyQt5.QtWidgets import (QAction, QApplication, QCalendarWidget,
                             QCheckBox, QDateEdit, QDialog,
                             QDialogButtonBox, QFileDialog,
                             QGridLayout, QHBoxLayout, QInputDialog,
                             QLabel, QLineEdit, QMainWindow,
                             QMessageBox, QPushButton, QScrollArea,
                             QTabWidget, QVBoxLayout, QWidget, QComboBox)

import interlocks
from Exceptions import *

# these imports not required in this module, imported here to report version in About dialog
import numpy

numpy_version = numpy.__version__
import sqlite3

sqlite3_version = sqlite3.version
sqlite_version = sqlite3.sqlite_version

import DetectInstalledSites
import GuiPrefs
import GuiLogView
# import GuiDatabase
import GuiBulkImport
import GuiTourneyImport

import GuiRingPlayerStats
import GuiTourneyPlayerStats
import GuiTourneyViewer
import GuiPositionalStats
import GuiAutoImport
import GuiGraphViewer
import GuiTourneyGraphViewer
import GuiSessionViewer
import GuiHandViewer
import GuiOddsCalc
import GuiStove

import SQL
import Database
import Configuration
import Card
import Exceptions
import Stats
import api, app

Configuration.set_logfile("fpdb-log.txt")

log = logging.getLogger("fpdb")

try:
    assert not hasattr(sys, 'frozen')  # We're surely not in a git repo if this fails
    import subprocess

    VERSION = subprocess.Popen(["git", "describe", "--tags", "--dirty"], stdout=subprocess.PIPE).communicate()[0]
    VERSION = VERSION[:-1]
except Exception:
    VERSION = "3.0.0alpha"


class fpdb(QMainWindow):
    def launch_ppt(self):
        path = os.getcwd()
        if os.name == 'nt':
            pathcomp = f"{path}\pyfpdb\ppt\p2.jar"
        else:
            pathcomp = f"{path}/ppt/p2.jar"
        subprocess.call(['java', '-jar', pathcomp])

    def add_and_display_tab(self, new_page, new_tab_name):
        """adds a tab, namely creates the button and displays it and appends all the relevant arrays"""
        for name in self.nb_tab_names:  # todo: check this is valid
            if name == new_tab_name:
                self.display_tab(new_tab_name)
                return  # if tab already exists, just go to it

        used_before = False
        for i, name in enumerate(self.tab_names):
            if name == new_tab_name:
                used_before = True
                event_box = self.tabs[i]
                page = self.pages[i]
                break

        if not used_before:
            page = new_page
            self.pages.append(new_page)
            self.tab_names.append(new_tab_name)

        index = self.nb.addTab(page, new_tab_name)
        self.nb_tab_names.append(new_tab_name)
        self.nb.setCurrentIndex(index)

    def display_tab(self, new_tab_name):
        """displays the indicated tab"""
        tab_no = -1
        for i, name in enumerate(self.nb_tab_names):
            if new_tab_name == name:
                tab_no = i
                break

        if tab_no < 0 or tab_no >= self.nb.count():
            raise FpdbError(f"invalid tab_no {str(tab_no)}")
        else:
            self.nb.setCurrentIndex(tab_no)

    def dia_about(self, widget, data=None):
        QMessageBox.about(
            self,
            f"FPDB{str(VERSION)}",
            "Copyright 2008-2023. See contributors.txt for details"
            + "You are free to change, and distribute original or changed versions "
              "of fpdb within the rules set out by the license"
            + "https://github.com/jejellyroll-fr/fpdb-3"
            + "\n"
            + "Your config file is: "
            + self.config.file,
        )
        return

    def dia_advanced_preferences(self, widget, data=None):
        # force reload of prefs from xml file - needed because HUD could
        # have changed file contents
        self.load_profile()
        if GuiPrefs.GuiPrefs(self.config, self).exec_():
            # save updated config
            self.config.save()
            self.reload_config()

    def dia_database_stats(self, widget, data=None):
        self.warning_box(
            string=f"Number of Hands: {self.db.getHandCount()}\nNumber of Tourneys: {self.db.getTourneyCount()}\nNumber of TourneyTypes: {self.db.getTourneyTypeCount()}",
            diatitle="Database Statistics")

    # end def dia_database_stats

    def dia_hud_preferences(self, widget, data=None):
        dia = QDialog(self)
        dia.setWindowTitle("Modifying Huds")
        dia.resize(1200, 600)
        label = QLabel("Please edit your huds.")
        dia.setLayout(QVBoxLayout())
        dia.layout().addWidget(label)
        label2 = QLabel("Please select the game category for which you want to configure HUD stats:")
        popups = []
        dia.layout().addWidget(label2)
        self.comboGame = QComboBox()

        games = self.config.get_stat_sets()
        for game in games:
            self.comboGame.addItem(game)

        dia.layout().addWidget(self.comboGame)
        self.comboGame.setCurrentIndex(1)
        result = self.comboGame.currentText()

        self.load_profile()
        # print('resultat', result)
        hud_stats = self.config.stat_sets[result]
        hud_nb_col = self.config.stat_sets[result].cols
        hud_nb_row = self.config.stat_sets[result].rows
        tab_rows = hud_nb_col * hud_nb_row
        # print('stats set',hud_stats )
        stat2_dict, stat3_dict, stat4_dict, stat5_dict, stat6_dict, stat7_dict, stat8_dict, stat9_dict, stat10_dict, \
            stat11_dict, stat12_dict, stat13_dict = [], [], [], [], [], [], [], [], [], [], [], []

        # HUD column will contain a button that shows favseat and HUD locations.
        # Make it possible to load screenshot to arrange HUD windowlets.

        self.table = QGridLayout()
        self.table.setSpacing(0)

        scrolling_frame = QScrollArea(dia)
        dia.layout().addWidget(scrolling_frame)
        scrolling_frame.setLayout(self.table)

        result3 = len(self.config.stat_sets[result].stats)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, dia)
        btns.accepted.connect(dia.accept)
        btns.rejected.connect(dia.reject)
        dia.layout().addWidget(btns)
        self.comboGame.currentIndexChanged.connect(self.index_changed)
        response = dia.exec_()
        if self.comboGame.currentIndexChanged and response:
            for y in range(0, result3):
                # print(result, self.stat2_dict[y].text(), self.stat3_dict[y].text(), self.stat4_dict[y].text(), self.stat5_dict[y].text(), self.stat6_dict[y].text(), self.stat7_dict[y].text(), self.stat8_dict[y].text(), self.stat9_dict[y].text(), self.stat10_dict[y].text(), self.stat11_dict[y].text(), self.stat12_dict[y].text(), self.stat13_dict[y].text())
                # print(self.result, stat2_dict[y].text())
                # print "site %s enabled=%s name=%s" % (available_site_names[site_number], check_buttons[site_number].get_active(), screen_names[site_number].get_text(), history_paths[site_number].get_text())
                self.config.edit_hud(result, self.stat2_dict[y].text(), self.stat3_dict[y].text(),
                                     self.stat4_dict[y].text(), self.stat5_dict[y].text(), self.stat6_dict[y].text(),
                                     self.stat7_dict[y].text(), self.stat8_dict[y].text(), self.stat9_dict[y].text(),
                                     self.stat10_dict[y].text(), self.stat11_dict[y].text(), self.stat12_dict[y].text(),
                                     self.stat13_dict[y].text())

            self.config.save()
            self.reload_config()

    def index_changed(self, index):
        self.comboGame.setCurrentIndex(index)
        result = self.comboGame.currentText()
        for i in reversed(range(self.table.count())):
            self.table.itemAt(i).widget().deleteLater()

        self.table.setSpacing(0)

        column_headers = ["coordonate", "stats name", "click", "hudcolor", "hudprefix", "hudsuffix",
                          "popup", "stat_hicolor", "stat_hith", "stat_locolor", "stat_loth",
                          "tip"]  # todo ("HUD")

        for header_number in range(0, len(column_headers)):
            label = QLabel(column_headers[header_number])
            label.setAlignment(Qt.AlignCenter)
            self.table.addWidget(label, 0, header_number)

        self.stat2_dict, self.stat3_dict, self.stat4_dict, self.stat5_dict, self.stat6_dict, self.stat7_dict, \
            self.stat8_dict, self.stat9_dict, self.stat10_dict, self.stat11_dict, self.stat12_dict, \
            self.stat13_dict = [], [], [], [], [], [], [], [], [], [], [], []

        self.load_profile()
        # print('resultat', result)
        hud_stats = self.config.stat_sets[result]
        hud_nb_col = self.config.stat_sets[result].cols
        hud_nb_row = self.config.stat_sets[result].rows
        tab_rows = hud_nb_col * hud_nb_row
        # print('stats set',hud_stats )

        result2 = list(self.config.stat_sets[result].stats)
        result3 = len(self.config.stat_sets[result].stats)
        # print(self.config.stat_sets[result].stats)
        # print(result2)
        # print(result3)
        y_pos = 1
        for y in range(0, result3):
            # print(result2[y])
            stat = result2[y]
            # print(self.config.stat_sets[result].stats[stat].stat_name)
            stat2 = QLabel()
            stat2.setText(str(stat))
            self.table.addWidget(stat2, y_pos, 0)
            self.stat2_dict.append(stat2)
            if os.name == 'nt':
                icoPath = os.path.dirname(__file__)

                icoPath = f"{icoPath}\\"
                # print(icoPath)
            else:
                icoPath = ""
            stat3 = QComboBox()
            stats_cash = self.config.get_gui_cash_stat_params()
            for x in range(0, len(stats_cash)):
                # print(stats_cash[x][0])
                stat3.addItem(QIcon(f"{icoPath}Letter-C-icon.png"), stats_cash[x][0])
            stats_tour = self.config.get_gui_tour_stat_params()
            for x in range(0, len(stats_tour)):
                # print(stats_tour[x][0])
                stat3.addItem(QIcon(f"{icoPath}Letter-T-icon.png"), stats_tour[x][0])
            stat3.setCurrentText(str(self.config.stat_sets[result].stats[stat].stat_name))
            self.table.addWidget(stat3, y_pos, 1)
            self.stat3_dict.append(stat3)

            stat4 = QLineEdit()
            stat4.setText(str(self.config.stat_sets[result].stats[stat].click))
            self.table.addWidget(stat4, y_pos, 2)
            self.stat4_dict.append(stat4)

            stat5 = QLineEdit()
            stat5.setText(str(self.config.stat_sets[result].stats[stat].hudcolor))
            self.table.addWidget(stat5, y_pos, 3)
            self.stat5_dict.append(stat5)

            stat6 = QLineEdit()
            stat6.setText(str(self.config.stat_sets[result].stats[stat].hudprefix))
            self.table.addWidget(stat6, y_pos, 4)
            self.stat6_dict.append(stat6)

            stat7 = QLineEdit()
            stat7.setText(str(self.config.stat_sets[result].stats[stat].hudsuffix))
            self.table.addWidget(stat7, y_pos, 5)
            self.stat7_dict.append(stat7)

            stat8 = QComboBox()
            for popup in self.config.popup_windows.keys():
                stat8.addItem(popup)
            stat8.setCurrentText(str(self.config.stat_sets[result].stats[stat].popup))
            self.table.addWidget(stat8, y_pos, 6)
            self.stat8_dict.append(stat8)

            stat9 = QLineEdit()
            stat9.setText(str(self.config.stat_sets[result].stats[stat].stat_hicolor))
            self.table.addWidget(stat9, y_pos, 7)
            self.stat9_dict.append(stat9)

            stat10 = QLineEdit()
            stat10.setText(str(self.config.stat_sets[result].stats[stat].stat_hith))
            self.table.addWidget(stat10, y_pos, 8)
            self.stat10_dict.append(stat10)

            stat11 = QLineEdit()
            stat11.setText(str(self.config.stat_sets[result].stats[stat].stat_locolor))
            self.table.addWidget(stat11, y_pos, 9)
            self.stat11_dict.append(stat11)

            stat12 = QLineEdit()
            stat12.setText(str(self.config.stat_sets[result].stats[stat].stat_loth))
            self.table.addWidget(stat12, y_pos, 10)
            self.stat12_dict.append(stat12)

            stat13 = QLineEdit()
            stat13.setText(str(self.config.stat_sets[result].stats[stat].tip))
            self.table.addWidget(stat13, y_pos, 11)
            self.stat13_dict.append(stat13)
            # if available_site_names[site_number] in detector.supportedSites:
            # pass

            y_pos += 1

    def dia_import_filters(self, checkState):
        dia = QDialog()
        dia.setWindowTitle("Skip these games when importing")
        dia.setLayout(QVBoxLayout())
        checkboxes = {}
        filters = self.config.get_import_parameters()['importFilters']
        for game in Card.games:
            checkboxes[game] = QCheckBox(game)
            dia.layout().addWidget(checkboxes[game])
            if game in filters:
                checkboxes[game].setChecked(True)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dia.layout().addWidget(btns)
        btns.accepted.connect(dia.accept)
        btns.rejected.connect(dia.reject)
        if dia.exec_():
            filterGames = []
            for game, cb in list(checkboxes.items()):
                if cb.isChecked():
                    filterGames.append(game)
            self.config.editImportFilters(",".join(filterGames))
            self.config.save()

    def dia_dump_db(self, widget, data=None):
        filename = "database-dump.sql"
        result = self.db.dumpDatabase()

        with open(filename, 'w') as dumpFile:
            dumpFile.write(result)

    # end def dia_database_stats

    def dia_recreate_tables(self, widget, data=None):
        """Dialogue that asks user to confirm that he wants to delete and recreate the tables"""
        if self.obtain_global_lock("fpdb.dia_recreate_tables"):  # returns true if successful
            dia_confirm = QMessageBox(QMessageBox.Warning, "Wipe DB", "Confirm deleting and recreating tables",
                                      QMessageBox.Yes | QMessageBox.No, self)
            diastring = f"Please confirm that you want to (re-)create the tables. If there already are tables in" \
                        f" the database {self.db.database} on {self.db.host}" \
                        f" they will be deleted and you will have to re-import your histories.\nThis may take a while."

            dia_confirm.setInformativeText(diastring)  # todo: make above string with bold for db, host and deleted
            response = dia_confirm.exec_()

            if response == QMessageBox.Yes:
                self.db.recreate_tables()
                # find any guibulkimport/guiautoimport windows and clear cache:
                for t in self.threads:
                    if isinstance(t, GuiBulkImport.GuiBulkImport) or isinstance(t, GuiAutoImport.GuiAutoImport):
                        t.importer.database.resetCache()
                self.release_global_lock()
            else:
                self.release_global_lock()
                log.info('User cancelled recreating tables')
        else:
            self.warning_box("Cannot open Database Maintenance window because other"
                             " windows have been opened. Re-start fpdb to use this option.")

    def dia_recreate_hudcache(self, widget, data=None):
        if self.obtain_global_lock("dia_recreate_hudcache"):
            self.dia_confirm = QDialog()
            self.dia_confirm.setWindowTitle("Confirm recreating HUD cache")
            self.dia_confirm.setLayout(QVBoxLayout())
            self.dia_confirm.layout().addWidget(QLabel("Please confirm that you want to re-create the HUD cache."))

            hb1 = QHBoxLayout()
            self.h_start_date = QDateEdit(QDate.fromString(self.db.get_hero_hudcache_start(), "yyyy-MM-dd"))
            lbl = QLabel(" Hero's cache starts: ")
            btn = QPushButton("Cal")
            btn.clicked.connect(partial(self.__calendar_dialog, entry=self.h_start_date))

            hb1.addWidget(lbl)
            hb1.addStretch()
            hb1.addWidget(self.h_start_date)
            hb1.addWidget(btn)
            self.dia_confirm.layout().addLayout(hb1)

            hb2 = QHBoxLayout()
            self.start_date = QDateEdit(QDate.fromString(self.db.get_hero_hudcache_start(), "yyyy-MM-dd"))
            lbl = QLabel(" Villains' cache starts: ")
            btn = QPushButton("Cal")
            btn.clicked.connect(partial(self.__calendar_dialog, entry=self.start_date))

            hb2.addWidget(lbl)
            hb2.addStretch()
            hb2.addWidget(self.start_date)
            hb2.addWidget(btn)
            self.dia_confirm.layout().addLayout(hb2)

            btns = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
            self.dia_confirm.layout().addWidget(btns)
            btns.accepted.connect(self.dia_confirm.accept)
            btns.rejected.connect(self.dia_confirm.reject)

            response = self.dia_confirm.exec_()
            if response:
                log.info("Rebuilding HUD Cache ...")

                self.db.rebuild_cache(self.h_start_date.date().toString("yyyy-MM-dd"),
                                      self.start_date.date().toString("yyyy-MM-dd"))
            else:
                log.info('User cancelled rebuilding hud cache')

            self.release_global_lock()
        else:
            self.warning_box("Cannot open Database Maintenance window because other windows have been opened. "
                             "Re-start fpdb to use this option.")

    def dia_rebuild_indexes(self, widget, data=None):
        if self.obtain_global_lock("dia_rebuild_indexes"):
            self.dia_confirm = QMessageBox(QMessageBox.Warning,
                                           "Rebuild DB",
                                           "Confirm rebuilding database indexes",
                                           QMessageBox.Yes | QMessageBox.No,
                                           self)
            diastring = "Please confirm that you want to rebuild the database indexes."
            self.dia_confirm.setInformativeText(diastring)

            response = self.dia_confirm.exec_()
            if response == QMessageBox.Yes:
                log.info(" Rebuilding Indexes ... ")
                self.db.rebuild_indexes()

                log.info(" Cleaning Database ... ")
                self.db.vacuumDB()

                log.info(" Analyzing Database ... ")
                self.db.analyzeDB()
            else:
                log.info('User cancelled rebuilding db indexes')

            self.release_global_lock()
        else:
            self.warning_box("Cannot open Database Maintenance window because"
                             " other windows have been opened. Re-start fpdb to use this option.")

    def dia_logs(self, widget, data=None):
        """opens the log viewer window"""
        # remove members from self.threads if close messages received
        self.process_close_messages()

        viewer = None
        for i, t in enumerate(self.threads):
            if str(t.__class__) == 'GuiLogView.GuiLogView':
                viewer = t
                break

        if viewer is None:
            # print "creating new log viewer"
            new_thread = GuiLogView.GuiLogView(self.config, self.window, self.closeq)
            self.threads.append(new_thread)
        else:
            # print "showing existing log viewer"
            viewer.get_dialog().present()

        # if lock_set:
        #    self.release_global_lock()

    def dia_site_preferences_seat(self, widget, data=None):
        dia = QDialog(self)
        dia.setWindowTitle("Seat Preferences")
        dia.resize(1200, 600)
        label = QLabel("Please select your prefered seat.")
        dia.setLayout(QVBoxLayout())
        dia.layout().addWidget(label)

        self.load_profile()
        site_names = self.config.site_ids
        available_site_names = []
        for site_name in site_names:
            try:
                tmp = self.config.supported_sites[site_name].enabled
                available_site_names.append(site_name)
            except KeyError:
                pass

        column_headers = ["Site", "2 players:\nbetween 0 & 2", "3 players:\nbetween 0 & 3 ",
                          "4 players:\nbetween 0 & 4", "5 players:\nbetween 0 & 5", "6 players:\nbetween 0 & 6",
                          "7 players:\nbetween 0 & 7", "8 players:\nbetween 0 & 8", "9 players:\nbetween 0 & 9",
                          "10 players:\nbetween 0 & 10"]  # todo ("HUD")
        # HUD column will contain a button that shows favseat and HUD locations.
        # Make it possible to load screenshot to arrange HUD windowlets.

        table = QGridLayout()
        table.setSpacing(0)

        scrolling_frame = QScrollArea(dia)
        dia.layout().addWidget(scrolling_frame)
        scrolling_frame.setLayout(table)

        for header_number in range(0, len(column_headers)):
            label = QLabel(column_headers[header_number])
            label.setAlignment(Qt.AlignCenter)
            table.addWidget(label, 0, header_number)

        history_paths = []
        check_buttons = []
        screen_names = []
        seat2_dict, seat3_dict, seat4_dict, seat5_dict, seat6_dict, seat7_dict, seat8_dict, \
            seat9_dict, seat10_dict = [], [], [], [], [], [], [], [], []
        summary_paths = []
        detector = DetectInstalledSites.DetectInstalledSites()

        y_pos = 1
        for site_number in range(0, len(available_site_names)):
            check_button = QCheckBox(available_site_names[site_number])
            check_button.setChecked(self.config.supported_sites[available_site_names[site_number]].enabled)
            table.addWidget(check_button, y_pos, 0)
            check_buttons.append(check_button)
            hud_seat = self.config.supported_sites[available_site_names[site_number]].fav_seat[2]

            # print('hud seat ps:', type(hud_seat), hud_seat)
            seat2 = QLineEdit()

            seat2.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[2]))
            table.addWidget(seat2, y_pos, 1)
            seat2_dict.append(seat2)
            seat2.textChanged.connect(partial(self.autoenableSite, checkbox=check_buttons[site_number]))

            seat3 = QLineEdit()
            seat3.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[3]))
            table.addWidget(seat3, y_pos, 2)
            seat3_dict.append(seat3)

            seat4 = QLineEdit()
            seat4.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[4]))
            table.addWidget(seat4, y_pos, 3)
            seat4_dict.append(seat4)

            seat5 = QLineEdit()
            seat5.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[5]))
            table.addWidget(seat5, y_pos, 4)
            seat5_dict.append(seat5)

            seat6 = QLineEdit()
            seat6.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[6]))
            table.addWidget(seat6, y_pos, 5)
            seat6_dict.append(seat6)

            seat7 = QLineEdit()
            seat7.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[7]))
            table.addWidget(seat7, y_pos, 6)
            seat7_dict.append(seat7)

            seat8 = QLineEdit()
            seat8.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[8]))
            table.addWidget(seat8, y_pos, 7)
            seat8_dict.append(seat8)

            seat9 = QLineEdit()
            seat9.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[9]))
            table.addWidget(seat9, y_pos, 8)
            seat9_dict.append(seat9)

            seat10 = QLineEdit()
            seat10.setText(str(self.config.supported_sites[available_site_names[site_number]].fav_seat[10]))
            table.addWidget(seat10, y_pos, 9)
            seat10_dict.append(seat10)

            if available_site_names[site_number] in detector.supportedSites:
                pass

            y_pos += 1

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, dia)
        btns.accepted.connect(dia.accept)
        btns.rejected.connect(dia.reject)
        dia.layout().addWidget(btns)

        response = dia.exec_()
        if response:
            for site_number in range(0, len(available_site_names)):
                # print "site %s enabled=%s name=%s" % (available_site_names[site_number],
                # check_buttons[site_number].get_active(), screen_names[site_number].get_text(),
                # history_paths[site_number].get_text())
                self.config.edit_fav_seat(available_site_names[site_number],
                                          str(check_buttons[site_number].isChecked()), seat2_dict[site_number].text(),
                                          seat3_dict[site_number].text(), seat4_dict[site_number].text(),
                                          seat5_dict[site_number].text(), seat6_dict[site_number].text(),
                                          seat7_dict[site_number].text(), seat8_dict[site_number].text(),
                                          seat9_dict[site_number].text(), seat10_dict[site_number].text())

            self.config.save()
            self.reload_config()

    def dia_site_preferences(self, widget, data=None):
        dia = QDialog(self)
        dia.setWindowTitle("Site Preferences")
        dia.resize(1200, 600)
        label = QLabel("Please select which sites you play on and enter your usernames.")
        dia.setLayout(QVBoxLayout())
        dia.layout().addWidget(label)

        self.load_profile()
        site_names = self.config.site_ids
        available_site_names = []
        for site_name in site_names:
            try:
                tmp = self.config.supported_sites[site_name].enabled
                available_site_names.append(site_name)
            except KeyError:
                pass

        column_headers = ["Site", "Detect", "Screen Name", "Hand History Path", "",
                          "Tournament Summary Path", "", "Favorite seat"]  # todo ("HUD")
        # HUD column will contain a button that shows favseat and HUD locations.
        # Make it possible to load screenshot to arrange HUD windowlets.

        table = QGridLayout()
        table.setSpacing(0)

        scrolling_frame = QScrollArea(dia)
        dia.layout().addWidget(scrolling_frame)
        scrolling_frame.setLayout(table)

        for header_number in range(0, len(column_headers)):
            label = QLabel(column_headers[header_number])
            label.setAlignment(Qt.AlignCenter)
            table.addWidget(label, 0, header_number)

        check_buttons = []
        screen_names = []
        history_paths = []
        summary_paths = []
        detector = DetectInstalledSites.DetectInstalledSites()

        y_pos = 1
        for site_number in range(0, len(available_site_names)):
            check_button = QCheckBox(available_site_names[site_number])
            check_button.setChecked(self.config.supported_sites[available_site_names[site_number]].enabled)
            table.addWidget(check_button, y_pos, 0)
            check_buttons.append(check_button)

            hero = QLineEdit()
            hero.setText(self.config.supported_sites[available_site_names[site_number]].screen_name)
            table.addWidget(hero, y_pos, 2)
            screen_names.append(hero)
            hero.textChanged.connect(partial(self.autoenableSite, checkbox=check_buttons[site_number]))

            entry = QLineEdit()
            entry.setText(self.config.supported_sites[available_site_names[site_number]].HH_path)
            table.addWidget(entry, y_pos, 3)
            history_paths.append(entry)

            choose1 = QPushButton("Browse")
            table.addWidget(choose1, y_pos, 4)
            choose1.clicked.connect(partial(self.browseClicked, parent=dia, path=history_paths[site_number]))

            entry = QLineEdit()
            entry.setText(self.config.supported_sites[available_site_names[site_number]].TS_path)
            table.addWidget(entry, y_pos, 5)
            summary_paths.append(entry)

            choose2 = QPushButton("Browse")
            table.addWidget(choose2, y_pos, 6)
            choose2.clicked.connect(partial(self.browseClicked, parent=dia, path=summary_paths[site_number]))

            if available_site_names[site_number] in detector.supportedSites:
                button = QPushButton("Detect")
                table.addWidget(button, y_pos, 1)
                button.clicked.connect(partial(self.detect_clicked, data=(detector, available_site_names[site_number],
                                                                          screen_names[site_number],
                                                                          history_paths[site_number],
                                                                          summary_paths[site_number])))
            y_pos += 1

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, dia)
        btns.accepted.connect(dia.accept)
        btns.rejected.connect(dia.reject)
        dia.layout().addWidget(btns)

        response = dia.exec_()
        if response:
            for site_number in range(0, len(available_site_names)):
                # print "site %s enabled=%s name=%s" % (available_site_names[site_number],
                # check_buttons[site_number].get_active(), screen_names[site_number].get_text(),
                # history_paths[site_number].get_text())
                self.config.edit_site(available_site_names[site_number], str(check_buttons[site_number].isChecked()),
                                      screen_names[site_number].text(), history_paths[site_number].text(),
                                      summary_paths[site_number].text())

            self.config.save()
            self.reload_config()

    def autoenableSite(self, text, checkbox):
        # autoactivate site if something gets typed in the screename field
        checkbox.setChecked(True)

    def browseClicked(self, widget, parent, path):
        """runs when user clicks one of the browse buttons for the TS folder"""

        newpath = QFileDialog.getExistingDirectory(parent, "Please choose the path that you want to Auto Import",
                                                   path.text())
        if newpath:
            path.setText(newpath)

    def detect_clicked(self, widget, data):
        detector = data[0]
        site_name = data[1]
        entry_screen_name = data[2]
        entry_history_path = data[3]
        entry_summary_path = data[4]
        if detector.sitestatusdict[site_name]['detected']:
            entry_screen_name.setText(detector.sitestatusdict[site_name]['heroname'])
            entry_history_path.setText(detector.sitestatusdict[site_name]['hhpath'])
            if detector.sitestatusdict[site_name]['tspath']:
                entry_summary_path.setText(detector.sitestatusdict[site_name]['tspath'])

    def reload_config(self):
        if len(self.nb_tab_names) == 1:
            # only main tab open, reload profile
            self.load_profile()
            self.warning_box(f"Configuration settings have been updated,"
                             f" Fpdb needs to be restarted now\n\nClick OK to close Fpdb")
            sys.exit()
        else:
            self.warning_box(f"Updated preferences have not been loaded because windows are open."
                             f" Re-start fpdb to load them.")

    def process_close_messages(self):
        # check for close messages
        try:
            while True:
                name = self.closeq.get(False)
                for i, t in enumerate(self.threads):
                    if str(t.__class__) == str(name):
                        # thread has ended so remove from list:
                        del self.threads[i]
                        break
        except queue.Empty:
            # no close messages on queue, do nothing
            pass

    def __calendar_dialog(self, widget, entry):
        d = QDialog(self.dia_confirm)
        d.setWindowTitle('Pick a date')

        vb = QVBoxLayout()
        d.setLayout(vb)
        cal = QCalendarWidget()
        vb.addWidget(cal)

        btn = QPushButton('Done')
        btn.clicked.connect(partial(self.__get_date, calendar=cal, entry=entry, win=d))

        vb.addWidget(btn)

        d.exec_()
        return

    def createMenuBar(self):
        mb = self.menuBar()
        configMenu = mb.addMenu('Configure')
        importMenu = mb.addMenu('Import')
        hudMenu = mb.addMenu('HUD')
        cashMenu = mb.addMenu('Cash')
        tournamentMenu = mb.addMenu('Tournament')
        maintenanceMenu = mb.addMenu('Maintenance')
        toolsMenu = mb.addMenu('Tools')
        # dataMenu = mb.addMenu('Dataviz')
        helpMenu = mb.addMenu('Help')

        # Create actions
        def makeAction(name, callback, shortcut=None, tip=None):
            action = QAction(name, self)
            if shortcut:
                action.setShortcut(shortcut)
            if tip:
                action.setToolTip(tip)
            action.triggered.connect(callback)
            return action

        configMenu.addAction(makeAction('Site Settings', self.dia_site_preferences))
        configMenu.addAction(makeAction('Seat Settings', self.dia_site_preferences_seat))
        configMenu.addAction(makeAction('Hud Settings', self.dia_hud_preferences))
        configMenu.addAction(
            makeAction('Adv Preferences', self.dia_advanced_preferences, tip='Edit your preferences'))
        # configMenu.addAction(makeAction(('HUD Stats Settings'), self.dia_hud_preferences))
        configMenu.addAction(makeAction('Import filters', self.dia_import_filters))
        configMenu.addSeparator()
        configMenu.addAction(makeAction('Close Fpdb', self.quit, 'Ctrl+Q', 'Quit the Program'))

        importMenu.addAction(makeAction('Bulk Import', self.tab_bulk_import, 'Ctrl+B'))
        # importMenu.addAction(makeAction(('_Import through eMail/IMAP'), self.tab_imap_import))

        hudMenu.addAction(makeAction('HUD and Auto Import', self.tab_auto_import, 'Ctrl+A'))

        cashMenu.addAction(makeAction('Graphs', self.tabGraphViewer, 'Ctrl+G'))
        cashMenu.addAction(makeAction('Ring Player Stats', self.tab_ring_player_stats, 'Ctrl+P'))
        cashMenu.addAction(makeAction('Hand Viewer', self.tab_hand_viewer))
        # cashMenu.addAction(makeAction(('Positional Stats (tabulated view)'), self.tab_positional_stats))
        cashMenu.addAction(makeAction('Session Stats', self.tab_session_stats, 'Ctrl+S'))
        # cashMenu.addAction(makeAction(('Stove (preview)'), self.tabStove))

        tournamentMenu.addAction(makeAction('Tourney Graphs', self.tabTourneyGraphViewer))
        tournamentMenu.addAction(makeAction('Tourney Stats', self.tab_tourney_player_stats, 'Ctrl+T'))
        # tournamentMenu.addAction(makeAction(('Tourney Viewer'), self.tab_tourney_viewer_stats))
        tournamentMenu.addAction(makeAction('Tourney Viewer', self.tab_tourney_viewer_stats))

        maintenanceMenu.addAction(makeAction('Statistics', self.dia_database_stats, 'View Database Statistics'))
        maintenanceMenu.addAction(makeAction('Create or Recreate Tables', self.dia_recreate_tables))
        maintenanceMenu.addAction(makeAction('Rebuild HUD Cache', self.dia_recreate_hudcache))
        maintenanceMenu.addAction(makeAction('Rebuild DB Indexes', self.dia_rebuild_indexes))
        maintenanceMenu.addAction(makeAction('Dump Database to Textfile (takes ALOT of time)', self.dia_dump_db))

        toolsMenu.addAction(makeAction('Odds Calc', self.tab_odds_calc))
        toolsMenu.addAction(makeAction('PokerProTools', self.launch_ppt))

        # dataMenu.addAction(makeAction(('launch server'), self.launch_dataviz_server))

        helpMenu.addAction(makeAction('Log Messages', self.dia_logs, 'Log and Debug Messages'))
        helpMenu.addAction(makeAction('Help Tab', self.tab_main_help))
        helpMenu.addSeparator()
        helpMenu.addAction(makeAction('Infos', self.dia_about, 'About the program'))

    def load_profile(self, create_db=False):
        """Loads profile from the provided path name."""
        self.config = Configuration.Config(file=options.config, dbname=options.dbname)
        if self.config.file_error:
            self.warning_box(f"There is an error in your config file"
                             f" {self.config.file}:\n{str(self.config.file_error)}", diatitle="CONFIG FILE ERROR")
            sys.exit()

        log.info(f"Logfile is {os.path.join(self.config.dir_log, self.config.log_file)}")
        log.info(f"load profiles {self.config.example_copy}")
        log.info(f"{self.display_config_created_dialogue}")
        log.info(f"{self.config.wrongConfigVersion}")
        if self.config.example_copy or self.display_config_created_dialogue:
            self.info_box("Config file", [
                "Config file has been created at " + self.config.file + ".",
                "Enter your screen_name and hand history path in the Site Preferences window"
                " (Main menu) before trying to import hands."
            ])

            self.display_config_created_dialogue = False
        elif self.config.wrongConfigVersion:
            diaConfigVersionWarning = QDialog()
            diaConfigVersionWarning.setWindowTitle("Strong Warning - Local configuration out of date")
            diaConfigVersionWarning.setLayout(QVBoxLayout())
            label = QLabel([
                "\nYour local configuration file needs to be updated."
            ])
            diaConfigVersionWarning.layout().addWidget(label)
            label = QLabel([
                "\nYour local configuration file needs to be updated.",
                "This error is not necessarily fatal but it is strongly recommended that you update the configuration."
            ])

            diaConfigVersionWarning.layout().addWidget(label)
            label = QLabel([
                "To create a new configuration, see:",
                "fpdb.sourceforge.net/apps/mediawiki/fpdb/index.php?title=Reset_Configuration"
            ])

            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            diaConfigVersionWarning.layout().addWidget(label)
            label = QLabel([
                f"A new configuration will destroy all personal settings"
                f" (hud layout, site folders, screennames, favourite seats).\n"
            ])

            diaConfigVersionWarning.layout().addWidget(label)

            label = QLabel("To keep existing personal settings, you must edit the local file.")
            diaConfigVersionWarning.layout().addWidget(label)

            label = QLabel("See the release note for information about the edits needed")
            diaConfigVersionWarning.layout().addWidget(label)

            btns = QDialogButtonBox(QDialogButtonBox.Ok)
            btns.accepted.connect(diaConfigVersionWarning.accept)
            diaConfigVersionWarning.layout().addWidget(btns)

            diaConfigVersionWarning.exec_()
            self.config.wrongConfigVersion = False

        self.settings = {}
        self.settings['global_lock'] = self.lock
        if os.sep == "/":
            self.settings['os'] = "linuxmac"
        else:
            self.settings['os'] = "windows"

        self.settings.update({'cl_options': cl_options})
        self.settings.update(self.config.get_db_parameters())
        self.settings.update(self.config.get_import_parameters())
        self.settings.update(self.config.get_default_paths())

        if self.db is not None and self.db.is_connected():
            self.db.disconnect()

        self.sql = SQL.Sql(db_server=self.settings['db-server'])
        err_msg = None
        try:
            self.db = Database.Database(self.config, sql=self.sql)
            if self.db.get_backend_name() == 'SQLite':
                # tell sqlite users where the db file is
                log.info(f"Connected to SQLite: {self.db.db_path}")
        except Exceptions.FpdbMySQLAccessDenied:
            err_msg = "MySQL Server reports: Access denied. Are your permissions set correctly?"
        except Exceptions.FpdbMySQLNoDatabase:
            err_msg = f"MySQL client reports: 2002 or 2003 error." \
                      f" Unable to connect - Please check that the MySQL service has been started."

        except Exceptions.FpdbPostgresqlAccessDenied:
            err_msg = "PostgreSQL Server reports: Access denied. Are your permissions set correctly?"
        except Exceptions.FpdbPostgresqlNoDatabase:
            err_msg = f"PostgreSQL client reports: Unable to connect -" \
                f"Please check that the PostgreSQL service has been started."
        if err_msg is not None:
            self.db = None
            self.warning_box(err_msg)
        if self.db is not None and not self.db.is_connected():
            self.db = None

        if self.db is not None and self.db.wrongDbVersion:
            diaDbVersionWarning = QMessageBox(QMessageBox.Warning, "Strong Warning - Invalid database version",
                                              "An invalid DB version or missing tables have been detected.",
                                              QMessageBox.Ok, self)
            diaDbVersionWarning.setInformativeText(
                f"This error is not necessarily fatal but it is strongly"
                f" recommended that you recreate the tables by using the Database menu."
                f"Not doing this will likely lead to misbehaviour including fpdb crashes, corrupt data etc."
            )

            diaDbVersionWarning.exec_()
        if self.db is not None and self.db.is_connected():
            self.statusBar().showMessage(f"Status: Connected to {self.db.get_backend_name()}"
                                         f" database named {self.db.database} on host {self.db.host}")

            # rollback to make sure any locks are cleared:
            self.db.rollback()

        # If the db-version is out of date, don't validate the config
        # otherwise the end user gets bombarded with false messages
        # about every site not existing
        if hasattr(self.db, 'wrongDbVersion'):
            if not self.db.wrongDbVersion:
                self.validate_config()

    def obtain_global_lock(self, source):
        ret = self.lock.acquire(source=source)  # will return false if lock is already held
        if ret:
            log.info(f"Global lock taken by {source}")
            self.lockTakenBy = source
        else:
            log.info(f"Failed to get global lock, it is currently held by {source}")
        return ret
        # need to release it later:
        # self.lock.release()

    def quit(self, widget, data=None):
        # TODO: can we get some / all of the stuff done in this function to execute on any kind of abort?
        # FIXME  get two "quitting normally" messages, following the addition of the self.window.destroy() call
        #       ... because self.window.destroy() leads to self.destroy() which calls this!
        if not self.quitting:
            log.info("Quitting normally")
            self.quitting = True
        # TODO: check if current settings differ from profile, if so offer to save or abort

        if self.db is not None:
            if self.db.backend == self.db.MYSQL_INNODB:
                try:
                    import _mysql_exceptions
                    if self.db is not None and self.db.is_connected():
                        self.db.disconnect()
                except _mysql_exceptions.OperationalError:  # oh, damn, we're already disconnected
                    pass
            else:
                if self.db is not None and self.db.is_connected():
                    self.db.disconnect()
        else:
            pass
        # self.statusIcon.set_visible(False)
        QCoreApplication.quit()

    def release_global_lock(self):
        self.lock.release()
        self.lockTakenBy = None
        log.info("Global lock released.")

    def tab_auto_import(self, widget, data=None):
        """opens the auto import tab"""
        new_aimp_thread = GuiAutoImport.GuiAutoImport(self.settings, self.config, self.sql, self)
        self.threads.append(new_aimp_thread)
        self.add_and_display_tab(new_aimp_thread, "HUD")
        if options.autoimport:
            new_aimp_thread.startClicked(new_aimp_thread.startButton, "autostart")
            options.autoimport = False

    def tab_bulk_import(self, widget, data=None):
        """opens a tab for bulk importing"""
        new_import_thread = GuiBulkImport.GuiBulkImport(self.settings, self.config, self.sql, self)
        self.threads.append(new_import_thread)
        self.add_and_display_tab(new_import_thread, "Bulk Import")

    def tab_odds_calc(self, widget, data=None):
        """opens a tab for bulk importing"""
        new_import_thread = GuiOddsCalc.GuiOddsCalc(self)
        self.threads.append(new_import_thread)
        self.add_and_display_tab(new_import_thread, "Odds Calc")

    def tab_tourney_import(self, widget, data=None):
        """opens a tab for bulk importing tournament summaries"""
        new_import_thread = GuiTourneyImport.GuiTourneyImport(self.settings, self.config, self.sql, self.window)
        self.threads.append(new_import_thread)
        bulk_tab = new_import_thread.get_vbox()
        self.add_and_display_tab(bulk_tab, "Tournament Results Import")

    def tab_imap_import(self, widget, data=None):
        new_thread = GuiImapFetcher.GuiImapFetcher(self.config, self.db, self.sql, self)
        self.threads.append(new_thread)
        tab = new_thread.get_vbox()
        self.add_and_display_tab(tab, "eMail Import")

    # end def tab_import_imap_summaries

    def tab_ring_player_stats(self, widget, data=None):
        new_ps_thread = GuiRingPlayerStats.GuiRingPlayerStats(self.config, self.sql, self)
        self.threads.append(new_ps_thread)
        self.add_and_display_tab(new_ps_thread, "Ring Player Stats")

    def tab_tourney_player_stats(self, widget, data=None):
        new_ps_thread = GuiTourneyPlayerStats.GuiTourneyPlayerStats(self.config, self.db, self.sql, self)
        self.threads.append(new_ps_thread)
        self.add_and_display_tab(new_ps_thread, "Tourney Stats")

    def tab_tourney_viewer_stats(self, widget, data=None):
        new_thread = GuiTourneyViewer.GuiTourneyViewer(self.config, self.db, self.sql, self)
        self.threads.append(new_thread)
        self.add_and_display_tab(new_thread, "Tourney Viewer")

    def tab_positional_stats(self, widget, data=None):
        new_ps_thread = GuiPositionalStats.GuiPositionalStats(self.config, self.sql)
        self.threads.append(new_ps_thread)
        ps_tab = new_ps_thread.get_vbox()
        self.add_and_display_tab(ps_tab, "Positional Stats")

    def tab_session_stats(self, widget, data=None):
        new_ps_thread = GuiSessionViewer.GuiSessionViewer(self.config, self.sql, self, self)
        self.threads.append(new_ps_thread)
        self.add_and_display_tab(new_ps_thread, "Session Stats")

    def tab_hand_viewer(self, widget, data=None):
        new_ps_thread = GuiHandViewer.GuiHandViewer(self.config, self.sql, self)
        self.threads.append(new_ps_thread)
        self.add_and_display_tab(new_ps_thread, "Hand Viewer")

    def tab_main_help(self, widget, data=None):
        """Displays a tab with the main fpdb help screen"""
        mh_tab = QLabel(("""
                        Welcome to Fpdb!
                        
                        This program is currently in an alpha-state, so our database format is still sometimes changed.
                        You should therefore always keep your hand history files so that you can re-import
                        after an update, if necessary.
                        
                        all configuration now happens in HUD_config.xml.
                        
                        This program is free/libre open source software licensed partially under the AGPL3,
                        and partially under GPL2 or later.
                        The Windows installer package includes code licensed under the MIT license.
                        You can find the full license texts in agpl-3.0.txt, gpl-2.0.txt, gpl-3.0.txt
                        and mit.txt in the fpdb installation directory."""))
        self.add_and_display_tab(mh_tab, "Help")

    def tabGraphViewer(self, widget, data=None):
        """opens a graph viewer tab"""
        new_gv_thread = GuiGraphViewer.GuiGraphViewer(self.sql, self.config, self)
        self.threads.append(new_gv_thread)
        self.add_and_display_tab(new_gv_thread, "Graphs")

    def tabTourneyGraphViewer(self, widget, data=None):
        """opens a graph viewer tab"""
        new_gv_thread = GuiTourneyGraphViewer.GuiTourneyGraphViewer(self.sql, self.config, self)
        self.threads.append(new_gv_thread)
        self.add_and_display_tab(new_gv_thread, "Tourney Graphs")

    def tabStove(self, widget, data=None):
        """opens a tab for poker stove"""
        thread = GuiStove.GuiStove(self.config, self)
        self.threads.append(thread)
        # tab = thread.get_vbox()
        self.add_and_display_tab(thread, "Stove")

    def __init__(self):
        QMainWindow.__init__(self)
        cards = os.path.join(Configuration.GRAPHICS_PATH, 'tribal.jpg')
        if os.path.exists(cards):
            self.setWindowIcon(QIcon(cards))
        set_locale_translation()
        # no more than 1 process can this lock at a time:
        self.lock = interlocks.InterProcessLock(name="fpdb_global_lock")
        self.db = None
        self.status_bar = None
        self.quitting = False
        self.visible = False
        self.threads = []  # objects used by tabs - no need for threads, gtk handles it
        self.closeq = queue.Queue(20)  # used to signal ending of a thread (only logviewer for now)

        if options.initialRun:
            self.display_config_created_dialogue = True
            self.display_site_preferences = True
        else:
            self.display_config_created_dialogue = False
            self.display_site_preferences = False

        # create window, move it to specific location on command line
        if options.xloc is not None or options.yloc is not None:
            if options.xloc is None:
                options.xloc = 0
            if options.yloc is None:
                options.yloc = 0
            self.move(options.xloc, options.yloc)

        self.setWindowTitle("Free Poker DB 3")

        # set a default x/y size for the window
        defx, defy = 1920, 1080
        sg = QApplication.primaryScreen().availableGeometry()
        if sg.width() < defx:
            defx = sg.width()
        if sg.height() < defy:
            defy = sg.height()
        self.resize(defx, defy)

        # create our Main Menu Bar
        self.createMenuBar()

        # create a tab bar
        self.nb = QTabWidget()
        self.setCentralWidget(self.nb)
        self.tabs = []  # the event_boxes forming the actual tabs
        self.tab_names = []  # names of tabs used since program started, not removed if tab is closed
        self.pages = []  # the contents of the page, not removed if tab is closed
        self.nb_tab_names = []  # list of tab names currently displayed in notebook

        # create the first tab
        self.tab_main_help(None, None)

        # determine window visibility from command line options
        if options.minimized:
            self.showMinimized()
        if options.hidden:
            self.hide()

        if not options.hidden:
            self.show()
            self.visible = True  # Flip on

        self.load_profile(create_db=True)

        if self.config.install_method == 'app':
            for site in list(self.config.supported_sites.values()):
                if site.screen_name != "YOUR SCREEN NAME HERE":
                    break
            else:  # No site has a screen name set
                options.initialRun = True
                self.display_config_created_dialogue = True
                self.display_site_preferences = True

        if options.initialRun and self.display_site_preferences:
            self.dia_site_preferences(None, None)
            self.display_site_preferences = False

        # setup error logging
        if not options.errorsToConsole:
            fileName = os.path.join(self.config.dir_log, 'fpdb-errors.txt')
            log.info(f"Note: error output is being diverted to {self.config.dir_log}."
                  f" Any major error will be reported there _only_.")

            errorFile = codecs.open(fileName, 'w', 'utf-8')
            sys.stderr = errorFile

        sys.stderr.write("fpdb starting ...")

        if options.autoimport:
            self.tab_auto_import(None)

    def info_box(self, str1, str2):
        diapath = QMessageBox(self)
        diapath.setWindowTitle(str1)
        diapath.setText(str2)
        return diapath.exec_()

    def warning_box(self, string, diatitle="FPDB WARNING"):
        return QMessageBox(QMessageBox.Warning, diatitle, string).exec_()

    def validate_config(self):
        # check if sites in config file are in DB
        for site in self.config.supported_sites:  # get site names from config file
            try:
                self.config.get_site_id(site)  # and check against list from db
            except KeyError as exc:
                log.warning(f"site {site} missing from db")
                dia = QMessageBox()
                dia.setIcon(QMessageBox.Warning)
                dia.setText("Unknown Site")
                dia.setStandardButtons(QMessageBox.Ok)
                dia.exec_()
                diastring = f"Warning: Unable to find site '{site}'"
                dia.format_secondary_text(diastring)
                dia.run()
                dia.destroy()

if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    me = fpdb()
    app.exec_()
