#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import re

from ConfigureCategoryFrame import ConfigureCategoryFrame

try:
    import wx
except:
    print "You need WXPython installed"
    exit()

config_file  = "clipman.conf"
program_name = "Clipman"
version      = "0.18"
subname      = "Herping softly"
name_ver_etc = "%s v%s - %s" % (program_name, version, subname)

def escape(string):
    string = string.replace(u"\\", u"\\\\")
    string = string.replace(os.linesep, u"\\n")
    return string

def unescape(string):
    def rep(m):
        return m.group(1) + "\n"
    string = string.replace(os.linesep, u"")
    string = re.sub(r"([^\\])\\n", rep, string)
    string = string.replace("\\\\", "\\")
    return string

class SaveableClass(object):
    def FromFile(self, filename):
        try:
            f = open(filename, 'r')
        except:
            return None
        for line in f.readlines():
            variable, value = re.split("\s*=\s*", line)
            self.__dict__[variable] = eval(value)

    def ToFile(self, filename):
        f = open(filename, 'w')
        for item in self.__dict__:
            if type(item) not in [dict, list, int, float, str, unicode, bool]:
                #We're skipping anything aside from properties
                continue
            value = self.__dict__[item]
            f.write( "%s = %s%s" % (item, repr(value), os.linesep) )

class Category(SaveableClass):
    def __init__(self):
        self.RegexCapture   = False
        self.CapturePattern = ""
        self.LimitEntries   = False
        self.MaxEntryCount  = 35

        self.Entries = LoadableList()

def limit_size(text, configuration):
    maxlines = configuration.MaxLinesPerPaste
    maxlen = configuration.MaxLineLength

    result = u""
    lines = text.split(os.linesep)
    def f(line):
        return len(re.findall("[^\s]", line)) != 0
    lines = filter(f, lines)

    if len(lines) == 0: return ""

    if len(lines[0]) > maxlen:
        result += "%s..." % lines[0][:maxlen-3]
    else:
        result += lines[0]

    for i, line in enumerate(lines[1:]):
        if i >= maxlines:
            result+="\n. . ."
            break
        if len(line) > maxlen:
            line = "%s..." % line[:maxlen-3]
        result += "\n%s" % line

    return result.replace("\t", "    ")

def menu_from_iterable(menu, element_list, function_factory, offset = 0):
    for i in range( len(element_list) ):
        value = element_list[i]
        i += offset
        item = menu.Append(wx.ID_ANY, value)
        func = function_factory(i)
        menu.Bind(wx.EVT_MENU, func, item)

def set_clipboard(text):
    wx.TheClipboard.Open()
    data_object = wx.TextDataObject()
    data_object.Text = text
    success = wx.TheClipboard.SetData(data_object)
    wx.TheClipboard.Close()

    return success

class Configuration(SaveableClass):
    def __init__(self):
        self.Icon = "icon.png"
        self.RecentHistoryFile = "recent.history"
        self.CategoriesFile    = "fixed.categories"
        self.CategoriesExtension = ".list"

        self.MaxRecentEntries  = 15
        self.MaxOlderEntries   = 35
        self.MaxCategories     = 5

        self.MaxLineLength    = 64
        self.MaxLinesPerPaste = 2

        self.SkipEmptyLines   = True

        self.ClipboardSyncFrequency = 100

        self.MoveFixedToTopUponSelection = True
        self.MoveCategoryToTopUponSelection = False

        self.AlwaysShowFixedEditButton = True

class History(object):
    def __init__(self, conf):
        self.Current       = ""
        self.RecentHistory = LoadableList()
        self.OlderHistory = LoadableList()

        self.CategoryList  = LoadableList()
        self.Categories    = {  }

        self.Configuration = conf
    def Load(self):
        self.RecentHistory.FromFile(self.Configuration.RecentHistoryFile)
        if len(self.RecentHistory) > 0:
            self.Current = self.RecentHistory[-1]

        self.CategoryList.FromFile(self.Configuration.CategoriesFile)

        ext = self.Configuration.CategoriesExtension
        for cat in self.CategoryList:
            self.Categories[cat] = LoadableList()
            self.Categories[cat].FromFile("%s%s" % (cat, ext) )


    def Save(self):
        self.RecentHistory.ToFile(self.Configuration.RecentHistoryFile)

        self.CategoryList.ToFile(self.Configuration.CategoriesFile)

        ext = self.Configuration.CategoriesExtension
        for cat in self.CategoryList:
            self.Categories[cat].ToFile("%s%s" % (cat, ext) )

    def Add(self, element):
        self.Current = element

        rh = self.RecentHistory
        oh = self.OlderHistory

        if element in oh:
            index = oh.index(element)
            del oh[ index ]

        if element not in rh:
            rh += [element]
        elif element != rh[-1]:
            index = rh.index(element)
            del rh[ index ]
            rh += [element]

        if len(rh) >= self.Configuration.MaxRecentEntries:
            oh += rh[0]
            del rh[0]

        if len(oh) >= self.Configuration.MaxOlderEntries:
            del oh[0]
    def AddFixed(self, category, element):
        c = self.Categories[category]
        if element in c: return None
        else:
            c += [ element ]

class LoadableList(list):
    def ToFile(self, filename):
        try:
            f = open(filename, 'w')
        except:
            return None

        for item in self.__iter__():
            item = escape(item)
            data = "%s%s" % (item, os.linesep)
            data = data.encode('utf-8')
            f.write(data)

    def FromFile(self, filename):
        try:
            f = open(filename, 'r')
        except:
            return None #It's not a big deal. First run perhaps.

        for line in f.readlines():
            line = line.decode('utf-8')
            line = unescape(line)
            self.__iadd__( [line] )

class ClipmanIcon(wx.TaskBarIcon):
    def __init__(self):
        wx.TaskBarIcon.__init__(self)

        self.Configuration = Configuration()
        self.Configuration.FromFile(config_file)

        self.Icon = wx.IconFromBitmap( wx.Bitmap(self.Configuration.Icon) )
        self.UpdateIcon()
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.OnLMBDown)

        self.Timer = wx.Timer(self)
        self.Timer.Start(self.Configuration.ClipboardSyncFrequency)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.Timer)

        self.History = History(self.Configuration)
        self.History.Load()

    def OnTimer(self, event):
        wx.TheClipboard.Open()
        data_object = wx.TextDataObject()
        success = wx.TheClipboard.GetData(data_object)
        wx.TheClipboard.Close()

        if not success: return None
        text = data_object.Text

        self.History.Add(text)

    def MenuExit(self, event):
        self.Configuration.ToFile(config_file)
        self.History.Save()

        self.Timer.Destroy()
        wx.CallAfter(self.Destroy)

    def MenuConfigure(self, event):
        win = PreferencesWindow(self)
        win.Show()

    def MenuAbout(self, event):
        title = "About %s" % program_name
        message = "Version %s\n" % version
        message += "    codename %s\n" % subname
        message += "\n"
        message += "Copyleft 2011-2012 Asmageddon"
        dialog = wx.MessageDialog(None, message, title, wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

    def OnLMBDown(self, event):
        self.PopupMenu(self.CreateHistoryMenu())

    def UpdateIcon(self):
        self.SetIcon(self.Icon, "Derpo derpo")

    def ChooseCategoryItem(self, category, index):
        cat = self.History.Categories[category]
        index = len(cat) - index - 1
        set_clipboard( cat[index] )

    def ChooseItem(self, index):
        rh = self.History.RecentHistory
        index = len(rh) - index - 1

        set_clipboard( rh[index] )

        del rh[index]
    def ChooseFixedItem(self, category, index):
        fh = self.History.Categories[category]

        index = len(fh) - index - 1

        set_clipboard( fh[index] )

        if self.Configuration.MoveFixedToTopUponSelection:
            item = fh[index]
            del fh[index]
            fh += [ item ]

    def ClearRecent(self, event):
        del self.History.RecentHistory[:-1]
        self.OnTimer(None)

    def CreatePopupMenu(self):
        menu = wx.Menu()

        item_name = menu.Append(wx.ID_ANY, name_ver_etc)
        item_name.Enable(False)

        menu.AppendSeparator()

        item_about = menu.Append(wx.ID_ABOUT, 'About')
        menu.Bind(wx.EVT_MENU, self.MenuAbout)

        item_preferences = menu.Append(wx.ID_PREFERENCES, 'Preferences')
        menu.Bind(wx.EVT_MENU, self.MenuConfigure, item_preferences)

        menu.AppendSeparator()

        item_exit  = menu.Append(wx.ID_EXIT, 'Exit', 'Exit!')
        menu.Bind(wx.EVT_MENU, self.MenuExit, item_exit)

        return menu

    def ConfigureCategory(self, category):
        print "Configuring %s" % category
        conf = self.Configuration
        cat  = self.History.Categories[category]
        frame = ConfigureCategoryFrame(None, category = cat, configuration = conf)
        frame.Show()

    def CreateHistoryMenu(self):
        menu = wx.Menu()

        conf = self.Configuration

        rh = self.History.RecentHistory

        limiter = lambda item, c=conf: limit_size(item, c)

        rh2 = map(limiter, reversed(rh))

        def FuncFactory(i, self = self):
            return lambda e, i=i: self.ChooseItem(i)

        current = menu.Append(wx.ID_FORWARD, limiter(self.History.Current) )
        menu.Bind(wx.EVT_MENU, FuncFactory(0), current)

        menu_from_iterable(menu, rh2[1:], FuncFactory, 1)

        menu.AppendSeparator()

        fix = menu.Append(wx.ID_ANY, "Fixed entries")
        fix.Enable(False)

        for cat in self.History.CategoryList:
            submenu = wx.Menu()

            def FuncFactory(i, self = self, cat = cat):
                return lambda e, i=i, cat = cat: self.ChooseFixedItem(cat, i)
            def AddFuncFactory(self = self, cat = cat):
                return lambda e, cat = cat: self.AddFixed(cat)
            def ConfigureFuncFactory(self = self, cat = cat):
                return lambda e, cat = cat: self.ConfigureCategory(cat)

            curtext = limit_size(self.History.Current, self.Configuration)
            curtext = curtext.split('\n')[0]
            add = submenu.Append(wx.ID_ADD, 'Add "%s"' % curtext)
            submenu.Bind(wx.EVT_MENU, AddFuncFactory(), add)

            cc = self.History.Categories[cat]
            cc = map(limiter, reversed(cc))

            menu_from_iterable(submenu, cc, FuncFactory)

            submenu.AppendSeparator()

            configure = submenu.Append(wx.ID_PREFERENCES, 'Configure "%s"' % cat)
            submenu.Bind(wx.EVT_MENU, ConfigureFuncFactory(), configure)

            menu.AppendMenu(wx.ID_ANY, cat, submenu)

        menu.AppendSeparator()

        clear = menu.Append(wx.ID_CLEAR, "Clear")

        menu.Bind(wx.EVT_MENU, self.ClearRecent, clear)

        return menu

    def AddFixed(self, category):
        self.History.AddFixed(category, self.History.Current)

class ClipmanApp(wx.App):
    def __init__(self):
        wx.App.__init__(self, False)
        icon = ClipmanIcon()

try:
    app = ClipmanApp()
    app.SetTopWindow(wx.Frame(None, -1))
    app.MainLoop()
except KeyboardInterrupt:
    print "Received keyboard interrupt, C'ya!"
    app.Destroy()