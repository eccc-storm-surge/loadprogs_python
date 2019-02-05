import logging
from pathlib import Path

import pandas as pd
from matplotlib.gridspec import GridSpec

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from data.obs import Station
from util.crosspec import crosspec
import numpy as np


def plot_ts_and_spectre(hourly_series: pd.Series, data_label="", img_dir: Path=None, subplot_titles=None,
                        raw_data=None, tides=None):

    logging.basicConfig(level=logging.INFO)

    min_period_h = 6.
    max_period_h = 24 * 30.
    eps = 1e-8
    vline_width = 0.5
    vline_style = "dashed"


    if img_dir is None:
        img_dir = Path(".")

    gs = GridSpec(3, 1, hspace=0.8)
    fig = plt.figure(figsize=(10, 8))

    # timeseries
    ax = fig.add_subplot(gs[0, 0])
    hourly_series.plot(ax=ax, grid=True, color="k")
    if subplot_titles is not None:
        ax.set_title(subplot_titles[0])

    # power spectrum
    ax = fig.add_subplot(gs[1, 0])
    # hourly_series.to_csv("test.csv", header=None)
    f, pxx = crosspec(min(1024, len(hourly_series)), hourly_series.values)
    f += eps

    selection = ((1.0 / f) >= min_period_h) & ((1.0 / f) <= max_period_h)
    f = f[selection]
    pxx = pxx[selection]

    ax.loglog(f, pxx, color="k")
    ax.set_xlim(1.0 / max_period_h, 1.0 / min_period_h)
    ax.grid(True)
    if subplot_titles is not None:
        ax.set_title(subplot_titles[1])

    def __format_spectre_x(x, pos):
        if x == 0:
            return r"$\inf$"

        return f"{1.0 / x: .1f}"

    ax.xaxis.set_major_formatter(
        FuncFormatter(__format_spectre_x)
    )

    ax.axvline(1. / 12, color="b", label="T = 12h", lw=vline_width, linestyle=vline_style)
    ax.axvline(1. / 24, color="r", label="T = 24h", lw=vline_width, linestyle=vline_style)
    ax.axvline(1. / 48, color="g", label="T = 48h", lw=vline_width, linestyle=vline_style)
    ax.legend()

    ax.set_xlabel("Period (h)")

    # Power spectrum density
    ax = fig.add_subplot(gs[2, 0])
    dt = 1.

    plt.psd(hourly_series.values, Fs=1 / dt, NFFT=min(1024, len(hourly_series)), label="detided", color="k")

    if tides is not None:
        # raw_data.plot(ax=ax)
        v = tides.values.copy()
        v[np.isnan(v)] = 0
        plt.psd(v, Fs=1 / dt, NFFT=min(1024, len(tides.values)), label="tides", color="cyan")

    if raw_data is not None:
        v = raw_data.values.copy()
        v[np.isnan(v)] = 0.
        plt.psd(v, Fs=1 / dt, NFFT=min(1024, len(v)), label="raw", color="m")

    ax.axvline(1. / (12 * dt), color="b", label="T = 12h", lw=vline_width, linestyle=vline_style)
    ax.axvline(1. / (24 * dt), color="r", label="T = 24h", lw=vline_width, linestyle=vline_style)
    ax.axvline(1. / (48 * dt), color="g", label="T = 48h", lw=vline_width, linestyle=vline_style)
    ax.legend(bbox_to_anchor=(1.02, 0.5), loc="center left", borderaxespad=0)

    img_file = img_dir / f"ts_spectre_{data_label}.png"

    fig.savefig(str(img_file), dpi=300, bbox_inches="tight")
    plt.close(fig)


def test():
    st_id = "8443970"

    data_dir = "/home/olh001/MATLAB/detide/data/obs/merged_2016_2017/"

    data_file = Path(data_dir) / f"X{st_id}.dat"

    s = Station(data_file=data_file, station_info={"name": st_id, "id": st_id, "lat": 42.3539, "lon": -71.0503}, do_filtering=True)

    print(s.data)
    obs_data = s.get_detided_series(do_filtering=True)
    obs_data = obs_data.asfreq("30T").fillna(method="ffill", limit=1).asfreq("60T")

    plot_ts_and_spectre(obs_data, "test", tides=s.data["tides"].asfreq("30T").fillna(method="ffill", limit=1).asfreq("60T"),
                        raw_data=s.data["twl-mean"].asfreq("30T").fillna(method="ffill", limit=1).asfreq("60T"))
    plt.show()


if __name__ == '__main__':
    test()