####################################
# File name: logParser.py          #
# Author: Shawn Wu                 #
# Email: swu@fitbit.com            #
# Date created: 06/08/2018          #
####################################

import re
import os
import datetime
import sys

class Event(object):
	def __init__(self):
		super(Event, self).__init__()
		self.errorCount = 0
		self.startTime = ""
		self.state = "unknown"

class Logger(object):
	def __init__(self, fileName):
		super(Logger, self).__init__()
		filename = fileName
		self.f = open(filename,"w+")

	def write(self, line):
		self.f.write(line)
		self.f.write("\n")
		print(line)

	def close(self):
		self.f.close()
		
class Processer(object):
	def __init__(self, logger, processerName, eventId, printAllState, productName):
		super(Processer, self).__init__()

		self.startReg = re.compile(r'stats \| '+ eventId +' - Start')
		self.endReg = re.compile(r'stats \| '+ eventId +' - End')

		self.eventReg = re.compile(r'stats \| '+ eventId +' -')
		self.timeReg = re.compile(r'    \|.+?(?=\| stats )')
		
		# check if the error is null
		self.noErroReg = re.compile(r'"error":null')

		# print the error if exists
		self.genErroReg = re.compile(r'"error":.+?(?=\})')
		self.stateReg = re.compile(r'"completion_state":"Success"')
		self.nameReg = re.compile(r'device_name\":\"'+ productName)
		self.stack = []
		self.processerName = processerName
		self.logger = logger
		self.printAllState = printAllState
		self.productName = productName

	def processEventIfNecessary(self, line):
		# check if it is a event related line
		if self.eventReg.search(line) and self.nameReg.search(line):
			self.printStateIfNecessary(line)
			self.checkError(line)
			self.checkEventStart(line)
			self.checkEventEnd(line)

	def printStateIfNecessary(self, line):
		if self.printAllState is True:
			self.logger.write(line)

	def checkError(self, line):
	    # check if there's an error statement
		if self.genErroReg.search(line):
			# if the error is not null, print it
			if self.noErroReg.search(line) is None:
				self.logger.write("found a " + self.processerName +" error: ")
				self.logger.write(line)
				self.addNewEventIfNecessary()
				self.stack[-1].errorCount = self.stack[-1].errorCount + 1

	def checkEventStart(self, line):
		if self.startReg.search(line):
			self.logger.write("")
			self.logger.write("||------------" + self.processerName + "----------------")
			event = Event()
			event.startTime = self.getTime(line)
			self.stack.append(event)
			self.logger.write("start processing a new " + self.productName + " " + self.processerName + " at time " + event.startTime)

	def checkEventEnd(self, line):
		if self.endReg.search(line):
			self.addNewEventIfNecessary()
			if self.stack[-1].errorCount > 0:
				self.logger.write("a " + self.processerName + " started at: " + self.stack[-1].startTime + " falied " + str(self.stack[-1].errorCount) + " times")
			
			if self.stateReg.search(line):
				self.stack[-1].state = "success"
			else:
				self.stack[-1].state = "fail"
			
			self.logger.write("finish processing a " + self.productName + " " + self.processerName + " at time " + self.getTime(line) + ", state: " + self.stack[-1].state)
			self.logger.write("--------------" + self.processerName + "--------------||")
			self.logger.write("")

	def getTime(self, line):
		time = ""
		if self.timeReg.search(line):
		    time = self.timeReg.findall(line)[0][6:-1]
		return time

	def addNewEventIfNecessary(self):
		if len(self.stack) == 0:
			event = Event()
			self.stack.append(event)


	def eval(self):
		success = 0
		fail = 0
		for event in self.stack:
			if event.state == "success":
				success += 1
			elif event.state == "fail":
				fail += 1

		self.logger.write("processer completed " + str(len(self.stack)) + " " + self.processerName + " for this directory, success: " + str(success) + " fail: " + str(fail) + " unknown: " + str(len(self.stack) - success - fail))


class Gatt(Processer):
	def __init__(self, logger, processerName, eventId, productName):
		super(Gatt, self).__init__(logger, processerName, eventId, True, productName)
		self.state = False
		self.nameReg = re.compile(r'device_name\":\"'+ productName)
		self.connectReg = re.compile(r'stats \| Gatt - Connect')
		self.disconnectReg = re.compile(r'stats \| Gatt - Disconnect')

	def printStateIfNecessary(self, line):
		if self.printAllState is True:
			if self.nameReg.search(line):
				if self.connectReg.search(line):
					self.setState(True, line)
				elif self.disconnectReg.search(line):
					self.setState(False, line)

	def eval(self):
		pass

	def checkError(self, line):
		pass

	def setState(self, state, line):
		if self.state == state:
			return
		self.state = state
		self.logger.write("")
		self.logger.write("||------------" + self.processerName + "----------------")
		if self.state is True:
			self.logger.write("tracker " + self.productName + " is connected at time " + self.getTime(line))
		else:
			self.logger.write("tracker " + self.productName + " is disconnected at time " + self.getTime(line))
		self.logger.write("--------------" + self.processerName + "--------------||")
		self.logger.write("")	

def processFile(processers, filePath, logger):
	# errorLogReg = re.compile(r'ERROR   \| Bluetooth')
	with open(filePath, "r") as file:
	    for line in file:
			for processer in processers:
				processer.processEventIfNecessary(line)
			# if errorLogReg.search(line):
			# 	logger.write(line)

def main():
	if len(sys.argv) == 1:
		name = ""
	else:
		name = sys.argv[1]
	fs = os.listdir(".")
	for f in fs:
		if os.path.isdir(f):
			logger = Logger(f+".txt")
			
			processers = []
			processers.append(Gatt(logger, "gatt", "Gatt", name))
			processers.append(Processer(logger, "pair", "PairBluetoothTask", False, name))
			processers.append(Processer(logger, "firmware update", "FirmwareUpdate", False, name))
			processers.append(Processer(logger, "sync", "Sync", False, name))

			ls = os.listdir(f)
			ls.sort()
			for name in ls:
				filename = os.path.join(f, name)
				if re.compile(r'.+?(?=\log)').search(name):
					logger.write("||--------------------------" + name + "--------------------------------------")
					logger.write("start reading file " + filename)

					processFile(processers, filename, logger)

					logger.write("finish reading " + name + " file. ")
					logger.write("----------------------------" + name + "------------------------------------||")
					logger.write("")

			for processer in processers:
				processer.eval()

main()
