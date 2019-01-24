"""
   SNSPD IV Curve Generator
   Author:  Digilent, Inc., Andrew Mueller
   Revision: 1/11/2019

   Requires:
       Python 3.6+, numpy, matplotlib
       python-dateutil, pyparsing
"""

# -*- coding: utf-8 -*-
from ctypes import *
from dwfconstants import *
import math
import time
import matplotlib.pyplot as plt
import sys
import datetime

if len(sys.argv)  > 2:
    print("Usage: one optional paramater m disables file saving")
    exit(1)

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100):
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
    bar = '#' * filledLength + '-' * (length - filledLength)

    sys.stdout.write('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix))
    # Print New Line on Complete
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("/usr/lib/libdwf.so.3.8.3")


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
##comment out input prompts and hardcode values if repeating same measurment many times
amplitude = 1.5 #float(input("Driving amplitude? (Volts):  "))
periods = 1 #int(input("Number of desired IV cycles? "))
ptsppI = 5000 #int(input("Number of datapoints per period? "))
periodrate = .02 #float(input("Number of periods per second? "))
R = 200 #resistance in kOhms
ARatio = .8  #if 1, most possible averaging is done internal. If 0, all averaging is done external.

# go with 5 periods at 10000 samples per period
#50000 samples per second
prhzAcqI = periodrate * ptsppI


MaxprhzAcq = 50000 #should be increased as high as it can go on a certain config


#ratio = MaxprhzAcq/prhzAcqI
ratio = prhzAcqI/MaxprhzAcq

#choose ratio between internal and external averaging over an exponential metric
newratio = math.exp(math.log(ratio) + math.log(1/ratio)*ARatio)
print("new ratio is: ", newratio)
prhzAcq = newratio * MaxprhzAcq  #this is how fast we acctually ask for data from device

avg_Nint = prhzAcq/prhzAcqI

print("avg_Nint is: ", avg_Nint)
#number of samples that will be averaged over internally

#we need a fake ptsppI. ptspp will be used internally
ptspp = prhzAcq/periodrate

avg_N = int(100000000 / prhzAcq)

nSamples = ptspp * periods
ttime = 1.1*(nSamples/prhzAcq)  #added a little extra time. Long runs tend to lose samples otherwise

prhzAcq = int(prhzAcq)
nSamples = int(nSamples) + 1
avg_N = int(avg_N)
avg_Nint = int(avg_Nint)
ptspp = int(ptspp) + 1

print("nSamples is: ", nSamples)
print("ptspp is: ", ptspp)




print("Opening first device")
hdwf = c_int()
dwf.FDwfDeviceOpen(c_int(0), byref(hdwf))

if hdwf.value == hdwfNone.value:
    print("failed to open device")
    quit()





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
print("total internal samples:", nSamples)
print("")


print("Preparing to read sample...")


print("Generating triangle wave...")
dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_bool(True))
dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcTriangle)
dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(periodrate))
dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(amplitude))
dwf.FDwfAnalogOutConfigure(hdwf, c_int(0), c_bool(True))

stepsarray = (c_double*32)()
ranges = c_int()
phzMin = c_double()
phzMax = c_double()

#set up acquisition

dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(0), c_bool(True))

if amplitude*2 > 5:
    InputRange = 10;
else:
    InputRange = 1

dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(InputRange))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(1), c_double(1))  #set rangeof all channels to 1
#dwf.FDwfAnalogInChannelRangeSteps(hdwf, stepsarray, ranges)


#dwf.FDwfAnalogInFrequencyInfo(hdwf, byref(phzMin), byref(phzMax))
#output = []
#for x in range(0, len(stepsarray)):
#    output.append(stepsarray[x])
#print("array is:", output)
#print("min is: ", phzMin,", max is:", phzMax)


dwf.FDwfAnalogInChannelFilterSet(hdwf, c_int(-1), filterAverage)
#I think it's averaging over 12 bit values and outputing another 12 bit value

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
        print()
        print("Values lost. Decrease sample rate")
        exit(1)
    if cCorrupted.value :
        fCorrupted = 1
        print()
        print("Values corrupted. Decrease sample rate and/or sample number")
        exit(1)

    if cAvailable.value==0 :
        print("ending")
        continue


    if cSamples+cAvailable.value > nSamples : #grab the last little bit
        cAvailable = c_int(nSamples-cSamples) ###########- #########
        print("grab last little bit")
    #print("avaiable values: ", cAvailable.value)
    #print("nSamples is: ", nSamples," and cSamples is: ", cSamples)
    dwf.FDwfAnalogInStatusData(hdwf, c_int(0), byref(rgdSamples, sizeof(c_double)*cSamples), cAvailable) # get channel 1 data
    dwf.FDwfAnalogInStatusData(hdwf, c_int(1), byref(rgdSamples2, sizeof(c_double)*cSamples), cAvailable) # get channel 2 data
    cSamples += cAvailable.value
    #print("final cSamples: ", cSamples)
    #print("values added")

    printProgressBar(cSamples + 1, nSamples, prefix = 'Progress:', suffix = 'Complete', length = 50)

    #plt.plot(rgdSamples[0,cSamples], color = '#962424')
    #plt.show()
print()
print("Recording finished")
print("External averaging over ", avg_N, " samples.")
if fLost:
    print("Samples were lost! Reduce frequency")
if fCorrupted:
    print("Samples could be corrupted! Reduce frequency")


# should redo this to record internal averaged samples
if len(sys.argv) < 2:
    filename1 = datetime.datetime.now().strftime("IV_%m_%d_%Y-%H%M%S")
    f = open(filename1, "w")
    f.write("Volts2, Volts2\n")
    for x in range(0, len(rgdSamples)):
        f.write("%s," % rgdSamples[x])
        f.write("%s\n" % rgdSamples2[x])
    f.close()
    print("File saved as: ", filename1)
elif sys.argv[1] == "m":
    print("File save deactivated")

# find first point

samples = 0
sum1 = 0
sum2 = 0
Scounter = 0
Bcounter = 0
RGD1 = []
RGD2 = []



for sample in range(len(rgdSamples)):
    sum1 += rgdSamples[sample]
    sum2 += rgdSamples2[sample]
    Scounter += 1
    if Scounter >= avg_Nint:
        RGD1.append(sum1/Scounter)
        RGD2.append(sum2/Scounter)
        Bcounter += 1
        Scounter = 0
        sum1 = 0
        sum2 = 0

print("length of RGD1 is: ", len(RGD1))
print("length of RGD2 is: ", len(RGD2))







## in progress

begin = 0
for i in range(0, ptspp):
    if rgdSamples[i] < 0 and rgdSamples[i+1] > 0:
        begin = i + 1
        break
    elif i == ptspp:
        print("Proper begin point not found")

print("begin =", begin)
end = nSamples
for i in range(nSamples, ptspp, -1):
    if rgdSamples[i-1] < 0 and rgdSamples[i-2] > 0:
        end = i
        break
print("end =", end)

print("length of rgdSamples: ", len(rgdSamples))
print("length of rgdSamples2: ", len(rgdSamples2))

driver=[0.0]*len(rgdSamples)
rgpz=[0.0]*len(rgdSamples2)
for i in range(0,nSamples):
    driver[i]=rgdSamples[i]
    rgpz[i]=rgdSamples2[i]


if periods >= 2:
    plotlength = 2 * ptspp
if periods < 2:
    plotlength = nSamples

scatterx = rgpz[0:plotlength]
scattery = [0] * plotlength

print("length of scatterx: ", len(scatterx))
print("length of scattery: ", len(scattery))
#rgpz is discretized on a grid that is too course
for i in range(0,plotlength):
    scattery[i] = ((driver[i]-rgpz[i])/(R*1000))*1000000

plt.figure(0)
plt.plot(driver, color = '#962424') #red
 #rg or grpy is direct waveform generator voltage
plt.plot(rgpz, color = '#249096') #cyan


plt.figure(1)
plt.scatter(scatterx,scattery, s=1)
plt.xlabel("Input Voltage (V)")
plt.ylabel("Current (µA)")
plt.title("IV Performance")
#plt.savefig(filename1 + ".png")
plt.show()
