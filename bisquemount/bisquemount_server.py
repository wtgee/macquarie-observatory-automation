# coding: utf-8
#*************************************************************************#
#                    Code to control the Bisque mount                     #
#*************************************************************************#

import sys
import string
import select
import socket
from datetime import datetime
import time
import serial


#import binascii

#Open port 0 at "9600,8,N,1", timeout of 5 seconds
ser = serial.Serial(0)  #open first serial port. Need to change this when I find the address
print ser.portstr       #check which port was really used
                        #we open a serial port to talk to the focuser

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Make a client to communicate with the labjack and dome position
client_socket.connect(("10.72.26.145",3040))
#client_socket.settimeout(10)

class BisqueMountServer:

	dome_slewing_enabled = 0 #can enable disable automatic dome slewing

	def cmd_automaticDomeSlewing(self,the_command):
		'''Turn this on or off to determine whether the dome automatically updates
		it's position to the telescopes position.'''
		commands = str.split(the_command)
		if len(commands) == 1:
			if dome_slewing_enabled: return 'Automatic dome slewing is on.'
			else: return 'Automatic dome slewing is off.'
		elif len(commands) == 2:
			if commands[1] == 'on':
				self.dome_slewing_enabled = 1
				return 'Automatic dome slewing now enabled.'
			elif commands[1] == 'off':
				self.dome_slewing_enabled = 0
				return 'Automatic dome slewing now disabled.'
			else: return 'ERROR invalid input'
		else: return 'ERROR invalid input'

#**** SERIAL COMMANDS FOR THE FOCUSER *****#

	def cmd_focusGoToPositon(self,the_command):
		'''Tell the focuser to go to a position. User input currently unknown.
		16 bit position value sent as two bytes, most significant byte first.'''
		ser.write('g')
		response = ser.read()
		response = ser.read()
		if response == 'c': return 'Command complete'
		elif response == 'r': return 'Motor or encoder not working, operation terminated.'
		else: return 'ERROR, not sure what.'

	def cmd_focusReinitialise(self,the_command):
		'''Reinitialise the focuser. Will determine speed settings, store all data to
		the EEPROM, and move the focuser to the zero position.'''
		ser.write('h')
		response = ser.read()
		response = ser.read()
		if response == 'c': return 'Command complete'
		elif response == 'r': return 'Motor or encoder not working, operation terminated.'
		else: return 'ERROR, not sure what.'

	def cmd_focusReadPosition(self,the_command):
		'''This will read the position of the focuser.'''
		ser.write('p')
		response = ser.read()
		response = ser.read()
		return response
# coding: utf-8
	def cmd_focusReadStateRegister(self,the_command):
		'''After the focus controller receives the command byte, it will echo
		the command character back to the host, followed by the eight bit 
		status byte. All bits are active high; a 1 indicates the condition 
		is true, a 0 indicates it is false. Reading the device status resets
		the error conditions (bits 1 through 3 only).'''
		ser.write('t')
		response = ser.read()
		response = ser.read()
		message = ''
		if len(response) == 8:
			temp = list(response)
			if temp[1] == '1': message += 'Serial reciver framing error. '
			if temp[2] == '1': message += 'Serial reciver overrun error. '
			if temp[3] == '1': message += 'Motor/encoder error. '
			if temp[6] == '1': message += 'Focuser at zero position. '
			if temp[7] == '1': message += 'Focuser at maximum travel position. '
			return message
		else: return 'ERROR reading response from focuser.'

	def cmd_focusReadIdentityRegister(self,the_command): #What does this actually do?
		'''This command will allow the host to read the focus controller identify byte.
		This is a one byte command. The command character is ‘b’. After the focus
		controller receives the command byte, it will echo the command character back to
		the host, followed by the eight bit identify byte. This identify byte is a lower
		case ‘j’ (6Ah).'''
		ser.write('b')
		return ser.read()

	def cmd_focusWriteMaxTravelRegister(self,the_command): #NEED INPUT
		'''This command will allow the host to write the focus controller maximum 
		travel register. This command is used by the host PC to configure the focuser
		controller, based on the focuser characteristics defined by the user. When this
		command is received, all stored data in the EEPROM is updated.This is a three 
		byte command. The command character is ‘w’. This is followed by the desired 
		sixteen bit maximum count value, sent as two bytes, most significant byte first.'''
		ser.write('w')
		return ser.read()

	def cmd_focusWritePositionSpeedRegister(self,the_command): #NEED INPUT
		'''This command will allow the host to write the focus controller position speed
		register. This command is used by the host PC to configure the focuser controller,
		based on the focuser characteristics defined by the user. Position speed is used
		to move the focuser slowly when it is close to the desired Go To position. This is
		a three byte command. The command character is ‘d’. This is followed by the
		desired sixteen bit speed value, sent as two bytes, most significant byte first.'''
		ser.write('d')
		return ser.read()

	def cmd_focusWriteMoveSpeedRegister(self,the_command): #NEED INPUT
		'''This command will allow the host to write the focus controller move speed
		register. This command is used by the host PC to configure the focuser controller,
		based on the focuser characteristics defined by the user. Move speed is used to
		move the focuser slowly when a Move In or Move Out command is issued. It is also
		the speed the focuser moves when a pushbutton is pressed. This is a three byte
		command. The command character is ‘e’. This is followed by the desired sixteen bit
		speed value, sent as two bytes, most significant byte first.'''
		ser.write('e')
		return ser.write()

	def cmd_focusWriteShuttleSpeedRegister(self,the_command): #NEED INPUT
		'''This command will allow the host to write the focus controller shuttle speed 		register. This command is used by the host PC to configure the focuser controller,
		based on the focuser characteristics defined by the user. Shuttle speed is used to
		move the focuser rapidly during a Go To Position command, when far from the desired
		position. It is also the speed the focuser moves when a pushbutton is pressed for
		more than three seconds, and the motor speeds up. This is a three byte command. The
		command character is ‘f’. This is followed by the desired sixteen bit speed value,
		sent as two bytes, most significant byte first.'''
		ser.write('f')
		return ser.write()

	def cmd_focusSetZeroPosition(self,the_command):
		'''This command will set the Position register value to zero, regardless of the
		actual drawtube position. The position value stored in the EEPROM is also
		updated.'''
		ser.send('z')
		return ser.read()

	def cmd_focusMove(self,the_command):
		'''Tell the focuser to move in or out.'''
		commands = str.split(the_command)
		if len(commands) == 2:
			if commands[1] == 'in' or commands[1] == 'In':
				ser.send('i')
				message = ser.read()
				if message == 'r': return 'Motor or encoder not working'
				else: return message
			elif commands[1] == 'out' or commands[1] == 'Out':
				ser.send('o')
				message = ser.read()
				if message == 'r': return 'Motor or encoder not working'
				else: return message
			else: return 'ERROR invalid input'
		else: return 'ERROR invalid input'

	def cmd_fs(self,the_command):
		'''Stops focuser motion.'''
		ser.write('s')
		return ser.read()


		



#**** COMMANDS TO TALK TO MOUNT ****#
		

	def cmd_find(self,the_command):
		'''Will find an object in TheSky's Star chart and return data.'''
		commands = str.split(the_command)
		if len(commands) == 2:
			obj = commands[1]
			linestoreplace = ['sky6StarChart.Find("object");\r\n']
			newlines = ['sky6StarChart.Find("'+obj+'");\r\n']
			if self.editscript('Find.template', 'Find.js', linestoreplace,newlines):
				script = self.readscript('Find.js')
				client_socket.send(script)
				return self.messages()
			else: return 'ERROR with files'
		else: return 'ERROR, invalid input.'

	def cmd_getTargetRaDec(self,the_command): #***************************
		'''Returns the RA and dec of the target.'''
		commands = str.split(the_command)
		if len(commands) == 2:
			obj = commands[1]
			linestoreplace = ['var Target = "object";/*Parameterize*/\r\n']
			newlines = ['var Target = "'+obj+'";/*Parameterize*/\r\n']
			if self.editscript('GetTargetRaDec.template', 'GetTargetRaDec.js', linestoreplace,newlines):
				script = self.readscript('GetTargetRaDec.js')
				client_socket.send(script)
				return self.messages()
			else: return 'ERROR reading files'
		else: return 'ERROR, invalid input length'

	def cmd_mountGetRaDec(self,the_command):
		'''Gets the current RA and Dec of the mount.'''
		TheSkyXCommand = self.readscript('MountGetRaDec.js')
		client_socket.send(TheSkyXCommand)
		return self.messages()

	def cmd_mountGetAzAlt(self,the_command):
		'''Gets the current Altitide and Azimuth of the mount.'''
		TheSkyXCommand = self.readscript('MountGetAzAlt.js')
		client_socket.send(TheSkyXCommand)
		return self.messages()


	def cmd_moveTelescope(self, the_command):
		'''Will move the telescope by a specified amount. To move up, down, right, or left
		type ie 'moveTelescope north'. To move a specific Ra and Dec coordinate type:
		'moveTelescope 21 20' for example, where 21 is the  Ra and 20 is the Dec'''
		commands = str.split(the_command)
		if len(commands) == 3:
			dRa = commands[1]
			dDec = commands[2]
			linestoreplace = ['var TargetRA = RAtemp;\r\n','var TargetDec = Dectemp;\r\n']
			newlines = ['var TargetRA = "'+dRa+'";\r\n','var TargetDec = "'+dDec+'";\r\n']
			if self.is_float_try(dRa) and self.is_float_try(dDec):
				if self.editscript('MountGoto.template', 'MountGoto.js', linestoreplace,newlines):
					script = self.readscript('MountGoto.js')
					client_socket.send(script)
					return self.messages()
				else: return 'ERROR writing script'
			else: return 'ERROR invalid input'
		elif len(commands) == 2:
			script = ''
			if commands[1] == 'up': script = self.readscript('moveUp.js')
			elif commands[1] == 'down': script = self.readscript('moveDown.js')
			elif commands[1] == 'left': script = self.readscript('moveLeft.js')
			elif commands[1] == 'right': script = self.readscript('moveRight.js')
			else: return 'ERROR invalid input'
			client_socket.send(script)
			return self.messages()
		else: return 'ERROR, invalid input'

	def cmd_findHome(self,the_command):
		'''Will put the telescope in it's 'home' position. This is the position it needs
		to be in before any observing can take place.'''
		script = self.readscript('FindHome.js')
		client_socket.send(script)
		return self.messages()

	def cmd_park(self,the_command):
		'''This will put the telescope in it's parked position, this is the position the
		telescope needs to be in before the telescope is turned off/not in use.'''
		script = self.readscript('Park.js')
		client_socket.send(script)
		return self.messages()

	def cmd_runQuery(self,the_command):
		'''Runs whatever 'Current query' is loaded in TheSkyX and returns a list of the object names.'''
		script = self.readscript('RunQuery.js')
		client_socket.send(script)
		return self.messages()

	def cmd_setParkPosition(self,the_command):
		'''This will set the telescopes current position as the park position. Please don't use
		this unless there is an error given of the nature 'no park position set'.'''
		script = self.readscript('setParkPosition.js')
		client_socket.send(script)
		return self.messages()

	def cmd_setWhenWhere(self,the_command):
		'''This can be used to specify the location, date and time to be used by the sky.
		Input should look like: double(JulianDay) int(IDSTOption) int(IUseSystemClock)
		String(IpszDescripton) double(longitude) double(latitude) double(TimeZone)
		double(Elevation). double means a number alowing decimal points, int means an
		integer and string means a string of words. JulianDay = a double that specifies
		the Julian Day at which to view the sky, IDSTOption = a long value that specifies
		the daylight saving time option to use. IUSe System Clock = a long value that informs
		TheSky to use the computers internal time for TheSky's time, longitude = a double
		value that specifies TheSky's longitude setting, latitude = a double value to specify
		TheSky's latitude setting. TimeZone = a double that specifies TheSky's time zone,
		elevation = a double value that specifies the elevation used by TheSky.'''
		commands = str.split(the_command)
		dJulianDay = 0.0
		IDSTOption = 0
		IUseSystemClock = 0
		IpszDescription = ''
		dLongitude = 0.0
		dLatitude = 0.0
		dTimeZone = 0.0
		dElevation = 0.0
		linestoreplace = ['var dJulianDate = 0.0;\n','var IDSTOption = 0;\n','var IUseSystemClock = 0;\n',"var IpszDescription = '';\n",'var dLongitude = 0.0;\n','var dLatitude = 0.0;\n','var dTimeZone = 0.0;\n','var dElevation = 0.0;\n']
		if len(commands) == 9:
			IpszDescription = commands[4]
			if self.is_float_try(commands[1]):
				dJulianDay = commands[1]
			else: return 'ERROR, invalid input'
			if commands[2].isdigit():
				IDSTOption = commands[2]
			else: return 'ERROR invalid input'
			if commands[3].isdigit():
				IUseSystemClock = commands[3]
			else: return 'ERROR, invalid input'
			if self.is_float_try(commands[5]):
				dLongitude = commands[5]
			else: return 'ERROR invalid input'
			if self.is_float_try(commands[6]):
				dLatitide = commands[6]
			else: return 'ERROR invalid input'
			if self.is_float_try(commands[7]):
				dTimeZone = commands[7]
			else: return 'ERROR, invalid input'
			if self.is_float_try(commands[8]):
				dElevation = commands[8]
			else: return 'ERROR invalid input'
			newlines = ['var dJulianDate = '+dJulianDay+';\n','var IDSTOption = '+IDSTOption+';\n','var IUseSystemClock = '+IUseSystemClock+';\n','var IpszDescription = '+IpszDescription+';\n','var dLongitude = '+dLongitude+';\n','var dLatitude = '+dLatitude+';\n','var dTimeZone = '+dTimeZone+';\n','var dElevation = '+dElevation+';\n']
			if self.editscript('SetWhenWhere.template','SetWhenWhere.js',linestoreplace,newlines):
				script = self.readscript('SetWhenWhere.js')
				client_socket.send(script)
				return self.messages()
			else: return 'ERROR, could not read/make file.'
		else: return 'ERROR, invalid input'
			

	def cmd_s(self,the_command):
		'''Stops all telescope motion.'''
		script = self.readscript('moveStop.js')
		client_socket.send(script)
		return self.messages()

	def cmd_slewToRaDec(self,the_command):
		'''Will slew the telescope to the Ra and Dec put in.'''
		commands = str.split(the_command)
		if len(commands) == 3:
			dRa = commands[1]
			dDec = commands[2]
			linestoreplace = ['var TargetRa = Ratemp;\r\n','var TargetDec = Dectemp;\r\n']
			newlines = ['var TargetRa = "'+dRa+'";\r\n','var TargetDec = "'+dDec+'";\r\n']
			if self.is_float_try(dRa) and self.is_float_try(dDec):
				if self.editscript('SlewToRaDec.template', 'SlewToRaDec.js', linestoreplace,newlines):
					script = self.readscript('SlewToRaDec.js')
					client_socket.send(script)
					return self.messages()
				else: return "ERROR with files"
			else: return 'ERROR invalid input'
		else: return 'ERROR invalid input'

	def cmd_slewToAzAlt(self,the_command):
		'''Will slew the telescope to the Az and Alt put in.'''
		commands = str.split(the_command)
		if len(commands) == 3:
			dAz = commands[1]
			dAlt = commands[2]
			linestoreplace = ['var TargetAz = Aztemp;\r\n','var TargetAlt = Alttemp;\r\n']
			newlines = ['var TargetAz = "'+dAz+'";\r\n','var TargetAlt = "'+dAlt+'";\r\n']
			if self.is_float_try(dAz) and self.is_float_try(dAlt):
				if self.editscript('SlewToAzAlt.template', 'SlewToAzAlt.js', linestoreplace,newlines):
					script = self.readscript('SlewToAzAlt.js')
					client_socket.send(script)
					return self.messages()
				else: return "ERROR with files"
			else: return 'ERROR invalid input'
		else: return 'ERROR invalid input'



	def cmd_tracking(self,the_command):
		'''Turns tracking on or off and determines whether to use the sidereal time to set the tracking
		rate, or use a user input, input in form: 'tracking:on/off usesidereal:yes/no RaRate DecRate' ie if you
		wanted to turn tracking on and use sidereal rate input: 'on yes 0 0' to turn tracking on but set the rate
		to your own input put: 'on no 1.5 1.2'.'''
		commands = str.split(the_command)
		tracking = 0 #initially set tracking off
		usesidereal = 1 #intially set to use the sidereal time for tracking rates
		dRaRate = 0.0 #initally set ra tracking rate to 0
		dDecRate = 0.0 #initally set dec tracking rate to 0
		if len(commands) == 5:
			if commands[1] == 'on' or 'On': tracking = 1 #turn tracking on
			if commands[2] == 'no' or 'No': currentrates = 0 #use the current rates input by user
			if self.is_float_try(commands[3]) and self.is_float_try(commands[4]):
				dRaRate = commands[3]
				dDecRate = commands[4]
			else: return 'ERROR, invalid input'
			linestoreplace = ['\tsky6RASCOMTele.SetTracking(0,1,0,0);\r\n']
			newlines = ['\tsky6RASCOMTele.SetTracking('+str(tracking)+','+str(usesidereal)+','+str(dRaRate)+','+str(dDecRate)+');\r\n']
			if self.editscript('MountTracking.template', 'MountTracking.js', linestoreplace,newlines):
				script = self.readscript('MountTracking.js')
				client_socket.send(script)
				return self.messages()
			else: return 'ERROR writing script'
		else: return 'ERROR, invalid input'
				

	def cmd_sendSomething(self, the_command):
		commands = str.split(the_command)
		if len(commands) > 1:
			info = ''
			del commands[0]
			for i in range(len(commands)):
				info += commands[i]+' '
			TheSkyXCommand = info
			client_socket.send(TheSkyXCommand)
			return self.messages()
		else: return 'ERROR, invalid input'


	def cmd_telescopeConnect(self,the_command):
		'''Connect with the telescope.'''
		TheSkyXCommand = self.readscript('telescopeConnect.js')
		client_socket.send(TheSkyXCommand)
		return self.messages()


	def is_float_try(self,stringtry):
		'''Check to see if input is a float.'''
		try:
			float(stringtry)
			return True
		except ValueError:
			return False

	def readscript(self,script):
		'''Will read a file and return the text.'''
		try:
			f = open(script,'r')
			temp = f.read()
			f.close()
			return temp
		except ValueError:
			return -1

	def editscript(self,script, newscript, linestoreplace, newlines):
		'''This will make a script based on the template script to send to TheSky.'''
		try:
			f = open(script,'r') #open the template file
			newf = open(newscript,'w') #write the actual file we want to send to TheSkyX
			temp = []
			temp = f.readlines()
			j = 0
			for s in linestoreplace:
				for i in range(len(temp)):
					if temp[i] == s:
						temp[i] = newlines[j]
				j += 1
			for line in temp:	
				newf.write(line)
			newf.close()
			f.close()
			return 1
		except ValueError:
			return 0


	def messages(self):
		'''I'm trying to make this so if you don't get a response within 10 seconds instead
		of hanging indefinitely or completely quitting, the user is simply told, and can 
		try again.'''
		data = ''
		success = 0
		for i in range(10):
			try:
				time.sleep(1)
				data = str(client_socket.recv(50000))
				success = 1
			except ValueError:
				data = 'ERROR, TheSkyX not responding'
			if success: break
		return data

	def auto_dome_slew(self): #!!!!!!!!! WORK BEING DONE HERE
		'''Can set up a situation where the dome automatically slews to the
		same azimuth as the telescope.'''
		if self.dome_slewing_enabled:
			data = self.cmd_mountGetAzAlt()
			#Gotta split it up so we just get the
			temp = str.split(data)
			Azimuth = data[0]
			client_socket.send(Azimuth)
			return client_socket.recv(1024)

			

	
