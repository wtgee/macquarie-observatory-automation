# coding: utf-8
# A user can input the settings they want and then the program will take some images with the camera using these settings
import sys
sys.path.append('../common/')
import ImageCombination
from indiclient import *
from ds9 import *
import time
import pyfits
import numpy
import os
import math
import socket,subprocess
import commands

import parameterfile
failed=False
#Try to connect to the camera
try:
    indi=indiclient("localhost",7779)
    video_dev=os.popen('uvcdynctrl -l | grep '+parameterfile.fiberfeed_model).read().split('DM')[0].strip()
    if len(video_dev)>0:
        dummy=indi.set_and_send_text("V4L2 CCD","DEVICE_PORT","PORT","/dev/"+video_dev)
        dummy=indi.set_and_send_text("V4L2 CCD","CONNECTION","CONNECT","On")
        dummy=indi.set_and_send_text("V4L2 CCD","CONNECTION","DISCONNECT","Off")
        #set the camera saving images locally instead of sending them onto some sort of client. This is not designed to have a client.
        print 'successfully connected to camera'
    else:
        print 'Can not connect to camera, camera might not connected!'
except Exception: print 'Can not connect to camera'
time.sleep(1)
#Check connection
try:
    result=indi.get_text("V4L2 CCD","CONNECTION","CONNECT")
    if result=='Off':
        print 'Unable to connect to imagingsource side camera'
        failed=True
except Exception: print 'Unable to check camera connection'

if result!='Off':
    #set up some options that should not change often
    dummy=indi.set_and_send_text("V4L2 CCD","UPLOAD_MODE","UPLOAD_CLIENT","Off")
    dummy=indi.set_and_send_text("V4L2 CCD","UPLOAD_MODE","UPLOAD_BOTH","Off")
    dummy=indi.set_and_send_text("V4L2 CCD","UPLOAD_MODE","UPLOAD_LOCAL","On")
    #dummy=indi.set_and_send_text("V4L2 CCD","CCD_COOLER","COOLER_ON","On")
    #dummy=indi.set_and_send_text("V4L2 CCD","CCD_COOLER","COOLER_OFF","Off")
    if not os.path.exists('./program_images/'):
        dummy=subprocess.call('mkdir ./program_images', shell=True)
    dummy=indi.set_and_send_text("V4L2 CCD","UPLOAD_SETTINGS","UPLOAD_DIR",".")
    dummy=indi.set_and_send_text("V4L2 CCD","UPLOAD_SETTINGS","UPLOAD_PREFIX","TEMPIMAGE")
    dummy=indi.set_and_send_text("V4L2 CCD","MENU000","MENU000_OPT001","Off")
    dummy=indi.set_and_send_text("V4L2 CCD","MENU000","MENU000_OPT000","On")


class FiberFeedServer:

    magnitude_conversion = 0 # How to convert from the magnitude iraf gives out and the actual magnitude of a star.
                             # I *think* you just add this number (when calculated) to all Iraf mags and you're set.

    north_move_arcmins = 1  # program variables that indicate the direction of movement when spiralling
    east_move_arcmins = 1
    oneArcmininPixelsN = parameterfile.ff_oneArcmininPixelsN  # This tells us how many pixels there are to one arcsecond in the North/South direction
    oneArcmininPixelsE = parameterfile.ff_oneArcmininPixelsE  # This tells us how many pixels there are to one arcsecond in the East/West direction
    axis_flip = 1.0
    theta = 0
    transformation_matrix = [math.cos(theta), math.sin(theta), -1*math.sin(theta), math.cos(theta)]

    # Transformation matrix to be visualised as follows:
    #
    #    |   cos(theta)   sin(theta)   |      ie      |   transformation_matrix[0]  transformation_matrix[1]   |
    #    |  -sin(theta)   cos(theta)   |              |   transformation_matrix[2]  transformation_matrix[3]   |
    #
    # Transformation matrix is a rotation matrix.

    exptime=0.033

    if result!='Off':
        #Set the default camera settings here
        #def default_settings(self):
        dummy=indi.set_and_send_text("V4L2 CCD","V4L2_FRAMEINT_DISCRETE","2/15","Off")
        dummy=indi.set_and_send_text("V4L2 CCD","V4L2_FRAMEINT_DISCRETE","4/15","Off")
        dummy=indi.set_and_send_text("V4L2 CCD","V4L2_FRAMEINT_DISCRETE","1/60","Off")
        dummy=indi.set_and_send_text("V4L2 CCD","V4L2_FRAMEINT_DISCRETE","1/15","Off")
        dummy=indi.set_and_send_text("V4L2 CCD","V4L2_FRAMEINT_DISCRETE","1/30","On")
        #self.exptime=0.033
        dummy=indi.set_and_send_float('V4L2 CCD','Image Adjustments','Gain',300)
        dummy=indi.set_and_send_float('V4L2 CCD','Image Adjustments','Brightness',0)
        #dummy=indi.set_and_send_float('V4L2 CCD','Image Adjustments','Gamma',100)
        #return True

        #dummy= self.default_settings()
        #except Exception: print 'Unable to set the default settings'
    image_chop=False

    # writing all these in arrays shortens the code later on
    properties = ['Gain', 'Brightness', 'Gamma']


    #parameters dictating whether the guiding camera is being used
    exposing=False
    movement=[0.0,0.0]
    HFD=0.0
    filename='empty'

#******************************* The main camera comands ***********************************#

    def cmd_captureImages(self, the_command):
        '''This takes the photos to be used for science. Input the name of the images to capture (images will then be
        numbered: ie filename1.fits filename2.fits) and the number of images to capture. Note: when specifying a filename
        you do not need to include the extention: ie input "filename" not "filename.fits". Optional input is to force the
        routine to not show the images once it has taken them. Just add 'no' at the end of the call. '''
        comands = str.split(the_command)
        if len(comands) < 3: return 'Please input number of images to capture.'
        try: int(comands[2])
        except Exception: return 'Invalid number.'
        upperlimit = int(comands[2])
        base_filename = comands[1]
        if len(comands)==3:
            capture = self.capture_images(base_filename, upperlimit)
            if not capture: return 'ERROR capturing images'
        if (len(comands)==4):
            if (comands[3]=='no'):
                capture = self.capture_images(base_filename, upperlimit,show=False)
                if not capture: return 'ERROR capturing images'
            else:
                return 'Type "no" for no image display. Otherwise, leave empty.'
        return 'Capture complete'

    def cmd_brightStarCoords(self, the_command):
        '''This takes one photo to be used to detect the brightest star and find its coordinates. It returns the CCD coordinates corresponding to the brightest star detected (if any). This function does not take inputs. '''
        comands=str.split(the_command)
        if len(comands) >2: return 'This function does not take 3 arguments (in this version, anyway)...'
        elif len(comands) == 2 and comands[1]=='high':
            try: dummy = self.cmd_imageCube('imageCube brightstar high')
            except Exception: print 'Could not capture images'
        else:
            try: dummy = self.cmd_imageCube('imageCube brightstar 10')
            except Exception: print 'Could not capture images'
        localtime=time.localtime(time.time())
        #for the purposes of testing the guiding, save each image as a separate file.
        self.filename='guiding_'+str(localtime[0])+str(localtime[1]).zfill(2)+str(localtime[2]).zfill(2)+str(localtime[3]).zfill(2)+str(localtime[4]).zfill(2)+str(localtime[5]).zfill(2)
        #analyse the image using whatever software we are using at the moment and find the brightest star.
        try:
            brightcoords = self.analyseImage('program_images/brightstar.fits','program_images/brightstar.txt')
            os.system('cp program_images/brightstar.fits program_images/'+self.filename+'.fits')
        except Exception: return 'Could not analyse image.'
        #return the coordinates, magnitude and sharpness
        if brightcoords == 0: return 'no stars found.'
        return str(brightcoords[0])+' '+str(brightcoords[1])+' '+str(brightcoords[2])+' '+str(brightcoords[3])


    def cmd_adjustExposure(self, the_command):
        '''This function will adjust the exposure time of the camera until the brightest pixel is between a given range, close to the 8 bit resolution maximum of the imagingsource cameras (255). Takes no inputs'''
        print 'Resetting Gain to maximum'
        dummy=indi.set_and_send_float('V4L2 CCD','Image Adjustments','Gain',300)
        max_pix=0
        direction=0
        direction_old=0
        deviation=0.01
        print 'Adjusting exposure time. Please wait.'
        while (max_pix < 100)|(max_pix>245):
            #take one image but do not display it
            try: dummy = self.cmd_captureImages('captureImages exposure_adjust 1 no')
            except Exception: print 'Could not capture image'
            im=pyfits.getdata('exposure_adjust.fits')
            #find out what the maximum flux of the image is
            max_pix=im.max()
            print 'max_pix=',max_pix
            #Now use an asymptotic approach to find the exposure time that will yield a value between 200 and 255
            #Make sure that exposure never gets above 100000 or below 51
            if max_pix < 100:
                value = indi.get_float("V4L2 CCD","CCD_EXPOSURE","CCD_EXPOSURE_VALUE")
                direction=1
                if value < 10:
                    value+=deviation
                    print 'Exposure=',value*1000.,'ms'
                    self.exptime=value
                else:
                    return 'Exposure too big already, maybe there is no star in the field...'
            if max_pix > 245:
                value = indi.get_float("V4L2 CCD","CCD_EXPOSURE","CCD_EXPOSURE_VALUE")
                direction=-1
                if value> 0.020:
                    value-=deviation
                    if value>0:
                        print 'Exposure=',value*1000.,'ms'
                        self.exptime=value
                    else:
                        value=0.030
                        deviation=0.010
                        print 'Exposure=',value*1000.,'ms'
                        self.exptime=value
                elif value <0.020 and value >0.0002:
                    value=0.020
                    print 'Exposure=',value*1000.,'ms'
                    self.exptime=value
                    print 'Minimum exposure reached, adjusting Gain'
                    gain = indi.get_float("V4L2 CCD","Image Adjustments","Gain")
                    dummy=indi.set_and_send_float('V4L2 CCD','Image Adjustments','Gain',int(gain*0.75))
                    if gain<200:
                        return 'Reached lowest possible exposure time. Star may still be saturated but nothing can be done.'
                else: return 'Exposure too short to reduce. Maybe this is too bright?'
            if direction_old==direction: deviation*=2
            else: deviation/=2
            direction_old=direction
        return 'Finished adjusting exposure'

    def cmd_setCameraValues(self,the_command):
        '''This sets up the camera with gain, brightness and gamma settings wanted by the user. A user can set each setting individually. The properties are: \nGain \nBrightness \nGamma. \nTo set a property type: setCameraValues Gain 3 \nTo get a list of properties type: setCameraValues show.\nTo use the default settings type "setCameraValues default"'''
        comands = str.split(the_command)
        if len(comands) == 1: return 'An input parameter is required. Type "help setCameraValues" for more information'
        elif len(comands) == 2 and comands[1] == 'default':
            dummy=self.default_settings()
            if dummy==True:
                return 'Default settings used for all properties.'
            else: return 'Unable to set default values for camera.'
        elif len(comands) == 3:
            #fmts = self.dev.enumerate_formats()
            #props = self.dev.enumerate_properties()
            pro = comands[1]
            if pro in self.properties:
                try: float(comands[2])
                except Exception: return 'Invalid input'
                try: dummy=dummy=indi.set_and_send_float('V4L2 CCD','Image Adjustments',pro,float(commands[2]))
                except Exception: return 'Unable to communicate with the camera server to change property.'
            else: return 'Invalid input, type "setCameraValues show" for a list of current values and ranges'
            return str(pro)+' value updated'

        else: return 'Invalid command. Type "setCameraValues" for a list of allowed inputs and ranges'


    def cmd_starDistanceFromCenter(self, the_command):
        '''This checks the position of the brighest star in shot with reference to the desired central pixel of the frame and
        the sharpness of the same star. A call to this function will return a vector distance between the centeral
        pixel and the brightest star in arcseconds in the North and East directions. When calling this function
        you must specify which file for daofind to use (do not add the file extension, ie type "filename" NOT "filename.fits"'''
        comands = str.split(the_command)
        if len(comands) != 2: return 'Invalid input, give name of file with data.'
        filename = comands[1]
        dDec = 0
        dAz = 0
        brightest_star_info = self.analyseImage('program_images/'+filename+'.fits', filename+'.txt')
        if not brightest_star_info: return 'No star found to measure distance to'
        star_sharp = float(brightest_star_info[3])  # We will use this to check the focus of the star
        star_mag = float(brightest_star_info[0])    # We use this to identify the brightest star
        xpixel_pos = float(brightest_star_info[1])  # x pixel position of the brightest star
        ypixel_pos = float(brightest_star_info[2])  # y pixel position of the brightest star
        # Find distance from the center of the image
        target_xpixel,target_ypixel = numpy.loadtxt('guiding_coords')
        x_distance = float(target_xpixel) - xpixel_pos # The position of the star relative to the central pixel
        y_distance = float(target_ypixel) - ypixel_pos
        vector_to_move = [x_distance, y_distance]
        print vector_to_move
        translated_N = self.transformation_matrix[0]*x_distance + self.transformation_matrix[1]*y_distance
        translated_E =  (self.transformation_matrix[2]*x_distance + self.transformation_matrix[3]*y_distance)*self.axis_flip

        #Need to convert distance into coordinates for the telescope orientation

        # we should have it in RA Dec
        dArcminN = translated_N/self.oneArcmininPixelsN
        dArcminE = translated_E/self.oneArcmininPixelsE # Now we convert where to move a positive is a move East
        return str(dArcminN)+' '+str(dArcminE)
        # ^ This returns the distance between the central pixel and the brightest star in arcmins in the North and East directions

    def cmd_orientationCapture(self, the_command):  # need to have some define settings for this perhaps who knows
        '''This will take the photos for camera orientation and automatically name them so that another function
        can calculate the orientation easily. For the base photograph type the command "base", to take the
        photograph after the telescope has been moved North type "north amountmoved" where amountmoved is in arcseconds.
        To take the photograph after the telescope has been moved East type "east amountmoved" where again amountmoved
        is in arcseconds'''
        comands = str.split(the_command)
        image_name = ''
        if len(comands) == 2 and comands[1] == 'base': image_name = 'base_orientation'
        elif len(comands) == 3:
            if comands[1] == 'North' and self.is_float_try(comands[2]):
                image_name = 'north_orientation'
                self.north_move_arcmins = float(comands[2])
            elif comands[1] == 'East' and self.is_float_try(comands[2]):
                image_name = 'east_orientation'
                self.east_move_arcmins = float(comands[2])
            else: return 'ERROR see help'
        else: return 'Invalid input'

        capture = self.cmd_imageCube('imageCube '+image_name+' 10')
        if not 'Final image created' in capture: return 'ERROR capturing image'
        else: return str(comands[1])+' image captured.' # change this to a number perhaps for ease when automating

    def cmd_Chop(self, the_command):
        '''Changes the value of self.image_chop such that, if it is True, any time an image taken from the camera is analysed, only a scetion in the middle is considered. This is mostly for the purposes of adjusting the exposure and looking for bright stars.'''
        comands = str.split(the_command)
        if len(comands)==1: return 'Image chop is set to '+str(self.image_chop)
        elif len(comands)==2 and comands[1]=='on': self.image_chop=True
        elif len(comands)==2 and comands[1]=='off': self.image_chop=False
        else: return 'Incorrect usage of function. Activate chopping of images using "on" or "off".'
        return 'Image chop status set to '+str(self.image_chop)

    def cmd_focusCapture(self,the_command):
        '''This will capture the images to be used for focusing an image. When calling this image you need
        to give the function the focuser counts the photo is being taken at. Might make life easier to combine
        this with the orientate capture'''
        comands = str.split(the_command)
        if len(comands) !=2: return 'ERROR'
        try: focus_count = int(comands[1])
        except Exception: return 'ERROR'
        filename = 'focusImage'

        capture = self.capture_images(filename, 1)
        if not capture: return 'ERROR capturing images'

        bright_star_info = self.analyseImage(filename+'.fits', 'focus_output.txt')
        sharpness_value = bright_star_info[3]
        return sharpness_value

    def cmd_calculateCameraOrientation(self, the_command):
        '''This does the maths for the camera orientation. Theta is the angle between the positive x axis of the camera and the North direction'''
        base_star_info = self.analyseImage('program_images/base_orientation.fits','program_images/base_orientation.txt')
        north_star_info = self.analyseImage('program_images/north_orientation.fits','program_images/north_orientation.txt')
        east_star_info = self.analyseImage('program_images/east_orientation.fits','program_images/east_orientation.txt')
        if base_star_info == 0 or north_star_info == 0 or east_star_info == 0:
            return 'Orientation photos need to be taken or no stars detected.'
        #brightest_star_info = self.find_brightest_star(outfile) # need to account for error here
                                                             # also what if brighter star comes into field of view?
        #star_sharp = float(brightest_star_info[3])    # We will use this to check the focus of the star

        try:
            base_xpixel_pos = float(base_star_info[1])    # x pixel position of the brightest star
            base_ypixel_pos = float(base_star_info[2])    # y pixel position of the brightest star
            #base_star_mag = float(brightest_star_info[2]) # We use this to identify the brightest star
            north_xpixel_pos = float(north_star_info[1])
            north_ypixel_pos = float(north_star_info[2])
            #north_star_mag = float(north_star_info[2])
            east_xpixel_pos = float(east_star_info[1])  # The east move is to determine if we need a swap or not
            east_ypixel_pos = float(east_star_info[2])
            #east_star_mag = float(east_star_info[2])
        except Exception: return 'For some reason, could not convert pixel positions to floats...'

        print 'base position= ',base_star_info
        print 'north position= ',north_star_info
        print 'east position= ',east_star_info

        vector_movedN = [north_xpixel_pos - base_xpixel_pos, north_ypixel_pos - base_ypixel_pos]
        print 'vector_movedN ',vector_movedN
        hypotenuseN = math.hypot(vector_movedN[0], vector_movedN[1]) # this is number of pixels moved whilst moving North
        self.oneArcmininPixelsN = hypotenuseN/self.north_move_arcmins
        print 'hypotenuseN ',hypotenuseN, ' oneArcmininPixelsN', self.oneArcmininPixelsN

        if vector_movedN[0] == 0 and vector_movedN[1] > 0: self.theta = math.pi/2.0
        elif vector_movedN[0] == 0 and vector_movedN[1] < 0: self.theta = 3.0*math.pi/2.0
        elif vector_movedN[1] == 0 and vector_movedN[0] > 0: self.theta = 0
        elif vector_movedN[1] == 0 and vector_movedN[0] < 0: self.theta = math.pi
        else: self.theta = math.atan(vector_movedN[1]/vector_movedN[0])
#               print str(self.theta)

        if vector_movedN[0] < 0: self.theta = math.pi+ self.theta
        print 'angle=',str(self.theta)

        # Need to recalculate the transformation matrix:
        self.transformation_matrix = [math.cos(self.theta), math.sin(self.theta), -1*math.sin(self.theta), math.cos(self.theta)]
        print self.transformation_matrix
        vector_movedE = [east_xpixel_pos - north_xpixel_pos, east_ypixel_pos - north_ypixel_pos]
        print 'vector_movedE ',vector_movedE
        hypotenuseE = math.hypot(vector_movedE[0], vector_movedE[1]) # this is number of pixels moved for E/W
        self.oneArcmininPixelsE = hypotenuseE/self.east_move_arcmins
        print 'hypotenuseE ',hypotenuseE, ' oneArcmininPixelsE', self.oneArcmininPixelsE

        translated_y =  self.transformation_matrix[2]*vector_movedE[0] + self.transformation_matrix[3]*vector_movedE[1]
        print translated_y
        if translated_y <= 0: self.axis_flip = -1 # because positive is west, negative is east
        else: self.axis_flip = 1
        return 'Orientation complete '+str(self.theta)

        #  The above camera orientation command uses the following definition for the axis' with all rotations
        #  being made in an anticlockwise direction
        #
        #             W
        #             |
        #             |
        #             |
        #  S ------------------- N
        #             |
        #             |
        #             |
        #             E
        #
        # so if we had a zero rotation angle, North would be along the x axis
        #



    def cmd_imageCube(self, the_command):
        '''This function can be used to pull a series of images from the camera and coadd them in a simple way.
        This is slightly better process for measuring the position of a star for the purposes of guiding.
        In essence, this will take 10 images, average them and create a master image for analysis to be perfomed on.'''
        comands = str.split(the_command)
        if len(comands) != 3: return 'Please specify the name of the final image and the number of images to median through. Alternatively, specify "high" instead of the number of images to acquire a high enough number of average over scintilation.'
        if comands[2]=='high': nims=30 #3E4/self.set_values[2]
        else:
            try: nims=int(comands[2])
            except Exception: return 'Unable to convert number of images to integer'
        #make upperlimit images and average combine them.
        upperlimit = int(nims)
        base_filename = comands[1]
        if base_filename in commands.getoutput('ls program_images/'):
            os.system('rm program_images/'+base_filename+'*')
        print 'Starting to capture images'
        capture = self.capture_images('program_images/'+base_filename, upperlimit,show=False)
        if not capture: return 'ERROR capturing images'
        print 'Finished capturing images'
        self.check_if_file_exists('program_images/'+base_filename+'.fits')
        self.check_if_file_exists('program_images/inlist')
        os.system('ls program_images/'+base_filename+'_*.fits > inlist')
        try: dummy=ImageCombination.image_combine('inlist','program_images/'+base_filename+'.fits','median')
        except Exception: return 'Could not combine images'
        if dummy==False: return 'Could not combine images'
        return 'Final image created. It is image program_images/'+base_filename+'.fits'

    def cmd_defineCenter(self, the_command):
        '''This function can be used to define the pixel coordinates that coincide with the optical axis of the telescope
        (or where we want the guide star to be at all times). use the option 'show' to query the current central coordinates. usage: defineCenter <xcoord> <ycoord>'''
        comands=str.split(the_command)
        if len(comands) > 3: return 'Please specify the x and y coordinates as separate values'
        if len(comands)==2 and comands[1]=='show':
            target_xpixel,target_ypixel = numpy.loadtxt('guiding_coords')
            return str(target_xpixel)+' '+str(target_ypixel)
        try:
            new_x=float(comands[1])
            new_y=float(comands[2])
        except Exception: return 'ERROR: invalid coordinate format. They must be floats'
        numpy.savetxt('guiding_coords',[new_x,new_y])
        return 'Central coordinates updated'

    def cmd_centerIsHere(self, the_command):
        '''This function can be used to define the pixel coordinates that coincide with the optical axis of the telescope
        (or where we want the guide star to be at all times) by taking images and working out where the bright star is.
        Very similar to cmd_defineCenter, but takes the images as well and defines the bright star coordinates as the central coords. Takes no inputs'''
        comands=str.split(the_command)
        if len(comands) != 1: return 'no input needed for this function'
        dummy=self.cmd_imageCube('imageCube central high')
        star_info = self.analyseImage('program_images/central.fits', 'program_images/central.txt') # put in these parameters
        try:
            new_x=float(star_info[1])
            new_y=float(star_info[2])
        except Exception: return 'Finding brightest star failed'
        dummy=self.cmd_defineCenter('defineCenter '+str(new_x)+' '+str(new_y))
        return 'Finished updating central coordinates'

    def cmd_currentExposure(self, the_command):
        '''Function used to query the exposure time of the camera'''
        comands=str.split(the_command)
        if len(comands)!=1: return 'no input needed for this function'
        else: return str(self.exptime*1000.)+' ms'

    def cmd_changeExposure(self, the_command):
        '''Function used to query the exposure time of the camera'''
        comands=str.split(the_command)
        if len(comands)!=2: return 'Just specify the exposure time in seconds'
        try: t=float(comands[1])
        except Exception: return 'Exposure time must be a floating point number'
        self.exptime=t
        return 'Changed exposure time to '+str(t)+' seconds'

#*********************************** End of user comands ***********************************#

    def capture_images(self, base_filename, upperlimit,show=True):
        '''This takes the photos to be used for science. Input the name of the images to capture (images will then be
        numbered: ie filename1.fits filename2.fits) and the number of images to capture. Note: when specifying a filename
        you do not need to include the extention: ie input "filename" not "filename.fits"'''
        try: up=int(upperlimit)
        except Exception: return False

        for i in range( 0, up ):
            #self.dev.set_property( prop )
            if upperlimit > 1: filename= base_filename+'_'+str(i)  # if we are taking several images we need to number them
            else: filename = base_filename
            self.check_if_file_exists(filename+'.fits')
            dummy=indi.set_and_send_text("V4L2 CCD","UPLOAD_SETTINGS","UPLOAD_PREFIX",filename)
            dummy=indi.set_and_send_float("V4L2 CCD","CCD_EXPOSURE","CCD_EXPOSURE_VALUE",self.exptime)
            while not os.path.isfile(filename+'.fits'):
                print filename
                print 'Still waiting for file'
                time.sleep(0.1)
            im_temp=pyfits.getdata(filename+'.fits')
            badmask=pyfits.getdata('badmask.fits')
            im=im_temp*badmask
            os.system('rm '+filename+'.fits')
            pyfits.writeto(filename+'.fits',im)
            if self.image_chop:
                im_temp=pyfits.getdata(filename+'.fits')
                im=self.chop(im_temp)
                os.system('rm '+filename+'.fits')
                pyfits.writeto(filename+'.fits',im)
            if show:
                d=ds9(target='fiberfeed')
                d.set('file '+filename+'.fits')
        return True

    def analyseImage(self, input_image, outfile):
        '''Analyse the image using sextractor'''
        self.check_if_file_exists(outfile)
        try: os.system('sextractor '+input_image+' -c fiberfeed.sex -CATALOG_NAME '+outfile)
        except Exception: return 0
        brightest_star_info = self.find_brightest_star(outfile)
        return brightest_star_info

    def is_float_try(self, stringtry):
        try:
            float(stringtry)
            return True
        except ValueError:
            return False

    def find_brightest_star(self, readinfile):
        '''Routine to find the brightest star from a sextractor catalog file'''
        try: starfile = open(readinfile)
        except Exception: return 'ERROR; Unable to open file' # <-- change this to returning a number
        startemp = starfile.readlines()
        brighteststar = 50
        xpixel = 0
        ypixel = 0
        for lines in startemp:
            if lines[0][0] != '#': #don't want the comments
                linetemp = str.split(lines)
                #print linetemp
                if float(linetemp[2]) < brighteststar:
                    starmag = float(linetemp[2])
                    xpixel = float(linetemp[0])
                    ypixel = float(linetemp[1])
                    #The multiplication by two is just to convert the 0.5 frac_radius measurement into the half flux *diameter*
                    HFD = float(linetemp[4])*2.
                    brighteststar=starmag
        try: return [starmag, xpixel, ypixel, HFD]
        except Exception: return 0

    def check_if_file_exists(self, filename):
        '''Self explanatory'''
        if os.path.isfile(filename): os.remove(filename)
        return filename

    def cmd_guide(self,the_command):
        '''function that sets the exposing boolean to true and gets the imaging parameters from the uber server'''
        commands = str.split(the_command)
        if len(commands) != 1 : return 'error: this function does not take inputs.'
        self.exposing=True
        os.system('rm guiding_stats.txt')
        return 'Image being taken'

    def cmd_imagingStatus(self,the_command):
        '''function that returns the status of the imaging boolean'''
        commands=str.split(the_command)
        if len(commands)>1: return 'Error: this function does not take inputs'
        else: return str(self.exposing)

    def imaging_loop(self):
        #function that takes an image and then sets the imaging boolean off. This is to make sure this runs outside of uber.
        if self.exposing==True:
            try: result=self.cmd_brightStarCoords('brightStarCoords high')
            except Exception: print 'Something did not go down well with the exposure!'
            if 'no stars found' not in result:
                starinfo=str.split(result)
                print starinfo
                try:
                    xcoord=float(starinfo[1])
                    ycoord=float(starinfo[2])
                    self.HFD=float(starinfo[3])
                except Exception: return 'Could not convert coordinates of star to floats, for some reason...'
                print 'star found in coordinates', xcoord, ycoord
                try: output=self.cmd_defineCenter('defineCenter show')
                except Exception: print 'This failed, really should not happen!'
                central=str.split(output)
                try:
                    centralx=float(output[0])
                    centraly=float(output[1])
                except Exception: print 'could not convert central coordinates to floats'
                distance=math.hypot(centralx-xcoord, centraly-ycoord)
                if distance>2:
                    moving=self.cmd_starDistanceFromCenter('starDistanceFromCenter brightstar')
                    self.movement=str.split(moving)
            else:
                self.movement=[0.0,0.0]
                self.HFD=0.0
            target_xpixel,target_ypixel = numpy.loadtxt('guiding_coords')
            fileline=[self.HFD,float(self.movement[0]),float(self.movement[1]),self.filename,target_xpixel,target_ypixel]
            print fileline
            numpy.savetxt('guiding_stats.txt',fileline,fmt='%s')
            self.exposing=False


    def chop(self,im):
        '''Function that will return a section of the image that we are interested in. This will just chop off a box of width 'width' centred at middle_x,middle_y. It actually just sets all the values outside this ox to 0'''
        target_xpixel,target_ypixel = numpy.loadtxt('guiding_coords')
        middle_x=target_xpixel
        middle_y=target_ypixel
        width=100
        im_temp=im.copy()
        im_temp[:middle_y-width/2]=0
        im_temp[middle_y+width/2:]=0
        im_temp[:,:middle_x-width/2]=0
        im_temp[:,middle_x+width/2:]=0
        return im_temp
