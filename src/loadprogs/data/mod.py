from datetime import timedelta
from pathlib import Path

import pandas as pd
from pykdtree.kdtree import KDTree
from rpnpy.librmn.interp import EzscintError

from . import obs
from typing import List

from rpnpy.librmn import all as rmn
from rpnpy.rpndate import RPNDate

from .obs import Station
from .obs import read_station_metadata

from ..util import lat_lon

rmn.fstopt(rmn.FSTOP_MSGLVL, rmn.FSTOPI_MSG_FATAL)

import logging
import numpy as np

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_member_id_from_file_path(fpath: Path):
    return fpath.name.split("_")[-1]


def get_mod_col_name(member_id=""):
    return f"mod_{member_id}"


def map_stations_to_grid_indices(stations: List[obs.Station], stations_info_file: Path):
    """
    :param stations:
    :param stations_info_file: Path to the file that contains correspondence between station ids and the (I, J) coordinates
            of the corresponding grid cells, (I, J) indices are assumed to be 1-based as in Fortran or MATLAB.
    :return: dict relating station_id to the corresponding grid indices, 0-based as in Python and C in the returned dictionaries
    """

    df = read_station_metadata(stations_info_file)

    df = df.set_index("NO")

    obs_mod_map = {}
    for s in stations:
        i = df.loc[s.station_id, "DATA.I"]
        j = df.loc[s.station_id, "DATA.J"]

        obs_mod_map[s.station_id] = (i - 1, j - 1)

    return obs_mod_map


def get_analysis_period_b2b_mean(stations, mod_data_path: Path,
                                 station_id_to_grid_indices,
                                 mod_nomvar="ETAS",
                                 start_time=None, end_time=None,
                                 member_ids=("",), b2b_nhours=12):

    assert None not in [start_time, end_time], "You should specify the first and the last experiment dates"

    data_dict = {"station_id": [], "value": [], "time": [], "valid_hour": [], "member_id": []}

    dt_run_freq = timedelta(hours=b2b_nhours)
    n_exp = (end_time - start_time).total_seconds() // dt_run_freq.total_seconds() + 1
    n_exp = int(n_exp)

    logger.debug(f"n_exp={n_exp}; type(n_exp)={type(n_exp)}")

    exp_t_list = [start_time + i * dt_run_freq for i in range(n_exp)]

    for member_id in member_ids:
        for exp_t in exp_t_list:
            data_file = mod_data_path / f"{exp_t:%Y%m%d%H}_{member_id}"

            # get all data from a file in memory
            funit = rmn.fstopenall(str(data_file))

            keys = rmn.fstinl(funit, typvar="P@", nomvar=mod_nomvar)
            record_metas = [rmn.fstprm(k) for k in keys]
            vh_list = [int(rec["deet"] * rec["npas"] / 3600.) for rec in record_metas]

            # filter the keys by date first first, if required
            keys = [k for k, vh in zip(keys, vh_list) if 0 < vh <= b2b_nhours]
            record_metas = [meta for meta, vh in zip(record_metas, vh_list) if vh <= b2b_nhours]

            dates = [RPNDate(meta["datev"]).toDateTime() for meta in record_metas]

            records = [rmn.fstluk(k) for k in keys]

            for s in stations:
                i, j = station_id_to_grid_indices[s.station_id]
                data_dict["value"].extend([rec["d"][i, j] for rec in records])
                data_dict["station_id"].extend([s.station_id] * len(records))

                data_dict["time"].extend(dates)
                data_dict["valid_hour"].extend([int(rec["deet"] * rec["npas"] / 3600.0) for rec in records])
                data_dict["member_id"].extend([member_id] * len(dates))

            rmn.fstcloseall(funit)

    for i, d in enumerate(data_dict["time"]):
        assert d != 0, f"time[{i}]={d}"

    # logger.debug(list(data_dict.keys()))

    # check that the lists have the same length
    data_leng = {cn: len(cd) for cn, cd in data_dict.items()}
    logger.debug(f"data_leng: {data_leng}")

    df = pd.DataFrame.from_dict(data_dict)

    df_list = []
    for member_id, group in df.groupby("member_id"):
        group = group.set_index(["time", "valid_hour", "station_id"])

        group.rename({"value": f"mod_{member_id}"}, axis=1, inplace=True)
        group.drop("member_id", axis=1, inplace=True)

        logger.debug(len(group))

        df_list.append(group)

    df = pd.concat(df_list, axis=1).reindex(df_list[0].index)

    logger.debug(df.head())
    logger.debug("column names")

    df.reset_index(inplace=True)

    for c in df:
        logger.debug(c)

    # sorting, useful for debugging
    df.sort_values(["time", "valid_hour"], inplace=True)
    df.set_index("time", inplace=True)

    df = df.mean(axis=0)
    logger.debug("model points (analysis period mean)")
    logger.debug(df)

    return df


def prepare_mod_sql_data(mod_data, mod_members, stn):

    df = mod_data.copy()
    df = df.assign(lat=stn.latitude, lon=stn.longitude)
    df = df.rename(columns={f"{stn.station_id}_obs": "obs"}) \
           .reindex(columns=["valid_hour", "station_id", "lat", "lon", "time", "obs", *mod_members]) \
           .sort_values(by="time")

    return df


def get_mod_timeseries(stations, mod_data_path: Path,
                       station_id_to_grid_indices,
                       mod_nomvar="ETAS",
                       start_time=None, end_time=None,
                       member_ids=("",), run_freq_hours=12,
                       dt_texp_from_tbeg=timedelta(hours=0),
                       allow_missing=False
                       ):
    """
    Read all the files in mod_data_path and store data in a pd.DataFrame
    remove the time mean

    member id is derived from the last part (after the last underscore) of the output file name

    Args:
        allow_missing:
        run_freq_hours: Frequency of the experiment, if t ie a new experiment is started each t hours
        member_ids:
        end_time:
        start_time:
        mod_nomvar:
        stations:
        mod_data_path: (folder with simulation files)
        station_id_to_grid_indices:

    Returns:
        data frame with model data

    """

    assert None not in [start_time, end_time], "You should specify the first and the last experiment dates"

    data_dict = {"station_id": [], "value": [], "time": [], "valid_hour": [], "member_id": []}

    dt_run_freq = timedelta(hours=run_freq_hours)
    n_exp = (end_time - start_time).total_seconds() // dt_run_freq.total_seconds() + 1
    n_exp = int(n_exp)

    logger.setLevel(logging.DEBUG)
    logger.debug(f"n_exp={n_exp}; type(n_exp)={type(n_exp)}")

    exp_t_list = [start_time + i * dt_run_freq for i in range(n_exp)]
    # logger.debug(exp_t_list)

    for member_id in member_ids:
        for exp_t in exp_t_list:
            logger.info(f"treating experiment: {exp_t}")
            data_files = list(mod_data_path.glob(f"{exp_t:%Y%m%d%H}*{member_id}"))
            # logger.debug(data_files)

            if len(data_files) == 0:
                msg = f"Could not find any file for the experiment on {exp_t}"
                if allow_missing:
                    logger.info(msg)
                else:
                    raise IOError(msg)

            # sort by name
            data_files = [p for p in sorted(data_files, key=lambda ip: ip.name)]

            logger.debug(f"mod_data_path={mod_data_path}")
            # logger.debug(data_files)

            # get all data from a file in memory
            funit = rmn.fstopenall([str(data_file) for data_file in data_files])

            keys = rmn.fstinl(funit, typvar="P@", nomvar=mod_nomvar)

            # filter the keys by date first first, if required
            dates = [RPNDate(rmn.fstprm(k)["datev"]).toDateTime() for k in keys]

            records = [rmn.fstluk(k) for k in keys]

            for s in stations:
                i, j = station_id_to_grid_indices[s.station_id]
                data_dict["value"].extend([rec["d"][i, j] for rec in records])
                data_dict["station_id"].extend([s.station_id] * len(records))

                data_dict["time"].extend(dates)
                data_dict["valid_hour"].extend([int((t - (exp_t - dt_texp_from_tbeg)).total_seconds() // 3600) for t in dates])
                data_dict["member_id"].extend([member_id] * len(dates))

            rmn.fstcloseall(funit)

    for i, d in enumerate(data_dict["time"]):
        assert d != 0, f"time[{i}]={d}"

    logger.debug(list(data_dict.keys()))

    # check that the lists have the same length
    data_leng = {cn: len(cd) for cn, cd in data_dict.items()}
    logger.debug(f"data_leng: {data_leng}")

    df = pd.DataFrame.from_dict(data_dict)

    df_list = []
    for member_id, group in df.groupby("member_id"):
        group = group.set_index(["time", "valid_hour", "station_id"])

        group.rename({"value": f"mod_{member_id}"}, axis=1, inplace=True)
        group.drop("member_id", axis=1, inplace=True)

        logger.debug(len(group))

        df_list.append(group)

    df = pd.concat(df_list, axis=1)

    logger.debug("\n %s \n", df.head())
    logger.debug("column names")

    df.reset_index(inplace=True)

    for c in df:
        logger.debug(c)

    # sorting, useful for debugging
    df.sort_values(["time", "valid_hour"], inplace=True)
    df.loc[:, "date_of_origin"] = df.loc[:, "time"] - df.loc[:, "valid_hour"].map(lambda ti: timedelta(hours=ti))

    logger.debug("model points")
    logger.debug("\n %s \n", df)

    return df


def get_list_of_origin_dates(mod_data, run_freq_dt: timedelta):
    """
    returns a list of origin dates spaced by run_freq_dt
    :param mod_data:
    :param run_freq_dt:
    """

    do = mod_data.loc[:, "date_of_origin"]

    t0 = do.min()
    t1 = do.max()
    logger.debug(f"t0={t0}; t1={t1}; run_freq_dt={run_freq_dt}")
    logger.debug(mod_data.head())
    logger.debug("do: \n %s \n", do)

    return pd.date_range(t0, t1, freq=run_freq_dt)


def get_mod_twl_for_b2b(mod_data, config):
    df = mod_data.copy()
    logger.info("Detiding model outputs.")
    assert not any(df["time"].isna())

    # for b2b operations
    select_crit = df["valid_hour"] <= config.b2b_freq_hours
    select_crit = select_crit & (df["valid_hour"] >= 0) # remove t=0
    mod_data_twl = df.loc[select_crit, :]
    mod_data_twl.sort_values("time", inplace=True)
    logger.debug(mod_data_twl.head())

    mod_data_twl.set_index("time", inplace=True)

    return mod_data_twl


def remove_analysis_period_mean(mod_data, station, mod_member_keys, config):
    """
    removes analysis period mean from the model and observations
    :param mod_data:
    :param station:
    :param mod_member_keys:
    :param config:
    :return:
    """
    df = mod_data.copy()

    tmean = df.loc[(df["valid_hour"] <= config.b2b_freq_hours), f"{station.station_id}_obs"].mean()
    df.loc[:, f"{station.station_id}_obs"] -= tmean

    logger.debug(f"tmean({station.station_id})={tmean}")

    # mean to be removed from each member calculated based on the control member, which is assumed
    # to be the first in the list

    where_cond = (df["valid_hour"] <= config.b2b_freq_hours)
    tmean = df.loc[where_cond, mod_member_keys[0]].mean()

    for cn in mod_member_keys:
        df.loc[:, cn] -= tmean  # remove long time mean only of the control member
    return df


def get_mod_timeseries_closest_to(stations: List[Station], data_files: list,
                                  nnearest=9,
                                  nomvar="ETAS", typvar="P@",
                                  dist_upper_bound=None):
    """
    get timeseries for nnearest grid points to each station in the list of stations
    :param dist_upper_bound:
    :param typvar:
    :param nomvar:
    :param stations:
    :param data_files:
    :param nnearest:
    :returns a pandas dataframe with rows as time and columns as multiindex (stationid, (0, ..., nnearest))

    """

    station_id_to_indices = {}

    # get spatial indices corresponding to each station
    fu = rmn.fstopenall(str(data_files[0]))

    key = rmn.fstinf(fu, nomvar=nomvar, typvar=typvar)
    meta = rmn.fstprm(key)

    key_mask = rmn.fstinf(fu, nomvar=nomvar, typvar="@@")
    mask = rmn.fstluk(key_mask)["d"]

    try:
        grid = rmn.readGrid(fu, meta)["subgrid"][0]
        gd_lat_lon = rmn.gdll(grid)
        gd_lons, gd_lats = gd_lat_lon["lon"], gd_lat_lon["lat"]
    except EzscintError:
        # for unsupported grids
        gd_lons = rmn.fstlir(fu, nomvar="LON", dtype=np.float32)
        gd_lats = rmn.fstlir(fu, nomvar="LAT", dtype=np.float32)

        # try ^^, >>
        if gd_lons is None:
            gd_lons = rmn.fstlir(fu, nomvar=">>", dtype=np.float32)
            gd_lats = rmn.fstlir(fu, nomvar="^^", dtype=np.float32)

        gd_lons = gd_lons["d"]
        gd_lats = gd_lats["d"]

    rmn.fstcloseall(fu)

    xs, ys, zs = lat_lon.lon_lat_to_cartesian(gd_lons[mask > 0.5], gd_lats[mask > 0.5])
    ktree = KDTree(np.array(list(zip(xs, ys, zs))))

    i_mat, j_mat = np.indices(gd_lons.shape)

    for s in stations:

        xt, yt, zt = lat_lon.lon_lat_to_cartesian(s.longitude, s.latitude)
        dists, inds = ktree.query(np.array([(xt, yt, zt),], dtype=np.float32), k=nnearest)

        if dist_upper_bound is not None:
            inds = inds[dists <= dist_upper_bound]

        if len(inds) == 0:
            continue

        station_id_to_indices[s.station_id] = [
            (i_mat[mask> 0.5][i], j_mat[mask > 0.5][i]) for i in inds.squeeze()
        ]

    # station_id, gd_point_ind
    column_idx = pd.MultiIndex.from_tuples([
        (i, j) for i in station_id_to_indices for j in station_id_to_indices[i]],
        names=["station_id", "gd_indices"]
    )



    df_list = [pd.DataFrame(), ] * len(data_files)
    for ifile, fpath in enumerate(data_files):
        logger.info(f"mod: reading {fpath}")
        fu = rmn.fstopenall(str(fpath))
        keys = rmn.fstinl(fu, nomvar=nomvar, typvar=typvar)
        dates = [None] * len(keys)

        data = {}
        for idx in column_idx:
            data[idx] = [None] * len(dates)

        for ikey, key in enumerate(keys):
            rec = rmn.fstluk(key)

            dates[ikey] = RPNDate(rec["datev"]).toDateTime()
            for idx in column_idx:
                data[idx][ikey] = rec["d"][idx[1]]
                # print(idx[1], rec["d"][idx[1]])

        df = pd.DataFrame.from_dict(data=data)
        df.index = dates
        df.columns = column_idx

        df_list[ifile] = df

        rmn.fstcloseall(fu)

    # merge all data into a single dataframe
    df = pd.concat(df_list, axis=0)
    df.sort_index(axis=0, inplace=True)
    return df


def main():
    pass


if __name__ == '__main__':
    main()
