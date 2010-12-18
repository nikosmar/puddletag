#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Contains objects used throughout puddletag"""

#puddleobjects.py

#Copyright (C) 2008-2009 concentricpuddle

#This file is part of puddletag, a semi-good music tag editor.

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU 12 Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys, os,pdb,shutil

from itertools import groupby # for unique function.
from bisect import bisect_left, insort_left # for unique function.
from copy import copy
import audioinfo
from audioinfo import (IMAGETYPES, DESCRIPTION, DATA, IMAGETYPE,
    encode_fn, decode_fn)
from operator import itemgetter
path = os.path
from configobj import ConfigObj
import traceback
import time, re
from glob import glob
from constants import ACTIONDIR
from PyQt4.QtCore import QFile, QIODevice
from StringIO import StringIO
import itertools

MSGARGS = (QMessageBox.Warning, QMessageBox.Yes or QMessageBox.Default,
    QMessageBox.No or QMessageBox.Escape, QMessageBox.YesAll)
from functools import partial

mod_keys = {
    Qt.ShiftModifier: u'Shift',
    Qt.MetaModifier: u'Meta',
    Qt.AltModifier: u'Alt',
    Qt.ControlModifier: u'Ctrl',
    Qt.NoModifier: u'',
    Qt.KeypadModifier: u'',
    Qt.GroupSwitchModifier: u'',}

def keycmp(a, b):
    if a == b:
        return 0
    if a == Qt.CTRL:
        return -1
    elif b == Qt.CTRL:
        return 1

    if a == Qt.SHIFT:
        return -1
    elif b == Qt.SHIFT:
        return 1

    if a == Qt.ALT:
        return -1
    elif b == Qt.ALT:
        return 1

    if a == Qt.META:
        return -1
    elif b == Qt.META:
        return 1

    return 0

modifiers = {}
for i in range(1,len(mod_keys)):
    for keys in set(itertools.permutations(mod_keys, i)):
        mod = keys[0]
        for key in keys[1:]:
            mod = mod | key
        modifiers[int(mod)] = u'+'.join(mod_keys[key] for key in sorted(keys, cmp=keycmp) if mod_keys[key])

mod_keys = set((Qt.Key_Shift, Qt.Key_Control, Qt.Key_Meta, Qt.Key_Alt))

imagetypes = [
    (unicode(QApplication.translate('Cover Type', 'Other')), unicode(QApplication.translate("Cover Type", 'O'))),
    (unicode(QApplication.translate('Cover Type', 'File Icon')), unicode(QApplication.translate("Cover Type", 'I'))),
    (unicode(QApplication.translate('Cover Type', 'Other File Icon')), unicode(QApplication.translate("Cover Type", 'OI'))),
    (unicode(QApplication.translate('Cover Type', 'Cover (front)')), unicode(QApplication.translate("Cover Type", 'CF'))),
    (unicode(QApplication.translate('Cover Type', 'Cover (back)')), unicode(QApplication.translate("Cover Type", 'CB'))),
    (unicode(QApplication.translate('Cover Type', 'Leaflet page')), unicode(QApplication.translate("Cover Type", 'LF'))),
    (unicode(QApplication.translate('Cover Type', 'Media (e.g. label side of CD)')), unicode(QApplication.translate("Cover Type", 'M'))),
    (unicode(QApplication.translate('Cover Type', 'Lead artist')), unicode(QApplication.translate("Cover Type", 'LA'))),
    (unicode(QApplication.translate('Cover Type', 'Artist')), unicode(QApplication.translate("Cover Type", 'A'))),
    (unicode(QApplication.translate('Cover Type', 'Conductor')), unicode(QApplication.translate("Cover Type", 'C'))),
    (unicode(QApplication.translate('Cover Type', 'Band')), unicode(QApplication.translate("Cover Type", 'B'))),
    (unicode(QApplication.translate("Cover Type", 'Composer')), unicode(QApplication.translate("Cover Type", 'CP'))),
    (unicode(QApplication.translate("Cover Type", 'Lyricist')), unicode(QApplication.translate("Cover Type", 'L'))),
    (unicode(QApplication.translate("Cover Type", 'Recording Location')), unicode(QApplication.translate("Cover Type", 'RL'))),
    (unicode(QApplication.translate("Cover Type", 'During recording')), unicode(QApplication.translate("Cover Type", 'DR'))),
    (unicode(QApplication.translate("Cover Type", 'During performance')), unicode(QApplication.translate("Cover Type", 'DP'))),
    (unicode(QApplication.translate("Cover Type", 'Movie/video screen capture')), unicode(QApplication.translate("Cover Type", 'MC'))),
    (unicode(QApplication.translate("Cover Type", 'A bright coloured fish')), unicode(QApplication.translate("Cover Type", 'F'))),
    (unicode(QApplication.translate("Cover Type", 'Illustration')), unicode(QApplication.translate("Cover Type", 'P'))),
    (unicode(QApplication.translate("Cover Type", 'Band/artist logotype')), unicode(QApplication.translate("Cover Type", 'BL'))),
    (unicode(QApplication.translate("Cover Type", 'Publisher/Studio logotype')), unicode(QApplication.translate("Cover Type", 'PL')))]

class CoverButton(QPushButton):
    def __init__(self, *args):
        QPushButton.__init__(self, *args)
        menu = QMenu(self)

        triggered = SIGNAL('triggered()')
        def create(title, short, index):
            text = u'[%s] %s' % (short, title)
            action = QAction(text, self)
            self.connect(action, triggered, lambda: self.setCurrentIndex(index))
            return action

        actions = [create(title, short, index) for index, (title, short) 
                    in enumerate(imagetypes)]

        map(menu.addAction, actions)
        self.setMenu(menu)
        self.setCurrentIndex(3)
    
    def setCurrentIndex(self, index):
        self.setText(imagetypes[index][1])
        self.emit(SIGNAL('currentIndexChanged (int)'), index)
        self._index = index
    
    def currentIndex(self):
        return self._index

class PuddleConfig(object):
    """Module that allows you to values from INI config files, similar to
    Qt's Settings module (Created it because PyQt4.4.3 has problems with
    saving and loading lists.

    Only two functions of interest:

    get -> load a key from a specified section
    set -> save a key section"""
    def __init__(self, filename = None):
        self.settings = ConfigObj(filename, create_empty=True, encoding='utf8')

        if not filename:
            filename = os.path.join(os.getenv('HOME'),'.puddletag', 'puddletag.conf')
        self._setFilename(filename)

        #TODO: backward compatibility, remove all.
        self.setSection = self.set
        self.load = self.get

    def get(self, section, key, default, getint = False):
        settings = self.settings
        try:
            if isinstance(default, bool):
                if self.settings[section][key] == 'True':
                    return True
                return False
            elif getint or isinstance(default, (long,int)):
                try:
                    return int(self.settings[section][key])
                except TypeError:
                    return [int(z) for z in self.settings[section][key]]
            else:
                val = self.settings[section][key]
                if val is None:
                    return default
                return val
        except KeyError:
            return default

    def set(self, section = None, key = None, value = None):
        settings = self.settings
        if section in self.settings:
            settings[section][key] = value
        else:
            settings[section] = {}
            settings[section][key] = value
        settings.write()

    def _setFilename(self, filename):
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        self.settings.filename = filename
        self.savedir = dirname
        self.settings.reload()

    def _getFilename(self):
        return self.settings.filename

    def sections(self):
        return self.settings.keys()

    filename = property(_getFilename, _setFilename)

def _setupsaves(func):
    filename = os.path.join(PuddleConfig().savedir, 'windowsizes')
    settings = QSettings(filename, QSettings.IniFormat)
    return lambda x, y: func(x, y, settings)

@_setupsaves
def savewinsize(name, dialog, settings):
    settings.setValue(name, QVariant(dialog.saveGeometry()))

@_setupsaves
def winsettings(name, dialog, settings):
    dialog.restoreGeometry(settings.value(name).toByteArray())
    cevent = dialog.closeEvent
    def closeEvent(self, event=None):
        savewinsize(name, dialog)
        if event is None:
            cevent(self)
        else:
            cevent(event)
    setattr(dialog, 'closeEvent', closeEvent)

try:
    from Levenshtein import ratio
except ImportError:
    from difflib import SequenceMatcher
    ratio = lambda a,b: SequenceMatcher(None, a,b).ratio()

dirlevels = lambda a: len(a.split('/'))

def removeslash(x):
    while x.endswith('/'):
        return removeslash(x[:-1])
    return x

def create_buddy(text, control, hbox=None):
    label = QLabel(text)
    label.setBuddy(control)

    if not hbox:
        hbox = QHBoxLayout()
    hbox.addWidget(label)
    hbox.addWidget(control, 1)

    return hbox

def dircmp(a, b):
    """Compare function to sort directories via parent.
So that the child is renamed before parent, thereby not
giving Permission Denied errors."""
    a, b = removeslash(a), removeslash(b)
    if a == b:
        return 0
    elif a in b and (dirlevels(a) != dirlevels(b)):
        return 1
    elif b in a and (dirlevels(a) != dirlevels(b)):
        return -1
    elif len(a) > len(b):
        return 1
    elif len(b) > len(a):
        return -1
    elif len(b) == len(a):
        return 0

def dircmp1(a, b):
    """Like dircmp, but returns dirs as being in the same directory as equal."""
    a,b = removeslash(a), removeslash(b)
    if a == b or (dirlevels(a) == dirlevels(b)):
        return 0
    elif a in b:
        return 1
    elif b in a:
        return -1
    else:
        return 0

def issubfolder(parent, child, level = 1):
    parent, child = removeslash(parent), removeslash(child)
    if isinstance(parent, unicode):
        sep = unicode(os.path.sep)
    else:
        sep = os.path.sep
    if level is not None:
        if child.startswith(parent + sep) and dirlevels(parent) + level == dirlevels(child):
            return True
        return False
    else:
        if child.startswith(parent + sep) and dirlevels(parent) < dirlevels(child):
            return True
        return False

HORIZONTAL = 1
VERTICAL = 0

def get_icon(name, backup):
    if not name and not backup:
        return QIcon()
    elif not name and backup:
        return QIcon(backup)
    try:
        return QIcon.fromTheme(name, QIcon(backup))
    except AttributeError:
        return QIcon(backup_name)

def singleerror(parent, msg):
    QMessageBox.warning(parent, 'Error', msg, QMessageBox.Ok,
        QMessageBox.NoButton)

def errormsg(parent, msg, maximum):
    """Shows a messagebox containing an error message indicating that
    writing to filename has failed and asks the user to continue, stop,
    or continue without interruption.

    error is the error that caused the disruption.
    single is the number of files that are being written. If it is 1, then
    just a warningMessage is shown.

    Returns:
        True if yes to all.
        False if No.
        None if just yes."""
    if maximum > 1:
        mb = QMessageBox(QApplication.translate("Defaults", 'Error'),
            msg + QApplication.translate("Defaults", "<br /> Do you want to continue?"),
            *(MSGARGS + (parent, )))
        ret = mb.exec_()
        if ret == QMessageBox.No:
            return False
        elif ret == QMessageBox.YesAll:
            return True
    else:
        singleerror(parent, msg)

def safe_name(name, chars=r'/\*?;"|:', to=None):
    """Make a filename safe for use (remove some special chars)

    If any special chars are found they are replaced by to."""
    if not to:
        to = ""
    else:
        to = unicode(to)
    escaped = ""
    for ch in name:
        if ch not in chars: escaped = escaped + ch
        else: escaped = escaped + to
    if not escaped: return '""'
    return escaped

def unique(seq, stable = False):
    """unique(seq, stable=False): return a list of the elements in seq in arbitrary
    order, but without duplicates.
    If stable=True it keeps the original element order (using slower algorithms)."""
    # Developed from Tim Peters version:
    #   http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52560

    #if uniqueDebug and len(str(seq))<50: print "Input:", seq # For debugging.

    # Special case of an empty s:
    if not seq: return []

    # if it's a set:
    if isinstance(seq, set): return list(seq)

    if stable:
        # Try with a set:
        seqSet= set()
        result = []
        try:
            for e in seq:
                if e not in seqSet:
                    result.append(e)
                    seqSet.add(e)
        except TypeError:
            pass # move on to the next method
        else:
            #if uniqueDebug: print "Stable, set."
            return result

        # Since you can't hash all elements, use a bisection on sorted elements
        result = []
        sortedElem = []
        try:
            for elem in seq:
                pos = bisect_left(sortedElem, elem)
                if pos >= len(sortedElem) or sortedElem[pos] != elem:
                    insort_left(sortedElem, elem)
                    result.append(elem)
        except TypeError:
            pass  # Move on to the next method
        else:
            #if uniqueDebug: print "Stable, bisect."
            return result
    else: # Not stable
        # Try using a set first, because it's the fastest and it usually works
        try:
            u = set(seq)
        except TypeError:
            pass # move on to the next method
        else:
            #if uniqueDebug: print "Unstable, set."
            return list(u)

        # Elements can't be hashed, so bring equal items together with a sort and
        # remove them out in a single pass.
        try:
            t = sorted(seq)
        except TypeError:
            pass  # Move on to the next method
        else:
            #if uniqueDebug: print "Unstable, sorted."
            return [elem for elem,group in groupby(t)]

    # Brute force:
    result = []
    for elem in seq:
        if elem not in result:
            result.append(elem)
    #if uniqueDebug: print "Brute force (" + ("Unstable","Stable")[stable] + ")."
    return result

class compare:
    "Natural sorting class."
    def try_int(self, s):
        "Convert to integer if possible."
        try: return int(s)
        except: return s
    def natsort_key(self, s):
        "Used internally to get a tuple by which s is sorted."
        return map(self.try_int, re.findall(r'(\d+|\D+)', s))
    def natcmp(self, a, b):
        "Natural string comparison, case sensitive."
        return cmp(self.natsort_key(a), self.natsort_key(b))
    def natcasecmp(self, a, b):
        "Natural string comparison, ignores case."
        return self.natcmp(u"".join(a).lower(), u"".join(b).lower())

natcasecmp = compare().natcasecmp

def dupes(l, method = None):
    if method is None:
        method = lambda a,b: int(a==b)
    l = [{'key': z, 'index': i} for i, z in enumerate(l)]
    chars = chars=r'/\*?;"|:\''
    strings = sorted([(safe_name(z['key'].lower(), chars, ''), z['index'])
                            for z in l if z['key'] is not None])
    try:
        last = strings[0][0]
    except IndexError:
        return []
    groups = [[0]]
    for z, i in strings[1:]:
        if z is not None:
            val = method(last, z)
            if val >= 0.85:
                groups[-1].append(i)
            else:
                last = z
                groups.append([i])
    return [z for z in groups if len(z) > 1]

def getfiles(files, subfolders = False, pattern = ''):
    #pattern = u'*.ogg'
    def recursedir(folder, subfolders):
        folder = encode_fn(folder)
        if subfolders:
            #TODO: This really fucks up when reading files with malformed
            #unicode filenames.
            files = []
            [[files.append(path.join(z[0], y)) for y in z[2]]
                for z in os.walk(folder)]
        else:
            
            files = os.walk(folder).next()[2]
            files = [path.join(folder, f) for f in files]
        return files

    if len(files) == 1 and os.path.isdir(files[0]):
        files = files[0]
    if isinstance(files, basestring):
        if path.isdir(files):
            dirname = [files]
            files = recursedir(files, subfolders)
        else:
            dirname = []
            files = [files]
    else:
        dirnames = [z for z in files if os.path.isdir(z)]
        files = [z for z in files if not os.path.isdir(z)]
        dirname = dirnames
        while dirnames and subfolders:
            [files.extend(recursedir(d, True)) for d in dirnames]
            dirnames = [z for z in files if os.path.isdir(z)]
    if not (pattern or pattern.strip()):
        return files
    else:
        return fnmatch(pattern, files)

def gettags(files):
    return (gettag(audio) for audio in files)

def gettag(f):
    try:
        return audioinfo.Tag(f)
    except:
        print u'An error occured.'
        print f
        traceback.print_exc()
        return

def translate_filename_pattern(pat):
    """Translate a shell PATTERN to a regular expression.

    There is no way to quote meta-characters.
    """
    #from fnmatch.py with slight modification
    pat = pat.strip()
    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            res = res + '.*'
        elif c == '?':
            res = res + '.'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\','\\\\')
                i = j+1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)
    #return res + '\Z(?ms)'
    return res + '\Z'

def fnmatch(pattern, files, matchcase=False):
    regexp = u'|'.join(map(translate_filename_pattern, 
        [z.strip() for z in pattern.split(u';')]))
    if matchcase:
        match = re.compile(regexp).match
    else:
        match = re.compile(regexp, re.I).match
    return filter(match, files)

def gettaglist():
    cparser = PuddleConfig()
    filename = os.path.join(cparser.savedir, 'usertags')
    try:
        lines = sorted(set([z.strip() for z in open(filename, 'r').read().split('\n')]))
    except (IOError, OSError):
        lines = audioinfo.FIELDS[::]
    return lines

def settaglist(tags):
    cparser = PuddleConfig()
    filename = os.path.join(cparser.savedir, 'usertags')
    f = open(filename, 'w')
    text = '\n'.join(sorted([z for z in tags if not z.startswith('__')]))
    f.write(text)
    f.close()

def load_actions():
    import findfunc
    basename = os.path.basename

    funcs = {}
    cparser = PuddleConfig()
    set_value = partial(cparser.set, 'puddleactions')
    get_value = partial(cparser.get, 'puddleactions')

    firstrun = get_value('firstrun', True)
    set_value('firstrun', False)
    convert = get_value('convert', True)
    order = get_value('order', [])

    if convert:
        set_value('convert', False)
        findfunc.convert_actions(SAVEDIR, ACTIONDIR)
        if order:
            old_order = dict([(basename(z), i) for i,z in
                enumerate(order)])
            files = glob(os.path.join(ACTIONDIR, u'*.action'))
            order = {}
            for f in files:
                try:
                    order[old_order[basename(f)]] = f
                except KeyError:
                    pass
            order = [z[1] for z in sorted(order.items())]
            set_value('order', order)

    files = glob(os.path.join(ACTIONDIR, u'*.action'))
    if firstrun and not files:
        filenames = [':/caseconversion.action', ':/standard.action']
        files = map(open_resourcefile, filenames)
        set_value('firstrun', False)

        for fileobj, filename in zip(files, filenames):
            filename = os.path.join(ACTIONDIR, filename[2:])
            f = open(filename, 'w')
            f.write(fileobj.read())
            f.close()
        files = glob(os.path.join(ACTIONDIR, u'*.action'))

    files = [z for z in order if z in files] + \
        [z for z in files if z not in order]

    funcs = []
    for f in files:
        action = findfunc.load_action(f)
        funcs.append([action[0], action[1], f])
    return funcs

def open_resourcefile(filename):
    f = QFile(filename)
    f.open(QIODevice.ReadOnly | QIODevice.Text)
    return StringIO(f.readAll())

def progress(func, pstring, maximum, threadfin = None):
    """To be used for functions that need a threaded progressbar.

    Note that this function will only (and is meant to) work on dialogs.

    func is the function that will be run by the thread. It should yield None
    while successful. Otherwise it should yield an errormsg and the number
    of files (this'll be used when calling errormsg).

    pstring is the progress message. This is shown with the number of times
    func yielded a value. For instance, pstring = 'Loading... ', and maximum = 20
    will show 'Loading... 1 of 20', 'Loading... 2 of 20', etc.on the progress
    bar.

    maximum is the maximum value of the progessbar.

    threadfin is the function to run when the thread has finished. Usually
    for cleanup stuff.

    Note that the function returns a function that expects a parent for
    the progess window as the first argument. This with the rest of the arguments
    passed to the returned function are used when calling func (except in the
    case where only the parent argument is passed).
    """
    def s(*args):
        parent = args[0]
        win = ProgressWin(parent, maximum, pstring)
        if maximum > 1:
            win.show()
        if len(args) > 1:
            f = func(*args)
        else:
            f = func()
        parent.showmessage = True

        def threadfunc():
            i = 0
            err = False
            while not win.wasCanceled:
                try:
                    temp = f.next()
                    if temp is not None:
                        #temp[0] is the error message, temp[1] the num files
                        thread.emit(SIGNAL('error(QString, int)'),
                            temp[0], temp[1])
                        err = True
                        break
                    else:
                        thread.emit(SIGNAL('win(int)'), i)
                except StopIteration:
                    break
                i += 1

            if not err:
                thread.emit(SIGNAL('win(int)'), -1)

        def threadexit(*args):
            if args[0] == -1:
                win.close()
                win.destroy()
                if threadfin:
                    threadfin()
            elif isinstance(args[0], QString):
                if parent.showmessage:
                    ret = errormsg(parent, args[0], maximum)
                    if ret is True:
                        parent.showmessage = False
                    elif ret is False:
                        thread.emit(SIGNAL('win(int)'), -1)
                        return
                if not win.isVisible():
                    win.show()
                while thread.isRunning():
                    pass
                thread.start()
            win.setValue(win.value + 1)

        thread = PuddleThread(threadfunc, parent)
        thread.connect(thread, SIGNAL('win(int)'), threadexit)
        thread.connect(thread, SIGNAL('error(QString, int)'), threadexit)
        thread.start()
    return s

def timemethod(method):
    def f(*args, **kwargs):
        name = method.__name__
        t = time.time()
        ret = method(*args, **kwargs)
        print name, time.time() - t
        return ret
    return f

class HeaderSetting(QDialog):
    """A dialog that allows you to edit the header of a TagTable widget."""
    def __init__(self, tags = None, parent = None, showok = True, showedits = True):
        QDialog.__init__(self, parent)
        self.listbox = ListBox()
        self.tags = [list(z) for z in tags]
        self.listbox.addItems([z[0] for z in self.tags])

        self.vbox = QVBoxLayout()
        self.vboxgrid = QGridLayout()
        self.textname = QLineEdit()
        self.tag = QLineEdit()
        self.buttonlist = ListButtons()
        self.buttonlist.edit.setVisible(False)
        if showedits:
            self.vboxgrid.addWidget(QLabel(QApplication.translate("Column Settings", "Title")),0,0)
            self.vboxgrid.addWidget(self.textname,0,1)
            self.vboxgrid.addWidget(QLabel(QApplication.translate("Defaults", "Field")), 1,0)
            self.vboxgrid.addWidget(self.tag,1,1)
            self.vboxgrid.addLayout(self.buttonlist,2,0)
        else:
            self.vboxgrid.addLayout(self.buttonlist,1,0)
        self.vboxgrid.setColumnStretch(0,0)

        self.vbox.addLayout(self.vboxgrid)
        self.vbox.addStretch()

        self.grid = QGridLayout()
        self.grid.addWidget(self.listbox,1,0)
        self.grid.addLayout(self.vbox,1,1)
        self.grid.setColumnStretch(1,1)
        self.grid.setColumnStretch(0,2)

        self.connect(self.listbox, SIGNAL("currentItemChanged (QListWidgetItem *,QListWidgetItem *)"), self.fillEdits)
        self.connect(self.listbox, SIGNAL("itemSelectionChanged()"),self.enableEdits)


        self.okbuttons = OKCancel()
        if showok is True:
            self.grid.addLayout(self.okbuttons, 2,0,1,2)
        self.setLayout(self.grid)

        self.connect(self.okbuttons, SIGNAL("ok"), self.okClicked)
        self.connect(self.okbuttons, SIGNAL("cancel"), self.close)
        self.connect(self.textname, SIGNAL("textChanged (const QString&)"), self.updateList)
        self.connect(self.buttonlist, SIGNAL("add"), self.add)
        self.connect(self.buttonlist, SIGNAL("moveup"), self.moveup)
        self.connect(self.buttonlist, SIGNAL("movedown"), self.movedown)
        self.connect(self.buttonlist, SIGNAL("remove"), self.remove)
        self.connect(self.buttonlist, SIGNAL("duplicate"), self.duplicate)

        self.listbox.setCurrentRow(0)

    def enableEdits(self):
        if len(self.listbox.selectedItems()) > 1:
            self.textname.setEnabled(False)
            self.tag.setEnabled(False)
            return
        self.textname.setEnabled(True)
        self.tag.setEnabled(True)

    def remove(self):
        if len(self.tags) == 1: return
        self.disconnect(self.textname, SIGNAL("textChanged (const QString&)"), self.updateList)
        self.disconnect(self.listbox, SIGNAL("currentItemChanged (QListWidgetItem *,QListWidgetItem *)"), self.fillEdits)
        self.listbox.removeSelected(self.tags)
        row = self.listbox.currentRow()
        #self.listbox.clear()
        #self.listbox.addItems([z[0] for z in self.tags])

        if row == 0:
            self.listbox.setCurrentRow(0)
        elif row + 1 < self.listbox.count():
            self.listbox.setCurrentRow(row+1)
        else:
            self.listbox.setCurrentRow(self.listbox.count() -1)
        self.fillEdits(self.listbox.currentItem(), None)
        self.connect(self.textname, SIGNAL("textChanged (const QString&)"), self.updateList)
        self.connect(self.listbox, SIGNAL("currentItemChanged (QListWidgetItem *,QListWidgetItem *)"), self.fillEdits)

    def moveup(self):
        self.listbox.moveUp(self.tags)

    def movedown(self):
        self.listbox.moveDown(self.tags)

    def updateList(self, text):
        self.listbox.currentItem().setText(text)

    def fillEdits(self, current, prev):
        row = self.listbox.row(prev)
        try: #An error is raised if the last item has just been removed
            if row > -1:
                self.tags[row][0] = unicode(self.textname.text())
                self.tags[row][1] = unicode(self.tag.text())
        except IndexError:
            pass

        row = self.listbox.row(current)
        if row > -1:
            self.textname.setText(self.tags[row][0])
            self.tag.setText(self.tags[row][1])

    def okClicked(self):
        row = self.listbox.currentRow()
        if row > -1:
            self.tags[row][0] = unicode(self.textname.text())
            self.tags[row][1] = unicode(self.tag.text())
        self.emit(SIGNAL("headerChanged"),[z for z in self.tags])
        self.close()

    def add(self):
        row = self.listbox.count()
        self.tags.append(["",""])
        self.listbox.addItem("")
        self.listbox.clearSelection()
        self.listbox.setCurrentRow(row)
        self.textname.setFocus()

    def duplicate(self):
        row = self.listbox.currentRow()
        if row < 0:
            return
        tag = self.tags[row][::]
        self.tags.append(tag)
        self.listbox.addItem(tag[0])
        self.listbox.clearSelection()
        self.listbox.setCurrentRow(self.listbox.count() - 1)
        self.textname.setFocus()

class Label(QLabel):
    """Just a QLabel that sends a clicked() signal
    when left-clicked."""
    def __init__ (self, text = "", parent = None):
        QLabel.__init__ (self, text, parent)

    def mouseReleaseEvent(self, event):
      if event.button() == Qt.LeftButton:
        self.emit(SIGNAL("clicked()"))
      QLabel.mousePressEvent(self, event)

class ListBox(QListWidget):
    """Puddletag's replacement of QListWidget, because
    removing, moving and deleting items in a listbox
    is done a lot.

    First the modifier methods.
    removeSelected, moveUp and moveDown each does as the
    name implies. See docstrings for more info.

    connectToListButtons -> connects removeSelected etc. to
    the respective buttons in a ListButtons object.

    Attributes:
    editButton -> Set this to a button or control which will be enabled only
    when a single item is selected.

    yourlist -> The list that will be used in removeSelected et al, if None
    is passed when calling the function.."""
    def __init__(self, parent = None):
        QListWidget.__init__(self, parent)
        self.yourlist = None
        self.editButton = None
        self.setSelectionMode(self.ExtendedSelection)

    def items(self):
        return map(self.item, xrange(self.count()))

    def selectionChanged(self, selected, deselected):
        if self.editButton:
            if len(self.selectedItems()) == 1:
                self.editButton.setEnabled(True)
            else:
                self.editButton.setEnabled(False)
        QListWidget.selectionChanged(self, selected, deselected)

    def connectToListButtons(self, listbuttons, yourlist = None):
        """Connect the moveUp, moveDown and removeSelected to the
        moveup, movedown and remove signals of listbuttons and
        sets the editButton.

        yourlist is used a the argument in these functions if
        no other yourlist is passed."""
        self.editButton = listbuttons.edit
        self.connect(listbuttons, SIGNAL('moveup'), self.moveUp)
        self.connect(listbuttons, SIGNAL('movedown'), self.moveDown)
        self.connect(listbuttons, SIGNAL('remove'), self.removeSelected)
        self.yourlist = yourlist

    def removeSelected(self, yourlist = None, rows = None):
        """Removes the currently selected items.
        If yourlist is not None, then the selected
        items are removed for yourlist also. Note, that
        the indexes of the items in yourlist and the listbox
        have to correspond.

        If you want to remove anything other than the selected,
        just set rows to a list of integers."""
        if not yourlist:
            yourlist = self.yourlist
        if rows:
            rows = sorted(rows)
        else:
            rows = sorted([self.row(item) for item in self.selectedItems()])

        for i in range(len(rows)):
            self.takeItem(rows[i])
            if yourlist:
                try:
                    del(yourlist[rows[i]])
                except (KeyError, IndexError):
                    "The list doesn't have enough items or something"
            rows = [z - 1 for z in rows]

    def moveUp(self, yourlist = None, rows = None):
        """Moves the currently selected items up one place.
        If yourlist is not None, then the indexes of yourlist
        are updated in tandem. Note, that
        the indexes of the items in yourlist and the listbox
        have to correspond."""
        if not rows:
            rows = [self.row(item) for item in self.selectedItems()]
        rows = sorted(rows)
        if not yourlist:
            yourlist = self.yourlist
        currentrow = self.currentRow() - 1
        if 0 in rows:
            return

        [self.setItemSelected(item, False) for item in self.selectedItems()]
        for i in range(len(rows)):
            row = rows[i]
            item = self.takeItem(row)
            self.insertItem(row - 1, item)
            if yourlist:
                temp = copy(yourlist[row - 1])
                yourlist[row - 1] = yourlist[row]
                yourlist[row] = temp
        [self.setItemSelected(self.item(row - 1), True) for row in rows]
        self.setCurrentRow(currentrow)

    def moveDown(self, yourlist = None, rows = None):
        """See moveup. It's exactly the opposite."""
        if rows is None:
            rows = [self.row(item) for item in self.selectedItems()]
        if self.count() - 1 in rows:
            return
        [self.setItemSelected(item, False) for item in self.selectedItems()]
        if not yourlist:
            yourlist = self.yourlist
        rows = sorted(rows)
        lastindex = rows[0]
        groups = {lastindex:[lastindex]}
        lastrow = lastindex
        for row in rows[1:]:
            if row - 1 == lastindex:
                groups[lastrow].append(row)
            else:
                groups[row] = [row]
                lastrow = row
            lastindex = row

        for group in groups:
            item = self.takeItem(group + len(groups[group]))
            if yourlist:
                temp = copy(yourlist[group + len(groups[group])])
                for index in reversed(groups[group]):
                    yourlist[index + 1] = copy(yourlist[index])
                yourlist[group] = temp
            self.insertItem(group, item)

        [self.setItemSelected(self.item(row + 1), True) for row in rows]

    def selectedItems(self):
        return filter(lambda item: item.isSelected(),
            map(self.item, xrange(self.count())))

class ListButtons(QVBoxLayout):
    """A Layout that contains five buttons usually
    associated with listboxes. They are
    add, edit, movedown, moveup and remove.

    Each button, when clicked sends signal with the
    buttons name. e.g. add sends SIGNAL("add").

    You can find them all in the widgets attribute."""

    def __init__(self, parent = None):
        QVBoxLayout.__init__(self, parent)
        self.add = QToolButton()
        self.add.setIcon(get_icon('list-add', ':/filenew.png'))
        self.add.setToolTip(QApplication.translate("List Buttons", 'Add'))
        self.remove = QToolButton()
        self.remove.setIcon(get_icon('list-remove', ':/remove.png'))
        self.remove.setToolTip(QApplication.translate("List Buttons", 'Remove'))
        self.remove.setShortcut('Delete')
        self.moveup = QToolButton()
        self.moveup.setArrowType(Qt.UpArrow)
        self.moveup.setToolTip(QApplication.translate("List Buttons", 'Move Up'))
        self.movedown = QToolButton()
        self.movedown.setArrowType(Qt.DownArrow)
        self.movedown.setToolTip(QApplication.translate("List Buttons", 'Move Down'))
        self.edit = QToolButton()
        self.edit.setIcon(get_icon('document-edit', ':/edit.png'))
        self.edit.setToolTip(QApplication.translate("List Buttons", 'Edit'))
        self.duplicate = QToolButton()
        self.duplicate.setIcon(get_icon('edit-copy', ':/duplicate.png'))
        self.duplicate.setToolTip(QApplication.translate("List Buttons", 'Duplicate'))

        self.widgets = [self.add, self.edit, self.duplicate,
            self.remove, self.moveup, self.movedown]
        [self.addWidget(widget) for widget in self.widgets]
        self.insertStretch(4)
        self.insertSpacing(4,6)
        [z.setIconSize(QSize(16,16)) for z in self.widgets]
        self.addStretch()

        clicked = SIGNAL("clicked()")
        self.connect(self.add, clicked, self.addClicked)
        self.connect(self.remove, clicked, self.removeClicked)
        self.connect(self.moveup, clicked, self.moveupClicked)
        self.connect(self.movedown, clicked, self.movedownClicked)
        self.connect(self.edit, clicked, self.editClicked)
        self.connect(self.duplicate, clicked, self.duplicateClicked)

    def connectToWidget(self, widget, add=None, edit=None, remove=None,
                        moveup=None, movedown=None, duplicate=None):
        l = ['add', 'edit', 'remove']
        if moveup:
            l.append('moveup')
        if movedown:
            l.append('movedown')
        if duplicate:
            l.append('duplicate')
        connections = dict([(z,v) for z,v in zip(l,
                                [add, edit, remove, moveup, movedown,
                                duplicate]) if v])
        connect = lambda a: self.connect(self, SIGNAL(a),
                    connections[a] if a in connections else getattr(widget, a))
        map(connect, l)

    def addClicked(self):
        self.emit(SIGNAL("add"))

    def setEnabled(self, value):
        [w.setEnabled(value) for w in self.widgets]
        super(ListButtons, self).setEnabled(value)

    def removeClicked(self):
        self.emit(SIGNAL("remove"))

    def moveupClicked(self):
        self.emit(SIGNAL("moveup"))

    def movedownClicked(self):
        self.emit(SIGNAL("movedown"))

    def editClicked(self):
        self.emit(SIGNAL("edit"))

    def duplicateClicked(self):
        self.emit(SIGNAL('duplicate'))

class MoveButtons(QWidget):
    def __init__(self, arrayname, index = 0, orientation = HORIZONTAL, parent = None):
        QWidget.__init__(self, parent)
        self.next = QPushButton(QApplication.translate("List Buttons", '&>>'))
        self.prev = QPushButton(QApplication.translate("List Buttons", '&<<'))
        if orientation == VERTICAL:
            box = QVBoxLayout()
            box.addWidget(self.next, 0)
            box.addWidget(self.prev, 0)
        else:
            box = QHBoxLayout()
            box.addWidget(self.prev)
            box.addWidget(self.next)


        self.arrayname = arrayname

        self.setLayout(box)
        self.index = index
        self.connect(self.next, SIGNAL('clicked()'), self.nextClicked)
        self.connect(self.prev, SIGNAL('clicked()'), self.prevClicked)

    def _setCurrentIndex(self, index):
        try:
            if index >= len(self.arrayname) or index < 0:
                return
            else:
                self._currentindex = index
                if self._currentindex >= len(self.arrayname) - 1:
                    self.next.setEnabled(False)
                else:
                    self.next.setEnabled(True)

                if self._currentindex <= 0:
                    self.prev.setEnabled(False)
                else:
                    self.prev.setEnabled(True)
        except TypeError:
            "Probably arrayname is None or something."
            self.prev.setEnabled(False)
            self.next.setEnabled(False)

        if (not self.prev.isEnabled()) and (not self.next.isEnabled()):
            self.prev.hide()
            self.next.hide()
        else:
            self.prev.show()
            self.next.show()

        self.emit(SIGNAL('indexChanged'), index)

    def _getCurrentIndex(self):
        return self._currentindex

    index = property(_getCurrentIndex, _setCurrentIndex)

    def nextClicked(self):
        self.index += 1

    def prevClicked(self):
        self.index -= 1

    def updateButtons(self):
        self.index = self.index

class OKCancel(QHBoxLayout):
    """Yes, I know about QDialogButtonBox, but I'm not using PyQt4.2 here."""
    def __init__(self, parent = None):
        QHBoxLayout.__init__(self, parent)
        #QDialogButtonBox.__init__(self, parent)

        #self.addStretch()
        dbox = QDialogButtonBox()

        self.ok = dbox.addButton(dbox.Ok)
        self.cancel = dbox.addButton(dbox.Cancel)
        self.addStretch()
        self.addWidget(dbox)
        #self.cancel = QPushButton("&Cancel")
        #self.ok.setDefault(True)

        #self.addWidget(self.ok)
        #self.addWidget(self.cancel)

        self.connect(self.ok, SIGNAL("clicked()"), self.yes)
        self.connect(self.cancel, SIGNAL("clicked()"), self.no)

    def yes(self):
        self.emit(SIGNAL("ok"))

    def no(self):
        self.emit(SIGNAL("cancel"))

class LongInfoMessage(QDialog):
    def __init__(self, title, question, html, parent =None):
        QDialog.__init__(self, parent)
        winsettings('infomessage', self)
        question = QLabel(question)

        text = QTextEdit()
        text.setReadOnly(True)
        #text.setWordWrapMode(QTextOption.NoWrap)
        text.setHtml(html)

        okcancel = OKCancel()

        self.connect(okcancel, SIGNAL('ok'), self._ok)
        self.connect(okcancel, SIGNAL('cancel'), self.close)

        vbox = QVBoxLayout()
        self.setWindowTitle(title)
        vbox.addWidget(question)
        vbox.addWidget(text)
        vbox.addLayout(okcancel)
        self.setLayout(vbox)

    def _ok(self):
        self.close()
        self.accept()

class ArtworkLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super(ArtworkLabel, self).__init__(*args, **kwargs)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            event.accept()
        else:
            event.ignore()
        super(ArtworkLabel, self).dragEnterEvent(event)
    
    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            filenames = [unicode(z.path()) for z in mime.urls()]
            self.emit(SIGNAL('newImages'), *filenames)
        super(ArtworkLabel, self).dropEvent(event)
    
    def mouseReleaseEvent(self, event):
      if event.button() == Qt.LeftButton:
        self.emit(SIGNAL("clicked()"))
      QLabel.mousePressEvent(self, event)

class PicWidget(QWidget):
    """A widget that shows a file's pictures.

    images is a list of mutagen.id3.APIC objects.
    It allows the user to edit, save and delete whichever
    picture the user wants, by right-clicking on it.

    In addition, there are buttons to browse through
    all the pictures.

    Some important attributes are:
    currentImage -> The index of the current image
    maxImage -> Shows the current image fullsized.
    setImages -> Guess
    addImage -> Guess again...but it also shows and open file dialog.
    removeImage -> Removes the current image.
    next and prevImage -> Moves to the next and previous image.
    saveToFile -> Save the current image to file.
    showbuttons -> If True, the >> and << buttons are always shown. If False,
                    they are shown depending on context."""

    def __init__ (self, images = None, imagetags = None, parent = None, 
        readonly = None, buttons = False):
        """Initialises the widget.

        images -> A list of images as described in the classes docstring.
        parent -> Qt parent
        readonly -> indexes of images that are readonly. Can be changed by modifying
                    the readonly attribute.
        buttons -> If True, then the Add, Edit, etc. Buttons are shown.
                   If False, then these functions can be found by right clicking
                   on the picture."""

        self._contextFormat = QApplication.translate("Artwork Context", '%1/%2')
        
        QWidget.__init__(self, parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.sizePolicy().setVerticalStretch(0)
        self.sizePolicy().setHorizontalStretch(3)

        self.lastfilename = u'~'
        #The picture.
        self.label = ArtworkLabel()
        self.label.setFrameStyle(QFrame.Box)
        self.label.setMargin(10)
        self.label.setMinimumSize(200, 170)
        if buttons:
            self.label.setMaximumSize(200, 170)
        self._itags = []
        #else:
            #self.setMaximumSize(400,400)
        self.label.setAlignment(Qt.AlignCenter)
        self.connect(self.label, SIGNAL('newImages'), 
            lambda *filenames: self.addImages(self.loadPics(*filenames)))
        #self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        #Description and picture type shit.
        self._image_desc = QLineEdit(self)
        self._image_desc.setText(QApplication.translate("Artwork", 'Enter a description'))
        self._image_desc.setToolTip(
            QApplication.translate("Artwork",
            '<p>Enter a description for the current cover.</p>'
            '<p>For ID3 tags the description has to be different for each '
            "cover as per the ID3 spec. If they don't differ then spaces "
            'are appended to the description when the tag is saved.</p>'))
        self.connect(self._image_desc, SIGNAL('textEdited (const QString&)'),
            self.setDescription)
        controls = QVBoxLayout()

        if buttons:
            dbox = QVBoxLayout()
            label = QLabel(QApplication.translate("Artwork", '&Description'))
            label.setBuddy(self._image_desc)
            dbox.addWidget(label)
            dbox.addWidget(self._image_desc)
            controls.addLayout(dbox)
            self._image_type = QComboBox(self)
            self._image_type.addItems(IMAGETYPES)
            dbox = QVBoxLayout()
            label = QLabel(QApplication.translate("Artwork", '&Type'))
            label.setBuddy(self._image_type)
            dbox.addWidget(label)
            dbox.addWidget(self._image_type)
            controls.addLayout(dbox)
        else:
            self._image_type = CoverButton(self)
            hbox = QHBoxLayout()
            hbox.addWidget(self._image_desc, 1)
            hbox.addWidget(self._image_type)
            controls.addLayout(hbox)
        self._image_type.setToolTip(
            QApplication.translate("Artwork", '<p>Select a cover type for the artwork.</p>'))
        self.connect(self._image_type, SIGNAL('currentIndexChanged (int)'),
                            self.setType)

        self.showbuttons = True

        if not readonly:
            readonly = []
        self.readonly = readonly

        self.next = QToolButton()
        self.next.setArrowType(Qt.RightArrow)
        self.prev = QToolButton()
        self.prev.setArrowType(Qt.LeftArrow)
        self.connect(self.next, SIGNAL('clicked()'), self.nextImage)
        self.connect(self.prev, SIGNAL('clicked()'), self.prevImage)

        self._contextlabel = QLabel()
        self._contextlabel.setVisible(False)
        if buttons:
            movebuttons = QHBoxLayout()
            movebuttons.addStretch()
            movebuttons.addWidget(self.prev)
            movebuttons.addWidget(self.next)
            movebuttons.addWidget(self._contextlabel)
            movebuttons.addStretch()
        else:
            self.next.setArrowType(Qt.UpArrow)
            self.prev.setArrowType(Qt.DownArrow)
            movebuttons = QVBoxLayout()
            movebuttons.addStretch()
            movebuttons.addWidget(self.next)
            movebuttons.addWidget(self.prev)
            movebuttons.addStretch()

        vbox = QVBoxLayout()
        h = QHBoxLayout(); h.addStretch(); h.addWidget(self.label,1)
        if not buttons:
            h.addLayout(movebuttons)
            context_box = QHBoxLayout()
            context_box.setAlignment(Qt.AlignHCenter)
            context_box.addWidget(self._contextlabel)
            vbox.addLayout(context_box)
        h.addStretch()
        vbox.addLayout(h)
        
        vbox.setMargin(0)
        vbox.addLayout(controls)
        if buttons:
            vbox.addLayout(movebuttons)
        vbox.setAlignment(Qt.AlignCenter)
        #vbox.addStretch()

        self.connect(self.label, SIGNAL('clicked()'), self.maxImage)

        hbox = QHBoxLayout()
        hbox.addLayout(vbox)
        hbox.addStrut(12)
        hbox.setSizeConstraint(hbox.SetMinAndMaxSize)
        self.setLayout(hbox)

        if buttons:
            listbuttons = ListButtons()
            listbuttons.duplicate.hide()
            self.addpic = listbuttons.add
            self.removepic = listbuttons.remove
            self.editpic = listbuttons.edit
            self.savepic = QToolButton()
            self.savepic.setIcon(QIcon(':/save.png'))
            self.savepic.setIconSize(QSize(16,16))
            listbuttons.insertWidget(3,self.savepic)
            listbuttons.moveup.hide()
            listbuttons.movedown.hide()
            signal = SIGNAL('clicked()')
            hbox.addLayout(listbuttons)

        else:
            self.label.setContextMenuPolicy(Qt.ActionsContextMenu)
            self.savepic = QAction(QApplication.translate("Artwork", "&Save cover to file"), self)
            self.label.addAction(self.savepic)

            self.addpic = QAction(QApplication.translate("Artwork", "&Add cover"), self)
            self.label.addAction(self.addpic)

            self.removepic = QAction(QApplication.translate("Artwork", "&Remove cover"), self)
            self.label.addAction(self.removepic)

            self.editpic = QAction(QApplication.translate("Artwork", "&Change cover"), self)
            self.label.addAction(self.editpic)
            signal = SIGNAL('triggered()')

        self.connect(self.addpic, signal, self.addImage)
        self.connect(self.removepic, signal, self.removeImage)
        self.edit = partial(self.addImage, True)
        self.connect(self.editpic, signal, self.edit)
        self.connect(self.savepic, signal, self.saveToFile)

        self.win = PicWin(parent = self)
        self._currentImage = -1

        if not images:
            images = []

        if not imagetags:
            imagetags = []

        self.setImages(images, imagetags)

    def _setContext(self, text):
        if not text:
            self._contextlabel.setVisible(False)
            self._contextlabel.setText('')
        else:
            self._contextlabel.setText(QApplication.translate("Artwork Context", text))
            self._contextlabel.setVisible(True)

    def _getContext(self):
        return self._contextlabel.text()

    context = property(_getContext, _setContext)

    def setDescription(self, text):
        '''Sets the description of the current image to the text in the
            description text box.'''
        self.images[self.currentImage]['description'] = unicode(text)
        self.emit(SIGNAL('imageChanged'))

    def setType(self, index):
        """Like setDescription, but for imagetype"""
        try:
            self.images[self.currentImage]['imagetype'] = index
            self.emit(SIGNAL('imageChanged'))
        except IndexError:
            pass

    def addImage(self, edit = False, filename = None):
        """Adds an image from the given filename to self.images.

        If a filename is not given, then an open file dialog is shown.
        If edit is True, then the current image is changed."""

        if not filename:
            filedlg = QFileDialog()
            filename = unicode(filedlg.getOpenFileName(self,
                QApplication.translate("Artwork", 'Select Image...'), self.lastfilename,
                QApplication.translate("Artwork", "JPEG Images (*.jpg);;PNG Images (*.png);;All Files(*.*)")))

        if not filename:
            return
        self.lastfilename = os.path.dirname(filename)
        data = open(filename, 'rb').read()
        pic = self.loadPics(filename)
        if pic:
            pic = pic[0]
            if edit and self.images:
                self.images[self.currentImage].update(pic)
                self.currentImage = self.currentImage
            else:
                if not self.images:
                    self.setImages([pic])
                else:
                    self.images.append(pic)
                    self.currentImage = len(self.images) - 1
            self.emit(SIGNAL('imageChanged'))
    
    def addImages(self, images):
        if not self._itags:
            return
        if self.images:
            index = len(self.images)
            self.images.extend(images)
            self.currentImage = index
        else:
            self.setImages(images)
        self.emit(SIGNAL('imageChanged'))

    def close(self):
        self.win.close()
        QWidget.close(self)

    def enableButtons(self):
        """Enables or disables buttons depending on context.

        With < 1 image in self.images,
        they're hidden unless overidden by self.showbuttons."""
        if not self.images:
            self.next.setEnabled(False)
            self.prev.setEnabled(False)
        else:
            if self.currentImage >= len(self.images) - 1:
                self.next.setEnabled(False)
            else:
                self.next.setEnabled(True)
            if self.currentImage <= 0:
                self.prev.setEnabled(False)
            else:
                self.prev.setEnabled(True)

        if not self.showbuttons and not self.next.isEnabled() and not self.prev.isEnabled():
            self.next.hide()
            self.prev.hide()
        else:
            self.next.show()
            self.prev.show()

    def _getCurrentImage(self):
        return self._currentImage

    def _setCurrentImage(self, num):
        try:
            while True:
                #A lot of files have corrupt picture data. I just want to
                #skip those and not have the user be any wiser.
                image = QImage().fromData(self.images[num]['data'])
                if image.isNull():
                    del(self.images[num])
                else:
                    break
            [action.setEnabled(True) for action in
                    (self.editpic, self.savepic, self.removepic)]
        except IndexError:
            self.setNone()
            return
        if hasattr(self, '_itags'):
            self.setImageTags(self._itags)
        if num in self.readonly:
            self.editpic.setEnabled(False)
            self.removepic.setEnabled(False)
            self._image_desc.setEnabled(False)
            self._image_type.setEnabled(False)
        self.pixmap = QPixmap.fromImage(image)
        self.win.setImage(self.pixmap)
        #pdb.set_trace()
        #self.label.setPixmap(self.pixmap)

        self._image_desc.blockSignals(True)
        desc = self.images[num].get('description', QApplication.translate("Artwork", 'Enter a description'))
        self._image_desc.setText(desc)
        self._image_desc.blockSignals(False)
        self._image_type.blockSignals(True)
        try:
            self._image_type.setCurrentIndex(self.images[num]['imagetype'])
        except KeyError:
            self._image_type.setCurrentIndex(3)
        self._image_type.blockSignals(False)
        self._currentImage = num
        self.context = unicode(self._contextFormat.arg(unicode(num + 1)).arg(unicode(len(self.images))))
        self.label.setFrameStyle(QFrame.NoFrame)        
        self.enableButtons()
        self.resizeEvent()

    currentImage = property(_getCurrentImage, _setCurrentImage,"""Get or set the index of
    the current image. If the index isn't valid
    then a blank image is loaded.""")

    def maxImage(self):
        """Shows a window with the picture fullsized."""
        if self.pixmap:
            if self.win.isVisible():
                self.win.hide()
            else:
                self.win = PicWin(self.pixmap, self)
                self.win.show()

    def nextImage(self):
        self.currentImage += 1

    def prevImage(self):
        self.currentImage -= 1

    def saveToFile(self):
        """Opens a dialog that allows the user to save,
        the image in the current file to disk."""
        if self.currentImage > -1:
            filedlg = QFileDialog()
            filedlg.setNameFilters(filters.keys())
            if self.lastfilename:
                tempfilename = os.path.splitext(self.lastfilename)[0] + u'.jpg'
            else:
                tempfilename = ''
            filename = filedlg.getSaveFileName(self,
                QApplication.translate("Artwork", 'Save as...'), tempfilename,
                QApplication.translate("Artwork", "JPEG Images (*.jpg);;PNG Images (*.png);;All Files(*.*)"))
            if not filename:
                return
            filt = unicode(filedlg.selectedNameFilter())
            if not self.pixmap.save(filename):
                QMessageBox.critical(self, QApplication.translate("Defaults", 'Error'),
                    QApplication.translate("Artwork", 'Writing to <b>%1</b> failed.').arg(filename))

    def setNone(self):
        self.label.setFrameStyle(QFrame.Box)
        self.label.setPixmap(QPixmap())
        self.pixmap = None
        self.images = []
        self._image_desc.setEnabled(False)
        self._image_type.setEnabled(False)
        [action.setEnabled(False) for action in
                    (self.editpic, self.savepic, self.removepic)]
        self.context = u'No Images'


    def setImages(self, images, imagetags = None):
        """Sets images. images are dictionaries as described in the class docstring."""
        if imagetags:
            self.setImageTags(imagetags)
        if images:
            self.images = images
            self.currentImage = 0
        else:
            self.setNone()
        self.enableButtons()


    def removeImage(self):
        """Removes the current image."""
        if len(self.images) >= 1:
            del(self.images[self.currentImage])
            if self.currentImage >= len(self.images) - 1 and self.currentImage > 0:
                self.currentImage = len(self.images) - 1
            else:
                self.currentImage =  self.currentImage
        self.emit(SIGNAL('imageChanged'))

    def loadPics(self, *filenames):
        """Loads pictures from the filenames"""
        images = []
        for filename in filenames:
            image = QImage()
            if image.load(filename):
                try:
                    data = open(filename, 'rb').read()
                except IOError, e:
                    if filename.startswith(u':/'):
                        ba = QByteArray()
                        data = QBuffer(ba)
                        data.open(QIODevice.WriteOnly)
                        image.save(data, "JPG")
                        data = data.data()
                    else:
                        raise e
                pic = {'data': data, 'height': image.height(),
                    'width': image.width(), 'size': len(data),
                    'mime': 'image/jpeg',
                    'description': unicode(QApplication.translate("Artwork", 'Enter description')),
                    'imagetype': 3}
                images.append(pic)
        return images

    def setImageTags(self, itags):
        tags = {DESCRIPTION: self._image_desc.setEnabled,
                DATA: self.label.setEnabled,
                IMAGETYPE: self._image_type.setEnabled}
        self.enableButtons()
        if not itags:
            self.addpic.setEnabled(False)
        else:
            self.addpic.setEnabled(True)
        for z in itags:
            try:
                tags[z](True)
            except KeyError:
                pass

        others = [z for z in tags if z not in itags]
        if len(others) == len(tags):
            self.next.setEnabled(False)
            self.prev.setEnabled(False)
        for z in others:
            tags[z](False)
        self._itags = itags
    
    def resizeEvent(self, event=None):
        if event is not None:
            QWidget.resizeEvent(self, event)
        if self.pixmap:
            labelheight = self.label.height()
            labelwidth = self.label.width()
            ratio = labelheight / float(labelwidth)

            maxheight = int(labelheight / ratio)
            maxwidth = int(labelwidth * ratio)

            if maxwidth > maxheight:
                pixmap = self.pixmap.scaledToHeight(maxheight - 10)
            else:
                pixmap = self.pixmap.scaledToWidth(maxwidth - 10)

            self.label.setPixmap(pixmap)


class PicWin(QDialog):
    """A windows that shows an image."""
    def __init__(self, pixmap = None, parent = None):
        """Loads the image specified in QPixmap pixmap.
        If picture is clicked, the window closes.

        If you don't want to load an image when the class
        is created, let pixmap = None and call setImage later."""
        QDialog.__init__(self, parent)
        self.setWindowTitle('Album Art')
        self.label = Label()

        vbox = QVBoxLayout()
        vbox.setMargin(0)
        vbox.addWidget(self.label)
        self.setLayout(vbox)

        if pixmap is not None:
            self.setImage(pixmap)

        self.connect(self.label, SIGNAL('clicked()'), self.close)

    def setImage(self, pixmap):
        
        screensize = QDesktopWidget().availableGeometry()
        screen_side = screensize.height() **2 + screensize.width() ** 2
        pix_side = pixmap.height() **2 + pixmap.width() ** 2
        if pix_side > screen_side:
            pixmap = pixmap.scaled(screensize.size())
        self.setMaximumSize(pixmap.size())
        self.setMinimumSize(pixmap.size())
        self.label.setPixmap(pixmap)
        self.resize(pixmap.size())

class ProgressWin(QDialog):
    def __init__(self, parent=None, maximum = 100, progresstext = '', showcancel = True):
        QDialog.__init__(self, parent)
        self._infunc = False
        self._cached = 0
        self.setModal(True)
        self.setWindowTitle(QApplication.translate("Progress Dialog", "Please Wait..."))
        self._format = QApplication.translate("Progress Dialog",
            '%1%2 of %3...')

        self.ptext = progresstext

        self.pbar = QProgressBar(self)

        self.pbar.setRange(0, maximum)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignHCenter)

        if maximum <= 0:
            self.pbar.setTextVisible(False)
            self.label.setVisible(False)

        cancel = QPushButton(QApplication.translate("Defaults", 'Cancel'))
        cbox = QHBoxLayout()
        cbox.addStretch()
        cbox.addWidget(cancel)
        cancel.setVisible(showcancel)

        vbox = QVBoxLayout()
        vbox.addWidget(self.label)
        vbox.addWidget(self.pbar)
        vbox.addLayout(cbox)
        self.setLayout(vbox)
        self.wasCanceled = False
        self.connect(self, SIGNAL('rejected()'), self.cancel)
        self.connect(cancel, SIGNAL('clicked()'), self.cancel)
        
        if maximum > 0:
            self.setValue(1)
        else:
            timer = QTimer(self)
            timer.setInterval(100)
            update = lambda: self.setValue(self.pbar.value() + 1)
            self.connect(timer, SIGNAL('timeout()'), update)
            timer.start()

    def setValue(self, value):
        if self._infunc:
            return
        self._infunc = True
        if self.ptext:
            self.pbar.setTextVisible(False)
            self.label.setText(
                self._format.arg(self.ptext).arg(value).arg(self.pbar.maximum()))
        self.pbar.setValue(value)
        self._infunc = False
        if self.pbar.maximum() and value >= self.pbar.maximum():
            self.close()

    def cancel(self):
        self.wasCanceled = True
        self.emit(SIGNAL('canceled()'))
        self.close()

    def _value(self):
        return self.pbar.value()

    value = property(_value)

class PuddleCombo(QWidget):
    def __init__(self, name, default = None, parent = None):
        QWidget.__init__(self, parent)
        hbox = QHBoxLayout()
        hbox.setMargin(0)
        self.combo = QComboBox()
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)

        self.remove = QToolButton()
        self.remove.setIcon(get_icon('list-remove', ':/remove.png'))
        self.remove.setToolTip(QApplication.translate("Combo Box", 'Remove current item.'))
        self.remove.setIconSize(QSize(13, 13))
        self.connect(self.remove, SIGNAL('clicked()'), (self.removeCurrent))

        hbox.addWidget(self.combo)
        hbox.addWidget(self.remove)
        self.setLayout(hbox)
        
        self.combo.setEditable(True)

        self.setEditText = self.combo.setEditText
        self.currentText = self.combo.currentText
        
        self.name = name
        cparser = PuddleConfig()
        self.filename = os.path.join(os.path.dirname(cparser.filename), 'combos')
        if not default:
            default = []
        cparser.filename = self.filename
        items = cparser.load(self.name, 'values', default)
        newitems = []
        [newitems.append(z) for z in items if z not in newitems]
        self.combo.addItems(newitems)
        self.connect(self.combo, SIGNAL('editTextChanged(const QString&)'),
                self._editTextChanged)

    def load(self, name = None, default = None):
        if name:
            self.name = name
        if not default:
            default = []
        self.combo.clear()
        self.combo.addItems(cparser.load(self.name, 'values', default))

    def save(self):
        values = [unicode(self.combo.itemText(index)) for index in xrange(self.combo.count())]
        values.append(unicode(self.combo.currentText()))
        cparser = PuddleConfig(self.filename)
        cparser.setSection(self.name, 'values', values)

    def removeCurrent(self):
        self.combo.removeItem(self.combo.currentIndex())

    def _editTextChanged(self, text):
        self.emit(SIGNAL('editTextChanged(const QString&)'), text)
    
    def closeEvent(self, event):
        QWidget.closeEvent(self, event)

        self.save()

class PuddleDock(QDockWidget):
    """A normal QDockWidget that emits a 'visibilitychanged' signal
    when...uhm...it changes visibility."""
    _controls = {}

    def __init__(self, title, control=None, parent=None, status=None):
        QDockWidget.__init__(self, QApplication.translate("Dialogs", title), parent)
        self.title = title
        if control:
            control = control(status=status)
            self.setObjectName(title)
            self._control = control
            self._controls.update({title: control})
            self.setWidget(control)

    def setVisible(self, visible):
        QDockWidget.setVisible(self, visible)
        self.emit(SIGNAL('visibilitychanged'), visible)

class PuddleHeader(QHeaderView):
    def __init__(self, orientation = Qt.Horizontal, parent = None):
        if parent:
            super(PuddleHeader, self).__init__(orientation, parent)
        else:
            super(PuddleHeader, self).__init__()
        
        self.setSortIndicatorShown(True)
        self.setSortIndicator(0, Qt.AscendingOrder)
        self.setMovable(True)
        self.setClickable(True)
    
    def getMenu(self, actions = None):
        model = self.model()

        def create_action(section):
            title = model.headerData(section, self.orientation()).toString()
            action = QAction(title, self)
            action.setCheckable(True)
            def change_visibility(value):
                if value:
                    self.showSection(section)
                else:
                    self.hideSection(section)
            if self.isSectionHidden(section):
                action.setChecked(False)
            else:
                action.setChecked(True)
            self.connect(action, SIGNAL('toggled(bool)'), change_visibility)
            return action

        header_actions = [create_action(section) 
            for section in range(self.count())]
            
        menu = QMenu(self)
        if actions:
            [menu.addAction(a) for a in actions]
            menu.addSeperator()
        [menu.addAction(a) for a in header_actions]
        return menu
    
    def contextMenuEvent(self, event):
        menu = self.getMenu()
        menu.exec_(event.globalPos())
        
    

class PuddleStatus(object):
    _status = {}

    def __init__(self):
        object.__init__(self)
    def __setitem__(self, name, val):
        self._status[name] = val

    def __getitem__(self, name):
        x = self._status.get(name)
        if callable(x):
            return x()
        return x

class PuddleThread(QThread):
    """puddletag rudimentary threading.
    pass a command to run in another thread. The result
    is stored in retval."""
    def __init__(self, command, parent = None):
        QThread.__init__(self, parent)
        self.connect(self, SIGNAL('finished()'), self._finish)
        self.command = command

    def run(self):
        #print 'thread', self.command, time.time()
        try:
            self.retval = self.command()
        except StopIteration:
            self.retval = 'STOP'

    def _finish(self):
        if hasattr(self, 'retval'):
            self.emit(SIGNAL('threadfinished'), self.retval)
        else:
            self.emit(SIGNAL('threadfinished'), None)

class ShortcutEditor(QLineEdit):
    def __init__(self, shortcuts=None, *args, **kwargs):
        QLineEdit.__init__(self, *args, **kwargs)
        winsettings('shortcutcapture', self)

        self.key = ""
        self.modifiers = {}
        self._valid = False
        if shortcuts is None:
            shortcuts = []
        self._shortcuts = shortcuts

    def clear(self):
        super(ShortcutEditor, self).clear()
        self.valid = False

    def keyPressEvent(self, event):

        text = u''

        if event.modifiers():
            text = modifiers[int(event.modifiers())]

        if event.key() not in mod_keys:
            if text:
                text += u'+' + unicode(QKeySequence(event.key()).toString())
            else:
                text = unicode(QKeySequence(event.key()).toString())

            if text and text not in self._shortcuts:
                valid = True
            else:
                valid = False
        else:
            valid = False

        self.setText(text)
        self.valid = valid

    def _getValid(self):
        return self._valid

    def _setValid(self, value):
        self._valid = value
        self.emit(SIGNAL('validityChanged'), value)

    valid = property(_getValid, _setValid)


if __name__ == '__main__':
    class MainWin(QDialog):
        def __init__(self, parent = None):
            QDialog.__init__(self, parent)
            self.combo = PuddleCombo('patterncombo', [u'%artist% - $num(%track%, 2) - %title%', u'%artist% - %title%', u'%artist% - %album%', u'%artist% - Track %track%', u'%artist% - %title%', u'%artist%'])

            hbox = QHBoxLayout()
            hbox.addWidget(self.combo)
            self.setLayout(hbox)

        def closeEvent(self,e):
            self.combo.save()
            QDialog.closeEvent(self, e)

    app = QApplication(sys.argv)
    widget = MainWin()
    widget.show()
    app.exec_()
