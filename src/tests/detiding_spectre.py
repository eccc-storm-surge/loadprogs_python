from pathlib import Path

import numpy as np
from scipy import signal

from data.obs import Station
import matplotlib.pyplot as plt

from util.crosspec import crosspec


def main():
    st_id = "8443970"

    data_dir = "/home/olh001/MATLAB/detide/data/obs/merged_2016_2017/"

    data_file = Path(data_dir) / f"X{st_id}.dat"

    s = Station(data_file=data_file, station_info={"name": st_id, "id": st_id, "lat": 42.3539, "lon": -71.0503}, do_filtering=False)

    print(s.data)

    # initial water level time series
    # filling missing values with 0 as in Natacha's script (~/MATLAB/detide/loadprogs_matlab/crosspec.m)
    wl0 = s.data["twl-mean"].asfreq("60T").fillna(value=0)
    wl1_notides = s.data["detided"].asfreq("60T").fillna(value=0)


    plt.figure()
    plt.title("t-space")
    ax = plt.gca()
    wl0.plot(ax=ax, color="b", linestyle="dashed")
    wl1_notides.plot(ax=ax, color="r")

    plt.figure()
    plt.title("f-space")

    amp0 = np.fft.fft(wl0.values, norm="ortho")
    freq = np.fft.fftfreq(len(wl0), d=1.0 / 24.0)
    amp1_notides = np.fft.fft(wl1_notides.values, norm="ortho")

    freq_lower_limit = 0.
    freq_upper_limit = 1 / 0.25
    selection = (freq >= freq_lower_limit) & (freq <= freq_upper_limit)

    amp0 = amp0[selection]
    amp1_notides = amp1_notides[selection]
    freq = freq[selection]

    freq = freq[:]
    amp0 = amp0[:]
    amp1_notides = amp1_notides[::]

    p0 = amp0 * np.conjugate(amp0)
    p1 = amp1_notides * np.conjugate(amp1_notides)

    plt.semilogx(freq, p0, color="b")
    plt.semilogx(freq, p1, color="r")

    ax = plt.gca()
    # ax.xaxis.set_major_locator(MultipleLocator(base=12))
    plt.xlabel("freq (day**-1)")



    plt.figure()
    plt.title("PSD")
    dt = 1.0 / 24
    t = np.arange(0, len(wl0.values) * dt, dt)
    plt.psd(wl0.values, 1024, 1 / dt, color="b")
    plt.psd(wl1_notides.values, 1024, 1 / dt, color="r")

    plt.figure()
    plt.title("CSD")
    dt = 1.0

    # freq0, pxx0 = signal.csd(wl0.values, wl0.values, 1 / dt)
    # plt.plot(freq0, pxx0, color="b")

    freq1, pxx1 = signal.csd(wl0.values, wl1_notides.values, 1 / dt)
    plt.plot(freq1, pxx1, color="r")


    plt.figure()
    plt.title("Power spectre from MATLAB")
    #freq0, pxx0 = crosspec(1500, wl0.values)
    #plt.plot(freq0, pxx0, color="b")

    freq1, pxx1 = crosspec(1500, wl1_notides.values)
    plt.plot(freq1, pxx1, color="r")


    plt.show()






if __name__ == '__main__':
    main()