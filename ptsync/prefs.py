try:
    import ConfigParser as configparser
except:
    import configparser

import os
from appdirs import AppDirs


class AppConfig(object):
    def __init__(self):
        self.dirs = dirs = AppDirs('ptsync')
        self.config_file = os.path.join(dirs.user_data_dir, 'config')
        self.config = config = configparser.SafeConfigParser()
        self.init_options()
        self.load()

    def init_options(self):
        self.config.set('DEFAULT', 'playlistdir', '/home')

    def save(self):
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def load(self):
        if not os.path.exists(self.config_file):
            self.__initialize()
        else:
            self.config.read(self.config_file)
    
    def __initialize(self):
        if not os.path.exists(self.dirs.user_data_dir):
            os.makedirs(self.dirs.user_data_dir)
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w') as configfile:
                self.config.write(self.config_file)
    
    def download_dir(self):
        path = self.config.get('DEFAULT', 'playlistdir')
        if not os.path.exists(path):
            os.makedirs(path)
        return path


appconf = AppConfig()

