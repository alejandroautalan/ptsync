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
    
    def playlist_exists(self, pid):
        sql = "SELECT id from playlist WHERE id = ?"
        c = self.conn.cursor()
        c.execute(sql, (pid,))
        return c.fetchone()

    def playlist_save(self, data):
        isql = \
            """INSERT into playlist (id, title, subtitle, thumb)
            values (:id, :title, :subtitle, :thumb)"""
        usql = \
            """UPDATE playlist set title=:title, subtitle=:subtitle,
            thumb=:thumb WHERE id=:id"""
        sql = isql
        if self.playlist_exists(data['id']):
            sql = usql
        c = self.conn.cursor()
        c.execute(sql, data)
        self.conn.commit()
        
    def video_exists(self, vid):
        sql = "SELECT id from video WHERE id = ?"
        c = self.conn.cursor()
        c.execute(sql, (vid,))
        return c.fetchone()
    
    def video_find(self, vid):
        sql = "SELECT * from video WHERE id = ?"
        c = self.conn.cursor()
        c.execute(sql, (vid,))
        return c.fetchone()
        
    def video_save(self, data):
#        field = 'thumbdata'
#        if field in data:
#            data[field] = buffer(data[field])

        isql = \
            """INSERT into video (id, title, thumb, thumbdata)
            values (:id, :title, :thumb, :thumbdata)"""
        usql = \
            """UPDATE playlist
            SET title=:title, thumb=:thumb, thumbdata=:thumbdata WHERE id=:id"""
        sql = isql
        if self.video_exists(data['id']):
            sql = usql
        c = self.conn.cursor()
        c.execute(sql, data)
        self.conn.commit()
        
    def video_list(self):
        sql = "SELECT id, title, thumb FROM video"
        c = self.conn.cursor()
        c.execute(sql)
        return c.fetchall()

    def playlist_list(self):
        sql = "SELECT id, title, subtitle, thumb FROM playlist"
        c = self.conn.cursor()
        c.execute(sql)
        return c.fetchall()
    
    def playlist_video_list(self, plid):
        sql = \
            """
            SELECT v.id, v.title, v.thumb FROM video v
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
                thumb    VARCHAR( 128 ),
                thumbdata BLOB
            );""",
            """CREATE TABLE video ( 
                id    VARCHAR( 128 )  PRIMARY KEY,
                title VARCHAR( 128 ),
                thumb VARCHAR( 128 ),
                thumbdata BLOB 
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
