#!/usr/bin/python
# -*- coding: utf-8 -*-
import wx
import os
import re

config_file  = "clipman.conf"
program_name = "Clipman"
version      = "0.15"
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

def limit_size(text, max_line_length, max_lines):
	result = u""
	lines = text.split(os.linesep)
	for i, line in enumerate( lines ):
		if len(line) >= max_line_length:
			result += line[:max_line_length-3] + "..."
		else:
			result += line
		if i != len(lines) - 1:
			#if len(line) == 0:
				#result += u"⁋"
			#else:
			result+= "\n"

	result.replace("\t", "")

	return result

def menu_from_iterable(menu, element_list, function_factory):
	for element in element_list: pass

class Configuration(object):
	def __init__(self):
		self.Icon = "icon.png"
		self.RecentHistoryFile = "recent.history"
		self.FixedEntriesFile  = "fixed.history"

		self.MaxRecentEntries  = 15
		self.MaxFixedEntries   = 5
		self.MaxOlderEntries   = 35

		self.MaxLineLength    = 64
		self.MaxLinesPerPaste = 2

		self.MoveFixedToTopUponSelection = True

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
		self.FixedHistory  = LoadableList()
		self.OlderHistory  = LoadableList()

		self.Configuration = conf
	def Load(self, recent = None, fixed = None, rest = None):
		if recent != None:
			self.RecentHistory.FromFile(recent)
		if fixed  != None:
			self.FixedHistory.FromFile(fixed)
		if rest   != None:
			self.OlderHistory.FromFile(rest)
	def Save(self, recent = None, fixed = None, rest = None):
		if recent != None:
			self.RecentHistory.ToFile(recent)
		if fixed  != None:
			self.FixedHistory.ToFile(fixed)
		if rest   != None:
			self.OlderHistory.ToFile(rest)
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

		if len(rh) > self.Configuration.MaxRecentEntries:
			oh += rh[0]
			del rh[0]

		if len(oh) > self.Configuration.MaxOlderEntries:
			del oh[0]
	def AddFixed(self, element):
		if element in self.FixedHistory: return None
		else:
			self.FixedHistory += [ element ]

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
			line = line.decode('utf-8')
			line = line.replace(os.linesep, u"")
			line = line.replace(u"\\n", os.linesep)
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
		self.Timer.Start(100)
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

	def ChooseItem(self, index):
		rh = self.History.RecentHistory

		wx.TheClipboard.Open()
		data_object = wx.TextDataObject()
		data_object.Text = rh[index]
		success = wx.TheClipboard.SetData(data_object)
		wx.TheClipboard.Close()

		del rh[index]
	def ChooseFixedItem(self, index):
		fh = self.History.FixedHistory

		wx.TheClipboard.Open()
		data_object = wx.TextDataObject()
		data_object.Text = fh[index]
		success = wx.TheClipboard.SetData(data_object)
		wx.TheClipboard.Close()

		if self.Configuration.MoveFixedToTopUponSelection:
			item = fh[index]
			del fh[index]
			fh += [ item ]

	def ClearRecent(self, event):
		self.RecentHistory = []
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

		rh = self.History.RecentHistory
		fh = self.History.FixedHistory

		for i, h_item in enumerate( reversed(rh) ):
			if i == 0: item_id = wx.ID_FORWARD
			else:      item_id = wx.ID_ANY

			h_item = limit_size( h_item, self.Configuration.MaxLineLength, self.Configuration.MaxLinesPerPaste )
			i = len(rh) - i - 1

			item = menu.Append(item_id, h_item)
			func = lambda e, i = i: self.ChooseItem(i)

			menu.Bind(wx.EVT_MENU, func, item)

		menu.AppendSeparator()
		fix = menu.Append(wx.ID_ADD, self.History.Current)
		self.Bind(wx.EVT_MENU, self.AddFixed, fix)

		if len(fh) > 0:
			fl = self.Configuration.MaxFixedEntries
			for i in range( min(fl, len(fh)) ):
				h_item = fh[i]
				h_item = limit_size( h_item, self.Configuration.MaxLineLength, self.Configuration.MaxLinesPerPaste )

				item = menu.Append(wx.ID_ANY, h_item)
				func = lambda e, i = i: self.ChooseFixedItem(i)

				menu.Bind(wx.EVT_MENU, func, item)
			if len(fh) > fl:
				fixed_submenu = wx.Menu()
				for i in range(fl, len(fh)):
					h_item = fh[i]
					h_item = limit_size( h_item, self.Configuration.MaxLineLength, self.Configuration.MaxLinesPerPaste )

					item = fixed_submenu.Append(wx.ID_ANY, h_item)
					func = lambda e, i = i: self.ChooseFixedItem(i)

					menu.Bind(wx.EVT_MENU, func, item)
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