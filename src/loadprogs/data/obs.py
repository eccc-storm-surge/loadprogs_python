import re
from collections import defaultdict
from datetime import datetime, timezone
import sqlite3
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import List

import pandas as pd

import numpy as np
from ttide.t_tidec import t_tide
from ttide import t_predic
from . import utils
from ..util import log_utils
from ..util import constants
from collections import Counter

logger = log_utils.get_logger(__name__)

TWL_COLNAME = "twl"

def get_tides_and_filter_hourly(data, latitude, do_filtering=False, constituents=None, 
                                ray=constants.DEFAULT_DETIDE_RAYLEIGH,
                                do_cleanup=False, 
                                detide_min_frequency_hz=-np.Inf, do_qc=False):
    """
    detide_min_freq_hz (float, optional): minimum frequency to be considered when removing tides, default is -np.Inf
    """

    # the detiding expects equally spaced data filled with nans for missing points
    data_ = data.copy().asfreq(pd.Timedelta(hours=1))

    # Make sure the total water level column can be found
    data_.rename({data_.columns[-1]: TWL_COLNAME}, axis="columns", inplace=True)

    s = Station(do_filtering=do_filtering, 
                station_info={"lat": latitude}, 
                do_cleanup=do_cleanup,
                detide_min_frequency_hz=detide_min_frequency_hz, do_qc=do_qc)

    s.data = data_
    s.get_detided_series(do_filtering=do_filtering, constituents=constituents, ray=ray)

    return s.data["tides"], s.data["filtered"], s.ttidecon



class Station(object):

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, df):
        self._data: pd.DataFrame | None = None
        if df is not None and len(df.dropna()) > 1:
            self._data = df.copy()
        
        if self._data is not None:

            if "time" in self._data:
                logger.info("setting time as index for the purpose of resampling")
                self._data.set_index("time", inplace=True)

                # remove duplicate dates in index before converting to frequency
                self._data = self._data[~self._data.index.duplicated()].sort_index()  # just in case

                
                # make sure the data is equally spaced
                all_dt = (self._data.index[1:] - self._data.index[:-1])

                cntr = Counter(all_dt)
                dt_min = all_dt.min()
                dt_sel = cntr.most_common(1)[0][0]

                logger.info(f"{self.station_id}: time axis {self._data.index[0]}..{self._data.index[-1]}; freq={dt_sel}")
                if dt_sel != dt_min:
                    logger.info(f"Most frequent time step: {dt_sel} is not equal to the minimum time step={dt_min}")

                self._data = self._data.asfreq(dt_sel)


            # logger.info("\n%s\n", self._data.head())

            # all times are in UTC
            if hasattr(self._data.index, "tz"):
                if self._data.index.tz is None:
                    self._data.index = self._data.index.tz_localize("UTC")


            if self.do_qc:
                self.quality_control()

    def __init__(self, data_file=None, do_filtering=False, station_info=None, 
                       do_cleanup=False, detide_min_frequency_hz=-np.Inf, 
                       do_qc=True):
        """[summary]

        Args:
            data_file ([type], optional): [description]. Defaults to None.
            do_filtering (bool, optional): [description]. Defaults to False.
            station_info ([type], optional): [description]. Defaults to None.
            do_cleanup (bool, optional): If True perform data cleanup before detiding. Defaults to False.
            do_qc (bool, optional): If True - perform quality control for total water level. Defaults to True
            detide_min_freq_hz (float, optional): minimum frequency to be considered when removing tides, default is -np.Inf
        """
        self.nlines_for_header = 6
        self.data_file = data_file
        self.detide_min_freq_hz = detide_min_frequency_hz

        # station attributes
        self.station_id: str | None = None
        self.name: str = ""
        self.latitude = None
        self.longitude = None

        self._data = None
        self.data_dt = None

        # do filtering after de-tiding ? (Butterworth)
        self.do_filtering = do_filtering

        # Fallback if station record is not supplied
        if station_info is None:
            if data_file is not None:
                self._parse_header(data_file)
        else:
            # station attributes
            self.station_id = station_info.get("id", self.station_id)
            self.name = station_info.get("name", self.name)
            self.latitude = station_info.get("lat", self.latitude)
            self.longitude = station_info.get("lon", self.longitude)

        self.ttidecon = None

        # whether to perform or not data cleanup before detiding (deprecated, safer to use False)
        self.do_cleanup = do_cleanup

        # whether to perform qc on data (should not be needed for model)
        self.do_qc = do_qc 



    def quality_control(self, 
                        nan_fill_spread_max_dt: timedelta = timedelta(hours=3),
                        nan_fill_spread_min_dt: timedelta = timedelta(minutes=30),
                        ):
        """
        Try to remove spikes
        If the gap is smaller than nan_fill_spread_min_dt - do not touch it
        nan_fill_spread_max_dt - period by which gap edges are extended

        data is supposed to be uniform already
        """

        
        # make uniform time step
        logger.info(f"QC: Processing station {self.station_id}")
        dt = self._data[TWL_COLNAME].index[1] - self._data[TWL_COLNAME].index[0]
    
        nan_fill_spread_max_points = int(nan_fill_spread_max_dt.total_seconds() / dt.total_seconds())
        nan_fill_spread_min_points = int(nan_fill_spread_min_dt.total_seconds() / dt.total_seconds())


        h = self._data[TWL_COLNAME]

        # IQR
        h1 = h.dropna(axis="index")
        Q1 = h1.quantile(q=0.25, interpolation = 'midpoint')
        Q3 = h1.quantile(q=0.75, interpolation = 'midpoint')
        IQR = Q3 - Q1

        upper = Q3 + 2.5 * IQR
        lower = Q1 - 2.5 * IQR
        
        # if the values are already missing, no need to mark them for quality control
        crit = ((lower <= h.values) & (h.values <= upper)) | np.isnan(h.values)
        logger.info(f"0: {sum(crit) = }")


        # remove points around bad values
        from skimage import measure
        labels = measure.label(crit, background=False)

        df = pd.DataFrame.from_dict({"i": range(len(labels)), 
                                    "label": labels})
        
        i_limits = [
            (g["i"].min(), g["i"].max()) for label, g in df.groupby("label") if label != 0
        ]

        
        logger.info(f"{i_limits = }")
        # mask data around spikes
        for i_min, i_max in i_limits:
            if i_max - i_min + 1 <= 2 * nan_fill_spread_max_points:
                crit[i_min:i_max + 1] = False
            else:
                if i_min > 0:
                    crit[i_min:i_min + nan_fill_spread_max_points] = False
                if i_max < len(labels) - 1:
                    crit[i_max - nan_fill_spread_max_points + 1: i_max + 1] = False

        # mask around edges of missing data regions
        df = pd.DataFrame.from_dict({
            "i": range(len(h.values)), 
            "label": measure.label(np.isnan(h.values), background=False)
        })
        
        logger.info(f"{df.label.value_counts() = }")

        counts_and_limits = [(len(g["label"]), 
                              (g["i"].min(), g["i"].max())) for label, g in df.groupby("label") if label != 0]

        for c, c_limits in counts_and_limits:
            logger.info(f"{c = }; {c_limits = }; {nan_fill_spread_max_points = }; {nan_fill_spread_max_dt = } ")
            if c < nan_fill_spread_min_points:
                pass
            else:
                i1 = max(0, c_limits[0] - nan_fill_spread_max_points)
                i2 = min(len(df) - 1, c_limits[1] + nan_fill_spread_max_points)
                crit[i1:i2 + 1] = False

        
        # mask short data availability regions
        df_good = pd.DataFrame.from_dict({
            "i": range(len(h.values)), 
            "label": measure.label(~np.isnan(h.values), background=False)
        })
       


        if (~crit).any():
            logger.info(f"""
                            QC: {upper = }; {lower = }; 
                            masking the following:
                                {self._data.loc[~crit, TWL_COLNAME].values}
                          """)
            logger.info(f"1: {sum(crit) = }")
            self._data.loc[~crit, TWL_COLNAME] = np.nan

        

    def assign_data(self, df):
        self.data = df
        return self

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

            logger.info(f"{y}: n={len(group)}")

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
            return self

        self._data = self.data[self.data.index >= start_date]
        return self

    def remove_data_after(self, end_date: datetime = None):
        """
        Remove data points for time after end_date
        :param end_date:
        :return:
        """
        if end_date is None or self.data is None:
            return self

        self._data = self.data[self.data.index <= end_date]
        return self

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
        return self.data[TWL_COLNAME].values.copy()

    def get_detided_series(self, do_filtering=True, constituents=None, ray=0.5):
        key = "detided"
        if key in self.data.columns and do_filtering == self.do_filtering:
            return self.data[key]

        self._detide(do_filtering=do_filtering, constituents=constituents, ray=ray)
        self.do_filtering = do_filtering

        # logger.debug("self.data[key]:\n%s\n", self.data[key])
        # logger.debug("key=%s", key)

        return self.data[key]

    def _cleanup_data_for_detiding(self):
        # input data cleanup
        # utils.remove_spikes(self._data["twl"], inplace=True, whis=1.5)
        
        minute_index = pd.date_range(self._data.index.min(),
                                     self._data.index.max(),
                                     freq=timedelta(minutes=1))

        # remove spikes (like we had in canhys 176 instead of 4)
        data = self._data.copy()
        data[TWL_COLNAME] = utils.remove_spikes(data[TWL_COLNAME], whis=5)

        data = data.reindex(data.index.union(minute_index), axis=0)
        logger.debug("before interpolation\n: %s", data.head())

        interp_limit_npoints = 60  # not further than 60 mins
        data = data.interpolate(method="time", limit=interp_limit_npoints, limit_direction="forward")
        # data = data[data.index.minute == 0]
       

        logger.debug("\n interpolation limit: %s \n", interp_limit_npoints)
        logger.debug("after reindex\n: %s", data.head())

        
        # assumes the data are hourly at this point, TODO: generalize to uncomment
        # utils.remove_small_chunks(data["twl"], lowest_duration_hours=24, inplace=True)

        # remove leading/trailing nans if present
        data = utils.remove_leading_trailing_nans(data, focus_col="twl")

        # extend no-data region to eliminate spikes/trends at the edges
        data[TWL_COLNAME] = utils.remove_edges(data[TWL_COLNAME])

        logger.debug(f"t[1]-t[0] = {data.index[1]} - {data.index[0]}")
        logger.debug("obs processed (before detiding): \n%s\n", data.head())
        
        self.assign_data(data)
        return data

    def _detide(self, do_filtering=True, constituents=None, ray=constants.DEFAULT_DETIDE_RAYLEIGH):
        """

        :param do_filtering:

            Detide and filter (if do_filtering=True) and save detided data to self.data["detided"]

        """

        synth = 0

        if constituents is None:
            constituents = []

        # detide
        # v = self.get_twl_data_vector()

        msg = f"{self.station_id}: no data to detide.."
        assert self.data is not None, msg
        assert self._data is not None, msg

        if self.do_cleanup:
            clean_data = self._cleanup_data_for_detiding()[TWL_COLNAME]
        else:
            clean_data = self.data[TWL_COLNAME]
        

        # the clean data is assumed to be uniformly spaced
        computed_dt = (clean_data.index[1:] - clean_data.index[:-1]).min()
        assert computed_dt.total_seconds() > 0, "Detiding error, input timeseries is not sorted in time"
        assert (clean_data.asfreq(computed_dt).index == clean_data.index).all(), "Detiding error: input data is not equally spaced in time"
        
        n_time_steps_per_hour = 3600 // computed_dt.total_seconds()
        v = clean_data.values.copy()
        v -= np.nanmean(v)


        logger.debug(f"{sum(np.isnan(v)) = }; {len(v) = }")
        logger.debug(clean_data.head())
        logger.debug(f"ray={ray}; stime={clean_data.index[0]}; dt={computed_dt.total_seconds() / 3600.}")

        # logger.debug("nanmean(v) = %s", np.nanmean(v))
        # logger.debug(f"Before t_tide: v.shape={v.shape}")
        logger.debug(f"data range: {np.nanmin(v)}, {np.nanmax(v)}")
        con = t_tide(v,
                     dt=computed_dt.total_seconds() / 3600.,
                     synth=synth,
                     lat=self.latitude,
                     ray=ray,
                     constitnames=constituents,
                     stime=clean_data.index[0],
                     out_style=None, lsq="direct")

        fu = con["fu"]
        nu = con["nameu"]
        tc = con["tidecon"]
        
        # print("fu = ", con["fu"])
        # print("nameu = ", con["nameu"])
        
        if (fu <= self.detide_min_freq_hz).any():
            sel = fu > self.detide_min_freq_hz
            con["fu"] = fu[sel]
            con["nameu"] = nu[sel]
            con["tidecon"] = tc[sel, :] 

            con["xout"] = t_predic(
                con["stime"] + np.array([range(con["nobs"])]) * con["dt"] / 24.0,
                con["nameu"], con["fu"], con["tidecon"], synth=synth, 
                lat=self.latitude
            )

            # print("update -- ")
            # print("fu = ", con["fu"])
            # print("nameu = ", con["nameu"])
        

        v_notide = v - con["xout"].squeeze()
        
        # logger.debug("v_notide: \n %s \n", v_notide)

        v_notide_filtered = v_notide

        filtered_part = 0
        # filter
        if do_filtering:
            from scipy import signal
            # default old way defining the filter, might cause instabilities
            # b1, a1 = signal.butter(3, [2.0 / 26.0, 2.0 / 22.0], btype="band")
            # b2, a2 = signal.butter(3, [2.0 / 15.0, 2.0 / 11.0], btype="band")
            # b3, a3 = signal.butter(3, 2.0 / 8.0, btype="high")

            filter_order = 3
            band_type = "bandpass"
            sos1 = signal.butter(filter_order, 
                                 [2.0 / (26.0 * n_time_steps_per_hour), 2.0 / (22.0 * n_time_steps_per_hour)], btype=band_type, output="sos")
            sos2 = signal.butter(filter_order, 
                                 [2.0 / (15.0 * n_time_steps_per_hour), 2.0 / (11.0 * n_time_steps_per_hour)], btype=band_type, output="sos")
            sos3 = signal.butter(filter_order, 2.0 / (8.0 * n_time_steps_per_hour), btype="high", output="sos")

            # params from JPP
            # b1, a1 = signal.butter(3, [2.0 / 28.0, 2.0 / 22.0], btype="bandstop")
            # b2, a2 = signal.butter(3, [2.0 / 14.0, 2.0 / 11.0], btype="bandstop")
            # b3, a3 = signal.butter(5, [2.0 / 7.0, 2.0 / 6.0], btype="bandstop")

            # params hyb(JPP, Natacha)
            # b1, a1 = signal.butter(3, [2.0 / 26.0, 2.0 / 22.0], btype="band")
            # b2, a2 = signal.butter(3, [2.0 / 15.0, 2.0 / 11.0], btype="band")
            # b3, a3 = signal.butter(3, [2.0 / 7.0, 2.0 / 6.0], btype="band")

            v_to_filter = v_notide.copy()
            where_nans = np.isnan(v_notide)
            if np.any(~where_nans):
                v_to_filter[where_nans] = v_to_filter[~where_nans].mean()
            else:
                v_to_filter[where_nans] = 0.0

            pad_type = "odd"
            filters1 = signal.sosfiltfilt(sos1, v_to_filter, padtype=pad_type)
            filters2 = signal.sosfiltfilt(sos2, v_to_filter, padtype=pad_type)
            filters3 = signal.sosfiltfilt(sos3, v_to_filter, padtype=pad_type)

            filtered_part = filters1 + filters2 + filters3
            v_notide_filtered = v_notide - filters1 - filters2 - filters3
        
        self._data["twl-mean"] = v
        self._data["detided"] = v_notide_filtered

        # logger.debug("detided: \n %s \n", self.data["detided"])
        # logger.debug("v_notide_filtered: \n %s \n", v_notide_filtered)

        assert len(self.data) == len(v), f"{len(self.data) = }; {len(v) = }"
        self._data["tides"] = con["xout"]
        self.ttidecon = con

        self._data["filtered"] = filtered_part


    def remove_mean(self):
        """Remove time mean
        """
        if self.data is None or len(self.data) == 0:
            return

        # try to filter wrong data           
        q1 = self.data[TWL_COLNAME].quantile(q=0.25)
        q3 = self.data[TWL_COLNAME].quantile(q=0.75)
        iqr = q3 - q1
        sel = self.data[TWL_COLNAME] >= (q1 - 10 * iqr)
        sel = sel & (self.data[TWL_COLNAME] <= (q3 + 10 * iqr))

        reject = self.data.loc[:, TWL_COLNAME].loc[~sel]
        if len(reject) > 0:
            logger.info(f"{self.station_id}: Rejecting in remove_mean"
                        f" due to {q1 = }, {q3 = }, {iqr = }, \n values= \n{reject}")
            logger.info("Description of rejected \n %s \n", reject.describe())
        
        self.data[TWL_COLNAME] = self.data[TWL_COLNAME] - self.data[TWL_COLNAME].mean()

        

@lru_cache
def read_station_metadata(station_info: Path) -> pd.DataFrame:
    """
    Args:
        station_info: path to the station info file either .obs or .dat supported

    Returns:
        dataframe with station metadata parsed either from .obs or .dat file
    """

    if station_info.name.endswith(".obs"):
        info = pd.read_csv(station_info, skiprows=2, header=0, sep=r"\s+", converters={"NO": str})

        '''
        >>> print(st_info.head(5).to_string())
                             ID       NO        LAT         LON  ......  DATA.LON_OLD
        0           Eastport ME  8410140  44.763676  292.961487  ......    292.961487
        1          Belledune NB    02145  47.894047  294.193420  ......    294.193420
        2  Riviere-au-Renard QC    02330  48.992680  295.658752  ......    295.658752
        3           Rimouski QC    02985  48.459965  291.462952  ......    291.462952
        4          Sept-Iles QC    02780  50.158207  293.627502  ......    293.627502
        '''

    elif station_info.name.endswith(".dat"):  # list of tide gauges as in the regional surge suites
        colspecs = [
            (0, 4), (5, 9), (10, 36), (37, None),
        ]

        info = pd.read_fwf(station_info, header=None, colspecs=colspecs)

        # names
        info[2] = info[2].map(lambda s: s.strip())

        info.rename({0: "DATA.I", 1: "DATA.J", 2: "ID"}, inplace=True, axis=1)

        rest = info[3].str.split(r"\s+", expand=True)

        info["LON"] = rest[0].astype(float) * rest[1].map(lambda s: 1 if s == "E" else -1)
        info["LAT"] = rest[2].astype(float) * rest[3].map(lambda s: 1 if s == "N" else -1)
        info["NO"] = rest[5].astype(str)

        info.drop(columns=[3, ], inplace=True)
    else:
        raise ValueError(f"Not supported type of the station info file, please change the extension and"
                         f" reformat if required: {station_info.name}")

    logger.info("Station info \n %s",info)
    return info


def load_station_data_from_obs_dir(config):
    loading_funcs = {"txt": load_station_data_from_txt_dir,
                     "sqlite": load_station_data_from_canhys_dir,
                     "canhys": load_station_data_from_canhys_dir}

    st_info = read_station_metadata(config.station_info)

    st_info_recs = {}
    for row_index, row in st_info.iterrows():
        st_info_recs[row["NO"]] = {"name": row["ID"], "id": row["NO"], "lon": row["LON"], "lat": row["LAT"]}

    obs_st_ids_to_data = loading_funcs[config.obs_datatype](st_info_recs, config)

    assert len(obs_st_ids_to_data) > 0, "No obs data were loaded !"

    # initialize list of stations without data added yet

    stations = [Station(do_filtering=config.obs_do_filtering, 
                        station_info=st_info_recs[st_id], 
                        detide_min_frequency_hz=config.obs_detide_min_tide_frequency_hz,
                        do_qc=config.obs_do_qc)
                    .assign_data(obs_st_ids_to_data[st_id])
                    .remove_data_before(config.beg_time_obs)
                    .remove_data_after(config.end_time_obs)
                for st_id in st_info_recs
                if st_id in obs_st_ids_to_data]

    return [s for s in stations if s.data is not None]


def load_station_data_from_canhys_dir(station_records, config):
    t_tolerance = timedelta(hours=24)

    msg = "Observation start or end date is not valid"
    assert None not in [config.beg_time_obs, config.end_time_obs], msg

    _converters = {col: lambda x: x.lstrip("0") for col in (1, 2)}

    real_to_canhys_mapping = pd.read_csv(config.translator_path, usecols=(1, 2),
                                         names=["canhys", "real"], sep="|",
                                         header=None,
                                         converters=_converters).set_index("real")

    canhys_to_real_mapping = real_to_canhys_mapping.reset_index().set_index("canhys")

        
    # for some stations we can have several canhys ids
    station_info_canhys_ids = []
    for real_id in real_to_canhys_mapping.index.intersection(station_records):
        part = real_to_canhys_mapping.loc[real_id, "canhys"]
        if isinstance(part, str):
            part = [part]
        else:
            part = part.tolist()
        
        station_info_canhys_ids += part

    for chsid in station_info_canhys_ids:
        print(chsid)

    canhys_ids_to_dfs = defaultdict(list)

    for sql_file in sorted(config.obs_dir.iterdir(), key=lambda f: f.name):
        if not sql_file.is_file():
            logger.info(f"{sql_file.name} is not a file, skipping...")
            continue

        if not sql_file.name.endswith("sql"):
            logger.info(f"{sql_file.name} does not have the correct suffix '_sql', skipping")
            continue

        try:
            record_date = datetime.strptime(sql_file.name.split("_")[0], r"%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.info(f"Naming for {sql_file.name} is not correct, please double check, skipping..")
            continue

        # filter the dates
        if config.beg_time_obs is not None:
            if record_date + t_tolerance < config.beg_time_obs:
                continue

        if config.end_time_obs is not None:
            if record_date - t_tolerance > config.end_time_obs:
                continue

        logger.info(f"processing file: {sql_file}")

        # read data
        conn = sqlite3.connect(sql_file)
        cursor = conn.cursor()

        cursor.execute("select name from sqlite_master where type='table' and name='datavalue'")
        if not cursor.fetchone():
            logger.info(f"Table 'datavalue' not found in {sql_file.name}, skipping..")
            continue

        # old query: f"select datetimeutc, datavalue from datavalue where siteid={canhys_id};", con=conn)
        query = f"""SELECT siteid, datetimeutc, datavalue, variableid
                    FROM datavalue
                    WHERE siteid
                    IN ({','.join(station_info_canhys_ids)}) and variableid IN ({config.variable_id});"""

        data_for_all_stns = pd.read_sql(sql=query, con=conn).groupby(
            "siteid")  # TODO: maybe move the grouping to the sqlite query

        for canhys_id in station_info_canhys_ids:
            try:
                st_data = data_for_all_stns.get_group(int(canhys_id))
                canhys_ids_to_dfs[canhys_id] += [st_data]
            except KeyError:
                logger.info(fr"   \--> CanHys id {canhys_id} not found within table, skipping..")
                continue

    # Translate station ids from CanHys to real as well as merge time series for each station
    real_ids_to_dfs = {canhys_to_real_mapping.loc[canhys_id, "real"]: pd.concat(canhys_ids_to_dfs[canhys_id])
        .reset_index(drop=True)
        .rename(columns={"datetimeutc": "time", "datavalue": "twl"})
                       for canhys_id in canhys_ids_to_dfs}

    for r_id in real_ids_to_dfs:
        station_data = real_ids_to_dfs[r_id]
        # parse time column
        station_data["time"] = pd.to_datetime(station_data["time"], format=r"%Y-%m-%d %H:%M:%S")

        # if we have several variable_id for a given station (i.e. multiple sensors), use the
        # one with the longest record length
        idx = station_data.groupby("variableid").count().idxmax(axis="index")
        real_ids_to_dfs[r_id] = station_data.loc[station_data["variableid"] == idx.iloc[0]].drop("variableid",
                                                                                                 axis="columns")
    return real_ids_to_dfs


def load_station_data_from_txt_dir(station_records, config):
    real_ids_to_dfs = {}


    for inp_file in config.obs_dir.iterdir():
        if not inp_file.is_file():
            continue

        if not inp_file.name.endswith(".dat"):
            continue

        inp_file_st_id = inp_file.name[1:-4]

        if inp_file_st_id not in station_records:
            logger.info(f"{inp_file_st_id} is not found in {config.station_info} file.")
            continue

        logger.info(f"Start parsing {inp_file} ...")
        try:

            df = pd.read_csv(inp_file, header=None, sep=r"\s+")            
            logger.info("raw obs data from %s :\n%s\n", inp_file, df.head())

            twl_column_id = 5

            # preferred format
            if len(df.columns) == 2:

                
                twl_column_id = 1
                supported_time_formats = [
                    r"%Y %m %d %H %M %S",
                    r"%Y %m %d %H %M"
                ]

                def __parse_time(tok):
                    t = None
                    for fmt in supported_time_formats:
                        try:
                            t = datetime.strptime(tok, fmt)
                            return t
                        except ValueError:
                            pass
                    if t is None:
                        raise ValueError(f"Could not parse {tok}, "
                                         f"supported date-time formats: {supported_time_formats}")


                df["time"] = df[0].map(__parse_time)
            else:
                # df["time"] = df.apply(lambda row: datetime(*[int(row[i]) for i in range(twl_column_id)]), axis="columns")
                fields = ["year", "month", "day", "hour", "minute"]
                df["time"] = [pd.Timestamp(**dict(zip(fields, f))) for f in zip(*[df[i] for i in range(twl_column_id)])]
                df["time"] = df["time"].dt.tz_localize(timezone.utc)
                
                # df["time"] = df.apply(lambda row: datetime(*[int(row[i]) for i in range(twl_column_id)]), axis="columns")
            df.rename({twl_column_id: "twl"}, inplace=True, axis="columns")
            df = df.loc[:, ["time", "twl"]]
            crit = (df["time"] >= config.beg_time_obs) & (df["time"] <= config.end_time_obs)
            df = df.loc[crit, :]
            print(df.head())

        except ValueError:
            df = pd.read_csv(inp_file,
                             converters={0: lambda f: datetime.strptime(f, "%Y/%m/%d %H:%M")},
                             header=None,
                             skiprows=8,
                             names=["time", "twl"],
                             usecols=[0, 1])

        real_ids_to_dfs[inp_file_st_id] = df

    assert len(real_ids_to_dfs) > 0, f"did not find any observations in {config.obs_dir}"
    return real_ids_to_dfs


def get_stid_to_stname_map(stations: List[Station]) -> dict:
    """

    Args:
        stations: list of station objects

    Returns:

    """
    res = {}
    for station in stations:
        title = station.name.replace(",", " ")
        reg = re.split(r"\s+", title)[-1]
        name = title[:title.index(reg)].strip()
        reg = "".join([c for c in reg if c not in ["(", ")"]])
        res[station.station_id] = f"{name}, {reg}"
    return res


def load_station_data_from_obs_file(obs_file: Path) -> List[Station]:
    """
    Args:
        obs_file: path to the .obs text file in the format used for SPI
    Returns:
        List of stations with metadata from the .obs file
    """

    station_info = read_station_metadata(obs_file)

    st_info_recs = {}
    for row_index, row in station_info.iterrows():
        st_info_recs[row["NO"]] = {"name": row["ID"], "id": row["NO"], "lon": row["LON"], "lat": row["LAT"]}
    
    # initialize list of stations without data added
    return [Station(station_info=st_info_recs[st_id]) for st_id in st_info_recs]


if __name__ == "__main__":
    pass
