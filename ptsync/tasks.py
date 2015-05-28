import urllib
import http.client
import json
import logging
import queue
import threading

from database import DB


logger = logging.getLogger(__name__)

class LoadDatabaseTask(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app

    def run(self):
        db = DB.new_connection()
        self.app.task_cmd('task_start', 'Loading data ...')
        pls = db.list_playlists()
        for pl in pls:
            self.app.task_cmd('add_playlist', playlist=pl, save=False)
            videos = db.list_playlist_videos(pl['id'])
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
            if thumb['yt$name'] == 'mqdefault':
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
                    'thumb': vthumb
                }

                self.app.task_cmd('add_video', playlist_id=playlist_id, video=video)
                
#                msg = '{0}(IDX)){1}'.format(yt_id, yt_title)
#                logger.debug(msg)
#                logger.debug('index {0}'.format(downloaded))
                
                downloaded += 1
        self.app.task_cmd('task_stop', 'Done.')
    
    def fetch_info(self, playlistId, start = 1, limit = 0):
        connection = http.client.HTTPConnection('gdata.youtube.com')
        params = {
            'alt' : 'json',
            'max-results' : limit,
            'start-index' : start,
            'v' : 2
        }
        connection.request('GET', '/feeds/api/playlists/' + str(playlistId) + '/?' + urllib.parse.urlencode(params))
        response = connection.getresponse()
        if response.status != 200:
            logger.error('Not a valid/public playlist.')
            logger.info('Response status: {0}'.format(response.status))
        data = response.readall()
        data = json.loads(data.decode('utf-8'))
        return data

