import os
import sqlite
from prefs import appconf


class DB(object):
    def __init__(self):
        self.dbname = dbname = 'ptsync.sqlite'
        self.dburl = dburl = os.path.join(appconf.dirs.user_data_dir, dbname)

        init_db = False
        if not os.path.exists(dburl):
            init_db = True
        
        self.con = sqlite.connect(dburl)
        if init_db:
            self.__create()
    
    def __create(self):
        sql = \
"""
CREATE TABLE playlist ( 
    id    INTEGER         PRIMARY KEY AUTOINCREMENT,
    plkey VARCHAR( 128 ),
    name  VARCHAR( 128 ) 
);
CREATE TABLE video ( 
    id          INTEGER         PRIMARY KEY AUTOINCREMENT,
    keyid       VARCHAR( 128 ),
    name        VARCHAR( 128 ),
    playlist_id INTEGER         REFERENCES playlist ( id ) ON DELETE CASCADE 
);
"""
        con = self.con
        con.execute(sql)
        con.commit()

