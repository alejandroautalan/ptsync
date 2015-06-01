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
from playlistfile import PlaylistFile


logger = logging.getLogger(__name__)


class SyncTask(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app
        self.videos_dir = os.path.join(appconf.download_dir(), 'video')
        self.audio_dir = os.path.join(appconf.download_dir(), 'audio')

    def run(self):
        db = DB.new_connection()
        self.app.task_cmd('task_start', message='Downloading videos ...')
        videos = db.video_list()
        curdir = os.getcwd()
        for v in videos:
            if self.app.task_cancel.is_set():
                self.app.task_cmd('task_stop', message='Canceled.')
                self.app.task_cancel.clear()
                return

            # Video download
            try:
                if appconf.is_video_download_active():
                    self.download_video(v)
                else:
                    logger.info('Video download inactive.')
            except youtube_dl.utils.DownloadError as e:
                logger.error(str(e))
            # Audio download
            try:
                if appconf.is_audio_download_active():
                    self.download_audio(v)
                else:
                    logger.info('Audio download inactive.')
            except youtube_dl.utils.DownloadError as e:
                logger.error(str(e))
        os.chdir(curdir)
        self.app.task_cmd('task_stop', message='Done.')

    def download_video(self, video):
        video_key = video['id']
        if self.file_exists(video_key, self.videos_dir):
            msg = 'Video file for {0} already exists'.format(video_key)
            logger.info(msg)
            return
        os.chdir(self.videos_dir)
        ydl_opts = {
            'format': appconf.video_format(),
            'outtmpl': '%(id)s__%(title)s.%(ext)s'
            }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            url = 'http://www.youtube.com/watch?v={0}'.format(video_key)
            self.app.task_cmd('downloading_video', name=video['title'])
            ydl.download([url])

    def download_audio(self, video):
        video_key = video['id']
        if self.file_exists(video_key, self.audio_dir):
            msg = 'Audio file for {0} already exists'.format(video_key)
            logger.info(msg)
            return

        os.chdir(self.audio_dir)
        ydl_opts = {
            'format': appconf.audio_format(),
#                    'audioquality': 6,
            'outtmpl': '%(id)s__%(title)s.%(ext)s'
            }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            url = 'http://www.youtube.com/watch?v={0}'.format(video_key)
            self.app.task_cmd('downloading_video', name=video['title'])
            ydl.download([url])

    def file_exists(self, key, path):
        exists = False
        files = os.listdir(path)
        for f in files:
            if f.startswith(key):
                exists = True
        return exists


class LoadDatabaseTask(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app

    def run(self):
        db = DB.new_connection()
        self.app.task_cmd('task_start', message='Loading data ...')
        pls = db.playlist_list()
        for pl in pls:
            self.app.task_cmd('add_playlist', playlist=pl, save=False)
            videos = db.playlist_video_list(pl['id'])
            for video in videos:
                self.app.task_cmd('add_video', playlist_id=pl['id'],
                                  video=video, save=False)
        self.app.task_cmd('task_stop', message='Done.')


class AddPlaylistTask(threading.Thread):
    def __init__(self, app, plid):
        threading.Thread.__init__(self)
        self.app = app
        self.playlist_id = plid

    def run(self):
        self.app.task_cmd('task_start', message='Getting playlist information ...')
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

            if self.app.task_cancel.is_set():
                self.app.task_cmd('task_stop', 'Canceled.')
                self.app.task_cancel.clear()
                return

            data = self.fetch_info(playlist_id, downloaded, 10)
            entries = data['feed']['entry']
            for entry in entries:
                group = entry['media$group'];
                yt_id = group['yt$videoid']['$t']
                yt_title = group['media$title']['$t']

                vthumb = None
                for thumb in group['media$thumbnail']:
                    if thumb['yt$name'] == 'hqdefault':
                        vthumb = thumb['url']

                video = {
                    'id': yt_id,
                    'title': yt_title,
                    'thumb': vthumb,
                    'thumbdata': self.fetch_thumb(vthumb)
                }

                self.app.task_cmd('add_video', playlist_id=playlist_id, video=video)
                downloaded += 1
        self.app.task_cmd('task_stop', message='Done.')

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


class GeneratePlaylistsTask(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app

    def run(self):
        logger.debug('Starting task GeneratePlaylists')
        self.app.task_cmd('task_start', message='Generating playlists ...')
        playlist_dir = appconf.playlists_dir()
        videodirlist = os.listdir(os.path.join(playlist_dir, 'video'))
        audiodirlist = os.listdir(os.path.join(playlist_dir, 'audio'))
        
        db = DB.new_connection()
        pls = db.playlist_list()
        for pl in pls:
            audiolist = []
            videolist = []
            videos = db.playlist_video_list(pl['id'])
            for video in videos:
                filename = self.get_filename(video['id'], videodirlist)
                if filename:
                    videolist.append(os.path.join('video', filename))
                
                filename = self.get_filename(video['id'], audiodirlist)
                if filename:
                    audiolist.append(os.path.join('audio', filename))

            videopl = '{0}_video.m3u'.format(pl['title'])
            audiopl = '{0}_audio.m3u'.format(pl['title'])
            vpath = os.path.join(playlist_dir, videopl)
            apath = os.path.join(playlist_dir, audiopl)
            pl = PlaylistFile(videolist)
            pl.save(vpath)
            
            pl = PlaylistFile(audiolist)
            pl.save(apath)
        
        logger.debug('Done task GeneratePlaylists')
        self.app.task_cmd('task_stop', message='Done.')
        
    def get_filename(self, vid, dirlist):
        found = None
        for f in dirlist:
            if f.startswith(vid):
                found = f
                break
        return found

