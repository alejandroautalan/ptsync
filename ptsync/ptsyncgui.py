# -*- coding: utf-8 -*-
import os
import pygubu
from dialogs import *

APP_DIR = os.path.dirname(os.path.abspath(__file__))


class PtsyncGui(object):
    def __init__(self):
        self.builder = b = pygubu.Builder()
        b.add_from_file(os.path.join(APP_DIR, 'ptsync.ui'))
        self.mainwindow = mainwindow = b.get_object('mainwindow')
#        mainwindow.protocol("WM_DELETE_WINDOW", self.__on_window_close)
        self.dlg_preferences = None
        self.dlg_addplaylist = None
        b.connect_callbacks(self)
    
    def on_preferences_cb(self, event=None):
        if self.dlg_preferences is None:
            self.dlg_preferences = PreferencesDialog(self)
        self.dlg_preferences.dialog.run()
    
    def on_addplaylist_cb(self, event=None):
        if self.dlg_addplaylist is None:
            self.dlg_addplaylist = AddPlaylistDialog(self)
            self.dlg_addplaylist.dialog.bind('<<AddPlaylistURL>>', self.on_addplaylist_url)
        self.dlg_addplaylist.dialog.run()
        
    def on_addplaylist_url(self, event=None):
        print(self.dlg_addplaylist.url)
    
    def __on_window_close(self):
        pass
    
    def run(self):
        self.mainwindow.mainloop()

if __name__ == '__main__':
    app = PtsyncGui()
    app.run()
