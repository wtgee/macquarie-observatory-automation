#****************************************************************************#
#               Code to open and read from the weather station               #
#****************************************************************************#
import sys
sys.path.append('../common/')
from indiclient import *
import time
from datetime import datetime

import parameterfile
try: 
        indi=indiclient('localhost',7780)
        dummy=indi.set_and_send_text("AAG Cloud Watcher","CONNECTION","CONNECT","On")
        dummy=indi.set_and_send_text("AAG Cloud Watcher","CONNECTION","DISCONNECT","Off")
except Exception: print 'Unable to connect to weatherstation'
class WeatherstationServer:


#Global variables

	running = 1
	tempair = 0
	tempsky = 0
	clarity = 0
	light = 0
	rain = 0
	wind=0
	alertstate = 0
	slitvariable = 0 #This is the variable to send to the slits to tell them whether
			 #it's okay to be open or not. 0 to close, 1 to open.
	time_delay=10 #time delay between each reading of the 

        #set some variables that can be adjusted to redefine which limits are used for cloudy, rainy, light etc.
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsCloud","clear",-5)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsCloud","cloudy",0)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsCloud","overcast",30)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsRain","dry",2000)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsRain","wet",1700)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsRain","rain",400)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsBrightness","dark",2100)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsBrightness","light",100)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsBrightness","veryLight",0)
	dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsWind","calm",10)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","limitsWind","moderateWind",40)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","skyCorrection","k1",33)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","skyCorrection","k2",0)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","skyCorrection","k3",4)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","skyCorrection","k4",100)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","skyCorrection","k5",100)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","heaterParameters","tempLow",0)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","heaterParameters","tempHigh",20)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","heaterParameters","deltaLow",6)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","heaterParameters","deltaHigh",4)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","heaterParameters","min",10)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","heaterParameters","heatImpulseTemp",10)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","heaterParameters","heatImpulseDuration",60)
        dummy=indi.set_and_send_float("AAG Cloud Watcher","heaterParameters","heatImpulseCycle",600)


#A list of user commands:

	def cmd_clarity(self,the_command):
		'''Returns the clarity reading from the weather station. This is the difference between 
		the air temperature and the sky temperature.'''
		return str(self.clarity)

	def cmd_light(self,the_command):
		'''Returns the light reading from the weather station. Uncalibrated value, normal range: 0 to 30.'''
		return str(self.light)

	def cmd_rain(self,the_command):
		'''Returns the rain reading from the weather station. Uncalibrated value, normal range: 0 to 30.'''
		return str(self.rain)

	def cmd_tempair(self,the_command):
		'''Returns the air temperature reading from the weather station. Units are in degrees C.'''
		return str(self.tempair)

	def cmd_tempsky(self,the_command):
		'''Returns the sky temperature reading from the weather station. Units are in degrees C.'''
		return str(self.tempsky)

	def cmd_status(self,the_command):
		'''Returns all the latest data output from the weather station.'''
		return "Clarity: "+str(self.clarity)+"\nLight: "+str(self.light)+"\nRain: "+str(self.rain)+"\nAir temperature: "+str(self.tempair)+"\nSky temperature: "+str(self.tempsky)+"\nWind Speed: "+str(self.wind)

	def cmd_safe(self, the_command):
		'''Returns a 1 if it is safe to open the dome slits, and returns a zero otherwise.'''
		return str(self.slitvariable)


#************************* End of user commands ********************************#

#Background task that reads data from the weather station and records it to a file

	#definition to read from the serial port
	#I am assuming that only the rainsensortemp and heaterPWM are in hexadecimal
	#I'll know for sure when the aurora guys email me back
	currentTime=time.time()
	def main(self):
		if time.time()-self.currentTime > self.time_delay:
			self.currentTime=time.time()
			self.tempair = indi.get_float("AAG Cloud Watcher","sensors","ambientTemperatureSensor")  #sensor temperature
			
			self.tempsky = indi.get_float("AAG Cloud Watcher","sensors","correctedInfraredSky") #sky temperature
			self.clarity = self.tempair-self.tempsky #is the difference between the air temperature and the sky temperature
			self.light =  indi.get_float("AAG Cloud Watcher","sensors","brightnessSensor") #brightness Sensor reading
			self.rain = indi.get_float("AAG Cloud Watcher","sensors","rainSensor") #Rain Sensor reading
			self.wind= indi.get_float("AAG Cloud Watcher","readings","windSpeed") #anemometer reading

			#Initally set the alert variable to 0 (= Unsafe)
			#cloudvariable = 0 #this will be set to 1 if it is clear
			#rainvariable = 0  #this will be set to 1 if it is dry
			#lightvariable = 0 #this will be set to 1 if it is dark
			message = ''
			rain_list=['dry','wet','rain','unknown']
			cloud_list=['clear','cloudy','overcast','unknown']
			light_list=['dark','light','veryLight']
			wind_list=['calm','moderateWind','strongWind','unknown']

			for i in cloud_list:
				#print indi.get_text("AAG Cloud Watcher","cloudConditions",i)
				if indi.get_text("AAG Cloud Watcher","cloudConditions",i)=='On':
					#print i
					message += i+','
					if i=='clear': 
						cloudvariable=1
					else:
						cloudvariable=0
			for i in rain_list:
				if indi.get_text("AAG Cloud Watcher","rainConditions",i)=='On':
					message += ' '+i+','
					if i=='dry':
						rainvariable=1
					else:
						rainvariable=0
			for i in light_list:
				if indi.get_text("AAG Cloud Watcher","brightnessConditions",i)=='On':
					message += ' '+i+','
					if i=='dark':
						lightvariable=1
					else:
						lightvariable=0
			for i in wind_list:
				if indi.get_text("AAG Cloud Watcher","windConditions",i)=='On':
					message += ' '+i+','
					if i=='strongWind':
						windvariable=0
					else:
						windvariable=1

			self.slitvariable = cloudvariable*rainvariable*lightvariable*windvariable #if = 1, it's safe for slits to be open! Unsafe otherwise.
			#except Exception: print 'Unable to define slit variable'

			if self.slitvariable: message+=' Safe for dome to open.'
			else: message+=' NOT safe for dome to open.************' 
			self.log(message)

			return

	#definition to log the output, stores all data in a file
	def log(self,message):
		f = open('weatherlog.txt','a')
		f.write(str(time.time())+" "+str(datetime.now())+" "+str(message)+'\n')
		f.close()
                h = open('weatherlog_detailed.txt','a')
                h.write(str(time.time())+" "+str(datetime.now())+" "+"Clarity: "+str(self.clarity)+" Light: "+str(self.light)+" Rain: "+str(self.rain)+" Air temperature: "+str(self.tempair)+" Sky temperature: "+str(self.tempsky)+"\n"+" Wind Speed: "+str(self.wind)+"\n")
                h.close()


