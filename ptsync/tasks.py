import os
import urllib
import urllib.request
import urllib.error
import http.client
import json
import logging
import queue
import threading
import shlex
import subprocess
import shutil

from .database import DB
from .prefs import appconf
from .playlistfile import PlaylistFile


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
            if appconf.is_video_download_active():
                self.download_video(v)
            else:
                logger.info('Video download inactive.')
            # Audio download
            if appconf.is_audio_download_active():
                self.download_audio(v)
            else:
                logger.info('Audio download inactive.')
        os.chdir(curdir)
        self.app.task_cmd('task_stop', message='Done.')

    def download_video(self, video):
        video_key = video['id']
        if self.file_exists(video_key, self.videos_dir):
            msg = 'Video file for {0} already exists'.format(video_key)
            logger.info(msg)
            return
        os.chdir(self.videos_dir)
        opts = {
            'format': appconf.video_format(),
            'outtmpl': '%(id)s__%(title)s.%(ext)s',
            'url': 'http://www.youtube.com/watch?v={0}'.format(video_key)
        }
        cmd = 'youtube-dl --format "{format}" --output "{outtmpl}" "{url}"'
        cmd = cmd.format(**opts)
        self.app.task_cmd('downloading_video', name=video['title'])
        try:
            cp = subprocess.run(shlex.split(cmd), check=True)
        except subprocess.CalledProcessError as e:
            logger.error(str(e))
            raise e

    def download_audio(self, video):
        video_key = video['id']
        if self.file_exists(video_key, self.audio_dir):
            msg = 'Audio file for {0} already exists'.format(video_key)
            logger.info(msg)
            return

        os.chdir(self.audio_dir)
        opts = {
            'format': appconf.audio_format(),
            'outtmpl': '%(id)s__%(title)s.%(ext)s',
            'url': 'http://www.youtube.com/watch?v={0}'.format(video_key)
        }
        cmd = 'youtube-dl --format "{format}" --output "{outtmpl}" "{url}"'
        cmd = cmd.format(**opts)
        self.app.task_cmd('downloading_video', name=video['title'])
        try:
            cp = subprocess.run(shlex.split(cmd), check=True)
        except subprocess.CalledProcessError as e:
            logger.error(str(e))
            raise e

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
        self.app.task_cmd(
            'task_start', message='Getting playlist information ...')
        logger.info('Getting playlist information ... ')

        cmd = 'youtube-dl -J --flat-playlist "{0}"'.format(self.playlist_id)
        cmd = 'youtube-dl -J "{0}"'.format(self.playlist_id)
        try:
            cp = subprocess.run(shlex.split(
                cmd), stdout=subprocess.PIPE, check=True)
            data = json.loads(cp.stdout.decode())
            self._process_json(data)
        except subprocess.CalledProcessError as e:
            raise e

        self.app.task_cmd('task_stop', message='Done.')

    def _process_json(self, data):
        pl = {
            'id': data['id'],
            'title': data['title'],
            'thumb': None,
            'subtitle': None
        }
        self.app.task_cmd('add_playlist', playlist=pl)
        entries = data['entries']
        for e in entries:
            video = {
                'id': e['id'],
                'title': e['title'],
                'description': e['description'],
                'thumb': e['thumbnail'],
                'thumbdata': self.fetch_thumb(e['thumbnail'])
            }
            self.app.task_cmd('add_video', playlist_id=pl['id'], video=video)

    def fetch_thumb(self, url):
        data = None
        try:
            r = urllib.request.urlopen(url)
            data = r.read()
        except urllib.error.URLError as e:
            pass
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


class PlaylistCopyToTask(threading.Thread):
    def __init__(self, app, playlist_id, path):
        threading.Thread.__init__(self)
        self.app = app
        self.playlist_id = playlist_id
        self.path = path

    def run(self):
        logger.debug('Starting task PlaylistCopyTo')
        self.app.task_cmd(
            'task_start', message='Copying Playlist audio/video files ...')
        playlist_dir = appconf.playlists_dir()
        videodirlist = os.listdir(os.path.join(playlist_dir, 'video'))
        audiodirlist = os.listdir(os.path.join(playlist_dir, 'audio'))

        db = DB.new_connection()
        playlist = db.playlist_find(self.playlist_id)
        audiolist = []
        videolist = []
        videos = db.playlist_video_list(self.playlist_id)
        for video in videos:
            filename = self.get_filename(video['id'], videodirlist)
            if filename:
                copy_from = os.path.join(playlist_dir, 'video', filename)
                copy_to = os.path.join(self.path, filename)
                try:
                    shutil.copyfile(copy_from, copy_to)
                except IOError as e:
                    raise e
                videolist.append(filename)

            filename = self.get_filename(video['id'], audiodirlist)
            if filename:
                copy_from = os.path.join(playlist_dir, 'audio', filename)
                copy_to = os.path.join(self.path, filename)
                try:
                    shutil.copyfile(copy_from, copy_to)
                except IOError as e:
                    raise e
                audiolist.append(filename)

        videopl = '{0}__video.m3u'.format(playlist['title'])
        vpath = os.path.join(self.path, videopl)
        if videolist:
            pl = PlaylistFile(videolist)
            pl.save(vpath)

        audiopl = '{0}__audio.m3u'.format(playlist['title'])
        apath = os.path.join(self.path, audiopl)
        if audiolist:
            pl = PlaylistFile(audiolist)
            pl.save(apath)

        logger.debug('Done task PlaylistCopyTo')
        self.app.task_cmd('task_stop', message='Done.')

    def get_filename(self, vid, dirlist):
        found = None
        for f in dirlist:
            if f.startswith(vid):
                found = f
                break
        return found
