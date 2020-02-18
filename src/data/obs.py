import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pandas as pd

import numpy as np
from ttide import t_tide

from data import utils

MIN_DATA_LEN_FOR_DETIDING = 2160

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_tides_and_filter_hourly(data, do_filtering=False, constituents=None):

    # Make sure the total water level column can be found
    data_ = data.copy()
    data_.rename({data_.columns[-1]: "twl"}, axis="columns", inplace=True)

    s = Station()

    s.data = data_
    s.get_detided_series(do_filtering=do_filtering, constiuents=constituents)

    return s.data["tides"], s.data["filtered"], s.ttidecon


class Station(object):

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, df):
        if df is not None:
            self._data = df.copy()
        else:
            self._data = None

        #self._data = df

        if self._data is not None and len(self._data) > 0:

            if "time" in self._data:
                logger.debug("setting time as index for the purpose of resampling")
                self._data.set_index("time", inplace=True)

            logger.debug(self._data.head())

            # all times are in UTC
            if self._data.index.tz is None:
                self._data.index = self._data.index.tz_localize("UTC")

            self._data = self._data.asfreq("60T")

            # input data cleanup
            # utils.remove_spikes(self._data["twl"], inplace=True, thresh_std_fraction=1.5)
            utils.remove_small_chunks(self._data["twl"], inplace=True, lowest_duration_hours=12)

            self._data.dropna(inplace=True)

            # self._data = self._data.resample("60T", base=self._data.index[0].minute).asfreq()

            # take into account some obs that might have
            # 30 minutes in their time stamps not 00 (i.e NL)
            obs_data_f = self._data.asfreq("30T").fillna(method="ffill", limit=1)
            obs_data_b = self._data.asfreq("30T").fillna(method="bfill", limit=1)

            self._data = 0.5 * (obs_data_b + obs_data_f)
            self._data = self._data[self._data.index.minute == 0]

    def __init__(self, data_file=None, do_filtering=False, station_info=None, obs_datatype: str = "txt"):
        self.nlines_for_header = 6
        self.data_file = data_file

        # station attributes
        self.station_id = None
        self.name = ""
        self.latitude = None
        self.longitude = None

        # do filtering after de-tiding ? (Butterworth)
        self.do_filtering = do_filtering

        if station_info is None:
            if data_file is not None:
                self._parse_header(data_file)
        else:
            # station attributes
            self.station_id = station_info["id"]
            self.name = station_info["name"]
            self.latitude = station_info["lat"]
            self.longitude = station_info["lon"]

        self.ttidecon = None

        ############################################################
        # parse the data file, if provided
        if data_file is not None:

            # try parsing prepared data, if does not work, then try raw station data parser
            if obs_datatype == "txt":
                try:
                    df = pd.read_csv(data_file, header=None, sep=r"\s+")
                    logger.debug(df.head())

                    df["time"] = df.apply(lambda row: datetime(*[int(row[i]) for i in range(5)]), axis="columns")

                    df.rename({5: "twl"}, inplace=True, axis="columns")
                    df = df.loc[:, ["time", "twl"]]

                except ValueError:

                    df = pd.read_csv(data_file,
                                    converters={0: lambda f: datetime.strptime(f, "%Y/%m/%d %H:%M")},
                                    header=None,
                                    skiprows=8,
                                    names=["time", "twl"],
                                    usecols=[0, 1])

            elif obs_datatype == "sql":
                try:
                    pass
                except:
                    pass

        else:
            df = None

        self.data = df
        ###############################################################


    def drop_all_except_longest_year(self):
        """
        removes data for all years except the one that contains the most of the data
        """

        # do nothing if there is no data
        if len(self.data) == 0:
            return

        data_per_year = self.data.groupby(self.data.index.year)

        year_of_interest = None
        data_of_interest = None

        for y, group in data_per_year:

            group.dropna(inplace=True)

            if year_of_interest is None:
                year_of_interest = y
                data_of_interest = group
            else:
                if len(group) > len(data_of_interest):
                    year_of_interest = y
                    data_of_interest = group

                if len(group) == len(data_of_interest) and y > year_of_interest:
                    year_of_interest = y
                    data_of_interest = group

            logger.debug(f"{y}: n={len(group)}")

        self._data = data_of_interest.dropna().resample("60T", base=self.data.index[0].minute).asfreq()

    def get_data_len_since(self, start_date: datetime = None):
        if self.data is None:
            return 0

        if len(self.data) == 0:
            return 0

        if start_date is None:
            return len(self.data)

        return len(self.data[self.data.index >= start_date])

    def remove_data_before(self, start_date: datetime = None):
        """
        Remove data points for time before start_date
        :param start_date:
        :return:
        """
        if start_date is None or self.data is None:
            return

        self._data = self.data[self.data.index >= start_date]

    def remove_data_after(self, end_date: datetime = None):
        """
        Remove data points for time after end_date
        :param end_date:
        :return:
        """
        if end_date is None or self.data is None:
            return

        self._data = self.data[self.data.index <= end_date]




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

    def get_detided_series(self, do_filtering=True, constiuents=None):
        key = "detided"
        if key in self.data and do_filtering == self.do_filtering:
            return self.data[key]

        self._detide(do_filtering=do_filtering, constituents=constiuents)
        self.do_filtering = do_filtering
        return self.data[key]

    def _detide(self, do_filtering=True, constituents=None):
        """

        :param do_filtering:

            Detide and filter (if do_do_filtering=True) and save detided data to self.data["detided"]

        """

        if constituents is None:
            constituents = []

        # detide
        v = self.get_twl_data_vector()
        v -= np.nanmean(v)

        logger.debug(f"Before t_tide: v.shape={v.shape}")
        con = t_tide(v, synth=0, lat=self.latitude, ray=0.5, constitnames=constituents)
        v_notide = v - con["xout"].squeeze()

        filtered_part = 0
        # filter
        if do_filtering:
            from scipy import signal
            b1, a1 = signal.butter(3, [2.0 / 26.0, 2.0 / 22.0], btype="band")
            b2, a2 = signal.butter(3, [2.0 / 15.0, 2.0 / 11.0], btype="band")
            b3, a3 = signal.butter(3, 2.0 / 8.0, btype="high")

            # params from JPP
            # b1, a1 = signal.butter(3, [2.0 / 28.0, 2.0 / 22.0], btype="bandstop")
            # b2, a2 = signal.butter(3, [2.0 / 14.0, 2.0 / 11.0], btype="bandstop")
            # b3, a3 = signal.butter(5, [2.0 / 7.0, 2.0 / 6.0], btype="bandstop")

            # params hyb(JPP, Natacha)
            # b1, a1 = signal.butter(3, [2.0 / 26.0, 2.0 / 22.0], btype="band")
            # b2, a2 = signal.butter(3, [2.0 / 15.0, 2.0 / 11.0], btype="band")
            # b3, a3 = signal.butter(3, [2.0 / 7.0, 2.0 / 6.0], btype="band")

            v_to_filter = v_notide.copy()
            v_to_filter[np.isnan(v_notide)] = 0.0
            filters1 = signal.filtfilt(b1, a1, v_to_filter, padtype="odd", padlen=3 * (max(len(b1), len(a1)) - 1))
            filters2 = signal.filtfilt(b2, a2, v_to_filter, padtype="odd", padlen=3 * (max(len(b2), len(a2)) - 1))
            filters3 = signal.filtfilt(b3, a3, v_to_filter, padtype="odd", padlen=3 * (max(len(b3), len(a3)) - 1))

            filtered_part = filters1 + filters2 + filters3
            v_notide_filtered = v_notide - filters1 - filters2 - filters3
        else:
            v_notide_filtered = v_notide

        self.data["twl-mean"] = v
        self.data["detided"] = v_notide_filtered

        assert len(self.data) == len(v)
        self.data["tides"] = con["xout"]
        self.ttidecon = con

        self.data["filtered"] = filtered_part


def load_station_data_from_canhys_dir(sql_inp_dir=Path("data"), station_info_path: Path = None, translator_path: Path = None,
                                      beg_time_obs: datetime = None,
                                      end_time_obs: datetime = None,
                                      do_filtering=False):

    import time
    t0 = time.perf_counter()

    st_info = pd.read_csv(station_info_path, skiprows=2, header=0, sep=r"\s+", converters={"NO": str})
    st_info["NO"] = st_info["NO"].map(lambda x: x.zfill(5))

    st_info_recs = {}
    for row_index, row in st_info.iterrows():
        st_info_recs[row["NO"]] = {"name": row["ID"], "id": row["NO"], "lon": row["LON"], "lat": row["LAT"]}

    '''
    >>> print(st_info.head(5).to_string())
                         ID       NO        LAT         LON  ......  DATA.LON_OLD
    0           Eastport ME  8410140  44.763676  292.961487  ......    292.961487
    1          Belledune NB    02145  47.894047  294.193420  ......    294.193420
    2  Riviere-au-Renard QC    02330  48.992680  295.658752  ......    295.658752
    3           Rimouski QC    02985  48.459965  291.462952  ......    291.462952
    4          Sept-Iles QC    02780  50.158207  293.627502  ......    293.627502
    '''

    translator = pd.read_csv(translator_path, usecols=(1, 2), 
                                              names=["canhys", "real"],
                                              sep="|").astype(str)

    '''
    >>> print(translator.head(5).to_string())
      canhys     real
    0  10002  05AA008
    1  10004  05AA011
    2  10006  05AA022
    3  10008  05AA024
    4  10012  05AA028
    '''

    station_info_canhys_ids = {translator.loc[(translator.real == real_id), "canhys"].iat[0] for real_id in st_info["NO"]}
    canhys_ids_to_dfs = {canhys_id: [] for canhys_id in station_info_canhys_ids}

    for sql_file in sql_inp_dir.iterdir():
        print(f"processing file: {sql_file}")
        if not sql_file.is_file():
            continue
        
        if not sql_file.name.endswith("sql"):
            continue
        
        try:
            record_date = datetime.strptime(sql_file.name.split("_")[0], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"Naming for {sql_file.name} is not correct, please double check. Skipping.")
            continue

        if beg_time_obs <= record_date and record_date <= end_time_obs:
            conn = sqlite3.connect(sql_file)
            cursor = conn.cursor()

            cursor.execute("select name from sqlite_master where type='table' and name='datavalue'")

            if not cursor.fetchone():
                print(f"Table 'datavalue' not found in {sql_file.name}, skipping.")
                continue

            for canhys_id in canhys_ids_to_dfs:
                st_data = pd.read_sql(sql=f"select datetimeutc, datavalue from datavalue where siteid={canhys_id};", con=conn)
                canhys_ids_to_dfs[canhys_id] += [st_data]
        
        else:
            print("Date of file not within range defined in config, skipping.")

    canhys_ids_to_dfs = {translator.loc[(translator.canhys == c_id), "real"].iat[0]: pd.concat(canhys_ids_to_dfs[c_id]) \
                                                                                       .reset_index(drop=True) \
                                                                                       .sort_values(by="datetimeutc") for c_id in canhys_ids_to_dfs}
    for c_id in canhys_ids_to_dfs:
        canhys_ids_to_dfs[c_id]["datetimeutc"] = pd.to_datetime(canhys_ids_to_dfs[c_id]["datetimeutc"], format="%Y-%m-%d %H:%M:%S")
    
    print(canhys_ids_to_dfs)

    print(f"Execution time: {time.perf_counter() - t0} seconds.")
    quit()
    
    return

        
def load_station_data_from_txt_dir(txt_inp_dir=Path("data"), station_info_path: Path = None, beg_time_obs: datetime = None,
                                   do_filtering=False):

    stations = []

    st_info = pd.read_csv(station_info_path, skiprows=2, header=0,
                          sep=r"\s+", converters={"NO": str})

    for inp_file in txt_inp_dir.iterdir():
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

        if not any(where):
            logger.info(f"{station_id} is not found in the {station_info_path} file.")
            continue

        logger.debug(f"station_info_rec={st_info_rec}")

        s = Station(data_file=inp_file, station_info=st_info_rec, do_filtering=do_filtering, obs_datatype="txt")

        # skip stations with no data
        if s.get_data_len_since() > 0:
            stations.append(s)
        else:
            logger.debug(f"No data for {s.station_id}, skipping ...")

    # make sure that the obs time-series starts on the specified datetime
    for stn in stations:
        stn.remove_data_before(start_date=beg_time_obs)
        s.remove_data_after(end_date=end_time_obs)

    # Make sure that there is enough obs data for de-tiding
    # stations = [s for s in stations if s.get_data_len_since(start_date=beg_time_obs) >= MIN_DATA_LEN_FOR_DETIDING]

    return stations


if __name__ == "__main__":
    pass