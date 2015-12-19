An application meant to sit somewhere running, 
and connect to a running MPD instance, to manage
listening to audiobooks and keeping track of your position
with a persistantly updated playlist.

It watches for the first item in the playlist to be what it 
considers an audiobook (based on the self.is_audiobook(...)
function, which you can override if you want), and then
checks if all items are of the same audiobook.  If so,
it saves a playlist with the name "Author - BookTitle",
and turns consume on, random off, and single off.
With consume on, after every track plays, it is removed
from the playlist.  This client continually watches for
changes to the playlist.  If there is an audiobook playing
and the first item in the list is removed, the client will
save the playlist, overwriting the existing one.  In this 
way, the audiobook's playlist will always contain the
remainder of the audiobook from the current track on.

If the client detects a non-audiobook on the playlist,
or a playlist consisting of multiple different audiobooks,
it does nothing and makes no changes to any playlist.

To restart an audiobook from the beginning, merely add the 
audiobook from the music library in its entirety to a 
playlist (rather than loading the saved playlist).  The
client will immediately detect it and overwrite the old playlist
with the new, full playlist.
