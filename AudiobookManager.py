import mpd
import re
import sys

# git clone git@github.com:schamp/PersistentMPDClient
from PersistentMPDClient.PersistentMPDClient import PersistentMPDClient

class AudiobookManager(object):
    """See README.md"""
    
    def __init__(self, socket=None, host=None, port=None):
        if socket:
            self.client = PersistentMPDClient(socket = socket)
        elif host and port:
            self.client = PersistentMPDClient(host = host, port = port)
        else:
            raise Exception("You must specify either socket or host and port.")

        # turn this on to see what's happening
        self.print_debug = True

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

    def update_playlist(self, playlist_name):
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

            m = re.match('^NAS/Audiobooks/([^/]+)/([^/]+)/.*', filename)
            if m:
                self.debug("File belongs to an audiobook: {}.".format(filename))
                return {
                   'author': m.group(1),
                   'title':  m.group(2)
                }
            else:
                self.debug("File does not belong to an audiobook: {}".format(filename))
                return None

        else:
            self.debug("could not parse out filename: {}".format(playlist_item))
            return None

    @staticmethod
    def get_playlist_name(a):
         return "{author} - {title}".format(
             author = a['author'],
             title  = a['title'],
         )

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
        a = AudiobookManager(host = host, port = port)
    a.exec()
