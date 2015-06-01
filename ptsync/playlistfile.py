import logging

logger = logging.getLogger(__name__)


class PlaylistFile:

    def __init__(self, items=None):
        self.items = items
        if items is None:
            self.items = []
    
    def add(self, path):
        items.append(path)
    
    def save(self, filename):
        logger.debug(filename)
        with open(filename, 'w') as of:
            for item in self.items:
                of.write(item)
                of.write('\n');
