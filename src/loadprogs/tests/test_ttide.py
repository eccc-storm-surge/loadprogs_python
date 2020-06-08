
"""
To check if any changes to ttide affect our detiding results
"""
from pathlib import Path
from datetime import datetime

import ttide

from ..data.obs import Station

def test():
    st_id = "8443970"

    data_dir = Path("/home/olh001/MATLAB/detide/data/obs/merged_2016_2017/")

    data_file = data_dir / f"X{st_id}.dat"

    s = Station(data_file=data_file, station_info={"name": st_id, "id": st_id, "lat": 42.3539, "lon": -71.0503},
                do_filtering=True)

    print(s.data)

    # initial water level time series
    # filling missing values with 0 as in Natacha's script (~/MATLAB/detide/loadprogs_matlab/crosspec.m)
    wl1_notides = s.get_detided_series(do_filtering=True).asfreq("60T")

    test_out_dir = Path(f"data/test_ttide/{datetime.utcnow():%Y%m%d%H}_{ttide.__version__}")
    test_out_dir.mkdir(exist_ok=True, parents=True)
    wl1_notides.to_csv(test_out_dir / f"{data_dir.name}_no_tides.csv")


if __name__ == '__main__':
    test()
