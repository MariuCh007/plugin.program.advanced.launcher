# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.


"""
    Plugin for Launching an applications
"""

# -*- coding: UTF-8 -*
# main imports
import sys
import os
import fnmatch
import xbmc
import xbmcgui
import xbmcplugin

import time, datetime
import math
import re
import urllib
import subprocess_hack
import xml.dom.minidom
import socket
import exceptions
import imghdr

import random
from traceback import print_exc
from operator import itemgetter

import shutil
from file_item import Thumbnails
thumbnails = Thumbnails()

try:
    # Eden & + compatible
    import hashlib
except:
    # Dharma compatible
    import md5

from xbmcaddon import Addon
PLUGIN_DATA_PATH = xbmc.translatePath( os.path.join( "special://profile/addon_data", "plugin.program.advanced.launcher") )
__settings__ = Addon( id="plugin.program.advanced.launcher" )
__lang__ = __settings__.getLocalizedString

def __language__(string):
    return __lang__(string).encode('utf-8','ignore')

# source path for launchers data
BASE_PATH = xbmc.translatePath( os.path.join( "special://" , "profile" ) )
BASE_CURRENT_SOURCE_PATH = os.path.join( PLUGIN_DATA_PATH , "launchers.xml" )
TEMP_CURRENT_SOURCE_PATH = os.path.join( PLUGIN_DATA_PATH , "launchers.tmp" )
SHORTCUT_FILE = os.path.join( PLUGIN_DATA_PATH , "shortcut.cut" )

DEFAULT_THUMB_PATH = os.path.join( PLUGIN_DATA_PATH , "thumbs" )
if not os.path.exists(DEFAULT_THUMB_PATH): os.makedirs(DEFAULT_THUMB_PATH)
DEFAULT_FANART_PATH = os.path.join( PLUGIN_DATA_PATH , "fanarts" )
if not os.path.exists(DEFAULT_FANART_PATH): os.makedirs(DEFAULT_FANART_PATH)
DEFAULT_NFO_PATH = os.path.join( PLUGIN_DATA_PATH , "nfos" )
if not os.path.exists(DEFAULT_NFO_PATH): os.makedirs(DEFAULT_NFO_PATH)
DEFAULT_BACKUP_PATH = os.path.join( PLUGIN_DATA_PATH , "backups" )
if not os.path.exists(DEFAULT_BACKUP_PATH): os.makedirs(DEFAULT_BACKUP_PATH)

REMOVE_COMMAND = "%%REMOVE%%"
FILE_MANAGER_COMMAND = "%%FILEMANAGER%%"
ADD_COMMAND = "%%ADD%%"
EDIT_COMMAND = "%%EDIT%%"
COMMAND_ARGS_SEPARATOR = "^^"
GET_INFO = "%%GET_INFO%%"
GET_THUMB = "%%GET_THUMB%%"
GET_FANART = "%%GET_FANART%%"
SEARCH_COMMAND = "%%SEARCH%%"
SEARCH_DATE_COMMAND = "%%SEARCH_DATE%%"
SEARCH_PLATFORM_COMMAND = "%%SEARCH_PLATFORM%%"
SEARCH_STUDIO_COMMAND = "%%SEARCH_STUDIO%%"
SEARCH_GENRE_COMMAND = "%%SEARCH_GENRE%%"

class Main:
    BASE_CACHE_PATH = xbmc.translatePath(os.path.join( "special://profile/Thumbnails", "Pictures" ))
    launchers = {}

    ''' initializes plugin and run the requiered action
        arguments:
            argv[0] - the path of the plugin (supplied by XBMC)
            argv[1] - the handle of the plugin (supplied by XBMC)
            argv[2] - one of the following (__language__( 30000 ) and 'rom' can be any launcher name or rom name created with the plugin) :
                /launcher - open the specific launcher (if exists) and browse its roms
                            if the launcher is standalone - run it.
                /launcher/rom - run the specifiec rom using it's launcher.
                                ignore command if doesn't exists.
                /launcher/%%REMOVE%% - remove the launcher
                /launcher/%%ADD%% - add a new rom (open wizard)
                /launcher/rom/%%REMOVE%% - remove the rom
                /%%ADD%% - add a new launcher (open wizard)
                /launcher/%%GET_INFO%% - get launcher info from configured scraper
                /launcher/%%GET_THUMB%% - get launcher thumb from configured scraper
                /launcher/%%GET_FANART%% - get launcher fanart from configured scraper
                /launcher/rom/%%GET_INFO%% - get rom info from configured scraper
                /launcher/rom/%%GET_THUMB%% - get rom thumb from configured scraper
                /launcher/rom/%%GET_FANART%% - get rom fanart from configured scraper

                (blank)     - open a list of the available launchers. if no launcher exists - open the launcher creation wizard.
    '''

    def __init__( self, *args, **kwargs ):
        # store an handle pointer
        self._handle = int(sys.argv[ 1 ])

        self._path = sys.argv[ 0 ]

        # get users preference
        self._get_settings()
        self._load_launchers(self.get_xml_source(BASE_CURRENT_SOURCE_PATH))

        # get users scrapers preference
        self._get_scrapers()

        # get emulators preference
        exec "import resources.lib.emulators as _emulators_data"
        self._get_program_arguments = _emulators_data._get_program_arguments
        self._get_program_extensions = _emulators_data._get_program_extensions
        self._get_mame_title = _emulators_data._get_mame_title
        self._test_bios_file = _emulators_data._test_bios_file

        self._print_log(__language__( 30700 ))

        # if a commmand is passed as parameter
        param = sys.argv[ 2 ]

        xbmcplugin.addSortMethod(handle=self._handle, sortMethod=xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(handle=self._handle, sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(handle=self._handle, sortMethod=xbmcplugin.SORT_METHOD_STUDIO)
        xbmcplugin.addSortMethod(handle=self._handle, sortMethod=xbmcplugin.SORT_METHOD_GENRE)
        xbmcplugin.addSortMethod(handle=self._handle, sortMethod=xbmcplugin.SORT_METHOD_UNSORTED)

        if param:
            param = param[1:]
            command = param.split(COMMAND_ARGS_SEPARATOR)
            dirname = os.path.dirname(command[0])
            basename = os.path.basename(command[0])
            # check the action needed
            if (dirname):
                launcher = dirname
                rom = basename
                if (rom == REMOVE_COMMAND):
                    # check if it is a single rom or a launcher
                    if (not os.path.dirname(launcher)):
                        self._remove_launcher(launcher)
                    else:
                        self._remove_rom(os.path.dirname(launcher), os.path.basename(launcher))
                elif (rom == EDIT_COMMAND):
                    # check if it is a single rom or a launcher
                    if (not os.path.dirname(launcher)):
                        self._edit_launcher(launcher)
                    else:
                        self._edit_rom(os.path.dirname(launcher), os.path.basename(launcher))
                elif (rom == GET_INFO):
                    # check if it is a single rom or a launcher
                    if (not os.path.dirname(launcher)):
                        self._scrap_launcher(launcher)
                    else:
                        self._scrap_rom(os.path.dirname(launcher), os.path.basename(launcher))
                elif (rom == GET_THUMB):
                    # check if it is a single rom or a launcher
                    if (not os.path.dirname(launcher)):
                        self._scrap_thumb_launcher(launcher)
                    else:
                        self._scrap_thumb_rom(os.path.dirname(launcher), os.path.basename(launcher))
                elif (rom == GET_FANART):
                    # check if it is a single rom or a launcher
                    if (not os.path.dirname(launcher)):
                        self._scrap_fanart_launcher(launcher)
                    else:
                        self._scrap_fanart_rom(os.path.dirname(launcher), os.path.basename(launcher))
                elif (rom == ADD_COMMAND):
                    self._add_roms(launcher)
                elif (rom == SEARCH_COMMAND):
                    self._find_add_roms(launcher)
                elif (rom == SEARCH_DATE_COMMAND):
                    self._find_date_add_roms(launcher)
                elif (rom == SEARCH_PLATFORM_COMMAND):
                    self._find_platform_add_roms(launcher)
                elif (rom == SEARCH_STUDIO_COMMAND):
                    self._find_studio_add_roms(launcher)
                elif (rom == SEARCH_GENRE_COMMAND):
                    self._find_genre_add_roms(launcher)
                else:
                    self._run_rom(launcher, rom)
            else:
                launcher = basename

                if (launcher == "backup"):
                    self._print_log(__language__( 30185 ))
                    backup_file = xbmcgui.Dialog().browse(1,__language__( 30186 ),"files",".xml", False, False, os.path.join(DEFAULT_BACKUP_PATH+"/"))
                    if (os.path.isfile(backup_file)):
                        self._load_launchers(self.get_xml_source(backup_file))

                elif (launcher == SEARCH_COMMAND):#search
                    # check if we need to get user input or search the rom list
                    self._find_roms()

                elif (launcher == FILE_MANAGER_COMMAND):#filemanager
                    self._file_manager()

                # if it's an add command
                elif (launcher == ADD_COMMAND):
                    self._add_new_launcher()
                else:
                    # if there is no rompath (a standalone launcher)
                    if (self.launchers[launcher]["rompath"] == ""):
                        # launch it
                        self._run_launcher(launcher)
                    else:
                        self._get_roms(launcher)
        else:

            # otherwise get the list of the programs in the current folder
            if (not self._get_launchers()):
                # if no launcher found - attempt to add a new one
                if (self._add_new_launcher()):
                    self._get_launchers()
                else:
                    xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=False , cacheToDisc=False)

    def _remove_rom(self, launcherID, rom):
        dialog = xbmcgui.Dialog()
        ret = dialog.yesno(__language__( 30000 ), __language__( 30010 ) % self.launchers[launcherID]["roms"][rom]["name"])
        if (ret):
            self.launchers[launcherID]["roms"].pop(rom)
            self._save_launchers()
            if ( len(self.launchers[launcherID]["roms"]) == 0 ):
                xbmc.executebuiltin("ReplaceWindow(Programs,%s)" % (self._path))
            else:
                xbmc.executebuiltin("Container.Update")

    def _empty_launcher(self, launcherID):
        dialog = xbmcgui.Dialog()
        ret = dialog.yesno(__language__( 30000 ), __language__( 30133 ) % self.launchers[launcherID]["name"])
        if (ret):
            self.launchers[launcherID]["roms"].clear()
            self._save_launchers()
            xbmc.executebuiltin("Container.Update")
            
    def _remove_launcher(self, launcherID):
        dialog = xbmcgui.Dialog()
        ret = dialog.yesno(__language__( 30000 ), __language__( 30010 ) % self.launchers[launcherID]["name"])
        if (ret):
            self.launchers.pop(launcherID)
            self._save_launchers()
            if ( len(self.launchers) == 0 ):
                xbmc.executebuiltin("ReplaceWindow(Home)")
            else:
                xbmc.executebuiltin("Container.Update")

    def _edit_rom(self, launcher, rom):
        dialog = xbmcgui.Dialog()
        title=os.path.basename(self.launchers[launcher]["roms"][rom]["filename"])
        if (self.launchers[launcher]["roms"][rom]["finished"] == "false"):
            finished_display = __language__( 30339 )
        else:
            finished_display = __language__( 30340 )
        type = dialog.select(__language__( 30300 ) % title, [__language__( 30338 ),__language__( 30301 ),__language__( 30302 ),__language__( 30303 ),finished_display,__language__( 30323 ),__language__( 30304 )])

        if (type == 0 ):
            # Scrap item (infos and images)
            self._full_scrap_rom(launcher,rom)

        if (type == 1 ):
            dialog = xbmcgui.Dialog()

            type2 = dialog.select(__language__( 30305 ), [__language__( 30311 ) % self.settings[ "datas_scraper" ],__language__( 30333 ),__language__( 30306 ) % self.launchers[launcher]["roms"][rom]["name"],__language__( 30308 ) % self.launchers[launcher]["roms"][rom]["release"],__language__( 30309 ) % self.launchers[launcher]["roms"][rom]["studio"],__language__( 30310 ) % self.launchers[launcher]["roms"][rom]["genre"],__language__( 30328 ) % self.launchers[launcher]["roms"][rom]["plot"][0:20],__language__( 30316 )])
                # Scrap rom Infos
            if (type2 == 0 ):
                self._scrap_rom(launcher,rom)
            if (type2 == 1 ):
                self._import_rom_nfo(launcher,rom)
            if (type2 == 2 ):
                # Edition of the rom title
                keyboard = xbmc.Keyboard(self.launchers[launcher]["roms"][rom]["name"], __language__( 30037 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    title = keyboard.getText()
                    if ( title == "" ):
                        title = self.launchers[launcher]["roms"][rom]["name"]
                    self.launchers[launcher]["roms"][rom]["name"] = title.rstrip()
                    self._save_launchers()
            if (type2 == 3 ):
                # Edition of the rom release date
                keyboard = xbmc.Keyboard(self.launchers[launcher]["roms"][rom]["release"], __language__( 30038 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    self.launchers[launcher]["roms"][rom]["release"] = keyboard.getText()
                    self._save_launchers()
            if (type2 == 4 ):
                # Edition of the rom studio name
                keyboard = xbmc.Keyboard(self.launchers[launcher]["roms"][rom]["studio"], __language__( 30039 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    self.launchers[launcher]["roms"][rom]["studio"] = keyboard.getText()
                    self._save_launchers()
            if (type2 == 5 ):
                # Edition of the rom game genre
                keyboard = xbmc.Keyboard(self.launchers[launcher]["roms"][rom]["genre"], __language__( 30040 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    self.launchers[launcher]["roms"][rom]["genre"] = keyboard.getText()
                    self._save_launchers()
            if (type2 == 6 ):
                # Import of the rom game plot
                text_file = xbmcgui.Dialog().browse(1,__language__( 30080 ),"files",".txt|.dat", False, False)
                if (os.path.isfile(text_file)):
                    text_plot = open(text_file)
                    string_plot = text_plot.read()
                    text_plot.close()
                    self.launchers[launcher]["roms"][rom]["plot"] = string_plot.replace('&quot;','"')
                    self._save_launchers()
            if (type2 == 7 ):
                self._export_rom_nfo(launcher,rom)

        if (type == 2 ):
            dialog = xbmcgui.Dialog()
            thumb_diag = __language__( 30312 ) % ( self.settings[ "thumbs_scraper" ] )
            if ( self.settings[ "thumbs_scraper" ] == "GameFAQs" ) | ( self.settings[ "thumbs_scraper" ] == "MobyGames" ):
                thumb_diag = __language__( 30321 ) % ( self.settings[ "thumbs_scraper" ],self.settings[ "display_game_region" ])
            if ( self.settings[ "thumbs_scraper" ] == "Google" ):
                thumb_diag = __language__( 30322 ) % ( self.settings[ "thumbs_scraper" ],self.settings[ "thumb_image_size_display" ].capitalize())
            type2 = dialog.select(__language__( 30302 ), [thumb_diag,__language__( 30332 ),__language__( 30313 )])
            if (type2 == 0 ):
                self._scrap_thumb_rom(launcher,rom)
            if (type2 == 1 ):
                # Import a rom thumbnail image
                image = xbmcgui.Dialog().browse(2,__language__( 30041 ),"files",".jpg|.jpeg|.gif|.png", True, False, os.path.join(self.launchers[launcher]["thumbpath"]))
                if (image):
                    if (os.path.isfile(image)):
                        img_ext = os.path.splitext(image)[-1][0:4]
                        if ( img_ext != '' ):
                            filename = self.launchers[launcher]["roms"][rom]["filename"]
                            if (self.launchers[launcher]["thumbpath"] == self.launchers[launcher]["fanartpath"] ):
                                if (self.launchers[launcher]["thumbpath"] == self.launchers[launcher]["rompath"] ):
                                    file_path = filename.replace("."+filename.split(".")[-1], '_thumb'+img_ext)
                                else:
                                    file_path = os.path.join(os.path.dirname(self.launchers[launcher]["thumbpath"]),os.path.basename(filename.replace("."+filename.split(".")[-1], '_thumb'+img_ext)))
                            else:
                                if (self.launchers[launcher]["thumbpath"] == self.launchers[launcher]["rompath"] ):
                                    file_path = filename.replace("."+filename.split(".")[-1], img_ext)
                                else:
                                    file_path = os.path.join(os.path.dirname(self.launchers[launcher]["thumbpath"]),os.path.basename(filename.replace("."+filename.split(".")[-1], img_ext)))
                            if ( image != file_path ):
                                try:
                                    shutil.copy2( image.decode(sys.getfilesystemencoding(),'ignore') , file_path.decode(sys.getfilesystemencoding(),'ignore') )
                                    self.launchers[launcher]["roms"][rom]["thumb"] = file_path
                                    self._save_launchers()
                                    _update_cache(file_path)
                                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30070 )))
                                except OSError:
                                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30063 ) % self.launchers[launcher]["roms"][rom]["name"]))

            if (type2 == 2 ):
                # Link to a rom thumbnail image
                if (self.launchers[launcher]["roms"][rom]["thumb"] == ""):
                    imagepath = self.launchers[launcher]["roms"][rom]["filename"]
                else:
                    imagepath = self.launchers[launcher]["roms"][rom]["thumb"]
                image = xbmcgui.Dialog().browse(2,__language__( 30041 ),"files",".jpg|.jpeg|.gif|.png", True, False, os.path.join(imagepath))
                if (image):
                    if (os.path.isfile(image)):
                        self.launchers[launcher]["roms"][rom]["thumb"] = image
                        self._save_launchers()
                        _update_cache(image)
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30070 )))

        if (type == 3 ):
            dialog = xbmcgui.Dialog()
            fanart_diag = __language__( 30312 ) % ( self.settings[ "fanarts_scraper" ] )
            if ( self.settings[ "fanarts_scraper" ] == "Google" ):
                fanart_diag = __language__( 30322 ) % ( self.settings[ "fanarts_scraper" ],self.settings[ "fanart_image_size_display" ].capitalize())
            type2 = dialog.select(__language__( 30303 ), [fanart_diag,__language__( 30332 ),__language__( 30313 )])
            if (type2 == 0 ):
                self._scrap_fanart_rom(launcher,rom)
            if (type2 == 1 ):
                # Import a rom fanart image
                image = xbmcgui.Dialog().browse(2,__language__( 30041 ),"files",".jpg|.jpeg|.gif|.png", True, False, os.path.join(self.launchers[launcher]["fanartpath"]))
                if (image):
                    if (os.path.isfile(image)):
                        img_ext = os.path.splitext(image)[-1][0:4]
                        if ( img_ext != '' ):
                            filename = self.launchers[launcher]["roms"][rom]["filename"]
                            if (self.launchers[launcher]["thumbpath"] == self.launchers[launcher]["fanartpath"] ):
                                if (self.launchers[launcher]["fanartpath"] == self.launchers[launcher]["rompath"] ):
                                    file_path = filename.replace("."+filename.split(".")[-1], '_fanart'+img_ext)
                                else:
                                    file_path = os.path.join(os.path.dirname(self.launchers[launcher]["fanartpath"]),os.path.basename(filename.replace("."+filename.split(".")[-1], '_fanart'+img_ext)))
                            else:
                                if (self.launchers[launcher]["fanartpath"] == self.launchers[launcher]["rompath"] ):
                                    file_path = filename.replace("."+filename.split(".")[-1], img_ext)
                                else:
                                    file_path = os.path.join(os.path.dirname(self.launchers[launcher]["fanartpath"]),os.path.basename(filename.replace("."+filename.split(".")[-1], img_ext)))
                            if ( image != file_path ):
                                try:
                                    shutil.copy2( image.decode(sys.getfilesystemencoding(),'ignore') , file_path.decode(sys.getfilesystemencoding(),'ignore') )
                                    self.launchers[launcher]["roms"][rom]["fanart"] = file_path
                                    self._save_launchers()
                                    _update_cache(file_path)
                                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30075 )))
                                except OSError:
                                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30064 ) % self.launchers[launcher]["roms"][rom]["name"]))
            if (type2 == 2 ):
                # Link to a rom fanart image
                if (self.launchers[launcher]["roms"][rom]["fanart"] == ""):
                    imagepath = self.launchers[launcher]["roms"][rom]["filename"]
                else:
                    imagepath = self.launchers[launcher]["roms"][rom]["fanart"]
                image = xbmcgui.Dialog().browse(2,__language__( 30042 ),"files",".jpg|.jpeg|.gif|.png", True, False, os.path.join(imagepath))
                if (image):
                    if (os.path.isfile(image)):
                        self.launchers[launcher]["roms"][rom]["fanart"] = image
                        self._save_launchers()
                        _update_cache(image)
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30075 )))

        if (type == 4 ):
            if (self.launchers[launcher]["roms"][rom]["finished"] == "false"):
                self.launchers[launcher]["roms"][rom]["finished"] = "true"
            else:
                self.launchers[launcher]["roms"][rom]["finished"] = "false"
            self._save_launchers()

        if (type == 5 ):
            dialog = xbmcgui.Dialog()
            type2 = dialog.select(__language__( 30323 ), [__language__( 30337 ) % self.launchers[launcher]["roms"][rom]["filename"], __language__( 30341 ) % self.launchers[launcher]["roms"][rom]["trailer"], __language__( 30331 ) % self.launchers[launcher]["roms"][rom]["custom"]])
            if (type2 == 0 ):
                # Selection of the item file
                item_file = xbmcgui.Dialog().browse(1,__language__( 30017 ),"files","."+self.launchers[launcher]["romext"].replace("|","|."), False, False, self.launchers[launcher]["roms"][rom]["filename"])
                self.launchers[launcher]["roms"][rom]["filename"] = item_file
                self._save_launchers()
            if (type2 == 1 ):
                # Selection of the rom trailer file
                trailer = xbmcgui.Dialog().browse(1,__language__( 30090 ),"files",".mp4|.mpg|.avi|.wmv|.mkv|.flv", False, False, self.launchers[launcher]["roms"][rom]["trailer"])
                self.launchers[launcher]["roms"][rom]["trailer"] = trailer
                self._save_launchers()
            if (type2 == 2 ):
                # Selection of the rom customs path
                custom = xbmcgui.Dialog().browse(0,__language__( 30057 ),"files","", False, False, self.launchers[launcher]["roms"][rom]["custom"])
                self.launchers[launcher]["roms"][rom]["custom"] = custom
                self._save_launchers()

        if (type == 6 ):
            self._remove_rom(launcher,rom)

        # Return to the launcher directory
        xbmc.executebuiltin("Container.Refresh")

    def _scrap_thumb_rom_algo(self, launcher, rom, title):
        xbmc.executebuiltin("XBMC.Notification(%s,%s, 300000)" % (__language__( 30000 ), __language__( 30065 ) % (self.launchers[launcher]["roms"][rom]["name"],(self.settings[ "thumbs_scraper" ]).encode('utf-8','ignore'))))
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        covers = self._get_thumbnails_list(self.launchers[launcher]["roms"][rom]["gamesys"],title,self.settings["game_region"],self.settings[ "thumb_image_size" ])
        if covers:
            nb_images = len(covers)
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30066 ) % (nb_images,self.launchers[launcher]["roms"][rom]["name"])))
            covers.insert(0,(self.launchers[launcher]["roms"][rom]["thumb"],self.launchers[launcher]["roms"][rom]["thumb"],__language__( 30068 )))
            self.image_url = MyDialog(covers)
            if ( self.image_url ):
                if (not self.image_url == self.launchers[launcher]["roms"][rom]["thumb"]):
                    img_url = self._get_thumbnail(self.image_url)
                    if ( img_url != '' ):
                        img_ext = os.path.splitext(img_url)[-1][0:4]
                        if ( img_ext != '' ):
                            filename = self.launchers[launcher]["roms"][rom]["filename"]
                            if (self.launchers[launcher]["thumbpath"] == self.launchers[launcher]["fanartpath"] ):
                                if (self.launchers[launcher]["thumbpath"] == self.launchers[launcher]["rompath"] ):
                                    file_path = filename.replace("."+filename.split(".")[-1], '_thumb'+img_ext)
                                else:
                                    file_path = os.path.join(os.path.dirname(self.launchers[launcher]["thumbpath"]),os.path.basename(filename.replace("."+filename.split(".")[-1], '_thumb'+img_ext)))
                            else:
                                if (self.launchers[launcher]["thumbpath"] == self.launchers[launcher]["rompath"] ):
                                    file_path = filename.replace("."+filename.split(".")[-1], img_ext)
                                else:
                                    file_path = os.path.join(os.path.dirname(self.launchers[launcher]["thumbpath"]),os.path.basename(filename.replace("."+filename.split(".")[-1], img_ext)))
                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 300000)" % (__language__( 30000 ), __language__( 30069 )))
                            try:
                                urllib.URLopener.version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'
                                h = urllib.urlretrieve(img_url,file_path)
                                filetype = imghdr.what(file_path)
                                if str(filetype) == 'None':
                                    raise NameError('Bad File')
                                self.launchers[launcher]["roms"][rom]["thumb"] = file_path
                                self._save_launchers()
                                _update_cache(file_path)
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30070 )))
                            except socket.timeout:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30080 )))
                            except exceptions.IOError:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30063 ) % self.launchers[launcher]["roms"][rom]["name"]))
                            except exceptions.NameError:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30081 )))
                    else:
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30067 ) % (self.launchers[launcher]["roms"][rom]["name"])))
        else:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30067 ) % (self.launchers[launcher]["roms"][rom]["name"])))

    def _scrap_thumb_rom(self, launcher, rom):
        if ( self.launchers[launcher]["application"].lower().find('mame') > 0 ) or ( self.settings[ "thumbs_scraper" ] == 'arcadeHITS' ):
            title=os.path.basename(self.launchers[launcher]["roms"][rom]["filename"]).split(".")[0]
            keyboard = xbmc.Keyboard(title, __language__( 30079 ))
        else:
            keyboard = xbmc.Keyboard(self.launchers[launcher]["roms"][rom]["name"], __language__( 30036 ))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            self._scrap_thumb_rom_algo(launcher, rom, keyboard.getText())
        xbmc.executebuiltin("Container.Update")

    def _scrap_thumb_launcher_algo(self, launcherID, title):
        xbmc.executebuiltin("XBMC.Notification(%s,%s, 300000)" % (__language__( 30000 ), __language__( 30065 ) % (self.launchers[launcherID]["name"],(self.settings[ "thumbs_scraper" ]).encode('utf-8','ignore'))))
        covers = self._get_thumbnails_list(self.launchers[launcherID]["gamesys"],title,self.settings["game_region"],self.settings[ "thumb_image_size" ])
        if covers:
            nb_images = len(covers)
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30066 ) % (nb_images,self.launchers[launcherID]["name"])))
            covers.insert(0,(self.launchers[launcherID]["thumb"],self.launchers[launcherID]["thumb"],__language__( 30068 )))
            self.image_url = MyDialog(covers)
            if ( self.image_url ):
                if (not self.image_url == self.launchers[launcherID]["thumb"]):
                    img_url = self._get_thumbnail(self.image_url)
                    if ( img_url != '' ):
                        img_ext = os.path.splitext(img_url)[-1][0:4]
                        if ( img_ext != '' ):
                            filename = self.launchers[launcherID]["application"]
                            if ( os.path.join(self.launchers[launcherID]["thumbpath"]) != "" ):
                                file_path = os.path.join(self.launchers[launcherID]["thumbpath"],os.path.basename(self.launchers[launcherID]["application"])+'_thumb'+img_ext)
                            else:
                                if (self.settings[ "launcher_thumb_path" ] == "" ):
                                    self.settings[ "launcher_thumb_path" ] = DEFAULT_THUMB_PATH
                                file_path = os.path.join(self.settings[ "launcher_thumb_path" ],os.path.basename(self.launchers[launcherID]["application"])+'_thumb'+img_ext)
                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 300000" % (__language__( 30000 ), __language__( 30069 )))
                            try:
                                urllib.URLopener.version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'
                                h = urllib.urlretrieve(img_url,file_path)
                                filetype = imghdr.what(file_path)
                                if str(filetype) == 'None':
                                    raise NameError('Bad File')
                                self.launchers[launcherID]["thumb"] = file_path
                                self._save_launchers()
                                _update_cache(file_path)
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30070 )))
                            except socket.timeout:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30080 )))
                            except exceptions.IOError:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30063 ) % self.launchers[launcherID]["name"]))
                            except exceptions.NameError:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30081 )))
                    else:
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30067 ) % (self.launchers[launcherID]["name"])))
        else:
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30067 ) % (self.launchers[launcherID]["name"])))

    def _scrap_thumb_launcher(self, launcherID):
        keyboard = xbmc.Keyboard(self.launchers[launcherID]["name"], __language__( 30036 ))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            self._scrap_thumb_launcher_algo(launcherID, keyboard.getText())
        xbmc.executebuiltin("Container.Update")

    def _scrap_fanart_rom_algo(self, launcher, rom, title):
        xbmc.executebuiltin("XBMC.Notification(%s,%s, 300000)" % (__language__( 30000 ), __language__( 30071 ) % (self.launchers[launcher]["roms"][rom]["name"],(self.settings[ "fanarts_scraper" ]).encode('utf-8','ignore'))))
        full_fanarts = self._get_fanarts_list(self.launchers[launcher]["roms"][rom]["gamesys"],title,self.settings[ "fanart_image_size" ])
        if full_fanarts:
            nb_images = len(full_fanarts)
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30072 ) % (nb_images,self.launchers[launcher]["roms"][rom]["name"])))
            full_fanarts.insert(0,(self.launchers[launcher]["roms"][rom]["fanart"],self.launchers[launcher]["roms"][rom]["fanart"],__language__( 30068 )))
            self.image_url = MyDialog(full_fanarts)
            if ( self.image_url ):
                if (not self.image_url == self.launchers[launcher]["roms"][rom]["fanart"]):
                    img_url = self._get_fanart(self.image_url)
                    if ( img_url != '' ):
                        img_ext = os.path.splitext(img_url)[-1][0:4]
                        if ( img_ext != '' ):
                            filename = self.launchers[launcher]["roms"][rom]["filename"]
                            if (self.launchers[launcher]["fanartpath"] == self.launchers[launcher]["thumbpath"] ):
                                if (self.launchers[launcher]["fanartpath"] == self.launchers[launcher]["rompath"] ):
                                    file_path = filename.replace("."+filename.split(".")[-1], '_fanart'+img_ext)
                                else:
                                    file_path = os.path.join(os.path.dirname(self.launchers[launcher]["fanartpath"]),os.path.basename(filename.replace("."+filename.split(".")[-1], '_fanart'+img_ext)))
                            else:
                                if (self.launchers[launcher]["fanartpath"] == self.launchers[launcher]["rompath"] ):
                                    file_path = filename.replace("."+filename.split(".")[-1], img_ext)
                                else:
                                    file_path = os.path.join(os.path.dirname(self.launchers[launcher]["fanartpath"]),os.path.basename(filename.replace("."+filename.split(".")[-1], img_ext)))
                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 300000)" % (__language__( 30000 ), __language__( 30074 )))
                            try:
                                urllib.URLopener.version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'
                                h = urllib.urlretrieve(img_url,file_path)
                                filetype = imghdr.what(file_path)
                                if str(filetype) == 'None':
                                    raise NameError('Bad File')
                                self.launchers[launcher]["roms"][rom]["fanart"] = file_path
                                self._save_launchers()
                                _update_cache(file_path)
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30075 )))
                            except socket.timeout:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30080 )))
                            except exceptions.IOError:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30064 ) % self.launchers[launcher]["roms"][rom]["name"]))
                            except exceptions.NameError:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30081 )))
                    else:
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30073 ) % (self.launchers[launcher]["roms"][rom]["name"])))
        else:
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30073 ) % (self.launchers[launcher]["roms"][rom]["name"])))

    def _scrap_fanart_rom(self, launcher, rom):
        if ( self.launchers[launcher]["application"].lower().find('mame') > 0 ) or ( self.settings[ "fanarts_scraper" ] == 'arcadeHITS' ):
            title=os.path.basename(self.launchers[launcher]["roms"][rom]["filename"]).split(".")[0]
            keyboard = xbmc.Keyboard(title, __language__( 30079 ))
        else:
            keyboard = xbmc.Keyboard(self.launchers[launcher]["roms"][rom]["name"], __language__( 30036 ))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            self._scrap_fanart_rom_algo(launcher, rom, keyboard.getText())
        xbmc.executebuiltin("Container.Update")

    def _scrap_fanart_launcher_algo(self, launcherID, title):
        xbmc.executebuiltin("XBMC.Notification(%s,%s, 300000)" % (__language__( 30000 ), __language__( 30071 ) % (self.launchers[launcherID]["name"],(self.settings[ "fanarts_scraper" ]).encode('utf-8','ignore'))))
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        covers = self._get_fanarts_list(self.launchers[launcherID]["gamesys"],title,self.settings[ "fanart_image_size" ])
        if covers:
            nb_images = len(covers)
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30072 ) % (nb_images,self.launchers[launcherID]["name"])))
            covers.insert(0,(self.launchers[launcherID]["fanart"],self.launchers[launcherID]["fanart"],__language__( 30068 )))
            self.image_url = MyDialog(covers)
            if ( self.image_url ):
                if (not self.image_url == self.launchers[launcherID]["fanart"]):
                    img_url = self._get_fanart(self.image_url)
                    if ( img_url != '' ):
                        img_ext = os.path.splitext(img_url)[-1][0:4]
                        if ( img_ext != '' ):
                            filename = self.launchers[launcherID]["application"]
                            if ( os.path.join(self.launchers[launcherID]["fanartpath"]) != "" ):
                                file_path = os.path.join(self.launchers[launcherID]["fanartpath"],os.path.basename(self.launchers[launcherID]["application"])+'_fanart'+img_ext)
                            else:
                                if (self.settings[ "launcher_fanart_path" ] == "" ):
                                    self.settings[ "launcher_fanart_path" ] = DEFAULT_FANART_PATH
                                file_path = os.path.join(self.settings[ "launcher_fanart_path" ],os.path.basename(self.launchers[launcherID]["application"])+'_fanart'+img_ext)
                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 300000)" % (__language__( 30000 ), __language__( 30074 )))
                            try:
                                urllib.URLopener.version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'
                                h = urllib.urlretrieve(img_url,file_path)
                                filetype = imghdr.what(file_path)
                                if str(filetype) == 'None':
                                    raise NameError('Bad File')
                                self.launchers[launcherID]["fanart"] = file_path
                                self._save_launchers()
                                _update_cache(file_path)
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30075 )))
                            except socket.timeout:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30080 )))
                            except exceptions.IOError:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30064 ) % self.launchers[launcherID]["name"]))
                            except exceptions.NameError:
                                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30081 )))
                    else:
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30073 ) % (self.launchers[launcherID]["name"])))
        else:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30073 ) % (self.launchers[launcherID]["name"])))

    def _scrap_fanart_launcher(self, launcherID):
        keyboard = xbmc.Keyboard(self.launchers[launcherID]["name"], __language__( 30036 ))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            self._scrap_fanart_launcher_algo(launcherID, keyboard.getText())
        xbmc.executebuiltin("Container.Update")

    def _scrap_rom_algo(self, launcher, rom, title):
        # Search game title
            results,display = self._get_games_list(title)
            if display:
                # Display corresponding game list found
                dialog = xbmcgui.Dialog()
                # Game selection
                selectgame = dialog.select(__language__( 30078 ) % ( self.settings[ "datas_scraper" ] ), display)
                if (not selectgame == -1):
                    if ( self.settings[ "ignore_title" ] ):
                        self.launchers[launcher]["roms"][rom]["name"] = title_format(self,title)
                    else:
                        self.launchers[launcher]["roms"][rom]["name"] = title_format(self,results[selectgame]["title"])
                    gamedata = self._get_game_data(results[selectgame])
                    self.launchers[launcher]["roms"][rom]["genre"] = gamedata["genre"]
                    self.launchers[launcher]["roms"][rom]["release"] = gamedata["release"]
                    self.launchers[launcher]["roms"][rom]["studio"] = gamedata["studio"]
                    self.launchers[launcher]["roms"][rom]["plot"] = gamedata["plot"]
            else:
                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30076 )))
    
    def _scrap_rom(self, launcher, rom):
        # Edition of the rom name
        title=os.path.basename(self.launchers[launcher]["roms"][rom]["filename"]).split(".")[0]
        if ( self.launchers[launcher]["application"].lower().find('mame') > 0 ) or ( self.settings[ "datas_scraper" ] == 'arcadeHITS' ):
            keyboard = xbmc.Keyboard(title, __language__( 30079 ))
        else:
            keyboard = xbmc.Keyboard(self.launchers[launcher]["roms"][rom]["name"], __language__( 30036 ))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            self._scrap_rom_algo(launcher, rom, keyboard.getText())
            self._save_launchers()
        xbmc.executebuiltin("Container.Update")

    def _full_scrap_rom(self, launcher, rom):
        # Edition of the rom name
        title=os.path.basename(self.launchers[launcher]["roms"][rom]["filename"]).split(".")[0]
        if ( self.launchers[launcher]["application"].lower().find('mame') > 0 ) or ( self.settings[ "datas_scraper" ] == 'arcadeHITS' ):
            keyboard = xbmc.Keyboard(title, __language__( 30079 ))
        else:
            keyboard = xbmc.Keyboard(self.launchers[launcher]["roms"][rom]["name"], __language__( 30036 ))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            self._scrap_rom_algo(launcher, rom, keyboard.getText())
            self._scrap_thumb_rom_algo(launcher, rom, keyboard.getText())
            self._scrap_fanart_rom_algo(launcher, rom, keyboard.getText())
            self._save_launchers()
            xbmc.executebuiltin("Container.Update")

    def _import_rom_nfo(self, launcher, rom):
        # Edition of the rom name
        nfo_file=os.path.splitext(self.launchers[launcher]["roms"][rom]["filename"])[0]+".nfo"
        if (os.path.isfile(nfo_file)):
            f = open(nfo_file, 'r')
            item_nfo = f.read().replace('\r','').replace('\n','')
            item_title = re.findall( "<title>(.*?)</title>", item_nfo )
            item_platform = re.findall( "<platform>(.*?)</platform>", item_nfo )
            item_year = re.findall( "<year>(.*?)</year>", item_nfo )
            item_publisher = re.findall( "<publisher>(.*?)</publisher>", item_nfo )
            item_genre = re.findall( "<genre>(.*?)</genre>", item_nfo )
            item_plot = re.findall( "<plot>(.*?)</plot>", item_nfo )
            if len(item_title) > 0 : self.launchers[launcher]["roms"][rom]["name"] = item_title[0].rstrip()
            self.launchers[launcher]["roms"][rom]["gamesys"] = self.launchers[launcher]["gamesys"]
            if len(item_year) > 0 :  self.launchers[launcher]["roms"][rom]["release"] = item_year[0]
            if len(item_publisher) > 0 : self.launchers[launcher]["roms"][rom]["studio"] = item_publisher[0]
            if len(item_genre) > 0 : self.launchers[launcher]["roms"][rom]["genre"] = item_genre[0]
            if len(item_plot) > 0 : self.launchers[launcher]["roms"][rom]["plot"] = item_plot[0].replace('&quot;','"')
            self._save_launchers()
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30083 ) % os.path.basename(nfo_file)))
        else:
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30082 ) % os.path.basename(nfo_file)))

    def _export_rom_nfo(self, launcher, rom):
        nfo_file=os.path.splitext(self.launchers[launcher]["roms"][rom]["filename"].decode(sys.getfilesystemencoding()))[0]+".nfo"
        if (os.path.isfile(nfo_file)):
            shutil.move( nfo_file, nfo_file+".tmp" )
            destination= open( nfo_file, "w" )
            source= open( nfo_file+".tmp", "r" )
            first_genre=0
            for line in source:
                item_title = re.findall( "<title>(.*?)</title>", line )
                item_platform = re.findall( "<platform>(.*?)</platform>", line )
                item_year = re.findall( "<year>(.*?)</year>", line )
                item_publisher = re.findall( "<publisher>(.*?)</publisher>", line )
                item_genre = re.findall( "<genre>(.*?)</genre>", line )
                item_plot = re.findall( "<plot>(.*?)</plot>", line )
                if len(item_title) > 0 : line = "\t<title>"+self.launchers[launcher]["roms"][rom]["name"]+"</title>\n"
                if len(item_platform) > 0 : line = "\t<platform>"+self.launchers[launcher]["roms"][rom]["gamesys"]+"</platform>\n"
                if len(item_year) > 0 : line = "\t<year>"+self.launchers[launcher]["roms"][rom]["release"]+"</year>\n"
                if len(item_publisher) > 0 : line = "\t<publisher>"+self.launchers[launcher]["roms"][rom]["studio"]+"</publisher>\n"
                if len(item_genre) > 0 :
                    if first_genre == 0 :
                        line = "\t<genre>"+self.launchers[launcher]["roms"][rom]["genre"]+"</genre>\n"
                        first_genre = 1
                if len(item_plot) > 0 : line = "\t<plot>"+self.launchers[launcher]["roms"][rom]["plot"]+"</plot>\n"
                destination.write( line )
            source.close()
            destination.close()
            os.remove(nfo_file+".tmp")
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30087 ) % os.path.basename(nfo_file).encode('utf8','ignore')))
        else:
            usock = open( nfo_file, 'w' )
            usock.write("<game>\n")
            usock.write("\t<title>"+self.launchers[launcher]["roms"][rom]["name"]+"</title>\n")
            usock.write("\t<platform>"+self.launchers[launcher]["roms"][rom]["gamesys"]+"</platform>\n")
            usock.write("\t<year>"+self.launchers[launcher]["roms"][rom]["release"]+"</year>\n")
            usock.write("\t<publisher>"+self.launchers[launcher]["roms"][rom]["studio"]+"</publisher>\n")
            usock.write("\t<genre>"+self.launchers[launcher]["roms"][rom]["genre"]+"</genre>\n")
            usock.write("\t<plot>"+self.launchers[launcher]["roms"][rom]["plot"]+"</plot>\n")
            usock.write("</game>\n")
            usock.close()
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30086 ) % os.path.basename(nfo_file).encode('utf8','ignore')))

    def _add_roms(self, launcher):
        dialog = xbmcgui.Dialog()
        type = dialog.select(__language__( 30106 ), [__language__( 30105 ),__language__( 30320 )])
        if (type == 0 ):
            self._import_roms(launcher)
        if (type == 1 ):
            self._add_new_rom(launcher)
        # Return to the launcher directory
        xbmc.executebuiltin("Container.Refresh")


    def _edit_launcher(self, launcherID):
        dialog = xbmcgui.Dialog()
        title=os.path.basename(self.launchers[launcherID]["application"])
        if (self.launchers[launcherID]["finished"] == "false"):
            finished_display = __language__( 30339 )
        else:
            finished_display = __language__( 30340 )
        if ( self.launchers[launcherID]["rompath"] == "" ):
            type = dialog.select(__language__( 30300 ) % title, [__language__( 30338 ),__language__( 30301 ),__language__( 30302 ),__language__( 30303 ),finished_display,__language__( 30323 ),__language__( 30304 )])
        else:
            type = dialog.select(__language__( 30300 ) % title, [__language__( 30338 ),__language__( 30301 ),__language__( 30302 ),__language__( 30303 ),finished_display,__language__( 30334 ),__language__( 30323 ),__language__( 30304 )])
        type_nb = 0

        # Scrap item (infos and images)
        if (type == type_nb ):
            self._full_scrap_launcher(launcherID)

        # Edition of the launcher infos
        type_nb = type_nb+1
        if (type == type_nb ):
            dialog = xbmcgui.Dialog()
            type2 = dialog.select(__language__( 30319 ), [__language__( 30311 ) % self.settings[ "datas_scraper" ],__language__( 30306 ) % self.launchers[launcherID]["name"],__language__( 30307 ) % self.launchers[launcherID]["gamesys"],__language__( 30308 ) % self.launchers[launcherID]["release"],__language__( 30309 ) % self.launchers[launcherID]["studio"],__language__( 30310 ) % self.launchers[launcherID]["genre"],__language__( 30328 ) % self.launchers[launcherID]["plot"][0:20],__language__( 30333 ),__language__( 30316 )])
            if (type2 == 0 ):
                # Edition of the launcher name
                self._scrap_launcher(launcherID)
            if (type2 == 1 ):
                # Edition of the launcher name
                keyboard = xbmc.Keyboard(self.launchers[launcherID]["name"], __language__( 30037 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    title = keyboard.getText()
                    if ( title == "" ):
                        title = self.launchers[launcherID]["name"]
                    self.launchers[launcherID]["name"] = title.rstrip()
                    self._save_launchers()
            if (type2 == 2 ):
                # Selection of the launcher game system
                dialog = xbmcgui.Dialog()
                platforms = _get_game_system_list()
                gamesystem = dialog.select(__language__( 30077 ), platforms)
                if (not gamesystem == -1 ):
                    self.launchers[launcherID]["gamesys"] = platforms[gamesystem]
                    self._save_launchers()
            if (type2 == 3 ):
                # Edition of the launcher release date
                keyboard = xbmc.Keyboard(self.launchers[launcherID]["release"], __language__( 30038 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    self.launchers[launcherID]["release"] = keyboard.getText()
                    self._save_launchers()
            if (type2 == 4 ):
                # Edition of the launcher studio name
                keyboard = xbmc.Keyboard(self.launchers[launcherID]["studio"], __language__( 30039 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    self.launchers[launcherID]["studio"] = keyboard.getText()
                    self._save_launchers()
            if (type2 == 5 ):
                # Edition of the launcher genre
                keyboard = xbmc.Keyboard(self.launchers[launcherID]["genre"], __language__( 30040 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    self.launchers[launcherID]["genre"] = keyboard.getText()
                    self._save_launchers()
            if (type2 == 6 ):
                # Import of the launcher plot
                text_file = xbmcgui.Dialog().browse(1,__language__( 30080 ),"files",".txt|.dat", False, False, self.launchers[launcherID]["application"])
                if ( os.path.isfile(text_file) == True ):
                    text_plot = open(text_file, 'r')
                    self.launchers[launcherID]["plot"] = text_plot.read()
                    text_plot.close()
                    self._save_launchers()
            if (type2 == 7 ):
                # Edition of the launcher name
                self._import_launcher_nfo(launcherID)
            if (type2 == 8 ):
                # Edition of the launcher name
                self._export_launcher_nfo(launcherID)

        # Launcher Thumbnail menu option
        type_nb = type_nb+1
        if (type == type_nb ):
            dialog = xbmcgui.Dialog()
            thumb_diag = __language__( 30312 ) % ( self.settings[ "thumbs_scraper" ] )
            if ( self.settings[ "thumbs_scraper" ] == "GameFAQs" ) | ( self.settings[ "thumbs_scraper" ] == "MobyGames" ):
                thumb_diag = __language__( 30321 ) % ( self.settings[ "thumbs_scraper" ],self.settings[ "display_game_region" ])
            if ( self.settings[ "thumbs_scraper" ] == "Google" ):
                thumb_diag = __language__( 30322 ) % ( self.settings[ "thumbs_scraper" ],self.settings[ "thumb_image_size_display" ])
            type2 = dialog.select(__language__( 30302 ), [thumb_diag,__language__( 30332 ),__language__( 30313 )])
            if (type2 == 0 ):
                self._scrap_thumb_launcher(launcherID)
            if (type2 == 1 ):
                # Import a Launcher thumbnail image
                image = xbmcgui.Dialog().browse(2,__language__( 30041 ),"files",".jpg|.jpeg|.gif|.png", True, False, os.path.join(self.launchers[launcherID]["thumbpath"]))
                if (image):
                    if (os.path.isfile(image)):
                        img_ext = os.path.splitext(image)[-1][0:4]
                        if ( img_ext != '' ):
                            filename = self.launchers[launcherID]["application"]
                            if ( os.path.join(self.launchers[launcherID]["thumbpath"]) != "" ):
                                file_path = os.path.join(self.launchers[launcherID]["thumbpath"],os.path.basename(self.launchers[launcherID]["application"])+'_thumb'+img_ext)
                            else:
                                if (self.settings[ "launcher_thumb_path" ] == "" ):
                                    self.settings[ "launcher_thumb_path" ] = DEFAULT_THUMB_PATH
                                file_path = os.path.join(self.settings[ "launcher_thumb_path" ],os.path.basename(self.launchers[launcherID]["application"])+'_thumb'+img_ext)
                            if ( image != file_path ):
                                try:
                                    shutil.copy2( image.decode(sys.getfilesystemencoding(),'ignore') , file_path.decode(sys.getfilesystemencoding(),'ignore') )
                                    self.launchers[launcherID]["thumb"] = file_path
                                    self._save_launchers()
                                    _update_cache(file_path)
                                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30070 )))
                                except OSError:
                                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30063 ) % self.launchers[launcherID]["name"]))

            if (type2 == 2 ):
                # Link to a launcher thumbnail image
                if (self.launchers[launcherID]["thumb"] == ""):
                    imagepath = self.launchers[launcherID]["thumbpath"]
                else:
                    imagepath = self.launchers[launcherID]["thumb"]
                image = xbmcgui.Dialog().browse(2,__language__( 30041 ),"files",".jpg|.jpeg|.gif|.png", True, False, os.path.join(imagepath))
                if (image):
                    if (os.path.isfile(image)):
                        self.launchers[launcherID]["thumb"] = image
                        self._save_launchers()
                        _update_cache(image)
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30070 )))

        # Launcher Fanart menu option
        type_nb = type_nb+1
        if (type == type_nb ):
            dialog = xbmcgui.Dialog()
            fanart_diag = __language__( 30312 ) % ( self.settings[ "fanarts_scraper" ] )
            if ( self.settings[ "fanarts_scraper" ] == "Google" ):
                fanart_diag = __language__( 30322 ) % ( self.settings[ "fanarts_scraper" ],self.settings[ "fanart_image_size_display" ].capitalize())
            type2 = dialog.select(__language__( 30303 ), [fanart_diag,__language__( 30332 ),__language__( 30313 )])
            if (type2 == 0 ):
                self._scrap_fanart_launcher(launcherID)
            if (type2 == 1 ):
                # Import a Launcher fanart image
                image = xbmcgui.Dialog().browse(2,__language__( 30041 ),"files",".jpg|.jpeg|.gif|.png", True, False, os.path.join(self.launchers[launcherID]["fanartpath"]))
                if (image):
                    if (os.path.isfile(image)):
                        img_ext = os.path.splitext(image)[-1][0:4]
                        if ( img_ext != '' ):
                            filename = self.launchers[launcherID]["application"]
                            if ( os.path.join(self.launchers[launcherID]["fanartpath"]) != "" ):
                                file_path = os.path.join(self.launchers[launcherID]["fanartpath"],os.path.basename(self.launchers[launcherID]["application"])+'_fanart'+img_ext)
                            else:
                                if (self.settings[ "launcher_fanart_path" ] == "" ):
                                    self.settings[ "launcher_fanart_path" ] = DEFAULT_FANART_PATH
                                file_path = os.path.join(self.settings[ "launcher_fanart_path" ],os.path.basename(self.launchers[launcherID]["application"])+'_fanart'+img_ext)
                            if ( image != file_path ):
                                try:
                                    shutil.copy2( image.decode(sys.getfilesystemencoding(),'ignore') , file_path.decode(sys.getfilesystemencoding(),'ignore') )
                                    self.launchers[launcherID]["fanart"] = file_path
                                    self._save_launchers()
                                    _update_cache(file_path)
                                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30070 )))
                                except OSError:
                                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30064 ) % self.launchers[launcherID]["name"]))
            if (type2 == 2 ):
                # Link to a launcher fanart image
                if (self.launchers[launcherID]["fanart"] == ""):
                    imagepath = self.launchers[launcherID]["fanartpath"]
                else:
                    imagepath = self.launchers[launcherID]["fanart"]
                image = xbmcgui.Dialog().browse(2,__language__( 30042 ),"files",".jpg|.jpeg|.gif|.png", True, False, os.path.join(imagepath))
                if (image):
                    if (os.path.isfile(image)):
                        self.launchers[launcherID]["fanart"] = image
                        self._save_launchers()
                        _update_cache(image)
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30075 )))

        type_nb = type_nb+1
        if (type == type_nb ):
            if (self.launchers[launcherID]["finished"] == "false"):
                self.launchers[launcherID]["finished"] = "true"
            else:
                self.launchers[launcherID]["finished"] = "false"
            self._save_launchers()

        # Launcher's Items List menu option
        if ( self.launchers[launcherID]["rompath"] != "" ):
            type_nb = type_nb+1
            if (type == type_nb ):
                dialog = xbmcgui.Dialog()
                type2 = dialog.select(__language__( 30334 ), [__language__( 30335 ),__language__( 30336 ),__language__( 30318 ),])
                # Import Items list form .nfo files
                if (type2 == 0 ):
                    self._import_items_list_nfo(launcherID)
                # Export Items list to .nfo files
                if (type2 == 1 ):
                    self._export_items_list_nfo(launcherID)
                # Empty Launcher menu option
                if (type2 == 2 ):
                    self._empty_launcher(launcherID)

        # Launcher Advanced menu option
        type_nb = type_nb+1
        if (type == type_nb ):
            if self.launchers[launcherID]["minimize"] == "true":
                minimize_str = __language__( 30204 )
            else:
                minimize_str = __language__( 30205 )
            if self.launchers[launcherID]["lnk"] == "true":
                lnk_str = __language__( 30204 )
            else:
                lnk_str = __language__( 30205 )
            if (os.environ.get( "OS", "xbox" ) == "xbox"):
                filter = ".xbe|.cut"
            else:
                if (sys.platform == "win32"):
                    filter = ".bat|.exe|.cmd"
                else:
                    filter = ""
            if ( self.launchers[launcherID]["rompath"] != "" ):
                if (sys.platform == 'win32'):
                    type2 = dialog.select(__language__( 30323 ), [__language__( 30327 ) % self.launchers[launcherID]["application"],__language__( 30315 ) % self.launchers[launcherID]["args"],__language__( 30324 ) % self.launchers[launcherID]["rompath"],__language__( 30317 ) % self.launchers[launcherID]["romext"],__language__( 30325 ) % self.launchers[launcherID]["thumbpath"], __language__( 30326 ) % self.launchers[launcherID]["fanartpath"], __language__( 30341 ) % self.launchers[launcherID]["trailerpath"], __language__( 30331 ) % self.launchers[launcherID]["custompath"],__language__( 30329 ) % minimize_str,__language__( 30330 ) % lnk_str])
                else:
                    type2 = dialog.select(__language__( 30323 ), [__language__( 30327 ) % self.launchers[launcherID]["application"],__language__( 30315 ) % self.launchers[launcherID]["args"],__language__( 30324 ) % self.launchers[launcherID]["rompath"],__language__( 30317 ) % self.launchers[launcherID]["romext"],__language__( 30325 ) % self.launchers[launcherID]["thumbpath"], __language__( 30326 ) % self.launchers[launcherID]["fanartpath"], __language__( 30341 ) % self.launchers[launcherID]["trailerpath"], __language__( 30331 ) % self.launchers[launcherID]["custompath"],__language__( 30329 ) % minimize_str])
            else:
                if (sys.platform == 'win32'):
                    type2 = dialog.select(__language__( 30323 ), [__language__( 30327 ) % self.launchers[launcherID]["application"],__language__( 30315 ) % self.launchers[launcherID]["args"],__language__( 30325 ) % self.launchers[launcherID]["thumbpath"], __language__( 30326 ) % self.launchers[launcherID]["fanartpath"], __language__( 30341 ) % self.launchers[launcherID]["trailerpath"], __language__( 30331 ) % self.launchers[launcherID]["custompath"],__language__( 30329 ) % minimize_str,__language__( 30330 ) % lnk_str])
                else:
                    type2 = dialog.select(__language__( 30323 ), [__language__( 30327 ) % self.launchers[launcherID]["application"],__language__( 30315 ) % self.launchers[launcherID]["args"],__language__( 30325 ) % self.launchers[launcherID]["thumbpath"], __language__( 30326 ) % self.launchers[launcherID]["fanartpath"], __language__( 30341 ) % self.launchers[launcherID]["trailerpath"], __language__( 30331 ) % self.launchers[launcherID]["custompath"],__language__( 30329 ) % minimize_str])

            # Launcher application path menu option
            type2_nb = 0
            if (type2 == type2_nb ):
                app = xbmcgui.Dialog().browse(1,__language__( 30023 ),"files",filter, False, False, self.launchers[launcherID]["application"])
                self.launchers[launcherID]["application"] = app

            # Edition of the launcher arguments
            type2_nb = type2_nb +1
            if (type2 == type2_nb ):
                keyboard = xbmc.Keyboard(self.launchers[launcherID]["args"], __language__( 30052 ))
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    self.launchers[launcherID]["args"] = keyboard.getText()
                    self._save_launchers()

            if ( self.launchers[launcherID]["rompath"] != "" ):
                # Launcher roms path menu option
                type2_nb = type2_nb + 1
                if (type2 == type2_nb ):
                    rom_path = xbmcgui.Dialog().browse(0,__language__( 30058 ),"files", "", False, False, self.launchers[launcherID]["rompath"])
                    self.launchers[launcherID]["rompath"] = rom_path

                # Edition of the launcher rom extensions (only for emulator launcher)
                type2_nb = type2_nb +1
                if (type2 == type2_nb ):
                    if (not self.launchers[launcherID]["rompath"] == ""):
                        keyboard = xbmc.Keyboard(self.launchers[launcherID]["romext"], __language__( 30054 ))
                        keyboard.doModal()
                        if (keyboard.isConfirmed()):
                            self.launchers[launcherID]["romext"] = keyboard.getText()
                            self._save_launchers()

            # Launcher thumbnails path menu option
            type2_nb = type2_nb + 1
            if (type2 == type2_nb ):
                thumb_path = xbmcgui.Dialog().browse(0,__language__( 30059 ),"files","", False, False, self.launchers[launcherID]["thumbpath"])
                self.launchers[launcherID]["thumbpath"] = thumb_path
            # Launcher fanarts path menu option
            type2_nb = type2_nb + 1
            if (type2 == type2_nb ):
                fanart_path = xbmcgui.Dialog().browse(0,__language__( 30060 ),"files","", False, False, self.launchers[launcherID]["fanartpath"])
                self.launchers[launcherID]["fanartpath"] = fanart_path
            # Launcher trailer file menu option
            type2_nb = type2_nb + 1
            if (type2 == type2_nb ):
                fanart_path = xbmcgui.Dialog().browse(1,__language__( 30090 ),"files",".mp4|.mpg|.avi|.wmv|.mkv|.flv", False, False, self.launchers[launcherID]["trailerpath"])
                self.launchers[launcherID]["trailerpath"] = fanart_path
            # Launcher custom path menu option
            type2_nb = type2_nb + 1
            if (type2 == type2_nb ):
                fanart_path = xbmcgui.Dialog().browse(0,__language__( 30057 ),"files","", False, False, self.launchers[launcherID]["custompath"])
                self.launchers[launcherID]["custompath"] = fanart_path
            # Launcher minimize state menu option
            type2_nb = type2_nb + 1
            if (type2 == type2_nb ):
                dialog = xbmcgui.Dialog()
                type3 = dialog.select(__language__( 30203 ), ["%s (%s)" % (__language__( 30205 ),__language__( 30201 )), "%s" % (__language__( 30204 ))])
                if (type3 == 1 ):
                    self.launchers[launcherID]["minimize"] = "true"
                else:
                    self.launchers[launcherID]["minimize"] = "false"
            self._save_launchers()
            # Launcher internal lnk option
            if (sys.platform == 'win32'):
                type2_nb = type2_nb + 1
                if (type2 == type2_nb ):
                    dialog = xbmcgui.Dialog()
                    type3 = dialog.select(__language__( 30206 ), ["%s (%s)" % (__language__( 30204 ),__language__( 30201 )), "%s (%s)" % (__language__( 30205 ),__language__( 30202 ))])
                    if (type3 == 1 ):
                        self.launchers[launcherID]["lnk"] = "false"
                    else:
                        self.launchers[launcherID]["lnk"] = "true"
            self._save_launchers()

        # Remove Launcher menu option
        type_nb = type_nb+1
        if (type == type_nb ):
            self._remove_launcher(launcherID)

        if (type == -1 ):
            self._save_launchers()

        # Return to the launcher directory
        xbmc.executebuiltin("Container.Refresh")

    def _scrap_launcher_algo(self, launcherID, title):
        # Scrapping launcher name info
        results,display = self._get_games_list(title)
        if display:
            # Display corresponding game list found
            dialog = xbmcgui.Dialog()
            # Game selection
            selectgame = dialog.select(__language__( 30078 ) % ( self.settings[ "datas_scraper" ] ), display)
            if (not selectgame == -1):
                if ( self.settings[ "ignore_title" ] ):
                    self.launchers[launcherID]["name"] = title_format(self,self.launchers[launcherID]["name"])
                else:
                    self.launchers[launcherID]["name"] = title_format(self,results[selectgame]["title"])
                gamedata = self._get_game_data(results[selectgame])
                self.launchers[launcherID]["genre"] = gamedata["genre"]
                self.launchers[launcherID]["release"] = gamedata["release"]
                self.launchers[launcherID]["studio"] = gamedata["studio"]
                self.launchers[launcherID]["plot"] = gamedata["plot"]
        else:
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30076 )))

    def _scrap_launcher(self, launcherID):
        # Edition of the launcher name
        keyboard = xbmc.Keyboard(self.launchers[launcherID]["name"], __language__( 30036 ))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            self._scrap_launcher_algo(launcherID, keyboard.getText())
            self._save_launchers()
            xbmc.executebuiltin("Container.Update")

    def _full_scrap_launcher(self, launcherID):
        # Edition of the launcher name
        keyboard = xbmc.Keyboard(self.launchers[launcherID]["name"], __language__( 30036 ))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            self._scrap_launcher_algo(launcherID, keyboard.getText())
            self._scrap_thumb_launcher_algo(launcherID, keyboard.getText())
            self._scrap_fanart_launcher_algo(launcherID, keyboard.getText())
            self._save_launchers()
            xbmc.executebuiltin("Container.Update")

    def _import_launcher_nfo(self, launcherID):
        if ( len(self.launchers[launcherID]["rompath"]) > 0 ):
            nfo_file = os.path.join(self.launchers[launcherID]["rompath"],os.path.basename(os.path.splitext(self.launchers[launcherID]["application"])[0]+".nfo"))
        else:
            if ( len(self.settings[ "launcher_nfo_path" ]) > 0 ):
                nfo_file = os.path.join(self.settings[ "launcher_nfo_path" ],os.path.basename(os.path.splitext(self.launchers[launcherID]["application"])[0]+".nfo"))
            else:
                nfo_file = xbmcgui.Dialog().browse(1,__language__( 30088 ),"files",".nfo", False, False)
        if (os.path.isfile(nfo_file)):
            f = open(nfo_file, 'r')
            item_nfo = f.read().replace('\r','').replace('\n','')
            item_title = re.findall( "<title>(.*?)</title>", item_nfo )
            item_platform = re.findall( "<platform>(.*?)</platform>", item_nfo )
            item_year = re.findall( "<year>(.*?)</year>", item_nfo )
            item_publisher = re.findall( "<publisher>(.*?)</publisher>", item_nfo )
            item_genre = re.findall( "<genre>(.*?)</genre>", item_nfo )
            item_plot = re.findall( "<plot>(.*?)</plot>", item_nfo )
            self.launchers[launcherID]["name"] = item_title[0].rstrip()
            self.launchers[launcherID]["gamesys"] = item_platform[0]
            self.launchers[launcherID]["release"] = item_year[0]
            self.launchers[launcherID]["studio"] = item_publisher[0]
            self.launchers[launcherID]["genre"] = item_genre[0]
            self.launchers[launcherID]["plot"] = item_plot[0].replace('&quot;','"')
            self._save_launchers()
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30083 ) % os.path.basename(nfo_file)))
        else:
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30082 ) % os.path.basename(nfo_file)))

    def _export_items_list_nfo(self, launcherID):
        for rom in self.launchers[launcherID]["roms"].iterkeys():
            self._export_rom_nfo(launcherID, rom)

    def _import_items_list_nfo(self, launcherID):
        for rom in self.launchers[launcherID]["roms"].iterkeys():
            self._import_rom_nfo(launcherID, rom)

    def _export_launcher_nfo(self, launcherID):
        if ( len(self.launchers[launcherID]["rompath"]) > 0 ):
            nfo_file = os.path.join(self.launchers[launcherID]["rompath"],os.path.basename(os.path.splitext(self.launchers[launcherID]["application"])[0]+".nfo"))
        else:
            if ( len(self.settings[ "launcher_nfo_path" ]) > 0 ):
                nfo_file = os.path.join(self.settings[ "launcher_nfo_path" ],os.path.basename(os.path.splitext(self.launchers[launcherID]["application"])[0]+".nfo"))
            else:
                nfo_path = xbmcgui.Dialog().browse(0,__language__( 30089 ),"files",".nfo", False, False)
                nfo_file = os.path.join(nfo_path,os.path.basename(os.path.splitext(self.launchers[launcherID]["application"])[0]+".nfo"))
        if (os.path.isfile(nfo_file)):
            shutil.move( nfo_file, nfo_file+".tmp" )
            destination= open( nfo_file, "w" )
            source= open( nfo_file+".tmp", "r" )
            for line in source:
                item_title = re.findall( "<title>(.*?)</title>", line )
                item_platform = re.findall( "<platform>(.*?)</platform>", line )
                item_year = re.findall( "<year>(.*?)</year>", line )
                item_publisher = re.findall( "<publisher>(.*?)</publisher>", line )
                item_genre = re.findall( "<genre>(.*?)</genre>", line )
                item_plot = re.findall( "<plot>(.*?)</plot>", line )
                if len(item_title) > 0 : line = "\t<title>"+self.launchers[launcherID]["name"]+"</title>\n"
                if len(item_platform) > 0 : line = "\t<platform>"+self.launchers[launcherID]["gamesys"]+"</platform>\n"
                if len(item_year) > 0 : line = "\t<year>"+self.launchers[launcherID]["release"]+"</year>\n"
                if len(item_publisher) > 0 : line = "\t<publisher>"+self.launchers[launcherID]["studio"]+"</publisher>\n"
                if len(item_genre) > 0 : line = "\t<genre>"+self.launchers[launcherID]["genre"]+"</genre>\n"
                if len(item_plot) > 0 : line = "\t<plot>"+self.launchers[launcherID]["plot"]+"</plot>\n"
                destination.write( line )
            source.close()
            destination.close()
            os.remove(nfo_file+".tmp")
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30087 ) % os.path.basename(nfo_file)))
        else:
            usock = open( nfo_file, 'w' )
            usock.write("<game>\n")
            usock.write("\t<title>"+self.launchers[launcherID]["name"]+"</title>\n")
            usock.write("\t<platform>"+self.launchers[launcherID]["gamesys"]+"</platform>\n")
            usock.write("\t<year>"+self.launchers[launcherID]["release"]+"</year>\n")
            usock.write("\t<publisher>"+self.launchers[launcherID]["studio"]+"</publisher>\n")
            usock.write("\t<genre>"+self.launchers[launcherID]["genre"]+"</genre>\n")
            usock.write("\t<plot>"+self.launchers[launcherID]["plot"]+"</plot>\n")
            usock.write("</game>\n")
            usock.close()
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30086 ) % os.path.basename(nfo_file)))

    def _run_launcher(self, launcherID):
        if (self.launchers.has_key(launcherID)):
            launcher = self.launchers[launcherID]
            apppath = os.path.dirname(launcher["application"])
            arguments = launcher["args"].replace("%apppath%" , apppath).replace("%APPPATH%" , apppath)
            if ( os.path.basename(launcher["application"]).lower().replace(".exe" , "") == "xbmc" ):
                xbmc.executebuiltin('XBMC.' + launcher["args"])
            else:
                if ( xbmc.Player().isPlaying() ):
                    if ( self.settings[ "media_state" ] == "0" ):
                        xbmc.executebuiltin('PlayerControl(Stop)')
                    if ( self.settings[ "media_state" ] == "1" ):
                        xbmc.executebuiltin('PlayerControl(Play)')
                    xbmc.sleep(2*self.settings[ "start_tempo" ])
                if (launcher["minimize"] == "true"):
                    _toogle_fullscreen()
                if ( self.settings[ "launcher_notification" ] ):
                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30034 ) % launcher["name"]))
                xbmc.sleep(self.settings[ "start_tempo" ])
                if (os.environ.get( "OS", "xbox" ) == "xbox"):
                    xbmc.executebuiltin('XBMC.Runxbe(' + launcher["application"] + ')')
                else:
                    if (sys.platform == 'win32'):
                        if ( launcher["application"].split(".")[-1] == "lnk" ):
                            #os.system("start \"\" \"%s\"" % (launcher["application"]))
                            os.startfile(launcher["application"])
                        else:
                            if ( launcher["application"].split(".")[-1] == "bat" ):
                                info = subprocess_hack.STARTUPINFO()
                                info.dwFlags = 1
                                if ( self.settings[ "show_batch" ] ):
                                    info.wShowWindow = 5
                                else:
                                    info.wShowWindow = 0
                            else:
                                info = None
                            startproc = subprocess_hack.Popen(r'%s %s' % (launcher["application"], arguments), cwd=apppath, startupinfo=info)
                            startproc.wait()
                    elif (sys.platform.startswith('linux')):
                        if ( self.settings[ "lirc_state" ] ):
                            xbmc.executebuiltin('LIRC.stop')
                        os.system("\"%s\" %s " % (launcher["application"], arguments))
                        if ( self.settings[ "lirc_state" ] ):
                            xbmc.executebuiltin('LIRC.start')
                    elif (sys.platform.startswith('darwin')):
                        os.system("\"%s\" %s " % (launcher["application"], arguments))
                    else:
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30609 )))
                xbmc.sleep(self.settings[ "start_tempo" ])
                if (launcher["minimize"] == "true"):
                    _toogle_fullscreen()
                if ( self.settings[ "media_state" ] == "1" ):
                    xbmc.sleep(2*self.settings[ "start_tempo" ])
                    xbmc.executebuiltin('PlayerControl(Play)')

    def _get_settings( self ):
        # get the users preference settings
        self.settings = {}
        self.settings[ "datas_method" ] = __settings__.getSetting( "datas_method" )
        self.settings[ "thumbs_method" ] = __settings__.getSetting( "thumbs_method" )
        self.settings[ "fanarts_method" ] = __settings__.getSetting( "fanarts_method" )
        self.settings[ "scrap_info" ] = __settings__.getSetting( "scrap_info" )
        self.settings[ "scrap_thumbs" ] = __settings__.getSetting( "scrap_thumbs" )
        self.settings[ "scrap_fanarts" ] = __settings__.getSetting( "scrap_fanarts" )
        self.settings[ "select_fanarts" ] = __settings__.getSetting( "select_fanarts" )
        self.settings[ "overwrite_thumbs" ] = ( __settings__.getSetting( "overwrite_thumbs" ) == "true" )
        self.settings[ "overwrite_fanarts" ] = ( __settings__.getSetting( "overwrite_fanarts" ) == "true" )
        self.settings[ "clean_title" ] = ( __settings__.getSetting( "clean_title" ) == "true" )
        self.settings[ "ignore_bios" ] = ( __settings__.getSetting( "ignore_bios" ) == "true" )
        self.settings[ "ignore_title" ] = ( __settings__.getSetting( "ignore_title" ) == "true" )
        self.settings[ "title_formating" ] = ( __settings__.getSetting( "title_formating" ) == "true" )
        self.settings[ "datas_scraper" ] = __settings__.getSetting( "datas_scraper" )
        self.settings[ "thumbs_scraper" ] = __settings__.getSetting( "thumbs_scraper" )
        self.settings[ "fanarts_scraper" ] = __settings__.getSetting( "fanarts_scraper" )
        self.settings[ "game_region" ] = ['All','EU','JP','US'][int(__settings__.getSetting('game_region'))]
        self.settings[ "display_game_region" ] = [__language__( 30136 ),__language__( 30144 ),__language__( 30145 ),__language__( 30146 )][int(__settings__.getSetting('game_region'))]
        self.settings[ "thumb_image_size" ] = ['','isz:i','isz:s','isz:m','isz:l','isz:ex,iszw:1280,iszh:720','isz:ex,iszw:1920,isz:iszh:1080','isz:ex,iszw:3840,iszh:2160'][int(__settings__.getSetting('thumb_image_size'))]
        self.settings[ "thumb_image_size_display" ] = [__language__( 30136 ),__language__( 30137 ),__language__( 30138 ),__language__( 30139 ),__language__( 30140 ),__language__( 30141 ),__language__( 30142 ),__language__( 30143 )][int(__settings__.getSetting('thumb_image_size'))]
        self.settings[ "fanart_image_size" ] = ['','isz:i','isz:s','isz:m','isz:l','isz:ex,iszw:1280,iszh:720','isz:ex,iszw:1920,iszh:1080','isz:ex,iszw:3840,iszh:2160'][int(__settings__.getSetting('fanart_image_size'))]
        self.settings[ "fanart_image_size_display" ] = [__language__( 30136 ),__language__( 30137 ),__language__( 30138 ),__language__( 30139 ),__language__( 30140 ),__language__( 30141 ),__language__( 30142 ),__language__( 30143 )][int(__settings__.getSetting('fanart_image_size'))]
        self.settings[ "launcher_thumb_path" ] = __settings__.getSetting( "launcher_thumb_path" )
        self.settings[ "launcher_fanart_path" ] = __settings__.getSetting( "launcher_fanart_path" )
        self.settings[ "launcher_nfo_path" ] = __settings__.getSetting( "launcher_nfo_path" )
        self.settings[ "media_state" ] = __settings__.getSetting( "media_state" )
        self.settings[ "show_batch" ] = ( __settings__.getSetting( "show_batch" ) == "true" )
        self.settings[ "recursive_scan" ] = ( __settings__.getSetting( "recursive_scan" ) == "true" )
        self.settings[ "launcher_notification" ] = ( __settings__.getSetting( "launcher_notification" ) == "true" )
        self.settings[ "lirc_state" ] = ( __settings__.getSetting( "lirc_state" ) == "true" )
        self.settings[ "hide_finished" ] = ( __settings__.getSetting( "hide_finished" ) == "true" )
        self.settings[ "snap_flyer" ] = __settings__.getSetting( "snap_flyer" )
        self.settings[ "start_tempo" ] = int(round(float(__settings__.getSetting( "start_tempo" ))))
        self.settings[ "auto_backup" ] = ( __settings__.getSetting( "auto_backup" ) == "true" )
        self.settings[ "nb_backup_files" ] = int(round(float(__settings__.getSetting( "nb_backup_files" ))))
        self.settings[ "show_log" ] = ( __settings__.getSetting( "show_log" ) == "true" )

    def _print_log(self,string):
        if (self.settings[ "show_log" ]):
            print "[ALA] "+string

    def _get_scrapers( self ):
        # get the users gamedata scrapers preference
        exec "import resources.scrapers.datas.%s.datas_scraper as _data_scraper" % ( self.settings[ "datas_scraper" ] )
        self._get_games_list = _data_scraper._get_games_list
        self._get_game_data = _data_scraper._get_game_data
        self._get_first_game = _data_scraper._get_first_game

        # get the users thumbs scrapers preference
        exec "import resources.scrapers.thumbs.%s.thumbs_scraper as _thumbs_scraper" % ( self.settings[ "thumbs_scraper" ] )
        self._get_thumbnails_list = _thumbs_scraper._get_thumbnails_list
        self._get_thumbnail = _thumbs_scraper._get_thumbnail

        # get the users fanarts scrapers preference
        exec "import resources.scrapers.fanarts.%s.fanarts_scraper as _fanarts_scraper" % ( self.settings[ "fanarts_scraper" ] )
        self._get_fanarts_list = _fanarts_scraper._get_fanarts_list
        self._get_fanart = _fanarts_scraper._get_fanart

    def _run_rom(self, launcherID, romName):
        if (self.launchers.has_key(launcherID)):
            launcher = self.launchers[launcherID]
            if (launcher["roms"].has_key(romName)):
                rom = self.launchers[launcherID]["roms"][romName]
                romfile = os.path.basename(rom["filename"])
                apppath = os.path.dirname(launcher["application"])
                rompath = os.path.dirname(rom["filename"])
                romname = os.path.splitext(romfile)[0]

                files = []
                filesnames = []
                ext3s = ['.cd1', '-cd1', '_cd1', ' cd1']
                for ext3 in ext3s:
                    cleanromname = re.sub('(\[.*?\]|\{.*?\}|\(.*?\))', '', romname)
                    if ( cleanromname.lower().find(ext3) > -1 ):
                        temprompath = os.path.dirname(rom["filename"])
                        try:
                            filesnames = os.listdir(temprompath)
                        except:
                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30610 )))
                        namestem = cleanromname[:-len(ext3)]

                        for filesname in filesnames:
                            altname=re.findall('\{.*?\}',filesname)
                            searchname = re.sub('(\[.*?\]|\{.*?\}|\(.*?\))', '', filesname)
                            if searchname[0:len(namestem)] == namestem and searchname[len(namestem):len(namestem)+len(ext3) - 1]  == ext3[:-1]:
                                for romext in launcher["romext"].split("|"):
                                    if searchname[-len(romext):].lower() == romext.lower() :
                                        Discnum = searchname[(len(namestem)+len(ext3)-1):searchname.rfind(".")]
                                        try:
                                            int(Discnum)
                                            if not altname:
                                                files.append([Discnum, xbmc.getLocalizedString(427)+" "+Discnum, os.path.join(os.path.dirname(rom["filename"]),filesname)])
                                            else:
                                                files.append([Discnum, altname[0][1:-1], os.path.join(os.path.dirname(rom["filename"]),filesname)])
                                        except:
                                            pass
                        if len(files) > 0:
                            files.sort(key=lambda x: int(x[0]))
                            discs = []
                            for file in files:
                                discs.append(file[1])
                            dialog = xbmcgui.Dialog()
                            type3 = dialog.select("%s:" % __language__( 30035 ), discs)
                            if type3 > -1 :
                                myresult = files[type3]
                                rom["filename"] = myresult[2]
                                romfile = os.path.basename(rom["filename"])
                                rompath = os.path.dirname(rom["filename"])
                                romname = os.path.splitext(romfile)[0]
                            else:
                                return ""

                arguments = launcher["args"]
                arguments = arguments.replace("%rom%" , rom["filename"]).replace("%ROM%" , rom["filename"])
                arguments = arguments.replace("%romfile%" , romfile).replace("%ROMFILE%" , romfile)
                arguments = arguments.replace("%romname%" , romname).replace("%ROMNAME%" , romname)
                arguments = arguments.replace("%rombasename%" , base_filename(romname)).replace("%ROMBASENAME%" , base_filename(romname))
                arguments = arguments.replace("%apppath%" , apppath).replace("%APPPATH%" , apppath)
                arguments = arguments.replace("%rompath%" , rompath).replace("%ROMPATH%" , rompath)
                arguments = arguments.replace("%romtitle%" , rom["name"]).replace("%ROMTITLE%" , rom["name"])
                arguments = arguments.replace("%romspath%" , launcher["rompath"]).replace("%ROMSPATH%" , launcher["rompath"])

                if ( os.path.basename(launcher["application"]).lower().replace(".exe" , "") == "xbmc" ):
                    xbmc.executebuiltin('XBMC.' + arguments)
                else:
                    if ( xbmc.Player().isPlaying() ):
                        if ( self.settings[ "media_state" ] == "0" ):
                            xbmc.executebuiltin('PlayerControl(Stop)')
                        if ( self.settings[ "media_state" ] == "1" ):
                            xbmc.executebuiltin('PlayerControl(Play)')
                        xbmc.sleep(2*self.settings[ "start_tempo" ])
                    if (launcher["minimize"] == "true"):
                        _toogle_fullscreen()
                    if ( self.settings[ "launcher_notification" ] ):
                        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30034 ) % rom["name"]))
                    xbmc.sleep(self.settings[ "start_tempo" ])
                    if (os.environ.get( "OS", "xbox" ) == "xbox"):
                        f=open(SHORTCUT_FILE, "wb")
                        f.write("<shortcut>\n")
                        f.write("    <path>" + launcher["application"] + "</path>\n")
                        f.write("    <custom>\n")
                        f.write("       <game>" + rom["filename"] + "</game>\n")
                        f.write("    </custom>\n")
                        f.write("</shortcut>\n")
                        f.close()
                        xbmc.executebuiltin('XBMC.Runxbe(' + SHORTCUT_FILE + ')')
                    else:
                        if (sys.platform == 'win32'):
                            if ( launcher["lnk"] == "true" ) and ( launcher["romext"] == "lnk" ):
                                os.system("start \"\" \"%s\"" % (arguments))
                            else:
                                if ( launcher["application"].split(".")[-1] == "bat" ):
                                    info = subprocess_hack.STARTUPINFO()
                                    info.dwFlags = 1
                                    if ( self.settings[ "show_batch" ] ):
                                        info.wShowWindow = 5
                                    else:
                                        info.wShowWindow = 0
                                else:
                                    info = None
                                startproc = subprocess_hack.Popen(r'%s %s' % (launcher["application"], arguments), cwd=apppath, startupinfo=info)
                                startproc.wait()
                        elif (sys.platform.startswith('linux')):
                            if ( self.settings[ "lirc_state" ] ):
                                xbmc.executebuiltin('LIRC.stop')
                            os.system("\"%s\" %s " % (launcher["application"], arguments))
                            if ( self.settings[ "lirc_state" ] ):
                                xbmc.executebuiltin('LIRC.start')
                        elif (sys.platform.startswith('darwin')):
                            os.system("\"%s\" %s " % (launcher["application"], arguments))
                        else:
                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30609 )))
                    xbmc.sleep(self.settings[ "start_tempo" ])
                    if (launcher["minimize"] == "true"):
                        _toogle_fullscreen()
                    if ( self.settings[ "media_state" ] == "1" ):
                        xbmc.sleep(2*self.settings[ "start_tempo" ])
                        xbmc.executebuiltin('PlayerControl(Play)')

    ''' get an xml data from an xml file '''
    def get_xml_source( self, xmlpath ):
        try:
            usock = open( xmlpath, 'r' )
            # read source
            xmlSource = usock.read()
            # close socket
            usock.close()
            ok = True
        except:
            # oops print error message
            print "ERROR: %s::%s (%d) - %s" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
            ok = False
        if ( ok ):
            # clean, save and return the xml string
            xmlSource = xmlSource.replace("&amp;", "&")
            xmlSource = xmlSource.replace("&", "&amp;")
            f = open(BASE_CURRENT_SOURCE_PATH, 'w')
            f.write(xmlSource)
            f.close()
            return xmlSource.replace("\n","").replace("\r","")
        else:
            return ""

    def _save_launchers (self):
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        # make settings directory if doesn't exists
        if (not os.path.isdir(os.path.dirname(TEMP_CURRENT_SOURCE_PATH))):
            os.makedirs(os.path.dirname(TEMP_CURRENT_SOURCE_PATH))
        if ( self.settings[ "auto_backup" ] ):
            # delete old backup files
            fileData = {}
            dirList=os.listdir(DEFAULT_BACKUP_PATH)
            for fname in dirList:
                fileData[fname] = os.stat(os.path.join( DEFAULT_BACKUP_PATH,fname)).st_mtime
            sortedFiles = sorted(fileData.items(), key=itemgetter(1))
            delete = len(sortedFiles) - self.settings[ "nb_backup_files" ] + 1
            for x in range(0, delete):
                os.remove(os.path.join( DEFAULT_BACKUP_PATH,sortedFiles[x][0]))
            # make current launchers.xml backup
            if ( os.path.isfile(BASE_CURRENT_SOURCE_PATH)):
                try:
                    now = datetime.datetime.now()
                    timestamp = str(now.year)+str(now.month).rjust(2,'0')+str(now.day).rjust(2,'0')+"-"+str(now.hour).rjust(2,'0')+str(now.minute).rjust(2,'0')+str(now.second).rjust(2,'0')+"-"+str(now.microsecond)+"-"
                    BACKUP_CURRENT_SOURCE_PATH = os.path.join( DEFAULT_BACKUP_PATH , timestamp+"launchers.xml" )
                    shutil.copy2(BASE_CURRENT_SOURCE_PATH, BACKUP_CURRENT_SOURCE_PATH)
                except OSError:
                    xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30600 )))
        try:
            usock = open( TEMP_CURRENT_SOURCE_PATH, 'w' )
            usock.write("<?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"yes\"?>\n")
            usock.write("<launchers>\n")
            for launcherIndex in sorted(self.launchers, key= lambda x : self.launchers[x]["name"]):
                launcher = self.launchers[launcherIndex]
                usock.write("\t<launcher>\n")
                usock.write("\t\t<id>"+launcherIndex+"</id>\n")
                # replace low-9 quotation mark by comma
                usock.write("\t\t<name>"+launcher["name"]+"</name>\n")
                usock.write("\t\t<application>"+launcher["application"]+"</application>\n")
                usock.write("\t\t<args>"+launcher["args"]+"</args>\n")
                usock.write("\t\t<rompath>"+launcher["rompath"]+"</rompath>\n")
                usock.write("\t\t<thumbpath>"+launcher["thumbpath"]+"</thumbpath>\n")
                usock.write("\t\t<fanartpath>"+launcher["fanartpath"]+"</fanartpath>\n")
                usock.write("\t\t<trailerpath>"+launcher["trailerpath"]+"</trailerpath>\n")
                usock.write("\t\t<custompath>"+launcher["custompath"]+"</custompath>\n")
                usock.write("\t\t<romext>"+launcher["romext"]+"</romext>\n")
                usock.write("\t\t<platform>"+launcher["gamesys"]+"</platform>\n")
                usock.write("\t\t<thumb>"+launcher["thumb"]+"</thumb>\n")
                usock.write("\t\t<fanart>"+launcher["fanart"]+"</fanart>\n")
                usock.write("\t\t<genre>"+launcher["genre"]+"</genre>\n")
                usock.write("\t\t<release>"+launcher["release"]+"</release>\n")
                usock.write("\t\t<publisher>"+launcher["studio"]+"</publisher>\n")
                usock.write("\t\t<launcherplot>"+launcher["plot"]+"</launcherplot>\n")
                usock.write("\t\t<finished>"+launcher["finished"]+"</finished>\n")
                usock.write("\t\t<minimize>"+launcher["minimize"]+"</minimize>\n")
                usock.write("\t\t<lnk>"+launcher["lnk"]+"</lnk>\n")
                usock.write("\t\t<roms>\n")
                for romIndex in sorted(launcher["roms"], key= lambda x : launcher["roms"][x]["name"]):
                    romdata = launcher["roms"][romIndex]
                    usock.write("\t\t\t<rom>\n")
                    usock.write("\t\t\t\t<id>"+romIndex+"</id>\n")
                    # replace low-9 quotation mark by comma
                    usock.write("\t\t\t\t<name>"+romdata["name"]+"</name>\n")
                    usock.write("\t\t\t\t<filename>"+romdata["filename"]+"</filename>\n")
                    usock.write("\t\t\t\t<thumb>"+romdata["thumb"]+"</thumb>\n")
                    usock.write("\t\t\t\t<fanart>"+romdata["fanart"]+"</fanart>\n")
                    usock.write("\t\t\t\t<trailer>"+romdata["trailer"]+"</trailer>\n")
                    usock.write("\t\t\t\t<custom>"+romdata["custom"]+"</custom>\n")
                    usock.write("\t\t\t\t<genre>"+romdata["genre"]+"</genre>\n")
                    usock.write("\t\t\t\t<release>"+romdata["release"]+"</release>\n")
                    usock.write("\t\t\t\t<publisher>"+romdata["studio"]+"</publisher>\n")
                    usock.write("\t\t\t\t<gameplot>"+romdata["plot"]+"</gameplot>\n")
                    usock.write("\t\t\t\t<finished>"+romdata["finished"]+"</finished>\n")
                    usock.write("\t\t\t</rom>\n")
                usock.write("\t\t</roms>\n")
                usock.write("\t</launcher>\n")
            usock.write("</launchers>")
            usock.close()
            try:
                shutil.copy2(TEMP_CURRENT_SOURCE_PATH, BASE_CURRENT_SOURCE_PATH)
            except OSError:
                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30601 )))
        except OSError:
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30602 )))
        except IOError:
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30603 )))
        os.remove(TEMP_CURRENT_SOURCE_PATH)
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )


    ''' read the list of launchers and roms from launchers.xml file '''
    def _load_launchers(self, xmlSource):
        need_update = 0
        # clean, save and return the xml string
        xmlSource = xmlSource.replace("&amp;", "&")
        launchers = re.findall( "<launcher>(.*?)</launcher>", xmlSource )
        for launcher in launchers:
            launcherid = re.findall( "<id>(.*?)</id>", launcher )
            name = re.findall( "<name>(.*?)</name>", launcher )
            application = re.findall( "<application>(.*?)</application>", launcher )
            args = re.findall( "<args>(.*?)</args>", launcher )
            rompath = re.findall( "<rompath>(.*?)</rompath>", launcher )
            thumbpath = re.findall( "<thumbpath>(.*?)</thumbpath>", launcher )
            fanartpath = re.findall( "<fanartpath>(.*?)</fanartpath>", launcher )
            trailerpath = re.findall( "<trailerpath>(.*?)</trailerpath>", launcher )
            custompath = re.findall( "<custompath>(.*?)</custompath>", launcher )
            romext = re.findall( "<romext>(.*?)</romext>", launcher )
            gamesys = re.findall( "<platform>(.*?)</platform>", launcher )
            thumb = re.findall( "<thumb>(.*?)</thumb>", launcher )
            fanart = re.findall( "<fanart>(.*?)</fanart>", launcher )
            genre = re.findall( "<genre>(.*?)</genre>", launcher )
            release = re.findall( "<release>(.*?)</release>", launcher )
            studio = re.findall( "<publisher>(.*?)</publisher>", launcher )
            plot = re.findall( "<launcherplot>(.*?)</launcherplot>", launcher )
            lnk = re.findall( "<lnk>(.*?)</lnk>", launcher )
            finished = re.findall( "<finished>(.*?)</finished>", launcher )
            minimize = re.findall( "<minimize>(.*?)</minimize>", launcher )
            romsxml = re.findall( "<rom>(.*?)</rom>", launcher )

            if len(launcherid) > 0 : launcherid = launcherid[0]
            else:
                launcherid = _get_SID()
                need_update = 1
            # replace comma by single low-9 quotation mark
            if len(name) > 0 : name = name[0]
            else: name = "unknown"
            if len(application) > 0 : application = application[0]
            else: application = ""
            if len(args) > 0 : args = args[0]
            else: args = ""
            if len(rompath) > 0 : rompath = rompath[0]
            else: rompath = ""
            if len(thumbpath) > 0 : thumbpath = thumbpath[0]
            else: thumbpath = ""
            if len(fanartpath) > 0 : fanartpath = fanartpath[0]
            else: fanartpath = ""
            if len(trailerpath) > 0 : trailerpath = trailerpath[0]
            else: trailerpath = ""
            if len(custompath) > 0 : custompath = custompath[0]
            else: custompath = ""
            if len(romext) > 0: romext = romext[0]
            else: romext = ""
            if len(gamesys) > 0: gamesys = gamesys[0]
            else: gamesys = ""
            if len(thumb) > 0: thumb = thumb[0]
            else: thumb = ""
            if len(fanart) > 0: fanart = fanart[0]
            else: fanart = ""
            if len(genre) > 0: genre = genre[0]
            else: genre = ""
            if len(release) > 0: release = release[0]
            else: release = ""
            if len(studio) > 0: studio = studio[0]
            else: studio = ""
            if len(plot) > 0: plot = plot[0]
            else: plot = ""
            if len(finished) > 0: finished = finished[0]
            else: finished = "false"
            if len(lnk) > 0: lnk = lnk[0]
            else:
                if (sys.platform == 'win32'):
                    lnk = "true"
                else:
                    lnk = ""
            if len(minimize) > 0: minimize = minimize[0]
            else: minimize = "false"

            roms = {}
            for rom in romsxml:
                romid = re.findall( "<id>(.*?)</id>", rom )
                romname = re.findall( "<name>(.*?)</name>", rom )
                romfilename = re.findall( "<filename>(.*?)</filename>", rom )
                romthumb = re.findall( "<thumb>(.*?)</thumb>", rom )
                romfanart = re.findall( "<fanart>(.*?)</fanart>", rom )
                romtrailer = re.findall( "<trailer>(.*?)</trailer>", rom )
                romcustom = re.findall( "<custom>(.*?)</custom>", rom )
                romgenre = re.findall( "<genre>(.*?)</genre>", rom )
                romrelease = re.findall( "<release>(.*?)</release>", rom )
                romstudio = re.findall( "<publisher>(.*?)</publisher>", rom )
                romplot = re.findall( "<gameplot>(.*?)</gameplot>", rom )
                romfinished = re.findall( "<finished>(.*?)</finished>", rom )
                romgamesys = gamesys

                if len(romid) > 0 : romid = romid[0]
                else:
                    romid = _get_SID()
                    need_update = 1
                if len(romname) > 0 : romname = romname[0]
                else: romname = "unknown"
                if len(romfilename) > 0 : romfilename = romfilename[0]
                else: romfilename = ""
                if len(romthumb) > 0 : romthumb = romthumb[0]
                else: romthumb = ""
                if len(romfanart) > 0 : romfanart = romfanart[0]
                else: romfanart = ""
                if len(romtrailer) > 0 : romtrailer = romtrailer[0]
                else: romtrailer = ""
                if len(romcustom) > 0 : romcustom = romcustom[0]
                else: romcustom = ""
                if len(romgenre) > 0 : romgenre = romgenre[0]
                else: romgenre = ""
                if len(romrelease) > 0 : romrelease = romrelease[0]
                else: romrelease = ""
                if len(romstudio) > 0 : romstudio = romstudio[0]
                else: romstudio = ""
                if len(romplot) > 0 : romplot = romplot[0]
                else: romplot = ""
                if len(romfinished) > 0 : romfinished = romfinished[0]
                else: romfinished = "false"

                # prepare rom object data
                romdata = {}
                romdata["name"] = romname
                romdata["filename"] = romfilename
                romdata["gamesys"] = romgamesys
                romdata["thumb"] = romthumb
                romdata["fanart"] = romfanart
                romdata["trailer"] = romtrailer
                romdata["custom"] = romcustom
                romdata["genre"] = romgenre
                romdata["release"] = romrelease
                romdata["studio"] = romstudio
                romdata["plot"] = romplot
                romdata["finished"] = romfinished

                # add rom to the roms list (using id as index)
                roms[romid] = romdata

            # prepare launcher object data
            launcherdata = {}
            launcherdata["name"] = name
            launcherdata["application"] = application
            launcherdata["args"] = args
            launcherdata["rompath"] = rompath
            launcherdata["thumbpath"] = thumbpath
            launcherdata["fanartpath"] = fanartpath
            launcherdata["trailerpath"] = trailerpath
            launcherdata["custompath"] = custompath
            launcherdata["romext"] = romext
            launcherdata["gamesys"] = gamesys
            launcherdata["thumb"] = thumb
            launcherdata["fanart"] = fanart
            launcherdata["genre"] = genre
            launcherdata["release"] = release
            launcherdata["studio"] = studio
            launcherdata["plot"] = plot
            launcherdata["finished"] = finished
            launcherdata["lnk"] = lnk
            launcherdata["minimize"] = minimize
            launcherdata["roms"] = roms

            # add launcher to the launchers list (using id as index)
            self.launchers[launcherid] = launcherdata

        if ( need_update == 1 ):
            self._save_launchers()

    def _get_launchers( self ):
        if (len(self.launchers) > 0):
            for key in sorted(self.launchers, key= lambda x : self.launchers[x]["application"]):
                self._add_launcher(self.launchers[key]["name"], self.launchers[key]["application"], self.launchers[key]["rompath"], self.launchers[key]["thumbpath"], self.launchers[key]["fanartpath"], self.launchers[key]["trailerpath"], self.launchers[key]["custompath"], self.launchers[key]["romext"], self.launchers[key]["gamesys"], self.launchers[key]["thumb"], self.launchers[key]["fanart"], self.launchers[key]["genre"], self.launchers[key]["release"], self.launchers[key]["studio"], self.launchers[key]["plot"], self.launchers[key]["finished"], self.launchers[key]["lnk"], self.launchers[key]["minimize"], self.launchers[key]["roms"], len(self.launchers), key)
            xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True, cacheToDisc=False )
            return True
        else:
            return False

    def _get_roms( self, launcherID ):
        if (self.launchers.has_key(launcherID)):
            selectedLauncher = self.launchers[launcherID]
            # error 
            roms = selectedLauncher["roms"]
            if (len(roms) > 0) :
                for key in sorted(roms, key= lambda x : roms[x]["filename"]):
                    if (roms[key]["fanart"] ==""):
                        defined_fanart = selectedLauncher["fanart"]
                    else:
                        defined_fanart = roms[key]["fanart"]
                    self._add_rom(launcherID, roms[key]["name"], roms[key]["filename"], roms[key]["gamesys"], roms[key]["thumb"], defined_fanart, roms[key]["trailer"], roms[key]["custom"], roms[key]["genre"], roms[key]["release"], roms[key]["studio"], roms[key]["plot"], roms[key]["finished"], len(roms), key)
                xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True, cacheToDisc=False )
                return True
            else:
                return False
        else:
            return False

    def _report_hook( self, count, blocksize, totalsize ):
         percent = int( float( count * blocksize * 100) / totalsize )
         msg1 = __language__( 30033 )  % ( os.path.split( self.url )[ 1 ], )
         pDialog.update( percent, msg1 )
         if ( pDialog.iscanceled() ): raise

    def _import_roms(self, launcherID, addRoms = False):
        dialog = xbmcgui.Dialog()
        romsCount = 0
        filesCount = 0
        skipCount = 0
        selectedLauncher = self.launchers[launcherID]
        pDialog = xbmcgui.DialogProgress()
        app = selectedLauncher["application"]
        path = selectedLauncher["rompath"]
        exts = selectedLauncher["romext"]
        roms = selectedLauncher["roms"]
        self._print_log(__language__( 30701 ) % selectedLauncher["name"]) 
        self._print_log(__language__( 30105 )) 
        # Get game system, thumbnails and fanarts paths from launcher
        thumb_path = selectedLauncher["thumbpath"]
        fanart_path = selectedLauncher["fanartpath"]
        trailer_path = selectedLauncher["trailerpath"]
        custom_path = selectedLauncher["custompath"]
        gamesys = selectedLauncher["gamesys"]

        #remove dead entries
        if (len(roms) > 0):
            self._print_log(__language__( 30717 ) % len(roms))
            self._print_log(__language__( 30718 ))
            i = 0
            removedRoms = 0
            ret = pDialog.create(__language__( 30000 ), __language__( 30501 ) % (path))

            for key in sorted(roms.iterkeys()):
                self._print_log(__language__( 30719 ) % roms[key]["filename"] )
                pDialog.update(i * 100 / len(roms))
                i += 1
                if (not os.path.isfile(roms[key]["filename"])):
                    self._print_log(__language__( 30716 ))
                    self._print_log(__language__( 30720 ) % roms[key]["filename"] )
                    del roms[key]
                    removedRoms += 1
                else:
                    self._print_log(__language__( 30715 ))

            pDialog.close()
            if not (removedRoms == 0):
                self._print_log(__language__( 30502 ) % removedRoms)
                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30502 ) % removedRoms))
            else:
                self._print_log(__language__( 30721 ))
                
        else:
            self._print_log(__language__( 30722 ))

        self._print_log(__language__( 30014 ) % path)
        ret = pDialog.create(__language__( 30000 ), __language__( 30014 ) % path)

        files = []
        if ( self.settings[ "recursive_scan" ] ):
            self._print_log(__language__( 30723 ))
            for root, dirs, filess in os.walk(path):
                for filename in fnmatch.filter(filess, '*.*'):
                    files.append(os.path.join(root, filename))
        else:
            self._print_log(__language__( 30724 ))
            filesname = os.listdir(path)
            for filename in filesname:
                files.append(os.path.join(path, filename))

        for fullname in files:
            f = os.path.basename(fullname)
            thumb = ""
            fanart = ""
            if ( self.settings[ "datas_method" ] == "0" ):
                import_text = __language__( 30062 ) % (f.replace("."+f.split(".")[-1],""))
            if ( self.settings[ "datas_method" ] == "1" ):
                import_text = __language__( 30061 ) % (f.replace("."+f.split(".")[-1],""),__language__( 30167 ))
            if ( self.settings[ "datas_method" ] == "2" ):
                import_text = __language__( 30061 ) % (f.replace("."+f.split(".")[-1],""),self.settings[ "datas_scraper" ].encode('utf-8','ignore'))
            pDialog.update(filesCount * 100 / len(files), import_text)
            self._print_log(__language__( 30725 ) % fullname)
            for ext in exts.split("|"):
                romadded = False
                if f.upper().endswith("." + ext.upper()):
                    self._print_log(__language__( 30726 ) % ext.upper()) 
                    foundromfile = False
                    for g in roms:
                        if ( roms[g]["filename"] == fullname ):
                            self._print_log(__language__( 30727 )) 
                            foundromfile = True
                    ext3s = ['.cd', '-cd', '_cd', ' cd']
                    for ext3 in ext3s:
                       for nums in range(2, 9):
                           if ( f.lower().find(ext3 + str(nums)) > 0 ):
                               self._print_log(__language__( 30728 )) 
                               foundromfile = True
                    # Ignore MAME bios roms
                    romname = f[:-len(ext)-1]
                    romname = romname.replace('.',' ')
                    if ( app.lower().find('mame') > 0 ) or ( self.settings[ "thumbs_scraper" ] == 'arcadeHITS' ):
                        if ( self.settings["ignore_bios"] ):
                            if ( self._test_bios_file(romname)):
                                self._print_log(__language__( 30729 )) 
                                foundromfile = True
                    if ( foundromfile == False ):
                        self._print_log(__language__( 30730 )) 
                        # prepare rom object data
                        romdata = {}
                        results = []
                        # Romname conversion if MAME
                        if ( app.lower().find('mame') > 0 ) or ( self.settings[ "thumbs_scraper" ] == 'arcadeHITS' ):
                            romname = self._get_mame_title(romname)
                        # Clean multi-cd Title Name
                        ext3s = ['.cd1', '-cd1', '_cd1', ' cd1']
                        for ext3 in ext3s:
                            if ( romname.lower().find(ext3) > 0 ):
                               romname = romname[:-len(ext3)]
                        romdata["filename"] = fullname
                        romdata["gamesys"] = gamesys
                        romdata["trailer"] = ""
                        romdata["custom"] = custom_path
                        romdata["genre"] = ""
                        romdata["release"] = ""
                        romdata["studio"] = ""
                        romdata["plot"] = ""
                        romdata["finished"] = "false"

                        self._print_log(import_text) 
                        self._print_log(__language__( 30732 ) % romname) 
                        # Search game title from scrapers
                        if ( self.settings[ "datas_method" ] == "1" ):
                            nfo_file=os.path.splitext(romdata["filename"])[0]+".nfo"
                            self._print_log(__language__( 30719 ) % nfo_file) 
                            if (os.path.isfile(nfo_file)):
                                self._print_log(__language__( 30715 )) 
                                self._print_log(__language__( 30733 ) % nfo_file) 
                                ff = open(nfo_file, 'r')
                                item_nfo = ff.read().replace('\r','').replace('\n','')
                                item_title = re.findall( "<title>(.*?)</title>", item_nfo )
                                item_platform = re.findall( "<platform>(.*?)</platform>", item_nfo )
                                item_year = re.findall( "<year>(.*?)</year>", item_nfo )
                                item_publisher = re.findall( "<publisher>(.*?)</publisher>", item_nfo )
                                item_genre = re.findall( "<genre>(.*?)</genre>", item_nfo )
                                item_plot = re.findall( "<plot>(.*?)</plot>", item_nfo )
                                if len(item_title) > 0 : romdata["name"] = item_title[0].rstrip()
                                romdata["gamesys"] = romdata["gamesys"]
                                if len(item_year) > 0 :  romdata["release"] = item_year[0]
                                if len(item_publisher) > 0 : romdata["studio"] = item_publisher[0]
                                if len(item_genre) > 0 : romdata["genre"] = item_genre[0]
                                if len(item_plot) > 0 : romdata["plot"] = item_plot[0].replace('&quot;','"')
                                ff.close()
                            else:
                                self._print_log(__language__( 30726 )) 
                                romdata["name"] = title_format(self,romname)
                                self._print_log(__language__( 30734 )) 
                        else:
                            if ( self.settings[ "datas_method" ] != "0" ):
                                romdata["name"] = clean_filename(romname)
                                if ( app.lower().find('mame') > 0 ) or ( self.settings[ "datas_scraper" ] == 'arcadeHITS' ):
                                    self._print_log(__language__( 30735 )) 
                                    results = self._get_first_game(f[:-len(ext)-1],gamesys)
                                    selectgame = 0
                                else:
                                    if ( self.settings[ "scrap_info" ] == "1" ):
                                        self._print_log(__language__( 30736 )) 
                                        results = self._get_first_game(romdata["name"],gamesys)
                                        selectgame = 0
                                    else:
                                        self._print_log(__language__( 30737 )) 
                                        results,display = self._get_games_list(romdata["name"])
                                        if display:
                                            # Display corresponding game list found
                                            dialog = xbmcgui.Dialog()
                                            # Game selection
                                            selectgame = dialog.select(__language__( 30078 ) % ( self.settings[ "datas_scraper" ] ), display)
                                            if (selectgame == -1):
                                                results = []
                                if results:
                                    foundname = results[selectgame]["title"]
                                    if (foundname != ""):
                                        if ( self.settings[ "ignore_title" ] ):
                                            romdata["name"] = title_format(self,romname)
                                        else:
                                            romdata["name"] = title_format(self,foundname)

                                        # Game other game data
                                        gamedata = self._get_game_data(results[selectgame])
                                        romdata["genre"] = gamedata["genre"]
                                        romdata["release"] = gamedata["release"]
                                        romdata["studio"] = gamedata["studio"]
                                        romdata["plot"] = gamedata["plot"]
                                        progress_display = romdata["name"] + " (" + romdata["release"] + ")"
                                    else:
                                        progress_display = romname + ": " +__language__( 30503 )
                                else:
                                    romdata["name"] = title_format(self,romname)
                                    progress_display = romname + ": " +__language__( 30503 )
                            else:
                                self._print_log(__language__( 30738 )) 
                                romdata["name"] = title_format(self,romname)

                        # Search if thumbnails and fanarts already exist
                        self._print_log(__language__( 30704 ) % fullname )
                        if ( thumb_path == fanart_path ):
                            self._print_log(__language__( 30705 ))
                        else:
                            self._print_log(__language__( 30706 ))
                        if ( thumb_path == path ):
                            self._print_log(__language__( 30707 ))
                        else:
                            self._print_log(__language__( 30708 ))
                        if ( fanart_path == path ):
                            self._print_log(__language__( 30709 ))
                        else:
                            self._print_log(__language__( 30710 ))
                            
                        ext2s = ['png', 'jpg', 'gif', 'jpeg', 'bmp', 'PNG', 'JPG', 'GIF', 'JPEG', 'BMP']
                        for ext2 in ext2s:
                            if ( thumb_path == fanart_path ):
                                if ( thumb_path == path ):
                                    test_thumb = fullname.replace('.'+ext, '_thumb.'+ext2)
                                else:
                                    test_thumb = os.path.join(thumb_path, f.replace('.'+ext, '_thumb.'+ext2))
                                if ( fanart_path == path ):
                                    test_fanart = fullname.replace('.'+ext, '_fanart.'+ext2)
                                else:
                                    test_fanart = os.path.join(fanart_path, f.replace('.'+ext, '_fanart.'+ext2))
                            else:
                                if ( thumb_path == path ):
                                    test_thumb = fullname.replace('.'+ext, '.'+ext2)
                                else:
                                    test_thumb = os.path.join(thumb_path, f.replace('.'+ext, '.'+ext2))
                                if ( fanart_path == path ):
                                    test_fanart = fullname.replace('.'+ext, '.'+ext2)
                                else:
                                    test_fanart = os.path.join(fanart_path, f.replace('.'+ext, '.'+ext2))
                            self._print_log(__language__( 30711 ) % test_thumb)
                            if ( os.path.isfile(test_thumb) ):
                                thumb = test_thumb
                                self._print_log(__language__( 30715 ))
                            else:
                                self._print_log(__language__( 30716 ))
                            self._print_log(__language__( 30712 ) % test_fanart)
                            if ( os.path.isfile(test_fanart) ):
                                fanart = test_fanart
                                self._print_log(__language__( 30715 ))
                            else:
                                self._print_log(__language__( 30716 ))

                        self._print_log(__language__( 30713 ) % thumb)
                        self._print_log(__language__( 30714 ) % fanart)

                        title = os.path.basename(romdata["filename"]).split(".")[0]
                        
                        if ( self.settings[ "thumbs_method" ] == "2" ):
                            # If overwrite is activated or thumb file not exist
                            if ( self.settings[ "overwrite_thumbs"] ) or ( thumb == "" ):
                                pDialog.update(filesCount * 100 / len(files), __language__( 30065 ) % (f.replace("."+f.split(".")[-1],""),self.settings[ "thumbs_scraper" ].encode('utf-8','ignore')))
                                img_url=""
                                if (thumb_path == fanart_path):
                                    if (thumb_path == path):
                                        thumb = fullname.replace("."+f.split(".")[-1], '_thumb.jpg')
                                    else:
                                        thumb = os.path.join(thumb_path, f.replace("."+f.split(".")[-1], '_thumb.jpg'))
                                else:
                                    if (thumb_path == path):
                                        thumb = fullname.replace("."+f.split(".")[-1], '.jpg')
                                    else:
                                        thumb = os.path.join(thumb_path, f.replace("."+f.split(".")[-1], '.jpg'))
                                if ( app.lower().find('mame') > 0 ) or ( self.settings[ "thumbs_scraper" ] == 'arcadeHITS' ):
                                    covers = self._get_thumbnails_list(romdata["gamesys"],title,self.settings[ "game_region" ],self.settings[ "thumb_image_size" ])
                                else:
                                    covers = self._get_thumbnails_list(romdata["gamesys"],romdata["name"],self.settings[ "game_region" ],self.settings[ "thumb_image_size" ])
                                if covers:
                                    if ( self.settings[ "scrap_thumbs" ] == "1" ):
                                        if ( self.settings[ "snap_flyer" ] == "1" ) and ( self.settings[ "thumbs_scraper" ] == 'arcadeHITS' ):
                                            img_url = self._get_thumbnail(covers[-1][0])
                                        else:
                                            img_url = self._get_thumbnail(covers[0][0])
                                    else:
                                        nb_images = len(covers)
                                        pDialog.close()
                                        self.image_url = MyDialog(covers)
                                        if ( self.image_url ):
                                            img_url = self._get_thumbnail(self.image_url)
                                            ret = pDialog.create(__language__( 30000 ), __language__( 30014 ) % (path))
                                            pDialog.update(filesCount * 100 / len(files), __language__( 30061 ) % (f.replace("."+f.split(".")[-1],""),self.settings[ "datas_scraper" ].encode('utf-8','ignore')))
                                    cached_thumb = thumbnails.get_cached_covers_thumb( thumb ).replace("tbn" , "jpg")
                                    if ( img_url !='' ):
                                        try:
                                            urllib.URLopener.version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'
                                            h = urllib.urlretrieve(img_url,thumb)
                                            shutil.copy2( thumb.decode(sys.getfilesystemencoding(),'ignore') , cached_thumb.decode(sys.getfilesystemencoding(),'ignore') )
                                        except socket.timeout:
                                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30604 )))
                                        except exceptions.IOError:
                                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30654 )))
                                    else:
                                        if ( not os.path.isfile(thumb) ) & ( os.path.isfile(cached_thumb) ):
                                            os.remove(cached_thumb)
                            romdata["thumb"] = thumb
                        else :
                            if ( self.settings[ "thumbs_method" ] == "0" ):
                                romdata["thumb"] = ""
                            else:
                                pDialog.update(filesCount * 100 / len(files), __language__( 30065 ) % (f.replace("."+f.split(".")[-1],""),__language__( 30172 )))
                                romdata["thumb"] = thumb

                        if ( self.settings[ "fanarts_method" ] == "2" ):
                            # If overwrite activated or fanart file not exist
                            if ( self.settings[ "overwrite_fanarts"] ) or ( fanart == "" ):
                                pDialog.update(filesCount * 100 / len(files), __language__( 30071 ) % (f.replace("."+f.split(".")[-1],""),self.settings[ "fanarts_scraper" ].encode('utf-8','ignore')))
                                img_url=""
                                if (fanart_path == thumb_path):
                                    if (fanart_path == path):
                                        fanart = fullname.replace("."+f.split(".")[-1], '_fanart.jpg')
                                    else:
                                        fanart = os.path.join(fanart_path, f.replace("."+f.split(".")[-1], '_fanart.jpg'))
                                else:
                                    if (fanart_path == path):
                                        fanart = fullname.replace("."+f.split(".")[-1], '.jpg')
                                    else:
                                        fanart = os.path.join(fanart_path, f.replace("."+f.split(".")[-1], '.jpg'))
                                if ( app.lower().find('mame') > 0 ) or ( self.settings[ "fanarts_scraper" ] == 'arcadeHITS' ):
                                    covers = self._get_fanarts_list(romdata["gamesys"],title,self.settings[ "fanart_image_size" ])
                                else:
                                    covers = self._get_fanarts_list(romdata["gamesys"],romdata["name"],self.settings[ "fanart_image_size" ])
                                if covers:
                                    if ( self.settings[ "scrap_fanarts" ] == "1" ):
                                        if ( self.settings[ "select_fanarts" ] == "0" ):
                                            img_url = self._get_fanart(covers[0][0])
                                        if ( self.settings[ "select_fanarts" ] == "1" ):
                                            img_url = self._get_fanart(covers[int(round(len(covers)/2))-1][0])
                                        if ( self.settings[ "select_fanarts" ] == "2" ):
                                            img_url = self._get_fanart(covers[len(covers)-1][0])
                                    else:
                                        nb_images = len(covers)
                                        pDialog.close()
                                        self.image_url = MyDialog(covers)
                                        if ( self.image_url ):
                                            img_url = self._get_fanart(self.image_url)
                                            ret = pDialog.create(__language__( 30000 ), __language__( 30014 ) % (path))
                                            pDialog.update(filesCount * 100 / len(files), __language__( 30061 ) % (f.replace("."+f.split(".")[-1],""),self.settings[ "datas_scraper" ].encode('utf-8','ignore')))
                                    cached_thumb = thumbnails.get_cached_covers_thumb( fanart ).replace("tbn" , "jpg")
                                    if ( img_url !='' ):
                                        try:
                                            urllib.URLopener.version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'
                                            h = urllib.urlretrieve(img_url,fanart)
                                            shutil.copy2( fanart.decode(sys.getfilesystemencoding(),'ignore') , cached_thumb.decode(sys.getfilesystemencoding(),'ignore') )
                                        except socket.timeout:
                                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30606 )))
                                        except exceptions.IOError:
                                            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30607 )))
                                    else:
                                        if ( not os.path.isfile(fanart) ) & ( os.path.isfile(cached_thumb) ):
                                            os.remove(cached_thumb)
                            romdata["fanart"] = fanart
                        else :
                            if ( self.settings[ "fanarts_method" ] == "0" ):
                                romdata["fanart"] = ""
                            else:
                                pDialog.update(filesCount * 100 / len(files), __language__( 30071 ) % (f.replace("."+f.split(".")[-1],""),__language__( 30172 )))
                                romdata["fanart"] = fanart

                        # add rom to the roms list (using name as index)
                        romid = _get_SID()
                        roms[romid] = romdata
                        romsCount = romsCount + 1

                        if (addRoms):
                            self._add_rom(launcherID, romdata["name"], romdata["filename"], romdata["gamesys"], romdata["thumb"], romdata["fanart"], romdata["trailer"], romdata["custom"], romdata["genre"], romdata["release"], romdata["studio"], romdata["plot"], romdata["finished"], len(files), key)
                            romadded = True
            if not romadded:
                self._print_log(__language__( 30731 )) 
                skipCount = skipCount + 1

            filesCount = filesCount + 1
            self._save_launchers()

        if ( self.settings[ "scrap_info" ] != "0" ):
            pDialog.close()

        if (skipCount == 0):
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30015 ) % (romsCount) + " " + __language__( 30050 )))
            xbmc.executebuiltin("XBMC.ReloadSkin()")
        else:
            xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30016 ) % (romsCount, skipCount) + " " + __language__( 30050 )))

    def _add_launcher(self, name, cmd, path, thumbpath, fanartpath, trailerpath, custompath, ext, gamesys, thumb, fanart, genre, release, studio, plot, finished, lnk, minimize, roms, total, key) :
        if (int(xbmc.getInfoLabel("System.BuildVersion")[0:2]) < 12 ):
            # Dharma / Eden compatible
            display_date_format = "Date"
        else:
            # Frodo & + compatible
            display_date_format = "Year"
        commands = []
        commands.append((__language__( 30512 ), "XBMC.RunPlugin(%s?%s)"    % (self._path, SEARCH_COMMAND) , ))
        commands.append((__language__( 30051 ), "XBMC.RunPlugin(%s?%s)"    % (self._path, FILE_MANAGER_COMMAND) , ))
        commands.append((__language__( 30101 ), "XBMC.RunPlugin(%s?%s)" % (self._path, ADD_COMMAND) , ))
        commands.append(( __language__( 30109 ), "XBMC.RunPlugin(%s?%s/%s)" % (self._path, key, EDIT_COMMAND) , ))

        if (path == ""):
            folder = False
            icon = "DefaultProgram.png"
        else:
            folder = True
            icon = "DefaultFolder.png"
            commands.append((__language__( 30106 ), "XBMC.RunPlugin(%s?%s/%s)" % (self._path, key, ADD_COMMAND) , ))

        if (thumb):
            listitem = xbmcgui.ListItem( name, iconImage=icon, thumbnailImage=thumb )
        else:
            listitem = xbmcgui.ListItem( name, iconImage=icon )

        filename = os.path.splitext(cmd)
        if ( finished == "false" ):
            ICON_OVERLAY = 6
        else:
            ICON_OVERLAY = 7
        listitem.setProperty("fanart_image", fanart)
        listitem.setInfo( "video", { "Title": name, "Label": os.path.basename(cmd), "Plot" : plot , "Studio" : studio , "Genre" : genre , "Premiered" : release  , display_date_format : release  , "Writer" : gamesys , "Trailer" : os.path.join(trailerpath), "Director" : os.path.join(custompath), "overlay": ICON_OVERLAY } )
        listitem.addContextMenuItems( commands )
        if ( finished == "false" ) or ( self.settings[ "hide_finished" ] == False) :
            if (len(roms) > 0) :
                xbmcplugin.addDirectoryItem( handle=int( self._handle ), url="%s?%s"  % (self._path, key), listitem=listitem, isFolder=True)
            else:
                xbmcplugin.addDirectoryItem( handle=int( self._handle ), url="%s?%s"  % (self._path, key), listitem=listitem, isFolder=False)

    def _add_rom( self, launcherID, name, cmd , romgamesys, thumb, romfanart, romtrailer, romcustom, romgenre, romrelease, romstudio, romplot, finished, total, key):
        if (int(xbmc.getInfoLabel("System.BuildVersion")[0:2]) < 12 ):
            # Dharma / Eden compatible
            display_date_format = "Date"
        else:
            # Frodo & + compatible
            display_date_format = "Year"
        filename = os.path.splitext(cmd)
        icon = "DefaultProgram.png"
        if (thumb):
            listitem = xbmcgui.ListItem( name, iconImage=icon, thumbnailImage=thumb)
        else:
            listitem = xbmcgui.ListItem( name, iconImage=icon)
        if ( finished == "false" ):
            ICON_OVERLAY = 6
        else:
            ICON_OVERLAY = 7
        listitem.setProperty("fanart_image", romfanart)
        listitem.setInfo( "video", { "Title": name, "Label": os.path.basename(cmd), "Plot" : romplot, "Studio" : romstudio, "Genre" : romgenre, "Premiered" : romrelease  , display_date_format : romrelease, "Writer" : romgamesys, "Trailer" : os.path.join(romtrailer), "Director" : os.path.join(romcustom), "overlay": ICON_OVERLAY } )

        commands = []
        commands.append((__language__( 30512 ), "XBMC.RunPlugin(%s?%s)"    % (self._path, SEARCH_COMMAND) , ))
        commands.append(( __language__( 30107 ), "XBMC.RunPlugin(%s?%s/%s/%s)" % (self._path, launcherID, key, EDIT_COMMAND) , ))
        listitem.addContextMenuItems( commands )
        if ( finished == "false" ) or ( self.settings[ "hide_finished" ] == False) :
            xbmcplugin.addDirectoryItem( handle=int( self._handle ), url="%s?%s/%s"  % (self._path, launcherID, key), listitem=listitem, isFolder=False)

    def _add_new_rom ( self , launcherID) :
        dialog = xbmcgui.Dialog()
        launcher = self.launchers[launcherID]
        app = launcher["application"]
        ext = launcher["romext"]
        roms = launcher["roms"]
        rompath = launcher["rompath"]
        romgamesys = launcher["gamesys"]
        thumb_path = launcher["thumbpath"]
        fanart_path = launcher["fanartpath"]
        trailer_path = launcher["trailerpath"]
        custom_path = launcher["custompath"]

        romfile = dialog.browse(1, __language__( 30017 ),"files", "."+ext.replace("|","|."), False, False, rompath)
        if (romfile):
            title=os.path.basename(romfile)
            keyboard = xbmc.Keyboard(title.replace('.'+title.split('.')[-1],'').replace('.',' '), __language__( 30018 ))
            keyboard.doModal()
            if (keyboard.isConfirmed()):
                title = keyboard.getText()
                if ( title == "" ):
                    title = os.path.basename(romfile)
                    title = title.replace('.'+title.split('.')[-1],'').replace('.',' ')
                # prepare rom object data
                romdata = {}
                # Romname conversion if MAME
                if ( app.lower().find('mame') > 0 ):
                    romname = self._get_mame_title(title)
                    romdata["name"] = title_format(self,romname)
                else:
                    romdata["name"] = title_format(self,title)
                romdata["filename"] = romfile
                romdata["gamesys"] = romgamesys
                romdata["thumb"] = ""
                romdata["fanart"] = ""
                # Search for default thumbnails and fanart images path
                ext2s = ['png', 'jpg', 'gif', 'jpeg', 'bmp', 'PNG', 'JPG', 'GIF', 'JPEG', 'BMP']
                f = os.path.basename(romfile)
                for ext2 in ext2s:
                    if (thumb_path == fanart_path) :
                        if (thumb_path == rompath) :
                            if (os.path.isfile(os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '_thumb.'+ext2)))):
                                romdata["thumb"] = os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '_thumb.'+ext2))
                        else:
                            if (os.path.isfile(os.path.join(thumb_path, f.replace("."+f.split(".")[-1], '_thumb.'+ext2)))):
                                romdata["thumb"] = os.path.join(thumb_path, f.replace("."+f.split(".")[-1], '_thumb.'+ext2))
                    else:
                        if (thumb_path == "") :
                            romdata["thumb"] = os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '_thumb.jpg'))
                        else:
                            if (thumb_path == rompath) :
                                if (os.path.isfile(os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '.'+ext2)))):
                                    romdata["thumb"] = os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '.'+ext2))
                            else:
                                if (os.path.isfile(os.path.join(thumb_path, f.replace("."+f.split(".")[-1], '.'+ext2)))):
                                    romdata["thumb"] = os.path.join(thumb_path, f.replace("."+f.split(".")[-1], '.'+ext2))

                    if (fanart_path == thumb_path) :
                        if (fanart_path == rompath) :
                            if (os.path.isfile(os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '_fanart.'+ext2)))):
                                romdata["fanart"] = os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '_fanart.'+ext2))
                        else:
                            if (os.path.isfile(os.path.join(fanart_path, f.replace("."+f.split(".")[-1], '_fanart.'+ext2)))):
                                romdata["fanart"] = os.path.join(fanart_path, f.replace("."+f.split(".")[-1], '_fanart.'+ext2))
                    else:
                        if (fanart_path == "") :
                            romdata["fanart"] = os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '_fanart.jpg'))
                        else:
                            if (fanart_path == rompath) :
                                if (os.path.isfile(os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '.'+ext2)))):
                                   romdata["fanart"] = os.path.join(os.path.dirname(romfile), f.replace("."+f.split(".")[-1], '.'+ext2))
                            else:
                                if (os.path.isfile(os.path.join(fanart_path, f.replace("."+f.split(".")[-1], '.'+ext2)))):
                                    romdata["fanart"] = os.path.join(fanart_path, f.replace("."+f.split(".")[-1], '.'+ext2))
                romdata["custom"] = custom_path
                romdata["trailer"] = ""
                romdata["genre"] = ""
                romdata["release"] = ""
                romdata["studio"] = ""
                romdata["plot"] = ""
                romdata["finished"] = "false"

                # add rom to the roms list (using name as index)
                romid = _get_SID()
                roms[romid] = romdata

                xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30019 ) + " " + __language__( 30050 )))

        self._save_launchers()

    def _add_new_launcher ( self ) :
        dialog = xbmcgui.Dialog()
        type = dialog.select(__language__( 30101 ), [__language__( 30021 ), __language__( 30022 ),__language__( 30051 )])
        if (os.environ.get( "OS", "xbox" ) == "xbox"):
            filter = ".xbe|.cut"
        else:
            if (sys.platform == "win32"):
                filter = ".bat|.exe|.cmd|.lnk"
            else:
                filter = ""

        if (type == 0):
            app = xbmcgui.Dialog().browse(1,__language__( 30023 ),"files",filter)
            if (app):
                argument = self._get_program_arguments(os.path.basename(app))
                argkeyboard = xbmc.Keyboard(argument, __language__( 30024 ))
                argkeyboard.doModal()
                args = argkeyboard.getText()
                title = os.path.basename(app)
                keyboard = xbmc.Keyboard(title.replace('.'+title.split('.')[-1],'').replace('.',' '), __language__( 30025 ))
                keyboard.doModal()
                title = keyboard.getText()
                if ( title == "" ):
                    title = os.path.basename(app)
                    title = title.replace('.'+title.split('.')[-1],'').replace('.',' ')
                # Selection of the launcher game system
                dialog = xbmcgui.Dialog()
                platforms = _get_game_system_list()
                gamesystem = dialog.select(__language__( 30077 ), platforms)
                # Selection of the thumbnails and fanarts path
                if ( self.settings[ "launcher_thumb_path" ] == "" ):
                    thumb_path = xbmcgui.Dialog().browse(0,__language__( 30059 ),"files","", False, False)
                else:
                    thumb_path = self.settings[ "launcher_thumb_path" ]
                if ( self.settings[ "launcher_fanart_path" ] == "" ):
                    fanart_path = xbmcgui.Dialog().browse(0,__language__( 30060 ),"files","", False, False)
                else:
                    fanart_path = self.settings[ "launcher_fanart_path" ]
                # prepare launcher object data
                launcherdata = {}
                launcherdata["name"] = title
                launcherdata["application"] = app
                launcherdata["args"] = args
                launcherdata["rompath"] = ""
                if (thumb_path):
                    launcherdata["thumbpath"] = thumb_path
                else:
                    launcherdata["thumbpath"] = ""
                if (fanart_path):
                    launcherdata["fanartpath"] = fanart_path
                else:
                    launcherdata["fanartpath"] = ""
                launcherdata["custompath"] = ""
                launcherdata["trailerpath"] = ""
                launcherdata["romext"] = ""
                if (not gamesystem == -1 ):
                    launcherdata["gamesys"] = platforms[gamesystem]
                else:
                    launcherdata["gamesys"] = ""
                launcherdata["thumb"] = ""
                launcherdata["fanart"] = ""
                launcherdata["genre"] = ""
                launcherdata["release"] = ""
                launcherdata["studio"] = ""
                launcherdata["plot"] = ""
                launcherdata["finished"] = "false"
                if (sys.platform == "win32"):
                    launcherdata["lnk"] = "true"
                else:
                    launcherdata["lnk"] = ""
                launcherdata["minimize"] = "false"
                launcherdata["roms"] = {}

                # add launcher to the launchers list (using name as index)
                launcherid = _get_SID()
                self.launchers[launcherid] = launcherdata
                self._save_launchers()

                xbmc.executebuiltin("Container.Update")
                return True

        if (type == 1):
            app = xbmcgui.Dialog().browse(1,__language__( 30023 ),"files",filter)
            if (app):
                path = xbmcgui.Dialog().browse(0,__language__( 30058 ),"files", "", False, False)
                if (path):
                    extensions = self._get_program_extensions(os.path.basename(app))
                    extkey = xbmc.Keyboard(extensions, __language__( 30028 ))
                    extkey.doModal()
                    if (extkey.isConfirmed()):
                        ext = extkey.getText()
                        argument = self._get_program_arguments(os.path.basename(app))
                        argkeyboard = xbmc.Keyboard(argument, __language__( 30024 ))
                        argkeyboard.doModal()
                        args = argkeyboard.getText()
                        title = os.path.basename(app)
                        keyboard = xbmc.Keyboard(title.replace('.'+title.split('.')[-1],'').replace('.',' '), __language__( 30025 ))
                        keyboard.doModal()
                        title = keyboard.getText()
                        if ( title == "" ):
                            title = os.path.basename(app)
                            title = title.replace('.'+title.split('.')[-1],'').replace('.',' ')
                        # Selection of the launcher game system
                        dialog = xbmcgui.Dialog()
                        platforms = _get_game_system_list()
                        gamesystem = dialog.select(__language__( 30077 ), platforms)
                        # Selection of the thumbnails and fanarts path
                        thumb_path = xbmcgui.Dialog().browse(0,__language__( 30059 ),"files","", False, False, os.path.join(path))
                        fanart_path = xbmcgui.Dialog().browse(0,__language__( 30060 ),"files","", False, False, os.path.join(path))
                        # prepare launcher object data
                        launcherdata = {}
                        launcherdata["name"] = title
                        launcherdata["application"] = app
                        launcherdata["args"] = args
                        launcherdata["rompath"] = path
                        if (thumb_path):
                            launcherdata["thumbpath"] = thumb_path
                        else:
                            launcherdata["thumbpath"] = ""
                        if (fanart_path):
                            launcherdata["fanartpath"] = fanart_path
                        else:
                            launcherdata["fanartpath"] = ""
                        launcherdata["custompath"] = ""
                        launcherdata["trailerpath"] = ""
                        launcherdata["romext"] = ext
                        if (not gamesystem == -1 ):
                            launcherdata["gamesys"] = platforms[gamesystem]
                        else:
                            launcherdata["gamesys"] = ""
                        launcherdata["thumb"] = ""
                        launcherdata["fanart"] = ""
                        launcherdata["genre"] = ""
                        launcherdata["release"] = ""
                        launcherdata["studio"] = ""
                        launcherdata["plot"] = ""
                        launcherdata["finished"] = "false"
                        if (sys.platform == "win32"):
                            launcherdata["lnk"] = "true"
                        else:
                            launcherdata["lnk"] = ""
                        launcherdata["minimize"] = "false"
                        launcherdata["roms"] = {}

                        # add launcher to the launchers list (using name as index)
                        launcherid = _get_SID()
                        self.launchers[launcherid] = launcherdata
                        self._save_launchers()
                        xbmc.executebuiltin("Container.Update")
                        return True
        if (type == 2):
            self._file_manager()

        return False

    def _file_manager( self ):
        xbmc.executebuiltin("ActivateWindow(filemanager)")

    def _find_roms( self ):
        dialog = xbmcgui.Dialog()
        type = dialog.select(__language__( 30400 ), [__language__( 30401 ),__language__( 30402 ),__language__( 30403 ),__language__( 30404 ),__language__( 30405 )])
        type_nb = 0

        #Search by Title
        if (type == type_nb ):
            keyboard = xbmc.Keyboard("", __language__( 30036 ))
            keyboard.doModal()
            if (keyboard.isConfirmed()):
                search = keyboard.getText()
                xbmc.executebuiltin("ReplaceWindow(Programs,%s?%s/%s)" % (self._path, search, SEARCH_COMMAND))

        #Search by Release Date
        type_nb = type_nb+1
        if (type == type_nb ):
            search = []
            search = _search_category(self,"release")
            dialog = xbmcgui.Dialog()
            selected = dialog.select(__language__( 30406 ), search)
            if (not selected == -1 ):
                xbmc.executebuiltin("ReplaceWindow(Programs,%s?%s/%s)" % (self._path, search[selected], SEARCH_DATE_COMMAND))

        #Search by System Platform
        type_nb = type_nb+1
        if (type == type_nb ):
            search = []
            search = _search_category(self,"gamesys")
            dialog = xbmcgui.Dialog()
            selected = dialog.select(__language__( 30407 ), search)
            if (not selected == -1 ):
                xbmc.executebuiltin("ReplaceWindow(Programs,%s?%s/%s)" % (self._path, search[selected], SEARCH_PLATFORM_COMMAND))

        #Search by Studio
        type_nb = type_nb+1
        if (type == type_nb ):
            search = []
            search = _search_category(self,"studio")
            dialog = xbmcgui.Dialog()
            selected = dialog.select(__language__( 30408 ), search)
            if (not selected == -1 ):
                xbmc.executebuiltin("ReplaceWindow(Programs,%s?%s/%s)" % (self._path, search[selected], SEARCH_STUDIO_COMMAND))

        #Search by Genre
        type_nb = type_nb+1
        if (type == type_nb ):
            search = []
            search = _search_category(self,"genre")
            dialog = xbmcgui.Dialog()
            selected = dialog.select(__language__( 30409 ), search)
            if (not selected == -1 ):
                xbmc.executebuiltin("ReplaceWindow(Programs,%s?%s/%s)" % (self._path, search[selected], SEARCH_GENRE_COMMAND))

    def _find_add_roms( self, search ):
        _find_category_roms( self, search, "name" )

    def _find_date_add_roms( self, search ):
        _find_category_roms( self, search, "release" )

    def _find_platform_add_roms( self, search ):
        _find_category_roms( self, search, "gamesys" )

    def _find_studio_add_roms( self, search ):
        _find_category_roms( self, search, "studio" )

    def _find_genre_add_roms( self, search ):
        _find_category_roms( self, search, "genre" )

class MainGui( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
        xbmc.executebuiltin( "Skin.Reset(AnimeWindowXMLDialogClose)" )
        xbmc.executebuiltin( "Skin.SetBool(AnimeWindowXMLDialogClose)" )
        self.listing = kwargs.get( "listing" )

    def onInit(self):
        try :
            self.img_list = self.getControl(6)
            self.img_list.controlLeft(self.img_list)
            self.img_list.controlRight(self.img_list)
            self.getControl(3).setVisible(False)
        except :
            print_exc()
            self.img_list = self.getControl(3)

        self.getControl(5).setVisible(False)

        for index, item in enumerate(self.listing):
            listitem = xbmcgui.ListItem( item[2] )
            listitem.setIconImage( item[1] )
            listitem.setLabel2( item[0] )
            
            self.img_list.addItem( listitem )
        self.setFocus(self.img_list)

    def onAction(self, action):
        #Close the script
        if action == 10 :
            self.close()

    def onClick(self, controlID):
        #action sur la liste
        if controlID == 6 or controlID == 3:
            #Renvoie l'item selectionne
            num = self.img_list.getSelectedPosition()
            self.selected_url = self.img_list.getSelectedItem().getLabel2()
            self.close()

    def onFocus(self, controlID):
        pass

def MyDialog(img_list):
    w = MainGui( "DialogSelect.xml", BASE_PATH, listing=img_list )
    w.doModal()
    try:
        return w.selected_url
    except:
        print_exc()
        return False
    del w
    
def _update_cache(file_path):
    cached_thumb = thumbnails.get_cached_covers_thumb( file_path ).replace("tbn" , os.path.splitext(file_path)[-1][1:4])
    try:
        shutil.copy2( file_path.decode(sys.getfilesystemencoding(),'ignore') , cached_thumb.decode(sys.getfilesystemencoding(),'ignore') )
    except OSError:
        xbmc.executebuiltin("XBMC.Notification(%s,%s, 3000)" % (__language__( 30000 ), __language__( 30608 )))
    xbmc.executebuiltin("XBMC.ReloadSkin()")

def title_format(self,title):
    if ( self.settings[ "clean_title" ] ):
       title = re.sub('\[.*?\]', '', title)
       title = re.sub('\(.*?\)', '', title)
       title = re.sub('\{.*?\}', '', title)
    new_title = title.rstrip()
    if ( self.settings[ "title_formating" ] ):
        if (title.startswith("The ")): new_title = title.replace("The ","",1)+", The"
        if (title.startswith("A ")): new_title = title.replace("A ","",1)+", A"
        if (title.startswith("An ")): new_title = title.replace("An ","",1)+", An"
    else:
        if (title.endswith(", The")): new_title = "The "+"".join(title.rsplit(", The",1))
        if (title.endswith(", A")): new_title = "A "+"".join(title.rsplit(", A",1))
        if (title.endswith(", An")): new_title = "An "+"".join(title.rsplit(", An",1))
    return new_title

def clean_filename(title):
    title = re.sub('\[.*?\]', '', title)
    title = re.sub('\(.*?\)', '', title)
    title = re.sub('\{.*?\}', '', title)
    title = title.replace('_',' ')
    title = title.replace('-',' ')
    title = title.replace(':',' ')
    title = title.replace('.',' ')
    title = title.rstrip()
    return title

def base_filename(filename):
    filename = re.sub('(\[.*?\]|\(.*?\)|\{.*?\})', '', filename)
    filename = re.sub('(\.|-| |_)cd\d+$', '', filename)
    return filename.rstrip()

def _toogle_fullscreen():
    try:
        # Dharma / Eden compatible
        xbmc.executehttpapi("Action(199)")
    except:
        # Frodo & + compatible
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"togglefullscreen"},"id":"1"}')

def _get_SID():
    t1 = time.time()
    t2 = t1 + random.getrandbits(32)
    try: 
        # Eden & + compatible
        base = hashlib.md5( str(t1 +t2) )
    except:
        # Dharma compatible
        base = md5.new( str(t1 +t2) )
    sid = base.hexdigest()
    return sid

def _get_game_system_list():
    platforms = []
    try:
        rootDir = __settings__.getAddonInfo('path')
        if rootDir[-1] == ';':rootDir = rootDir[0:-1]
        resDir = os.path.join(rootDir, 'resources')
        scrapDir = os.path.join(resDir, 'scrapers')
        csvfile = open( os.path.join(scrapDir, 'gamesys'), "rb")
        for line in csvfile.readlines():
            result = line.replace('\n', '').replace('"', '').split(',')
            platforms.append(result[0])
        platforms.sort()
        return platforms
    except:
        return platforms

def _search_category(self,category):
    search = []
    if (len(self.launchers) > 0):
        for key in sorted(self.launchers.iterkeys()):
            if (len(self.launchers[key]["roms"]) > 0) :
                for keyr in sorted(self.launchers[key]["roms"].iterkeys()):
                    if ( self.launchers[key]["roms"][keyr][category] == "" ):
                        search.append("[ %s ]" % __language__( 30410 ))
                    else:
                        search.append(self.launchers[key]["roms"][keyr][category])
    search = list(set(search))
    search.sort()
    return search

def _find_category_roms( self, search, category ):
    #sorted by name
    if (len(self.launchers) > 0):
        rl = {}
        for launcherID in sorted(self.launchers.iterkeys()):
            selectedLauncher = self.launchers[launcherID]
            roms = selectedLauncher["roms"]
            notset = ("[ %s ]" % __language__( 30410 ))
            text = search.lower()
            empty = notset.lower()
            if (len(roms) > 0) :
                #go through rom list and search for user input
                for keyr in sorted(roms.iterkeys()):
                    rom = roms[keyr][category].lower()
                    if (rom == "") and (text == empty):
                        rl[keyr] = roms[keyr]
                        rl[keyr]["launcherID"] = launcherID
                    if category == 'name':
                        if (not rom.find(text) == -1):
                            rl[keyr] = roms[keyr]
                            rl[keyr]["launcherID"] = launcherID
                    else:
                        if (rom == text):
                            rl[keyr] = roms[keyr]
                            rl[keyr]["launcherID"] = launcherID
    #print the list sorted
    for key in sorted(rl.iterkeys()):
        self._add_rom(rl[key]["launcherID"], rl[key]["name"], rl[key]["filename"], rl[key]["gamesys"], rl[key]["thumb"], rl[key]["fanart"], rl[key]["trailer"], rl[key]["custom"], rl[key]["genre"], rl[key]["release"], rl[key]["studio"], rl[key]["plot"], rl[key]["finished"], len(rl), key)
    xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True, cacheToDisc=False )
