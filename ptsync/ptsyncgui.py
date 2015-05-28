# -*- coding: utf-8 -*-
import os
import queue
import logging
import argparse
import tkinter as tk

import pygubu
import tasks
from dialogs import *
from database import DB


APP_DIR = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger(__name__)


class PtsyncGui(object):
    def __init__(self):
        self.queue = queue.Queue()
        self.builder = b = pygubu.Builder()
        b.add_from_file(os.path.join(APP_DIR, 'ptsync.ui'))
        self.mainwindow = mainwindow = b.get_object('mainwindow')
        self.pltree = b.get_object('pltree')
        self.taskdialog = b.get_object('taskdialog', mainwindow)
        self.task_progress = b.get_object('task_progress')
        self.task_msg = b.get_object('task_msg')
#        mainwindow.protocol("WM_DELETE_WINDOW", self.__on_window_close)
        self.dlg_preferences = None
        self.dlg_addplaylist = None
        b.connect_callbacks(self)
        self.mainwindow.after_idle(self.load_database)
        self.process_queue()
    
    def on_preferences_cb(self, event=None):
        if self.dlg_preferences is None:
            self.dlg_preferences = PreferencesDialog(self)
        self.dlg_preferences.dialog.run()
    
    def on_addplaylist_cb(self, event=None):
        if self.dlg_addplaylist is None:
            self.dlg_addplaylist = AddPlaylistDialog(self)
            self.dlg_addplaylist.dialog.bind('<<AddPlaylistURL>>', self.on_addplaylist_url)
        self.dlg_addplaylist.dialog.run()
        
    def on_addplaylist_url(self, event=None):
        task = tasks.AddPlaylistTask(self, self.dlg_addplaylist.url)
        task.start()
    
    def load_database(self):
        task = tasks.LoadDatabaseTask(self)
        task.start()
    
    def __on_window_close(self):
        pass
    
    def run(self):
        self.mainwindow.mainloop()

    def process_queue(self):
        self.mainwindow.after(100, self.do_process_queue)

    def do_process_queue(self):
        try:
            while 1:
                data = self.queue.get_nowait()
                cmd, args, kw = data
                do_save = kw.get('save', True)
                if cmd == 'add_playlist':
                    pl = kw['playlist']
                    if do_save:
                        DB.save_playlist(pl)
                    try:
                        iid = self.pltree.insert('', tk.END, iid=pl['id'],
                                                 text=pl['title'])
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
                        DB.save_video(video)
                        DB.playlist_add_video(plid, video['id'])

                    try:
                        iid = self.pltree.insert(plid, tk.END, iid=video['id'],
                                                 text=video['title'],
                                                 values=(video['id'],))
                        see_func = lambda: self.pltree.see(iid)
                        self.mainwindow.after_idle(see_func)
                    except Exception as e:
                        msg = 'Failed to execute cmd {0}, {1}'.format(cmd, str(args))
                        logger.warning(msg)
                if cmd == 'task_start':
                    self.task_msg.configure(text=str(args))
                    self.task_progress.configure(mode='indeterminate')
                    self.task_progress.start(20)
                    self.taskdialog.run()
                if cmd == 'task_stop':
                    self.task_msg.configure(text=str(args))
                    self.task_progress.stop()
                    self.task_progress.configure(mode='determinate')
                    self.taskdialog.close()
                self.mainwindow.update()
        except queue.Empty:
            pass
        self.mainwindow.after(100, self.do_process_queue)
    
    def task_cmd(self, cmd, *args, **kw):
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
