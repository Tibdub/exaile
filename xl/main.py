# Here's where it all begins.....
#
# Holds the main Exaile class, whose instantiation starts up the entiriety 
# of Exaile and wich also handles Exaile shutdown.
#
# Also takes care of parsing commandline options.

__version__ = '0.3.0devel'

from xl import common, collection, playlist, player, settings
from xl import xdg, event, devices, hal, plugins, cover

import os

import logging

#import xlgui

from optparse import OptionParser

def get_options():
    """
        Get the options for exaile
    """
    usage = "Usage: %prog [option...|uri]"
    p = OptionParser(usage=usage)
    
    # Playback options
    p.add_option("-n", "--next", dest="next", action="store_true",
        default=False, help="Play the next track")
    p.add_option("-p", "--prev", dest="prev", action="store_true",
        default=False,   help="Play the previous track")
    p.add_option("-s", "--stop", dest="stop", action="store_true",
        default=False, help="Stop playback")
    p.add_option("-a", "--play", dest="play", action="store_true",
        default=False, help="Play")
    p.add_option("-t", "--play-pause", dest="play_pause", action="store_true",
        default=False, help="Toggle Play or Pause")

    # Current song options
    p.add_option("-q", "--query", dest="query", action="store_true",
        default=False, help="Query player")
    p.add_option("--gui-query", dest="guiquery", action="store_true",
        default=False, help="Show a popup of the currently playing track")
    p.add_option("--get-title", dest="get_title", action="store_true",
        default=False, help="Print the title of current track")
    p.add_option("--get-album", dest="get_album", action="store_true",
        default=False, help="Print the album of current track")
    p.add_option("--get-artist", dest="get_artist", action="store_true",
        default=False, help="Print the artist of current track")
    p.add_option("--get-length", dest="get_length", action="store_true",
        default=False, help="Print the length of current track")
    p.add_option('--set-rating', dest='rating', help='Set rating for current '
        'song')
    p.add_option('--get-rating', dest='get_rating', help='Get rating for '
        'current song', default=False, action='store_true')
    p.add_option("--current-position", dest="current_position", action="store_true",
        default=False, help="Print the position inside the current track as a percentage")

    # Volume options
    p.add_option("-i","--increase_vol", dest="inc_vol",action="store", 
        type="int",metavar="VOL",help="Increases the volume by VOL")
    p.add_option("-l","--decrease_vol", dest="dec_vol",action="store",
        type="int",metavar="VOL",help="Decreases the volume by VOL")
    p.add_option("--get-volume", dest="get_volume", action="store_true",
        default=False, help="Print the current volume")

    # Other options
    p.add_option("--new", dest="new", action="store_true",
        default=False, help="Start new instance")
    p.add_option("--version", dest="show_version", action="store_true")
    p.add_option("--start-minimized", dest="minim", action="store_true",
        default=False, help="Start Exaile minimized to tray, if possible")

    p.add_option("--debug", dest="debug", action="store_true",
        default=False, help="Show debugging output")
    p.add_option("--quiet", dest="quiet", action="store_true",
        default=False, help="Reduce level of output")
    return p


class Exaile(object):
    
    def __init__(self):
        """
            Initializes Exaile.
        """
        self.quitting = False

        #parse args
        self.options, self.args = get_options().parse_args()

        #set up logging
        loglevel = logging.INFO
        if self.options.debug:
            loglevel = logging.DEBUG
        elif self.options.quiet:
            loglevel = logging.WARNING
        logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(levelname)-8s: %(message)s (%(name)s)',
                datefmt="%m-%d %H:%M",
                filename=os.path.join(xdg.get_config_dir(), "exaile.log"),
                filemode="a")
        console = logging.StreamHandler()
        console.setLevel(loglevel)
        formatter = logging.Formatter("%(levelname)-8s: %(message)s (%(name)s)")
        console.setFormatter(formatter)
        logging.getLogger("").addHandler(console)

        #setup glib
        self.mainloop()

        #initialize DbusManager
        #self.dbus = xldbus.DbusManager(self.options, self.args)

        #initialize SettingsManager
        self.settings = settings.SettingsManager( os.path.join(
                xdg.get_config_dir(), "settings.ini" ) )

        #show splash screen if enabled
        #xlgui.show_splash(show=True)

        #Set up the player itself.
        self.player = player.get_default_player()()

        #Set up the playback Queue
        self.queue = player.PlayQueue(self.player)

        # Initialize the collection
        self.collection = collection.Collection("Collection",
                location=os.path.join(xdg.get_data_dirs()[0], 'music.db') )

        #initalize PlaylistsManager
        self.playlists = playlist.PlaylistManager()
        self._add_default_playlists() #TODO: run this only first time or 
                                      #      when requested


        #initalize device manager
        self.devices = devices.DeviceManager()

        #initialize HAL
        self.hal = hal.HAL(self.devices)

        # cover manager
        self.covers = cover.CoverManager(cache_dir=os.path.join(
            xdg.get_data_dirs()[0], "covers"))

        #initialize CoverManager
        #self.covers = ???

        #initialize LyricManager
        #self.lyrics = ???

        #initialize PluginManager
        self.plugins = plugins.PluginsManager(self)

        #setup GUI
        #self.gui = xlgui.Main()

    def _add_default_playlists(self):
        """
            Adds some default smart playlists to the playlist manager
        """

        # entire playlist
        entire_lib = playlist.SmartPlaylist("Entire Library",
            collection=self.collection) 
        self.playlists.add_smart_playlist(entire_lib)

        # random playlists
        for count in (100, 300, 500):
            pl = playlist.SmartPlaylist("Random %d" % count,
                collection=self.collection)
            pl.set_return_limit(count)
            pl.set_random_sort(True)
            self.playlists.add_smart_playlist(pl)

        # rating based playlists
        for item in (3, 4):
            pl = playlist.SmartPlaylist("Rating > %d" % item, 
                collection=self.collection)
            pl.add_param('rating', '>', item)
            self.playlists.add_smart_playlist(pl)


    # The mainloop stuff makes gobject play nicely with python threads.
    # Necessary for DBUS signal listening (hal) and gstreamer 
    # messages (player).
    def mainloop(self):
        import gobject, dbus.mainloop.glib
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.gthreads_init()
        loop = gobject.MainLoop()
        gobject.threads_init()
        context = loop.get_context()
        self.__mainloop(context)

    @common.threaded
    def __mainloop(self,context):
        while 1:
            try:
                context.iteration(True)
            except:
                pass

    def quit(self):
        """
            exits Exaile normally.

            takes care of saving prefs, databases, etc.
        """
        if self.quitting: return
        self.quitting = True

        # this event should be used by plugins and modules that dont need
        # to be saved in any particular order. modules that might be 
        # touched by events triggered here should be added statically
        # below.
        event.log_event("quit_application", self, self, async=False)

        self.plugins.save_enabled()

        #self.gui.quit()

        self.playlists.save_all()

        self.collection.save_to_location()
        self.collection.save_libraries()

        #TODO: save player, queue

        self.settings.save()

        exit()


# vim: et sts=4 sw=4

