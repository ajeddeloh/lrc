import serial, time, sys
import matplotlib.pyplot as plt
import numpy as np
import scipy.fft as fft
from scope import Rigol1054z

chanSettingsFile = "chan.txt"
scopeSettingsFile = "scope.txt"

if len(sys.argv) != 5:
    print("usage: lrc <start freq> <stop freq> <freq step> <r>")

startFreq = int(sys.argv[1])
stopFreq = int(sys.argv[2])
freqStep = int(sys.argv[3])
resistor = float(sys.argv[4])

with open(chanSettingsFile) as f:
    chanSettings = f.readlines()

with open(scopeSettingsFile) as f:
    scopeSettings = f.readlines()

scope = Rigol1054z()
scope.w(*scopeSettings)
scope.w(*["chan1:%s" % setting for setting in chanSettings])
scope.w(*["chan2:%s" % setting for setting in chanSettings])
scope.w("chan2:scale 0.005", timeout=.5)
scope.w("sing", "tfor", timeout=.5)
time.sleep(1)
tdiv = scope.qf("wav:xinc?")

# connect to fn generator
ser = serial.Serial("/dev/ttyUSB0", 115200)
def fngen(command):
    ser.write(command + b'\n')
    ser.readline()

# base fn generator settings
fngen(b'WFN0') # turn off ch2
fngen(b'WMW00') # sine
fngen(b'WMA02.00') # 4Vpp

def setchan2(scope):
    ch2 = scope.grab_all_raw(2)
    while max(ch2) > 245 or min(ch2) < 15:
        scale = scope.qf("chan2:scale?")
        scope.w(("chan2:scale %f" % (scale*2)),
                "sing", "tfor", timeout=0.2)
        ch2 = scope.grab_all_raw(2)
    return ch2

def measure(freq):
    ch2 = setchan2(scope)
    ch1 = scope.grab_all(1)
    fft1, fft2 = fft.rfft(ch1[1]), fft.rfft(ch2[1])
    n_samples = len(ch1[1])
    bin_size = 1/(n_samples*tdiv)
    bin = int(np.round(freq/bin_size))
    print(bin)
    vL = fft.rfft(ch2[1])[bin]
    vT = fft.rfft(ch1[1])[bin]
    return getZ(freq, vT, vL, resistor)

def getZ(freq, vtotal, vind, r):
    k = vind/vtotal
    z = (-k*r)/(k-1)
    print(z)
    return z

freqs, zs = [], []
for freq in range(startFreq, stopFreq+1, freqStep):
    # Frequency is set as an integer number of uHz
    fngen(b'WMF%d'% (freq*1e6))
    time.sleep(.1)
    zs.append(measure(freq))
    freqs.append(freq)

res = np.polyfit(freqs, np.array(zs), 1)
print(res[1], res[0]/(1j*2*np.pi))
plt.plot(freqs, np.imag(np.array(zs)))
plt.plot(freqs, np.imag(res[1]+res[0]*np.array(freqs)))

plt.show()

