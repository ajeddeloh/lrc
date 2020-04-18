import socket, time
import matplotlib.pyplot as plt
import scipy.fft as fft
import numpy as np

class Rigol1054z:
    defaultAddress = ("192.168.1.42", 5555)
    max_grab=250000
    header_size=12

    def __init__(self, address=defaultAddress):
        self.s = socket.create_connection(address)
        self.w("wav:mode raw")
        self.w("wav:form byte")

    def w(self, x):
        self.s.send((':' + x + '\n').encode())
    
    def q(self, x):
        self.w(x)
        return self.s.recv(4096).decode()
    
    def qf(self, x):
        return float(self.q(x))
    
    def qi(self, x):
        return int(self.q(x))
    
    def qr(self, x, l):
        self.w(x)
        d = self.s.recv(4096)
        while len(d) < l:
            d += self.s.recv(4096)
        return d

    def grab_chunk(self, start, stop):
        e = min(start+self.max_grab-1, stop)
        size = e - start + 1
        self.w('wav:start %s' % start)
        self.w('wav:stop %s' % e)
        data = self.qr('wav:data?', size+self.header_size)[11:-1]
        start = e+1
        return data, start
        

    def grab(self, chan, start, stop):
        samples = 1+stop-start
        self.w("wav:source chan%d" % chan)
        data, start = self.grab_chunk(start, stop)
        while start < stop:
            chunk, start = self.grab_chunk(start, stop)
            data += chunk
        
        xinc = self.qf('wav:xinc?')
        yinc = self.qf('wav:yinc?')
        yref = self.qf('wav:yref?')
        ydata = yinc*(np.array(list(data))-yref)
        xdata = np.linspace(0, samples*xinc, num=samples, endpoint=False)
        return xdata, ydata, xinc
    
    def grab_all(self, chan):
        self.w("stop")
        n_samples = self.qi('acq:mdepth?')
        return self.grab(chan, 1, n_samples)

s = Rigol1054z()
