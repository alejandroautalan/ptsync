import os
import urllib
import urllib.request
import urllib.error
import http.client
import json
import logging
import queue
import threading

#from pytube import YouTube
import youtube_dl

from database import DB
from prefs import appconf


logger = logging.getLogger(__name__)


class SyncTask(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app

    def run(self):
        db = DB.new_connection()
        self.app.task_cmd('task_start', 'Downloading videos ...')
        videos = db.video_list()
        curdir = os.getcwd()
        os.chdir(appconf.download_dir())
        for v in videos:
            video_key = v['id']
#            yt = YouTube()
#            yt.url = 'http://www.youtube.com/watch?v={0}'.format(video_key)
#            yt.filename = '{0}_{1}'.format(video_key, yt.filename)
#            video = yt.filter('mp4')[-1]
#            video.download(appconf.download_dir())
            ydl_opts = {
#                'format': 'bestaudio/best',
                'outtmpl': '%(id)s__%(title)s.%(ext)s'
                }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                url = 'http://www.youtube.com/watch?v={0}'.format(video_key)
                ydl.download([url])
        os.chdir(curdir)
        self.app.task_cmd('task_stop', 'Done.')


class LoadDatabaseTask(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app

    def run(self):
        db = DB.new_connection()
        self.app.task_cmd('task_start', 'Loading data ...')
        pls = db.playlist_list()
        for pl in pls:
            self.app.task_cmd('add_playlist', playlist=pl, save=False)
            videos = db.playlist_video_list(pl['id'])
            for video in videos:
                self.app.task_cmd('add_video', playlist_id=pl['id'],
                                  video=video, save=False)
        self.app.task_cmd('task_stop', 'Done.')


class AddPlaylistTask(threading.Thread):
    def __init__(self, app, plid):
        threading.Thread.__init__(self)
        self.app = app
        self.playlist_id = plid

    def run(self):
        self.app.task_cmd('task_start', 'Getting playlist information ...')
        logger.info('Getting playlist information ... ')
        
        playlist_id = self.playlist_id
        data = self.fetch_info(playlist_id)
        total_videos = int(data['feed']['openSearch$totalResults']['$t'])
        
        thumbnail = None
        for thumb in data['feed']['media$group']['media$thumbnail']:
            if thumb['yt$name'] == 'hqdefault':
                thumbnail = thumb['url']
        pl = {
            'id': playlist_id,
            'title': data['feed']['title']['$t'],
            'subtitle': data['feed']['subtitle']['$t'],
            'updated': data['feed']['updated']['$t'],
            'thumb': thumbnail
            }
        logger.info('Total videos: ' + str(total_videos))
        
        self.app.task_cmd('add_playlist', playlist=pl)
        downloaded = 1
        while downloaded <= total_videos:
            data = self.fetch_info(playlist_id, downloaded, 10)
            entries = data['feed']['entry']
            for entry in entries:
                group = entry['media$group'];
                yt_id = group['yt$videoid']['$t']
                yt_title = group['media$title']['$t']
                
                vthumb = None
                for thumb in group['media$thumbnail']:
                    if thumb['yt$name'] == 'mqdefault':
                        vthumb = thumb['url']

                video = {
                    'id': yt_id,
                    'title': yt_title,
                    'thumb': vthumb,
                    'thumbdata': self.fetch_thumb(vthumb)
                }

                self.app.task_cmd('add_video', playlist_id=playlist_id, video=video)
                
#                msg = '{0}(IDX)){1}'.format(yt_id, yt_title)
#                logger.debug(msg)
#                logger.debug('index {0}'.format(downloaded))
                
                downloaded += 1
        self.app.task_cmd('task_stop', 'Done.')
        
    def fetch_thumb(self, url):
        data = None
        try:
            r = urllib.request.urlopen(url)
            data = r.read()
        except urllib.error.URLError as e:
            pass
        return data
    
    def fetch_info(self, playlistId, start = 1, limit = 0):
        conn = http.client.HTTPConnection('gdata.youtube.com')
        params = {
            'alt' : 'json',
            'max-results' : limit,
            'start-index' : start,
            'v' : 2
        }
        conn.request('GET', '/feeds/api/playlists/' + str(playlistId) + '/?' + urllib.parse.urlencode(params))
        response = conn.getresponse()
        if response.status != 200:
            logger.error('Not a valid/public playlist.')
            logger.info('Response status: {0}'.format(response.status))
        data = response.readall()
        data = json.loads(data.decode('utf-8'))
        return data

