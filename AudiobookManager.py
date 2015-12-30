import mpd
import os
import re
import sys

# git clone git@github.com:schamp/PersistentMPDClient
from PersistentMPDClient.PersistentMPDClient import PersistentMPDClient

class AudiobookManager(object):
    """See README.md"""
    
    def __init__(self, 
                 audiobook_file_path, 
                 library_audiobook_path, 
                 socket=None, 
                 host=None, 
                 port=None, 
                 client=None,
                 debug=False):
        """library_audiobook_path is the path (e.g., 'NAS/Audiobooks') from the root of the
        MPD music library in which audiobooks can be found."""
        if client:
            self.client = client
        elif socket:
            self.client = PersistentMPDClient(socket = socket)
        elif host and port:
            self.client = PersistentMPDClient(host = host, port = port)
        else:
            raise Exception("You must specify either socket or host and port.")

        self.audiobook_file_path    = audiobook_file_path
        self.library_audiobook_path = library_audiobook_path

        # turn this on to see what's happening
        self.print_debug = debug

        # get current playlist
        self.current_playlist = self.client.playlist()
        self.playlist_name = None

        # see if we're currently playing an audiobook...
        if len(self.current_playlist) > 0:
            a = self.is_audiobook(self.current_playlist[0])
            if a:
                self.debug("already playing an audiobook.")
                self.playlist_name = self.get_playlist_name(a)
                self.debug("Saving playlist: {}".format(self.playlist_name))
                self.update_playlist(self.playlist_name)

    def list_audiobooks(self):
        # if there are any plain files in the audiobook path, 
        # they will have 'file' not 'directory' attributes
        # filter them out.
        author_dirs = [i['directory'] for i in self.client.lsinfo(self.library_audiobook_path) if 'directory' in i]
        book_dirs   = [i['directory'] for a in author_dirs for i in self.client.lsinfo(a) if 'directory' in i]
        books = list(map(self.parse_audiobook, book_dirs))
        for b in books:
            b['image']    = self.get_album_image(b)
            b['playlist'] = self.get_playlist_name(b)
        return books

    def get_album_image(self, book):
        uri = book['uri']
#        self.debug("Uri: {}".format(uri))
        
        book_path = uri.replace(self.library_audiobook_path, self.audiobook_file_path)
#        self.debug("book_path: {}".format(book_path))

        # os.path.normpath should convert forward slashes to backslashes for windows
        book_path = os.path.normpath(book_path)
#        self.debug("book_path: {}".format(book_path))

        image_file = os.path.join(book_path, 'cover.jpg')
#        self.debug("image_file: {}".format(image_file))

        return image_file if os.path.exists(image_file) else None

    def parse_audiobook(self, item):
        m = re.match('^{root}/([^/]+)/([^/]+)'.format(root = self.library_audiobook_path), item)
        if m:
            self.debug("File belongs to an audiobook: {}.".format(item))
            return {
               'author': m.group(1),
               'title':  m.group(2),
               'uri':    item,
            }
        else:
            self.debug("File does not belong to an audiobook: {}".format(item))
            return None

    def update_playlist(self, playlist_name):
        # restart playing from the first item -- if "random" was on when the user selected
        # "add, replace, and play" the first playing track may not be the first track.
        was_playing = self.client.status()['state'] == "play"
        if was_playing:
            self.client.pause()
        self.debug("saving playlist: {}".format(playlist_name))
        # try to remove it first, because it appears that saving won't overwrite.
        try:    
            self.client.rm(playlist_name)
        # we'll get this if it doesn't exist
        except mpd.CommandError:
            pass
        self.client.save(playlist_name)
        self.client.consume(1)
        self.client.random(0)
        self.client.single(0)
        if was_playing:
            self.client.play()

    def debug(self, s):
        if self.print_debug:
            print(s)

    def is_audiobook(self, playlist_item):
        """given a playlist item, returns an object with
        'author', 'title' attributes if it belongs to an audiobook,
        otherwise, returns None"""

        # remove the 'file' prefix
        if playlist_item.startswith('file: '):
            filename = playlist_item[6:]
            return self.parse_audiobook(filename)

        else:
            self.debug("could not parse out filename: {}".format(playlist_item))
            return None

    @staticmethod
    def get_playlist_name(book):
         return "{author} - {title}".format(
             author = book['author'],
             title  = book['title'],
         )

    def play_audiobook(self, book):
        playlist_name = self.get_playlist_name(book)
        self.client.clear()

        # see if the playlist exists.  If so, load and play it
        try:
            self.client.load(playlist_name)
            self.debug("successfully loaded saved playlist: {}".format(playlist_name))
        except mpd.CommandError:
            # if the playlist does not exist, will throw CommandError
            # so just add the whole audiobook
            self.client.add(book['uri'])
            self.debug("added playlist URI: {}".format(playlist_name))

        self.client.consume(1)
        self.client.random(0)
        self.client.single(0)
        self.client.play()

    def exec(self):
        # look for playlist changes forever
        while True:
            result = self.client.idle('playlist')
            self.debug("Idle done, result: {}".format(result))

            # if the playlist changes
            if result == ['playlist']:
                self.debug("Playlist changed.")

                # get the new playlist
                new_playlist = self.client.playlist()

                # if we were just (prior to this playlist change)
                # in an audiobook:
                if self.playlist_name:
                    # see if we've just finished the last item and 
                    # emptied the playlist:
                    if len(new_playlist) == 0:
                        self.debug("It looks like this audiobook is finished, removing the playlist.")
                        self.client.rm(self.playlist_name)
                        self.playlist_name = None
               
                # now we see if there's any new processing based on
                # the new playlist
                if len(new_playlist) > 0:
                    # see if it's an audiobook
                    a = self.is_audiobook(new_playlist[0])
                    if a:
                        # it is an audiobook, see if we've just finsihed
                        # the audiobook, or merely consumed 
                        # the first item of the playlist, or replaced 
                        # the playlist with a different one
                        if new_playlist == self.current_playlist[1:]:
                            self.debug("It looks like we're part of the same audiobook.")
                            # save the playlist for the current audiobook
                            self.update_playlist(self.playlist_name)
                        else:
                            self.debug("Not part of the same audiobook: {}".format(self.playlist_name))
                            # its a new audiobook (or some other weird combination) 
                            # that's been loaded
                            # if all the playlist items are for the same audiobook
                            same = True
                            for i in new_playlist:
                                if self.is_audiobook(i) != a:
                                    same = False
                                    break
    
                            if same:
                                self.debug("The new playlist is all the same audiobook.")
                                self.playlist_name = self.get_playlist_name(a)
                                self.debug("new playlist: {}".format(self.playlist_name))
                                # save new playlist, for the new audiobook
                                self.update_playlist(self.playlist_name)
    
                            else:
                                self.debug("The new playlist is not the same audiobook.")
                                self.playlist_name = None
    
                        self.current_playlist = new_playlist
                    else:
                        self.debug('Not an audiobook, continuing...')

if __name__ == "__main__":
    if len(sys.argv[1:]) == 1:
        socket = sys.argv[1]
        a = AudiobookManager(socket = socket)
    elif len(sys.argv[1:]) == 2:
        host, port = sys.argv[1:]
    a = AudiobookManager(audiobook_file_path = 'N:\Audiobooks', library_audiobook_path = 'NAS/Audiobooks', host = host, port = port)
    a.exec()
