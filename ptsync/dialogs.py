import os
import logging
import tkinter as tk
import tkinter.messagebox

from .prefs import appconf

logger = logging.getLogger(__name__)


class PreferencesDialog(object):
    def __init__(self, app):
        self.app = app
        self.dialog = app.builder.get_object('preferences', app.mainwindow)
        self.builder = app.builder
        self.builder.connect_callbacks(self)
        self.vnames = [k for k, v in appconf.VARS]
        self.builder.import_variables(self, self.vnames)
        self.__load_options()

    def on_preferences_close(self, event=None):
        self.__save_options()
        self.dialog.close()
    
    def __load_options(self):
        for varname in self.vnames:
            attr = getattr(self, varname)
            attr.set(appconf.config.get(appconf.DEF, varname))

    def __save_options(self):
        for varname in self.vnames:
            attr = getattr(self, varname)
            value = attr.get()
            logger.debug('option {0}'.format(repr(value)))
            appconf.config.set(appconf.DEF, varname, value)
        appconf.save()


class AddPlaylistDialog(object):
    def __init__(self, app):
        self.app = app
        self.dialog = app.builder.get_object('addplaylist', app.mainwindow)
        self.builder = app.builder
        self.builder.connect_callbacks(self)
        self.url = None

    def on_addplaylist_cancel(self, event=None):
        self.url = None
        self.dialog.close()
        
    def on_addplaylist_ok(self, event=None):
        self.url = self.builder.get_variable('playlisturl').get()
        self.dialog.close()
        self.dialog.toplevel.event_generate('<<AddPlaylistURL>>')


class CopyToDialog(object):
    def __init__(self, app):
        self.app = app
        self.dialog = app.builder.get_object('copytodialog', app.mainwindow)
        self.builder = app.builder
        self.builder.connect_callbacks(self)
        self.path = None

    def on_copyto_cancel(self, event=None):
        self.path = None
        self.dialog.close()
        
    def on_copyto_ok(self, event=None):
        self.path = self.builder.get_variable('copyto_path').get()
        if os.path.exists(self.path):
            self.dialog.close()
            self.dialog.toplevel.event_generate('<<PlaylistCopyTo>>')
        else:
            tk.messagebox.showinfo('PTSync', 'Please select a folder.')

