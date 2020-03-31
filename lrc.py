import serial, time, cmath
import universal_usbtmc
import matplotlib.pyplot as plt

kernel_tmc = universal_usbtmc.import_backend("linux_kernel")

fngen = "/dev/ttyUSB0"
startFreq = 1000
freqStep = 500
stopFreq = 50000
resistor = 99.4

scope = kernel_tmc.Instrument("/dev/usbtmc1")

def setup_channel(scope, channel):
    settings = ["bwlimit 20M", "coup ac", "disp on", "inv off", "prob 1", "offset 0", "vern on", "scale 0.05"]
    for setting in settings:
        scope.write(":chan%d:%s" % channel, setting)
    scope.write(":meas:source chan%d" % channel)
    scope.write(":meas:vpp")

scope.write(":meas:clear all")
setup_channel(scope, 1)
setup_channel(scope, 2)
scope.write(":chan3:disp off")
scope.write(":chan4:disp off")
scope.write("meas:rphase")

scope.write(":trig:mode edge")
scope.write(":trig:coup hfr")
scope.write(":trig:coup hfr")
scope.write(":trig:edge:source chan1")
scope.write(":trig:edge:slope pos")
scope.write(":trig:edge:level 0")
scope.write(":run")

ser = serial.Serial(fngen, 115200)
ser.write(b'WFN0\n') # turn off ch2
ser.readline()
ser.write(b'WMW00\n') # sine
ser.readline()
ser.write(b'WMA00.50\n') # 1Vpp
ser.readline()

fdata = []
ldata = []
rdata = []

def setchan2(scope):
    # if Vpp is absurd (not in [-1,1]) the scale is too big,
    # back off until it's not
    scope.write(":acq:type normal")
    time.sleep(.5)
    scope.write(":meas:source chan2")
    time.sleep(.5)
    scale = float(scope.query(":chan2:scale?"))
    vpp = float(scope.query(":meas:vpp?"))
    while vpp < -2 or vpp > 8*scale:
        scale = float(scope.query(":chan2:scale?"))
        scope.write(":chan2:scale %e" % (scale*2))
        time.sleep(1) # settle?
        vpp = float(scope.query(":meas:vpp?"))
    # set the scale to be reasonable for measured vpp
    scope.write(":chan2:scale %e" % (1.1 * vpp / 8))

def measure(scope, freq):
    """
    measure returns L, R
    measure does not change any scope settings, it just reads them
    """
    scope.write(":meas:stat:reset")
    time.sleep(4)
    vtotal = float(scope.query(":meas:stat:item? aver, vpp, chan1"))
    vind = float(scope.query(":meas:stat:item? aver, vpp, chan2"))
    phase = float(scope.query(":meas:stat:item? aver, rphase, chan1, chan2"))
    l, r = getL(freq, vtotal, vind, phase)
    return l, r

def getL(freq, vtotal, vind, phase):
    vind = cmath.rect(vind, phase*cmath.pi/180)
    k = vind/vtotal
    z = (-k*resistor)/(k-1)
    return z.imag/(2*cmath.pi*freq), z.real


for freq in range(startFreq, stopFreq, freqStep):
    ser.write(b'WMF%d\n'% (freq*1000000)) # 1Vpp
    ser.readline()
    time.sleep(.1)
    scope.write(":tim:scale %e" % (0.1/freq))
    setchan2(scope)
    if freq == startFreq:
        setchan2(scope)

    scope.write(":acq:type aver")
    scope.write(":acq:aver 512")
    scope.write(":acq:mdepth 6000")
    time.sleep(max(9000/freq, 1))
    l, r = measure(scope, freq)
    print(l*1e6, r)
    fdata.append(freq)
    ldata.append(l*1e6)
    rdata.append(r)

ser.close()

plt.plot(fdata, ldata)
plt.plot(fdata, rdata)
plt.show()

