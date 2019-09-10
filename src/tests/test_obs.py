from pathlib import Path

from data.obs import Station

from data import obs
import matplotlib.pyplot as plt

import pandas as pd


def test_get_tides_and_filter_hourly():
    st_id = "8443970"

    data_dir = "/home/olh001/MATLAB/detide/data/obs/merged_2016_2017/"

    data_file = Path(data_dir) / f"X{st_id}.dat"

    s = Station(data_file=data_file, station_info={"name": st_id, "id": st_id, "lat": 42.3539, "lon": -71.0503},
                do_filtering=True)

    print(s.data)

    s.get_detided_series(do_filtering=True)

    df = pd.DataFrame.from_dict({"time": s.data.index, "twl": s.data["twl"].values})

    print(df.head())

    tides, to_filter, _ = obs.get_tides_and_filter_hourly(df)
    other = s.data["twl-mean"] - tides - to_filter

    desc = (s.data["detided"] - other).describe()
    print(desc)

    s.data["detided"].plot(color="r")
    other.plot(color="b")
    plt.show()


if __name__ == '__main__':
    test_get_tides_and_filter_hourly()
