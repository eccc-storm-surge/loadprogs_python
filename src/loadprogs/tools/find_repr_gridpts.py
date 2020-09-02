
"""
Find representative grid points for stations by minimising
a performance score (gamma^2) from historical simulation

"""
import argparse
from datetime import datetime
from pathlib import Path

import pytz

from loadprogs.data import mod, obs
from loadprogs.data.obs import Station
from loadprogs.util import scores, obs_file
import pandas as pd


def read_cmd_args():
    DATETIME_FORMAT = r"%Y%m%d%H"

    parser = argparse.ArgumentParser(description="run experiment")

    parser.add_argument("--obs-index-in", required=True, type=Path,
                        help="path to a file containing obs station metadata (coordinates, ids, names)")

    parser.add_argument("--obs-index-out", required=True, type=Path,
                        help="path to a file containing obs station "
                             "metadata (coordinates, ids, names) + model grid indices starting from 1")

    parser.add_argument("--mod-files", required=True, nargs="+",
                        help="Path pattern (*,?) to the model output files")

    parser.add_argument("--obs-dir", required=True, type=Path,
                        help="Path to the directory with tide gauge data")

    parser.add_argument("--nnearest", default=9, type=int,
                        help="Number of nearest grid points used for the search of "
                             "the most representative, if <= 1, then the closest gridcell is mapped to each station")

    parser.add_argument("--detide_mod", type=int, default=1)
    parser.add_argument("--detide_obs", type=int, default=1)

    parser.add_argument("--nomvar", required=False, default="ETAS",
                        help="Variable name in the model outputs")

    parser.add_argument("--typvar", required=False, default="P@",
                        help="Variable type in the model outputs")

    parser.add_argument("--beg-time", required=False,
                        help="start time of the analysis period, format: " + DATETIME_FORMAT.replace("%", "%%"),
                        default=None,
                        type=lambda param: datetime.strptime(param, DATETIME_FORMAT))
    parser.add_argument("--end-time", required=False,
                        help="end time of the analysis period, format: " + DATETIME_FORMAT.replace("%", "%%"),
                        default=None,
                        type=lambda param: datetime.strptime(param, DATETIME_FORMAT))

    parser.add_argument("--dist-upper-bound-m", required=False,
                        help="upper bound on the search distance for the grid points "
                             "closest to a station, to eliminate stations outside the domain",
                        default=None)

    args = parser.parse_args()

    args.do_filtering = False
    args.constituents = [
        "MSM", "MM", "MSF", "MF", "ALP1", "2Q1", "SIG1", "Q1", "RHO1", "O1",
        "TAU1", "BET1", "NO1", "CHI1", "PI1", "P1", "S1", "K1", "PSI1", "PHI1", "THE1", "J1",
        "SO1", "OO1", "UPS1", "OQ2", "EPS2", "2N2", "MU2", "N2", "NU2", "GAM2",
        "H1", "M2", "H2", "MKS2", "LDA2", "L2", "T2",
        "S2", "R2", "K2", "MSN2", "ETA2", "MO3",
        "M3", "SO3", "MK3", "SK3", "MN4", "M4", "SN4", "MS4", "MK4", "S4", "SK4",
        "2MK5", "2SK5", "2MN6", "M6", "2MS6", "2MK6", "2SM6", "MSK6", "3MK7", "M8"
    ]

    # make the times timezone-aware
    if args.beg_time is not None:
        assert isinstance(args.beg_time, datetime)
        args.beg_time = args.beg_time.replace(tzinfo=pytz.UTC)

    if args.end_time is not None:
        args.end_time = args.end_time.replace(tzinfo=pytz.UTC)

    # print(args)

    # sanity checks
    if not args.obs_index_in.exists():
        raise IOError(f"Not found: {args.obs_index_in}")

    if not args.obs_dir.exists():
        raise IOError(f"Not found: {args.obs_dir}")

    mod_files = args.mod_files

    if len(mod_files) == 0:
        raise IOError(f"No files found matching: {args.mod_files}")

    if args.dist_upper_bound_m is not None:
        args.dist_upper_bound_m = float(args.dist_upper_bound_m)

    args.mod_files = mod_files
    return args


def main():

    cmd_args = read_cmd_args()

    # parameters for the observations
    config = argparse.Namespace()
    config.station_info = cmd_args.obs_index_in
    config.obs_dir = cmd_args.obs_dir
    config.obs_datatype = "txt"
    config.obs_do_filtering = False
    config.beg_time_obs = cmd_args.beg_time
    config.end_time_obs = cmd_args.end_time

    stations = obs.load_station_data_from_obs_dir(config)

    # load model data for the stations
    mod_raw = mod.get_mod_timeseries_closest_to(
        stations=stations,
        data_files=cmd_args.mod_files,
        nnearest=cmd_args.nnearest, nomvar=cmd_args.nomvar,
        typvar=cmd_args.typvar,
        dist_upper_bound=cmd_args.dist_upper_bound_m
    )

    station_id_to_station = {
        s.station_id: s for s in stations
    }

    print(mod_raw.columns)

    data = {
        "NO": [], "ID": [], "LAT": [], "LON": [], "DATA.I": [], "DATA.J": []
    }

    for station_id in mod_raw.columns.unique(level="station_id"):
        print(f"Processing {station_id}")
        s = station_id_to_station[station_id]
        assert isinstance(s, Station)
        data["NO"].append(station_id)
        data["ID"].append(s.name)
        data["LON"].append(s.longitude)
        data["LAT"].append(s.latitude)

        df = mod_raw[station_id]
        i_sel = None
        j_sel = None

        if cmd_args.detide_obs:
            obs_ts = s.get_detided_series(do_filtering=cmd_args.do_filtering)
        else:
            obs_ts = s.data["twl"]

        obs_ts -= obs_ts.mean()

        # select i and j for each station that minimize the scores
        score_min = None
        for gd_indices in df.columns:
            mod_ts = df[gd_indices]

            mod_ts = mod_ts.to_frame()
            mod_ts.columns = ["twl", ]

            mod_tides, mod_filt, tconst = obs.get_tides_and_filter_hourly(
                mod_ts,
                do_filtering=cmd_args.do_filtering,
                constituents=cmd_args.constituents)

            mod_ts = mod_ts["twl"] - mod_tides + mod_filt
            mod_ts -= mod_ts.mean()

            score = scores.gamma2(obs_ts, mod_ts)
            if score_min is None:
                score_min = score
                i_sel, j_sel = gd_indices

            if score_min > score:
                score_min = score
                i_sel, j_sel = gd_indices

        data["DATA.I"].append(i_sel + 1)
        data["DATA.J"].append(j_sel + 1)

    # save data to an obs file
    col_order = ["ID", "NO", "LAT", "LON", "DATA.I", "DATA.J"]
    obs_file.save_dataframe_to_obs(pd.DataFrame.from_dict(data)[col_order], out_file=cmd_args.obs_index_out)


if __name__ == '__main__':
    main()
