try:
    import ConfigParser as configparser
except:
    import configparser

import os
from appdirs import AppDirs


class AppConfig(object):
    DEF = 'DEFAULT'
    VARS = (
        ('playlist_dir', '/home'),
        ('video_download', 'true'),
        ('video_format', '[height <=? 720]'),
        ('audio_download', 'true'),
        ('audio_format', 'bestaudio'),
    )

    def __init__(self):
        self.dirs = dirs = AppDirs('ptsync')
        self.config_file = os.path.join(dirs.user_data_dir, 'config')
        self.config = config = configparser.SafeConfigParser()
        self.init_options()
        self.load()

    def init_options(self):
        c = self.config
        DEF = self.DEF
        for confvar, value in self.VARS:
            c.set(DEF, confvar, value)

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
                
    def playlists_dir(self):
        return self.download_dir()
    
    def download_dir(self):
        path = self.config.get(self.DEF, 'playlist_dir')
        paths = [
            path, os.path.join(path, 'video'),
            os.path.join(path, 'audio')
            ]
        for p in paths:
            if not os.path.exists(p):
                os.makedirs(p)
        return path
    
    def is_video_download_active(self):
        return self.config.getboolean(self.DEF, 'video_download')
        
    def is_audio_download_active(self):
        return self.config.getboolean(self.DEF, 'audio_download')
        
    def video_format(self):
        return self.config.get(self.DEF, 'video_format')
        
    def audio_format(self):
        return self.config.get(self.DEF, 'audio_format')


appconf = AppConfig()

