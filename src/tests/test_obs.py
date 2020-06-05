from pathlib import Path
from ..data import obs

import matplotlib.pyplot as plt
import pandas as pd


def test_get_tides_and_filter_hourly(test_do_filtering):

    st_id = "8410140"
    data_dir = "/home/olh001/data/eccc-ppp3/sse_obs/merged/2019_on_20200106"

    data_file = Path(data_dir) / f"X{st_id}.dat"

    s = obs.Station(data_file=data_file, station_info={"name": "Eastport ME", "id": st_id, "lat": 44.763676, "lon": 292.961487},
                do_filtering=test_do_filtering)

    print(s.data)

    s.get_detided_series(do_filtering=test_do_filtering)

    df = pd.DataFrame.from_dict({"time": s.data.index, "twl": s.data["twl"].values})

    print(df.head())

    tides, to_filter, _ = obs.get_tides_and_filter_hourly(df)
    other = s.data["twl-mean"] - tides - to_filter

    desc = (s.data["detided"] - other).describe()
    print(desc)

    s.data["detided"].plot(color="r")
    # other.plot(color="b")

    plt.show()


if __name__ == '__main__':
    test_get_tides_and_filter_hourly(False)
