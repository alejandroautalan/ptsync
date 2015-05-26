from prefs import appconf

class PreferencesDialog(object):
    def __init__(self, app):
        self.app = app
        self.dialog = app.builder.get_object('preferences', app.mainwindow)
        self.builder = app.builder
        self.playlistdir = self.builder.get_object('playlistdir')
        self.builder.connect_callbacks(self)
        self.__load_options()

    def on_preferences_close(self, event=None):
        self.__save_options()
        self.dialog.close()
    
    def __load_options(self):
        pldir = appconf.config.get('DEFAULT', 'playlistdir')
        self.playlistdir.configure(path=pldir)
        print(pldir)

    def __save_options(self):
        pldir = self.playlistdir.cget('path')
        appconf.config.set('DEFAULT', 'playlistdir', pldir)
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

