import serial, time, cmath, socket
import matplotlib.pyplot as plt

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

# connect to scope
#kernel_tmc = universal_usbtmc.import_backend("linux_kernel")
#scope = kernel_tmc.Instrument("/dev/usbtmc1")
scope = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
scope.connect(("192.168.1.42", 5555))

def scopew(command):
    command += "\n"
    scope.send(command.encode())

def scopeq(query):
    return float(scope.recv(BUF_SIZE))

# connect to fn generator
ser = serial.Serial("/dev/ttyUSB0", 115200)
def fngen(command):
    ser.write(command + b'\n')
    ser.readline()

# base scope settings
scopew(":meas:clear all")
for channel, settings in channels.items():
    for setting in settings:
        scopew(":%s:%s" % (channel, setting))

for setting in scopeSettings:
    scopew(":%s" % setting)

# base fn generator settings
fngen(b'WFN0') # turn off ch2
fngen(b'WMW00') # sine
fngen(b'WMA00.50') # 1Vpp

def setchan2(scope):
    # if Vpp is absurd (not in [-1,1]) the scale is too big,
    # back off until it's not
    scopew(":acq:type normal")
    time.sleep(.5)
    scopew(":meas:source chan2")
    time.sleep(.5)
    scale = scopeq(":chan2:scale?")
    vpp = scopeq(":meas:vpp?")
    while vpp < -2 or vpp > 8*scale:
        scale *= 2
        scope.write(":chan2:scale %e" % scale)
        time.sleep(1) # settle?
        vpp = scopeq(":meas:vpp?")
    # set the scale to be reasonable for measured vpp
    scope.write(":chan2:scale %e" % (1.1 * vpp / 8))

def measure(freq):
    scopew(":meas:stat:reset")
    time.sleep(10)
    vtotal = scopeq(":meas:stat:item? aver, vpp, chan1")
    vtotdev = scopeq(":meas:stat:item? dev, vpp, chan1")
    vind = scopeq(":meas:stat:item? aver, vpp, chan2")
    vinddev = scopeq(":meas:stat:item? dev, vpp, chan2")
    phase = scopeq(":meas:stat:item? aver, rphase, chan2, chan1")
    phasedev = scopeq(":meas:stat:item? dev, rphase, chan2, chan1")
    z, l, = getZLR(freq, vtotal, vind, phase)
    print(z, l)
    return z, l

def getZLR(freq, vtotal, vind, phase):
    vind = cmath.rect(vind, phase*cmath.pi/180)
    k = vind/vtotal
    z = (-k*resistor)/(k-1)
    return z, 1e6*z.imag/(2*cmath.pi*freq)

data = []
for freq in range(startFreq, stopFreq, freqStep):
    fngen(b'WMF%d'% (freq*1000000))
    time.sleep(.1)
    scope.write(":tim:scale %e" % (0.1/freq))
    setchan2(scope)

    scope.write(":acq:type aver")
    scope.write(":acq:aver 1024")
    scope.write(":acq:mdepth 6000")
    time.sleep(max(9000/freq, 1))
    z, l = measure(freq)
    data.append([freq, z, l])

ser.close()
transposed = list(zip(*data))
plt.plot(transposed[0], list(map(lambda x: x.imag, transposed[1])))
plt.show()

