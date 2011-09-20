# Given a list of functions and a list of strings, this program 
# is designed to find the function matching a given string.
# As this has to be done in principle when "compiling", the C way
# to do this is to have a list of functions and a list of strings.
#
# Function lists may have to be imported from many places, but
# within the same global scope. With the "simple server" mentality, 
# this can be passed a single object that contains the function 
# definitions, as a single object should be enough to contain all
# pieces of hardware (which should be 1).
#
# The idea is that a single call to:
# execute_command(command)
# ... returns a string for successful execution, or a useful string
#
# Try: 
# ./make_command_list dummy_functions.py 
# import dummy_functions as d
# import command_list as cl
# print cl.execute_command("one",d)
# print cl.execute_command("help",d)
# print cl.execute_command("oops",d)

import string
import pydoc

def execute_command(the_command, m):
    '''Find the_command amongst the list of commands like cmd_one in module m
    
    This returns a string containing the response, or a -1 if a quit is commanded.'''
    the_functions = dict(LookNorth=m.cmd_LookNorth,LookSouth=m.cmd_LookSouth,LookEast=m.cmd_LookEast,LookWest=m.cmd_LookWest,LookUp=m.cmd_LookUp,MoveLeft=m.cmd_MoveLeft,MoveRight=m.cmd_MoveRight,MoveUp=m.cmd_MoveUp,MoveDown=m.cmd_MoveDown,ZoomIn=m.cmd_ZoomIn,ZoomOut=m.cmd_ZoomOut,GrabScreen=m.cmd_GrabScreen,GetTargetRADec=m.cmd_GetTargetRADec,MountGoTo=m.cmd_MountGoTo,MountGetRADec=m.cmd_MountGetRADec,Find=m.cmd_Find)
    commands = string.split(the_command)
    if len(commands) == 0:
        return ""
    if commands[0] == "help":
        if (len(commands) == 1):
            return 'LookNorth\nLookSouth\nLookEast\nLookWest\nLookUp\nMoveLeft\nMoveRight\nMoveUp\nMoveDown\nZoomIn\nZoomOut\nGrabScreen\nGetTargetRADec\nMountGoTo\nMountGetRADec\nFind'
        elif commands[1] in the_functions:
            td=pydoc.TextDoc()
            return td.docroutine(the_functions[commands[1]])
        else:
            return "ERROR: "+commands[1]+" is not a valid command."
    elif commands[0] == 'exit' or commands[0] == 'bye' or commands[0] == 'quit':
        return -1
    elif commands[0] in the_functions:
        return the_functions[commands[0]](the_command)
    else:
        return "ERROR: Command not found."

