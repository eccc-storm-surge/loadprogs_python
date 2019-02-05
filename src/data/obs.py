from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import numpy as np
from ttide import t_tide

from data import utils


class Station(object):
    def __init__(self, data_file, do_filtering=True, station_info=None):

        self.nlines_for_header = 6
        self.data_file = data_file

        # station attributes
        self.station_id = None
        self.name = ""
        self.latitude = None
        self.longitude = None

        if station_info is None:
            self._parse_header(data_file)
        else:
            # station attributes
            self.station_id = station_info["id"]
            self.name = station_info["name"]
            self.latitude = station_info["lat"]
            self.longitude = station_info["lon"]

        self.ttidecon = None

        self.data = None

        # try parsing prepared data, if does not work, then try raw station data parser
        try:

            df = pd.read_csv(data_file, header=None, sep="\s+")
            print(df.head())

            df["time"] = df.apply(lambda row: datetime(*[int(row[i]) for i in range(5)]).replace(tzinfo=timezone.utc), axis="columns")

            df.rename({5: "twl"}, inplace=True, axis="columns")
            df = df.loc[:, ["time", "twl"]]

        except ValueError:

            df = pd.read_csv(data_file,
                             converters={0: lambda f: datetime.strptime(f, "%Y/%m/%d %H:%M")},
                             header=None,
                             skiprows=8,
                             names=["time", "twl"],
                             usecols=[0, 1])

        df.set_index("time", inplace=True)

        self.data = df.resample("60T", base=df.index[0].minute).asfreq()

        # input data cleanup
        utils.remove_spikes(self.data["twl"], inplace=True, thresh_std_fraction=1.5)
        utils.remove_small_chunks(self.data["twl"], inplace=True, lowest_duration_hours=12)

        # do detiding and filtering by default
        self.do_filtering = do_filtering
        self.get_detided_series(do_filtering=do_filtering)

    def __str__(self):
        return f"{self.name} ({self.station_id})"

    def _parse_header(self, fpath):
        with fpath.open() as f:
            for i, line in enumerate(f):
                if i >= 6:
                    return

                vname, value = line.split(",")
                value = value.strip()
                if "Station_Number" in vname:
                    self.station_id = int(value)
                elif "Station_Name" in vname:
                    self.name = value
                elif "Longitude" in vname:
                    self.longitude = float(value)
                elif "Latitude" in vname:
                    self.latitude = float(value)

    def get_twl_data_vector(self):
        return self.data["twl"].values.copy()

    def get_detided_series(self, do_filtering=True):
        key = "detided"
        if key in self.data and do_filtering == self.do_filtering:
            return self.data[key]

        self._detide(do_filtering=do_filtering)
        self.do_filtering = do_filtering
        return self.data[key]

    def _detide(self, do_filtering=True):
        """

        :param do_filtering:

            Detide and filter (if do_do_filtering=True) and save detided data to self.data["detided"]

        """
        # detide
        v = self.get_twl_data_vector()
        v -= np.nanmean(v)

        con = t_tide(v, synth=0, lat=self.latitude, ray=0.5)
        v_notide = v - con["xout"].squeeze()

        # filter
        if do_filtering:
            from scipy import signal
            b1, a1 = signal.butter(3, [2.0 / 26.0, 2.0 / 22.0], btype="band")
            b2, a2 = signal.butter(3, [2.0 / 15.0, 2.0 / 11.0], btype="band")
            b3, a3 = signal.butter(3, 2.0 / 8.0, btype="high")

            v_to_filter = v_notide.copy()
            v_to_filter[np.isnan(v_notide)] = 0.0
            filters1 = signal.filtfilt(b1, a1, v_to_filter, padtype="odd", padlen=3 * (max(len(b1), len(a1)) - 1))
            filters2 = signal.filtfilt(b2, a2, v_to_filter, padtype="odd", padlen=3 * (max(len(b2), len(a2)) - 1))
            filters3 = signal.filtfilt(b3, a3, v_to_filter, padtype="odd", padlen=3 * (max(len(b3), len(a3)) - 1))

            v_notide_filtered = v_notide - filters1 - filters2 - filters3
        else:
            v_notide_filtered = v_notide

        self.data["twl-mean"] = v
        self.data["detided"] = v_notide_filtered

        assert len(self.data) == len(v)
        self.data["tides"] = con["xout"]
        self.ttidecon = con


def load_station_data_from_dir(inp_dir=Path("data"), station_info_path: Path = None):
    stations = []

    st_info = pd.read_csv(station_info_path, skiprows=2, header=0, sep="\s+", converters={"NO": str})

    for inp_file in inp_dir.iterdir():
        if not inp_file.is_file():
            continue

        if not inp_file.name.endswith(".dat"):
            continue

        station_id = inp_file.name[1:-4]
        st_info_rec = {"id": station_id}

        where = st_info["NO"] == station_id
        for row_index, row in st_info[where].iterrows():
            st_info_rec["name"] = row["ID"]
            st_info_rec["lon"] = row["LON"]
            st_info_rec["lat"] = row["LAT"]

        print(f"station_info_rec={st_info_rec}")

        s = Station(inp_file, station_info=st_info_rec)
        stations.append(s)

    return stations
