import serial, time 
import matplotlib.pyplot as plt
import numpy as np
import scipy.fft as fft
from scope import Rigol1054z

chanSettingsFile = "chan.txt"
scopeSettingsFile = "scope.txt"

startFreq = 1000
freqStep = 3000
stopFreq = 50000
resistor = 99.4

with open(chanSettingsFile) as f:
    chanSettings = f.readlines()

with open(scopeSettingsFile) as f:
    scopeSettings = f.readlines()

channels = {
    "chan1": chanSettings,
    "chan2": chanSettings,
    "chan3": ["disp off"],
    "chan4": ["disp off"],
}

scope = Rigol1054z()

# connect to fn generator
ser = serial.Serial("/dev/ttyUSB0", 115200)
def fngen(command):
    ser.write(command + b'\n')
    ser.readline()

# base scope settings
for channel, settings in channels.items():
    for setting in settings:
        scope.w("%s:%s" % (channel, setting))

for setting in scopeSettings:
    scope.w("%s" % setting)

# base fn generator settings
fngen(b'WFN0') # turn off ch2
fngen(b'WMW00') # sine
fngen(b'WMA00.50') # 1Vpp

def setchan2(scope):
    # if Vpp is absurd (not in [-1,1]) the scale is too big,
    # back off until it's not
    scope.w("meas:source chan2")
    time.sleep(.5)
    scale = scope.qf("chan2:scale?")
    vpp = scope.qf("meas:vpp?")
    while vpp < -2 or vpp > 8*scale:
        scale *= 2
        scope.w("chan2:scale %e" % scale)
        time.sleep(1) # settle?
        vpp = scope.qf("meas:vpp?")
    # set the scale to be reasonable for measured vpp
    scope.w("chan2:scale %e" % (1.1 * vpp / 8))

def measure2(freq):
    scope.w("sing")
    ch1, ch2 = scope.grab_all(1), scope.grab_all(2)
    fft1, fft2 = fft.rfft(ch1[1]), fft.rfft(ch2[1])
    n_samples = len(ch1[1])
    bin_size = 1/(n_samples*ch2[2])
    bin = int(np.round(freq/bin_size))
    vind = fft.rfft(ch2[1])[bin]
    vtotal = fft.rfft(ch1[1])[bin]
    z, l = getZL(freq, vtotal, vind)
    print(l, bin, np.absolute(vind), np.absolute(vtotal))
    return l

def getZL(freq, vtotal, vind):
    k = vind/vtotal
    z = (-k*resistor)/(k-1)
    return z, 1e6*np.imag(z)/(2*np.pi*freq)

data = []
for freq in range(startFreq, stopFreq, freqStep):
    fngen(b'WMF%d'% (freq*1000000))
    time.sleep(.1)
    setchan2(scope)

    l = np.mean([measure2(freq) for x in range(1,10)])
    data.append([freq, l])

ser.close()
transposed = list(zip(*data))
plt.plot(transposed[0], transposed[1])
plt.show()

