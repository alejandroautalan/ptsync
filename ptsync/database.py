import os
import logging
import sqlite3 as sqlite
from prefs import appconf

logger = logging.getLogger(__name__)


class Database(object):
    def __init__(self):
        self.dbname = dbname = 'ptsync.sqlite'
        self.dburl = dburl = os.path.join(appconf.dirs.user_data_dir, dbname)

        init_db = False
        if not os.path.exists(dburl):
            init_db = True

        self.conn = sqlite.connect(dburl)
        self.conn.row_factory = sqlite.Row
        if init_db:
            self.__create()
            
    @classmethod
    def new_connection(cls):
        return Database()
    
    def find_playlist(self, pid):
        sql = "SELECT * from playlist WHERE id = ?"
        c = self.conn.cursor()
        c.execute(sql, (pid,))
        return c.fetchone()

    def save_playlist(self, data):
        isql = \
            """INSERT into playlist (id, title, subtitle, thumb)
            values (:id, :title, :subtitle, :thumb)"""
        usql = \
            """UPDATE playlist set title=:title, subtitle=:subtitle,
            thumb=:thumb WHERE id=:id"""
        sql = isql
        if self.find_playlist(data['id']):
            sql = usql
        c = self.conn.cursor()
        c.execute(sql, data)
        self.conn.commit()
        
    def find_video(self, vid):
        sql = "SELECT * from video WHERE id = ?"
        c = self.conn.cursor()
        c.execute(sql, (vid,))
        return c.fetchone()
        
    def save_video(self, data):
        isql = \
            """INSERT into video (id, title, thumb)
            values (:id, :title, :thumb)"""
        usql = \
            """UPDATE playlist set title=:title, thumb=:thumb WHERE id=:id"""
        sql = isql
        if self.find_video(data['id']):
            sql = usql
        c = self.conn.cursor()
        c.execute(sql, data)
        self.conn.commit()

    def list_playlists(self):
        sql = "SELECT * FROM playlist"
        c = self.conn.cursor()
        c.execute(sql)
        return c.fetchall()
    
    def list_playlist_videos(self, plid):
        sql = \
            """
            SELECT v.* FROM video v
               join playlist_video plv ON v.id = plv.video_id
               where plv.playlist_id = ?"""
        c = self.conn.cursor()
        c.execute(sql, (plid,))
        return c.fetchall()
        
    def playlist_has_video(self, plid, vid):
        sql = \
        "SELECT * FROM playlist_video WHERE playlist_id=? and video_id=?"
        c = self.conn.cursor()
        c.execute(sql, (plid, vid))
        return c.fetchone()
        
    def playlist_add_video(self, plid, vid):
        if self.playlist_has_video(plid, vid) is None:
            sql = \
            "INSERT INTO playlist_video (playlist_id, video_id) values (?,?)"
            c = self.conn.cursor()
            c.execute(sql, (plid, vid))
            self.conn.commit()
        
    
    def __create(self):
        sqls = (
            """
            CREATE TABLE playlist ( 
                id       VARCHAR( 128 )  PRIMARY KEY,
                title    VARCHAR( 128 ),
                subtitle VARCHAR( 128 ),
                thumb    VARCHAR( 128 ) 
            );""",
            """CREATE TABLE video ( 
                id    VARCHAR( 128 )  PRIMARY KEY,
                title VARCHAR( 128 ),
                thumb VARCHAR( 128 ) 
            );""",
            """CREATE TABLE playlist_video ( 
                playlist_id VARCHAR( 128 )  REFERENCES playlist ( id ) ON DELETE CASCADE,
                video_id    VARCHAR( 128 )  REFERENCES video ( id ) ON DELETE RESTRICT
                                                                    ON UPDATE CASCADE 
            );""")
        con = self.conn
        for sql in sqls:
            con.execute(sql)
        con.commit()

DB = Database()
