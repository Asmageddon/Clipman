#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import re

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

class PreferencesWindow(wx.Frame):
	def __init__(self, parent):
		self.ClipmanIcon = parent
		wx.Frame.__init__(self, None, size=(320,320), title="Preferences")
		tabs = wx.Notebook(self)

		pan = wx.Panel(tabs)
		tabs.AddPage(pan, "General")

		vbox = wx.BoxSizer(wx.VERTICAL)

		button = wx.Button(pan, label="herpo")
		vbox.Add(button, 1)
		button2 = wx.Button(pan, label="derpo")
		vbox.Add(button2, 1)

		pan.SetSizer(vbox)

		self.Bind(wx.EVT_CLOSE, self.OnClose)

	def OnClose(self, event):
		self.Destroy()

def limit_size(text, configuration):
	maxlines = configuration.MaxLinesPerPaste
	maxlen = configuration.MaxLineLength

	result = u""
	lines = text.split(os.linesep)
	def f(line):
		return len(re.findall("[^\s]", line)) != 0
	lines = filter(f, lines)

	if len(lines) == 0: return ""

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

class Configuration(object):
	def __init__(self):
		self.Icon = "icon.png"
		self.RecentHistoryFile = "recent.history"
		self.FixedEntriesFile  = "fixed.history"
		self.CategoryExtension = ".list"

		self.MaxRecentEntries  = 15
		self.MaxFixedEntries   = 5
		self.MaxOlderEntries   = 35
		self.MaxCategories     = 5

		self.MaxLineLength    = 64
		self.MaxLinesPerPaste = 2

		self.SkipEmptyLines   = True

		self.ClipboardSyncFrequency = 100

		self.MoveFixedToTopUponSelection = True
		self.MoveCategoryToTopUponSelection = False

		self.AlwaysShowFixedEditButton = True

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
			value = self.__dict__[item]
			f.write( "%s = %s%s" % (item, repr(value), os.linesep) )

class History(object):
	def __init__(self, conf):
		self.Current       = ""
		self.RecentHistory = LoadableList()
		self.FixedEntries  = LoadableList()
		self.OlderHistory  = LoadableList()

		self.Categories    = {  }

		self.Configuration = conf
	def Load(self, recent = None, fixed = None, rest = None):
		if recent != None:
			self.RecentHistory.FromFile(recent)
			if len(self.RecentHistory) > 0:
				self.Current = self.RecentHistory[-1]
		if fixed  != None:
			self.FixedEntries.FromFile(fixed)
		if rest   != None:
			self.OlderHistory.FromFile(rest)
		listing = os.listdir(os.curdir)
		ext = self.Configuration.CategoryExtension
		condition = lambda i: i.endswith(ext)
		for filename in filter(condition, listing):
			key = filename[:len(ext)]
			self.Categories[key] = LoadableList()
			self.Categories[key].FromFile(filename)
	def Save(self, recent = None, fixed = None, rest = None):
		if recent != None:
			self.RecentHistory.ToFile(recent)
		if fixed  != None:
			self.FixedEntries.ToFile(fixed)
		if rest   != None:
			self.OlderHistory.ToFile(rest)

		ext = self.Configuration.CategoryExtension
		for key in self.Categories:
			self.Categories[key].ToFile(key + ext)

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
	def AddFixed(self, element):
		if element in self.FixedEntries: return None
		else:
			self.FixedEntries += [ element ]

class LoadableList(list):
	def ToFile(self, filename):
		try:
			f = open(filename, 'w')
		except:
			dialog = wx.MessageDialog(self, "Couldn't save history to a file, sorry.", "Error", wx.OK)
			dialog.ShowModal()
			dialog.Destroy()
			return None

		for item in self.__iter__():
			item = item.replace(u"\\", u"\\\\")
			item = item.replace(os.linesep, u"\\n")
			data = "%s%s" % (item, os.linesep)
			data = data.encode('utf-8')
			f.write(data)

	def FromFile(self, filename):
		try:
			f = open(filename, 'r')
		except:
			return None #It's not a big deal. First run perhaps.

		for line in f.readlines():
			def rep(m):
				return m.group(1) + "\n"
			line = line.decode('utf-8')
			line = line.replace(os.linesep, u"")
			line = re.sub(r"([^\\])\\n", rep, line)
			line = line.replace("\\\\", "\\")
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
		self.History.Load(recent = self.Configuration.RecentHistoryFile)
		self.History.Load(fixed  = self.Configuration.FixedEntriesFile )

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
		self.History.Save(recent = self.Configuration.RecentHistoryFile)
		self.History.Save(fixed  = self.Configuration.FixedEntriesFile )

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
	def ChooseFixedItem(self, index):
		fh = self.History.FixedEntries

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

	def CreateHistoryMenu(self):
		menu = wx.Menu()

		conf = self.Configuration

		rh = self.History.RecentHistory
		fh = self.History.FixedEntries

		limiter = lambda item, c=conf: limit_size(item, c)

		rh2 = map(limiter, reversed(rh))

		def FuncFactory(i, self = self):
			return lambda e, i=i: self.ChooseItem(i)

		current = menu.Append(wx.ID_FORWARD, limiter(self.History.Current) )
		menu.Bind(wx.EVT_MENU, FuncFactory(0), current)

		menu_from_iterable(menu, rh2[1:], FuncFactory, 1)

		menu.AppendSeparator()
		fix = menu.Append(wx.ID_ADD, limiter(self.History.Current))
		self.Bind(wx.EVT_MENU, self.AddFixed, fix)

		if len(fh) > 0:
			fl = conf.MaxFixedEntries
			fh2 = map(limiter, reversed(fh))
			if len(fh2) > fl:
				fh2a = fh2[:fl]
				fh2b = fh2[fl:]
			else:
				fh2a = fh2
				fh2b = []

			def FuncFactory(i, self = self):
				return lambda e, i=i: self.ChooseFixedItem(i)

			menu_from_iterable(menu, fh2a, FuncFactory)
			if fh2b != [ ]:
				fixed_submenu = wx.Menu()
				menu_from_iterable(fixed_submenu, fh2b, FuncFactory, fl)
				menu.AppendMenu(wx.ID_MORE, "More", fixed_submenu)

		menu.AppendSeparator()

		clear = menu.Append(wx.ID_CLEAR, "Clear")

		menu.Bind(wx.EVT_MENU, self.ClearRecent, clear)

		return menu

	def AddFixed(self, event):
		self.History.AddFixed(self.History.Current)

class ClipmanApp(wx.App):
	def __init__(self):
		wx.App.__init__(self, False)
		icon = ClipmanIcon()

try:
	app = ClipmanApp()
	app.MainLoop()
except KeyboardInterrupt:
	print "Received keyboard interrupt, C'ya!"
	app.Destroy()