"""Routines for audacity remote control.

This is an adaptation of https://github.com/audacity/audacity/blob/master/scripts/piped-work/pipe_test.py

"""

import os
import sys
import time


VERBOSE = False
if not VERBOSE:  print = lambda *_, **__: None


if sys.platform == 'win32':
    print("pipe-test.py, running on windows")
    TONAME = '\\\\.\\pipe\\ToSrvPipe'
    FROMNAME = '\\\\.\\pipe\\FromSrvPipe'
    EOL = '\r\n\0'
else:
    print("pipe-test.py, running on linux or mac")
    TONAME = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
    FROMNAME = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
    EOL = '\n'


print("Write to  \"" + TONAME +"\"")
if not os.path.exists(TONAME):
    print(" ..does not exist.  Ensure Audacity is running with mod-script-pipe.")
    sys.exit()

print("Read from \"" + FROMNAME +"\"")
if not os.path.exists(FROMNAME):
    print(" ..does not exist.  Ensure Audacity is running with mod-script-pipe.")
    sys.exit()

print("-- Both pipes exist.  Good.")

TOFILE = open(TONAME, 'w')
print("-- File to write to has been opened")
FROMFILE = open(FROMNAME, 'rt')
print("-- File to read from has now been opened too\r\n")



def send_command(command):
    """Send a single command."""
    print("Send: >>> \n"+command)
    TOFILE.write(command + EOL)
    TOFILE.flush()

def get_response():
    """Return the command response."""
    result = ''
    line = ''
    while line != '\n':
        result += line
        line = FROMFILE.readline()
        #print(" I read line:["+line+"]")
    return result

def do_command(command):
    """Send one command, and return the response."""
    send_command(command)
    response = get_response()
    print("Rcvd: <<< \n" + response)
    return response

def quick_test():
    """Example list of commands."""
    do_command('Help: Command=Help')
    do_command('Help: Command="GetInfo"')
    #do_command('SetPreference: Name=GUI/Theme Value=classic Reload=1')

# quick_test()
def path_of(relpath:str, exists=True) -> str:
    path = os.path.join(os.getcwd(), relpath)
    if exists:
        assert os.path.exists(path), path
    return path


def apply_treatment_on(fname:str, outfile:str=None, *, play:bool=True):
    "outfile currently non-handled"
    infile = path_of(fname)

    SEQUENCE = (
        f'Import2: Filename="{infile}"',
        'Normalize: ApplyGain=yes RemoveDcOffset=yes Level=-1.000000 StereoIndependent=no',
        'ExportMP3:',
        # f'ExportMP3: Filename="{outfile}"',  # no effect, will create a dir under the input file
        'Play:' if play else '',
        'RemoveTracks:',
    )
    for cmd in SEQUENCE:
        if not cmd: continue
        do_command(cmd)
        time.sleep(0.5)


if __name__ == '__main__':
    apply_treatment_on('out/extract-1.mp3')
