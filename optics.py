import pyvisa as visa
import time
import numpy as np
import pymeasure
from pymeasure.instruments.keithley import Keithley2400
import matplotlib.pyplot as plt

class Meas:
    def __init__(
        self,
        Kepco_id="GPIB0::2::INSTR",
        Fluke_id="GPIB0::6::INSTR",
        Delayline_id="ASRL6::INSTR",
        Oscilloscope_id="USB0::0x0957::0x172D::MY50340112::INSTR",
    ):
        # open the resource manager and connect to the instruments
        rm = visa.ResourceManager()
        self.Kepco = rm.open_resource(Kepco_id)
        self.Fluke = rm.open_resource(Fluke_id)
        self.Delayline = rm.open_resource(Delayline_id)
        self.Oscilloscope = rm.open_resource(Oscilloscope_id)

    def Setfield(self, magcurr=0, Kepco=None, Fluke=None):
        if Kepco is None:
            Kepco = self.Kepco
        if Fluke is None:
            Fluke = self.Fluke

        Kepco.write("CURR {}".format(magcurr))
        Flag = False
        while not Flag:
            r = Kepco.query("MEAS:CURR?")
            readcurrent = float(r.split("\n")[0])
            if np.abs(magcurr - readcurrent) <= 0.1:
                Flag = True
        s = Fluke.query("Y1T0")
        Field = float(s.split(",")[0]) * 10000  # Oe
        print("kepco current is {} A;".format(magcurr), "field is {} Oe".format(Field))
        return Field

    def SetDelayline(self, t=100, Delayline=None):
        if Delayline is None:
            Delayline = self.Delayline

        writet = t - 200  # unit ps
        writep = round(writet * 1e-12 * 299792458 / 1e-6 / 2 * 10) / 10
        writepstr = "PX" + str(writep)
        Delayline.write(writepstr)
        time.sleep(1)

        run_count = 1
        while True:
            try:
                Delayline.write("DX")
                s = Delayline.read("DX", encoding="unicode_escape")
                readp = float((s.split("=")[1]).split(" ")[0])
                readt = readp * 1e-6 * 2 / 299792458 / 1e-12  # unit ps
                time.sleep(1)
                if np.abs(writep - readp) <= 0.1:
                    break
            except Exception as e:
                print(run_count)
                run_count += 1
                print(e)
                time.sleep(0.3)

        print(
            "delayline position is {};".format(readp),
            "time is {} ps".format(readt + 200),
        )

        return readp, readt + 200

    def OscilloscpeProcess(self, Oscilloscope=None):
        if Oscilloscope is None:
            Oscilloscope = self.Oscilloscope
        # Oscilloscope.write('*RST') #reset
        # Oscilloscope.write(':AUT') #auto scale
        # Oscilloscope.write(':DIG') #Initiate single snap
        Osi = Oscilloscope.query(":WAV:SOUR CHAN1;PRE?")  # channel 1
        dt = float(Osi.split(",")[4])
        dy = float(Osi.split(",")[7])
        TT = np.arange(0, 1000, 1) * dt
        Oscilloscope.write(":WAV:DATA?")  # channel 1
        str1 = Oscilloscope.read(":WAV:DATA?", encoding="unicode_escape")
        Binstr = [ord(c) for c in str1[10:2010]]    #convert to binary
        Y = []
        for i in range(0, 1000):
            Y.append((Binstr[2 * i] * 256 + Binstr[2 * i + 1] - 32768) * dy)

        data = sum(Y)
        return data

    def OscilloscpeProcess2(self, avg=100):
        Y = []
        for i in range(avg):
            Y.append(self.OscilloscpeProcess())
        Y = np.sort(Y)
        #    plt.plot(Y)
        data = np.mean(
            Y[round(3 * len(Y) / 4) - 5 : round(3 * len(Y) / 4) + 5]
        ) - np.mean(Y[round(len(Y) / 4) - 5 : round(len(Y) / 4) + 5])

        return data




## TODO: make the stuff below a separate class

    def FielddepMeaasurment(self, file_dir, ID="test",lock1=None, lock2=None, currs=[], count=1, Field=True, Reset=False):
        if lock1 is None:
            lock1 = self.Lockin(rm, 1)
        if lock2 is None:
            lock2 = self.lock2
        file_name = (
            file_dir
            + ID
            + "_Kepco_{}A_to_{}A_{}.csv".format(
                min(currs), max(currs), int(time.time())
            )
        )
        with open(file_name, "w") as f:
            f.write("Current, lockin1x, lockin1y, lockin2x, lockin2y, Field'\n")

        # Create subplots
        figure, axes = plt.subplots(4, 1, figsize=(5, 20))
        plt.subplots_adjust(
            left=0.2, bottom=0.1, right=0.9, top=0.9, wspace=0.4, hspace=0.4
        )
        # Data Coordinates
        x1, x2, x3, x4, y1, y2, y3, y4, field = [], [], [], [], [], [], [], [], []
        # GUI
        plt.ion()
        #  Plot
        (plot1,) = axes[0].plot(x1, y1, "bo-")
        (plot2,) = axes[1].plot(x2, y2, "go-")
        (plot3,) = axes[2].plot(x3, y3, "bo-")
        (plot4,) = axes[3].plot(x4, y4, "go-")
        # Labels
        if Field:
            axes[0].set_xlabel("Field", fontsize=18)
            axes[1].set_xlabel("Field", fontsize=18)
            axes[2].set_xlabel("Field", fontsize=18)
            axes[3].set_xlabel("Field", fontsize=18)
        else:
            axes[0].set_xlabel("Kepco Current", fontsize=18)
            axes[1].set_xlabel("Kepco Current", fontsize=18)
            axes[2].set_xlabel("Kepco Current", fontsize=18)
            axes[3].set_xlabel("Kepco Current", fontsize=18)

        axes[0].set_ylabel("Lockin1_X", fontsize=18)
        axes[1].set_ylabel("Lockin1_Y", fontsize=18)
        axes[2].set_ylabel("Lockin2_X", fontsize=18)
        axes[3].set_ylabel("Lockin2_Y", fontsize=18)

        for curr in currs:
            F = self.Setfield(magcurr=curr)
            A = lock1.lock_in_measure(
                count=count, time_step=0.1, wait_before_measure=0.0
            )
            B = lock2.lock_in_measure(
                count=count, time_step=0.1, wait_before_measure=0.0
            )

            if Field:
                x1.append(F)
                x2.append(F)
                x3.append(F)
                x4.append(F)
            else:
                x1.append(curr)
                x2.append(curr)
                x3.append(curr)
                x4.append(curr)

            y1.append(A[0])
            y2.append(A[1])
            y3.append(B[0])
            y4.append(B[1])
            field.append(F)

            plot1.set_xdata(x1)
            plot1.set_ydata(y1)
            axes[0].relim()
            axes[0].autoscale_view(True, True, True)
            figure.canvas.draw()
            figure.canvas.flush_events()
            plt.show()

            plot2.set_xdata(x2)
            plot2.set_ydata(y2)
            axes[1].relim()
            axes[1].autoscale_view(True, True, True)
            figure.canvas.draw()
            figure.canvas.flush_events()
            plt.show()

            plot3.set_xdata(x3)
            plot3.set_ydata(y3)
            axes[2].relim()
            axes[2].autoscale_view(True, True, True)
            figure.canvas.draw()
            figure.canvas.flush_events()
            plt.show()

            plot4.set_xdata(x4)
            plot4.set_ydata(y4)
            axes[3].relim()
            axes[3].autoscale_view(True, True, True)
            figure.canvas.draw()
            figure.canvas.flush_events()
            plt.show()

            with open(file_name, "a") as f:
                f.write("{},{},{},{},{},{}\n".format(curr, A[0], A[1], B[0], B[1], F))

            plt.savefig(file_name + ".png")
        if Reset:
            Setfield(magcurr=0)

    def TimedepMeaasurment(self, file_dir, ID="test", ts=[], curr=0, count=1, Reset=False, Pos=False):

        F = self.Setfield(magcurr=curr)

        file_name = (
            file_dir
            + ID
            + "_Delayline_{}ps_to_{}ps_{}Oe_{}.csv".format(
                min(ts), max(ts), F, int(time.time())
            )
        )
        with open(file_name, "w") as f:
            f.write("Time, lockin1x, lockin1y, lockin2x, lockin2y, Field, Position'\n")

        # Create subplots
        figure, axes = plt.subplots(4, 1, figsize=(5, 20))
        plt.subplots_adjust(
            left=0.2, bottom=0.1, right=0.9, top=0.9, wspace=0.4, hspace=0.4
        )
        # Data Coordinates
        x1, x2, x3, x4, y1, y2, y3, y4, delay, position = (
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
        )
        # GUI
        plt.ion()
        #  Plot
        (plot1,) = axes[0].plot(x1, y1, "bo-")
        (plot2,) = axes[1].plot(x2, y2, "go-")
        (plot3,) = axes[2].plot(x3, y3, "bo-")
        (plot4,) = axes[3].plot(x4, y4, "go-")
        # Labels
        if Pos:
            axes[0].set_xlabel("Position", fontsize=18)
            axes[1].set_xlabel("Position", fontsize=18)
            axes[2].set_xlabel("Position", fontsize=18)
            axes[3].set_xlabel("Position", fontsize=18)
        else:
            axes[0].set_xlabel("Time", fontsize=18)
            axes[1].set_xlabel("Time", fontsize=18)
            axes[2].set_xlabel("Time", fontsize=18)
            axes[3].set_xlabel("Time", fontsize=18)
        axes[0].set_ylabel("Lockin1_X", fontsize=18)
        axes[1].set_ylabel("Lockin1_Y", fontsize=18)
        axes[2].set_ylabel("Lockin2_X", fontsize=18)
        axes[3].set_ylabel("Lockin2_Y", fontsize=18)

        for t in ts:
            T = SetDelayline(t=t)
            A = lock1.lock_in_measure(
                count=count, time_step=0.1, wait_before_measure=0.0
            )
            B = lock2.lock_in_measure(
                count=count, time_step=0.1, wait_before_measure=0.0
            )

            if Pos:
                x1.append(T[0])
                x2.append(T[0])
                x3.append(T[0])
                x4.append(T[0])
            else:
                x1.append(T[1])
                x2.append(T[1])
                x3.append(T[1])
                x4.append(T[1])

            y1.append(A[0])
            y2.append(A[1])
            y3.append(B[0])
            y4.append(B[1])
            delay.append(T[1])
            position.append(T[0])

            plot1.set_xdata(x1)
            plot1.set_ydata(y1)
            axes[0].relim()
            axes[0].autoscale_view(True, True, True)
            figure.canvas.draw()
            figure.canvas.flush_events()
            plt.show()

            plot2.set_xdata(x2)
            plot2.set_ydata(y2)
            axes[1].relim()
            axes[1].autoscale_view(True, True, True)
            figure.canvas.draw()
            figure.canvas.flush_events()
            plt.show()

            plot3.set_xdata(x3)
            plot3.set_ydata(y3)
            axes[2].relim()
            axes[2].autoscale_view(True, True, True)
            figure.canvas.draw()
            figure.canvas.flush_events()
            plt.show()

            plot4.set_xdata(x4)
            plot4.set_ydata(y4)
            axes[3].relim()
            axes[3].autoscale_view(True, True, True)
            figure.canvas.draw()
            figure.canvas.flush_events()
            plt.show()

            with open(file_name, "a") as f:
                f.write(
                    "{},{},{},{},{},{},{}\n".format(t, A[0], A[1], B[0], B[1], F, T[0])
                )
            plt.savefig(file_name + ".png")
            plt.show()

        if Reset:
            self.Setfield(magcurr=0)
