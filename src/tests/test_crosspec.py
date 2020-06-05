from pathlib import Path

from scipy.io import loadmat

import matplotlib.pyplot as plt

from ..data.obs import Station
from ..util.crosspec import crosspec

import numpy as np

from ..util.plot_ts_and_spectre import plot_ts_and_spectre


def test1():
    n = 7350
    x = np.random.randn(n) + 10

    f, p = crosspec(1024, x)

    plt.figure()
    plt.plot(f, p, color="b")
    plt.show()


def test2():
    # st_id = "8443970"
    st_id = "755"

    # data_dir = "/home/olh001/MATLAB/detide/data/obs/merged_2016_2017/"
    data_dir = "/home/olh001/MATLAB/detide/download_scripts/meds/2017_201812_CPOP_RDSPS/"

    data_file = Path(data_dir) / f"X{st_id}.dat"

    s = Station(data_file=data_file, station_info={"name": st_id, "id": st_id, "lat": 42.3539, "lon": -71.0503},
                do_filtering=True)

    print(s.data)

    # initial water level time series
    # filling missing values with 0 as in Natacha's script (~/MATLAB/detide/loadprogs_matlab/crosspec.m)

    data = s.data.asfreq("30T").ffill(limit=1).asfreq("60T")

    plot_ts_and_spectre(data["detided"], "test2",
                        subplot_titles=None,
                        raw_data=data["twl-mean"],
                        tides=data["tides"])
    plt.show()


def test_all():
    mat_file_path = "/fs/site2/dev/eccc/cmd/e/olh001/detide_water_levels/data_for_scoring_rdsps_pseudo-analysis_experimental_2016121500_2017022818_v03/Etaprogs.mat"

    x = loadmat(mat_file_path)

    print(x["Obs"][0][0][4])

    plt.plot(x["Obs"][0][0][4][0])

    plt.figure()

    f0, p0 = crosspec(500, x["Obs"][0][0][4][0])
    plt.plot(f0, p0, color="b")

    f1, p1 = crosspec(500, x["Obs"][0][0][8][0])
    plt.plot(f1, p1, color="r")

    plt.show()


if __name__ == '__main__':
    test2()
    # test_all()