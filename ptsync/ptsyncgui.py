# -*- coding: utf-8 -*-
import os
import queue
import logging
import argparse
import tkinter as tk
import io
import threading
from PIL import Image, ImageTk

import pygubu
import tasks
from pygubu.stockimage import *
from dialogs import *
from database import DB


APP_DIR = os.path.dirname(os.path.abspath(__file__))
IMGS_DIR = os.path.join(APP_DIR, 'imgs')
logger = logging.getLogger(__name__)


class PtsyncGui(object):
    def __init__(self):
        # UI creation
        #
        self.builder = b = pygubu.Builder()
        b.add_from_file(os.path.join(APP_DIR, 'ptsync.ui'))
        b.add_resource_path(IMGS_DIR)
        self.mainwindow = mainwindow = b.get_object('mainwindow')
        self.pltree = b.get_object('pltree')
        self.taskdialog = b.get_object('taskdialog', mainwindow)
        self.task_progress = b.get_object('task_progress')
        self.task_msg = b.get_object('task_msg')
        #mainwindow.protocol("WM_DELETE_WINDOW", self.__on_window_close)
        self.dlg_preferences = None
        self.dlg_addplaylist = None
        b.connect_callbacks(self)
        
        # theading
        #
        self.queue = queue.Queue()
        self.task_cancel = threading.Event()
        self.mainwindow.after_idle(self.load_database)
        self.process_queue()
    
    def on_mainmenu_cb(self, itemid):
        if itemid == 'mprefs':
            # Show preferences dialog.
            if self.dlg_preferences is None:
                self.dlg_preferences = PreferencesDialog(self)
            self.dlg_preferences.dialog.run()
        if itemid == 'mgenplaylist':
            logger.info('mgenplaylist')
            task = tasks.GeneratePlaylistsTask(self)
            task.start()
    
    def on_addplaylist_cb(self, event=None):
        """Show add playlist dialog."""
        if self.dlg_addplaylist is None:
            self.dlg_addplaylist = AddPlaylistDialog(self)
            self.dlg_addplaylist.dialog.bind('<<AddPlaylistURL>>', self.on_addplaylist_url)
        self.dlg_addplaylist.dialog.run()
        
    def on_addplaylist_url(self, event=None):
        """Starts add playlist task."""
        task = tasks.AddPlaylistTask(self, self.dlg_addplaylist.url)
        task.start()
        
    def on_sync_cb(self, event=None):
        """Starts sync task."""
        task = tasks.SyncTask(self)
        task.start()
        
    def on_item_select(self, event=None):
        """Show thumbnail and video info"""
        tree = self.pltree
        sel = tree.selection()
        if sel:
            item = sel[0]
            if tree.tag_has('video', item):
                img = None
                if StockImage.is_registered(item):
                    img = StockImage.get(item)
                else:
                    video = DB.video_find(item)
                    data = video['thumbdata']
                    if data:
                        img  = Image.open(io.BytesIO(data))
                        img = ImageTk.PhotoImage(img)
                        StockImage.register_created(item, img)
                self.builder.get_object('vthumb').configure(image=img)

    def on_task_dialog_cancel(self, event=None):
        logger.debug('Send cancel signal')
        self.task_cancel.set()

    def load_database(self):
        """Load playlists from database"""
        task = tasks.LoadDatabaseTask(self)
        task.start()
    
    def __on_window_close(self):
        pass
    
    def run(self):
        self.mainwindow.mainloop()

    def process_queue(self):
        self.mainwindow.after(100, self.do_process_queue)

    def do_process_queue(self):
        """Queue processing"""
        try:
            while 1:
                data = self.queue.get_nowait()
                cmd, args, kw = data
                do_save = kw.get('save', True)
                if cmd == 'add_playlist':
                    pl = kw['playlist']
                    if do_save:
                        DB.playlist_save(pl)
                    try:
                        iid = self.pltree.insert('', tk.END, iid=pl['id'],
                                                 text=pl['title'],
                                                 tags='pl')
                        see_func = lambda: self.pltree.see(iid)
                        self.mainwindow.after_idle(see_func)
                    except Exception as e:
                        msg = 'Failed to execute cmd {0}, {1}'.format(cmd, str(args))
                        logger.warning(msg)
                        logger.debug(str(e))
                if cmd == 'add_video':
                    plid = kw['playlist_id']
                    video = kw['video']

                    if do_save:
                        DB.video_save(video)
                        DB.playlist_add_video(plid, video['id'])
                    try:
                        iid = self.pltree.insert(plid, tk.END, iid=video['id'],
                                                 text=video['title'],
                                                 values=('✖', video['id'],),
                                                 tags='video')
                        see_func = lambda: self.pltree.see(iid)
                        self.mainwindow.after_idle(see_func)
                    except Exception as e:
                        msg = 'Failed to execute cmd {0}, {1}'.format(cmd, str(args))
                        logger.warning(msg)
                if cmd == 'downloading_video':
                    msg = 'Downloading video: {0}'.format(kw['name'])
                    self.task_msg.configure(text=msg)
                # ✔
                if cmd == 'task_start':
                    self.task_msg.configure(text=kw['message'])
                    self.task_progress.configure(mode='indeterminate')
                    self.task_progress.start(20)
                    self.taskdialog.run()
                if cmd == 'task_stop':
                    self.task_msg.configure(text=kw['message'])
                    self.task_progress.stop()
                    self.task_progress.configure(mode='determinate')
                    self.taskdialog.close()
                self.mainwindow.update()
        except queue.Empty:
            pass
        self.mainwindow.after(100, self.do_process_queue)
    
    def task_cmd(self, cmd, *args, **kw):
        """Put a command into queue for processing"""
        self.queue.put((cmd, args, kw))
        

def main():
    # Setup logging level
    parser = argparse.ArgumentParser()
    parser.add_argument('--loglevel')
    args = parser.parse_args()

    loglevel = str(args.loglevel).upper()
    loglevel = getattr(logging, loglevel, logging.WARNING)
    logging.basicConfig(level=loglevel)
    
    app = PtsyncGui()
    app.run()


if __name__ == '__main__':
    main()
