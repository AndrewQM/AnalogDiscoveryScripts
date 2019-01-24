"""
   SNSPD IV Curve Generator
   Author:  Digilent, Inc., Andrew Mueller
   Revision: 1/11/2019

   Requires:
       Python 3.6+, numpy, matplotlib
       python-dateutil, pyparsing
"""
from ctypes import *
from dwfconstants import *
import math
import time
import matplotlib.pyplot as plt
import sys
import datetime



# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total:
        print()


if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("/usr/lib/libdwf.so.3.8.2")


hdwf = c_int()

#print("Opening first device")
#dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))  #automatic enumeration does not work

#if hdwf.value == hdwfNone.value:
 #   szerr = create_string_buffer(512)
  #  dwf.FDwfGetLastErrorMsg(szerr)
   # print(szerr.value)
    #print("failed to open device")
    #quit()

cdevices = c_int()
dwf.FDwfEnum(c_int(0), byref(cdevices))
print("Number of Devices: "+str(cdevices.value))

if cdevices.value == 0:
    print("no device detected")
    quit()
############################################################
print("Opening first device")
hdwf = c_int()
dwf.FDwfDeviceOpen(c_int(0), byref(hdwf))

if hdwf.value == hdwfNone.value:
    print("failed to open device")
    quit()


##comment out input prompts and hardcode values if repeating same measurment many times
amplitude = 3.0 #float(input("Driving amplitude? (Volts):  "))
periods = 4 #int(input("Number of desired IV cycles? "))
ptspp = 400 #int(input("Number of datapoints per period? "))
periodrate = 10 #float(input("Number of periods per second? "))


prhzAcq = periodrate * ptspp
nSamples = ptspp * periods
ttime = nSamples/prhzAcq


#declare ctype variables

sts = c_byte()
#prhzAcq = 5000 #samplerate
hzAcq = c_double(prhzAcq)
#nSamples = 20000 #total samples
rgdSamples = (c_double*nSamples)()
rgdSamples2 = (c_double*nSamples)()
cAvailable = c_int()
cLost = c_int()
cCorrupted = c_int()
fLost = 0
fCorrupted = 0

#print DWF version
version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: "+str(version.value))

#open device

print("completion time:", ttime, "seconds")
print("total samples:", nSamples)
print("")


print("Preparing to read sample...")


print("Generating triangle wave...")
dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_bool(True))
dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcTriangle)
dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(periodrate))
dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(amplitude))
dwf.FDwfAnalogOutConfigure(hdwf, c_int(0), c_bool(True))

#set up acquisition
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(0), c_bool(True))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(2.1*amplitude))
dwf.FDwfAnalogInAcquisitionModeSet(hdwf, acqmodeRecord)
dwf.FDwfAnalogInFrequencySet(hdwf, hzAcq)
dwf.FDwfAnalogInRecordLengthSet(hdwf, c_double(ttime)) # -1 infinite record length

#wait at least 2 seconds for the offset to stabilize
time.sleep(2)

#begin acquisition
dwf.FDwfAnalogInConfigure(hdwf, c_int(0), c_int(1))
print("waiting to finish")

plt.figure(0)
plt.axis([0,nSamples,-amplitude,amplitude])


cSamples = 0
display = 0
printProgressBar(0, nSamples, prefix = 'Progress:', suffix = 'Complete', length = 50)
while cSamples < nSamples:

    dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
    if cSamples == 0 and (sts == DwfStateConfig or sts == DwfStatePrefill or sts == DwfStateArmed) :
        # Acquisition not yet started.
        print("not started")
        continue

    dwf.FDwfAnalogInStatusRecord(hdwf, byref(cAvailable), byref(cLost), byref(cCorrupted))

    cSamples += cLost.value

    if cLost.value :
        fLost = 1
        print("Values lost. Decrease sample rate")
        exit(1)
    if cCorrupted.value :
        fCorrupted = 1
        print("Values corrupted. Decrease sample rate and/or sample number")
        exit(1)

    if cAvailable.value==0 :
        continue

    if cSamples+cAvailable.value > nSamples : #grab the last little bit
        cAvailable = c_int(nSamples-cSamples) ###########- #########

    dwf.FDwfAnalogInStatusData(hdwf, c_int(0), byref(rgdSamples, sizeof(c_double)*cSamples), cAvailable) # get channel 1 data
    dwf.FDwfAnalogInStatusData(hdwf, c_int(1), byref(rgdSamples2, sizeof(c_double)*cSamples), cAvailable) # get channel 2 data
    cSamples += cAvailable.value

    printProgressBar(cSamples + 1, nSamples, prefix = 'Progress:', suffix = 'Complete', length = 50)

    #plt.plot(rgdSamples[0,cSamples], color = '#962424')
    #plt.show()
print()
print("Recording finished")
if fLost:
    print("Samples were lost! Reduce frequency")
if fCorrupted:
    print("Samples could be corrupted! Reduce frequency")


filename1 = datetime.datetime.now().strftime("IV_%m_%d_%Y-%H%M%S")
f = open(filename1, "w")
f.write("Volts2, Volts2\n")
for x in range(0, len(rgdSamples)):
    f.write("%s," % rgdSamples[x])
    f.write("%s\n" % rgdSamples2[x])
f.close()
print("File saved as: ", filename1)

# find first point


## in progress
for i in range(0, ptspp):
    if rgdSamples[i] < 0 and rgdSamples[i+1] > 0:
        begin = i + 1
        break

#end = nSamples
#for i in range(nSamples, ptspp, -1):
#    if rgdSamples[i] < 0 and rgdSamples[i-1] > 0:
#        end = i
#        break


driver=[0.0]*len(rgdSamples)
rgpz=[0.0]*len(rgdSamples2)
for i in range(begin,nSamples):
    driver[i]=rgdSamples[i]
    rgpz[i]=rgdSamples2[i]



scatterx = rgpz[0:2*ptspp]
scattery = [0] * (2*ptspp)

for i in range(0,2*ptspp):
    scattery[i] = (driver[i]-rgpz[i])*100

plt.figure(1)
plt.plot(driver, color = '#962424') #red
 #rg or grpy is direct waveform generator voltage
plt.plot(rgpz, color = '#249096') #cyan


plt.figure(2)
plt.scatter(scatterx,scattery)
plt.show()
