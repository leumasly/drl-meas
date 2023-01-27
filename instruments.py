import pyvisa as visa
import time
import numpy as np
import pymeasure
from pymeasure.instruments.keithley import Keithley2400

class Lockin:
    SENSITIVITY = {
        1: 26,
        0.5: 25,
        0.2: 24,
        0.1: 23,
        0.05: 22,
        0.02: 21,
        0.01: 20,
        0.005: 19,
        0.002: 18,
        0.001: 17,
        0.0005: 16,
        0.0002: 15,
        0.0001: 14,
        0.00005: 13,
        0.00002: 12,
        0.00001: 11,
        0.000005: 10,
        0.000002: 9,
        0.000001: 8,
        0.0000005: 7,
        0.0000002: 6,
        0.0000001: 5,
        0.00000005: 4,
        0.00000002: 3,
        0.00000001: 2,
        0.000000005: 1,
        0.000000002: 0,
    }

    def __init__(self, resource, gpib=1):
        self.lock_in = resource.open_resource("GPIB0::{}::INSTR".format(gpib))

        # self.lock_in.query('OUTX1;*IDN?')
        # self.lock_in.write('*RST')
        # self.lock_in.write('ALRM 0;KCLK 0;*ESE 53;ERRE 246;LIAE 7;*CLS;')

    def change_harmonic(self, harm=1, sens=1):
        self.lock_in.write("HARM {}".format(harm))
        self.lock_in.write("SENS {}".format(SENSITIVITY[sens]))

    def lock_in_read(self):
        x = float(self.lock_in.query("OUTP? 1").strip())
        y = float(self.lock_in.query("OUTP? 2").strip())
        r = float(self.lock_in.query("OUTP? 3").strip())
        theta = float(self.lock_in.query("OUTP? 4").strip())
        return x, y, r, theta

    def lock_in_measure(
        self, count=10, time_step=0.1, wait_before_measure=1, harm=1, sens=0.00001
    ):
        # self.change_harmonic(harm, sens)
        time.sleep(wait_before_measure)
        xs, ys, rs, thetas = [], [], [], []
        for i in range(count):
            x, y, r, theta = self.lock_in_read()
            xs += [x]
            ys += [y]
            rs += [r]
            thetas += [theta]
            time.sleep(time_step)

        xs = sorted(xs)
        ys = sorted(ys)
        rs = sorted(rs)
        thetas = sorted(thetas)

        if len(xs) > 30:
            xs = xs[round(1 / 6 * len(xs)) : -round(1 / 6 * len(xs))]
            ys = ys[round(1 / 6 * len(ys)) : -round(1 / 6 * len(ys))]
            rs = rs[round(1 / 6 * len(rs)) : -round(1 / 6 * len(rs))]
            thetas = thetas[round(1 / 6 * len(thetas)) : -round(1 / 6 * len(thetas))]

        x_mean, x_std = np.mean(xs), np.std(xs)
        y_mean, y_std = np.mean(ys), np.std(ys)
        r_mean, r_std = np.mean(rs), np.std(rs)
        theta_mean, theta_std = np.mean(thetas), np.std(thetas)

        return x_mean, y_mean, r_mean, theta_mean, x_std, y_std, r_std, theta_std
