Measure Inductance with a Scope and Function Generator
======================================================

This project measures inductors using a Rigol 1054z oscilloscope and a FeelTech
FY6800 function generator. It measures the inductance over an adjustable
frequency range. It can also measure series resistance (though it does not plot
it yet).

## Setup:

Make sure the oscope is accessible over network at `192.168.1.42:5555`. Make sure
the function generator is accessible over USB at `/dev/ttyUSB0`. I'll probably
break those out into command line options later, but for just edit the source
if yours are at different addresses.

### Wiring:

```
    oscope channel 1 ----+---- function generator
                         |
			 R=100
			 |
    oscope channel 2 ----+
                         |
			 L=?
			 |
		      Grounds
```

## Running:

`python lrc.py <start freq> <stop freq> <freq step>`

## Theory:

This measures inductance using a voltage divider with a known resistor and the
inductor. Initially it simply used the scope's built in measurements to measure
the peak to peak voltages and phase differences. This proved problematic
because at low frequencies where the voltage across the inductor is small it is
dominated by noise. Similarly, at high frequency the phase differences become
very small and can be dominated by noise. I switched to doing it all in the
frequency domain which eliminates noise except at the frequency being tested,
greatly improving precision. This also eliminates the need to constantly be
changing the time division setting and speeds up measurement.

Windowing is normally a problem as the window chosen can affect the amplitude
and phase measured. However, in this case because we only care about the ratio
of two signals at the same frequency, it's not of concern since they're both
affected by the windowing function equally. Still, for best results set the
time division and sample length such that the frequencies being measured fall
exactly into an fft bin.

## TODO:

 - Better argument parsing
 - Measure parasitic capacitance
 - Measure distortion to detect saturation
 - Better output graphs
 - Code clean up
