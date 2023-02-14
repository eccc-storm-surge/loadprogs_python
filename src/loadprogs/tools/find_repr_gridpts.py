#!/usr/bin/env python

"""
Find representative grid points for stations by minimising
a performance score (gamma^2) from historical simulation

Usage examples:

if wishing to generate .obs file for the closest model grid cells (i.e. without minimising gamma^2):

    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in ~/Python/obs_to_grid_mapping/gdsps_NA_v003.obs  \
                                                    --obs-index-out ~/Python/obs_to_grid_mapping/gdsps_NA_opt_v003.obs \
                                                    --obs-dir ~/sse_obs/merged/gdsps_2019_2020_on_20200909/ \
                                                    --nnearest 1 \
                                                    --mod-files /home/olh001/data/ppp4/gdsps_data/pengcheng/eORCA12_pre/bathy_v4.nc


    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in ~/Python/obs_to_grid_mapping/gdsps_NA_v003.obs  \
                                                    --obs-index-out ~/Python/obs_to_grid_mapping/gdsps_NA_opt_v005.obs \
                                                    --obs-dir ~/sse_obs/merged/gdsps_2019_2020_on_20200909/ \
                                                    --nnearest 1 \
                                                    --mod-files /home/olh001/data/ppp4/gdsps_data/pengcheng/eORCA12_pre/bathy_v4_GoSBoF44.nc


    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in ~/Python/obs_to_grid_mapping/gdsps_NA_opt_v006.obs  \
                                                    --obs-index-out ~/Python/obs_to_grid_mapping/gdsps_NA_opt_v007.obs \
                                                    --obs-dir ~/sse_obs/merged/gdsps_2019_2020_on_20200909/ \
                                                    --nnearest 1 \
                                                    --mod-files /home/olh001/data/ppp4/gdsps_data/pengcheng/eORCA12_pre/bathy_v4_GoSBoF56.nc \
                                                    --mod-bathy-vname Bathymetry

    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in ~/Python/obs_to_grid_mapping/gdsps/gdsps_NA_opt_v006.obs  \
                                                        --obs-index-out ~/Python/obs_to_grid_mapping/gdsps/gdsps_NA_opt_v009.obs \
                                                        --obs-dir ~/sse_obs/merged/gdsps_2019_2020_on_20200909/ \
                                                        --nnearest 1 \
                                                        --mod-files /home/olh001/data/ppp4/gdsps_data/pengcheng/eORCA12_pre/bathy_v4_GoSBoF56.nc \
                                                        --mod-bathy-vname Bathymetry \
                                                        --bathy-min-m 10

    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in ~/Python/obs_to_grid_mapping/gdsps/gdsps_NA_opt_v006.obs  \
                                                        --obs-index-out ~/Python/obs_to_grid_mapping/gdsps/gdsps_NA_opt_v010.obs \
                                                        --obs-dir ~/sse_obs/merged/gdsps_2019_2020_on_20200909/ \
                                                        --nnearest 1 \
                                                        --mod-files /home/olh001/data/ppp4/gdsps_data/pengcheng/eORCA12_pre/bathy_v4_GoSBoF56.nc \
                                                        --mod-bathy-vname Bathymetry \
                                                        --bathy-min-m 0

    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in  /home/olh001/Python/surge_notebooks/gdsps_points_incomplete.obs \
                                                    --obs-index-out /home/olh001/Python/surge_notebooks/gdsps_points_incomplete-idx-added.obs \
                                                    --nnearest 1 \
                                                    --mod-files /home/sssm001/constants/cmde/surge/gdsps/v1.0.0/bathy_v4_GoSBoF57.nc \
                                                    --mod-bathy-vname Bathymetry \
                                                    --bathy-min-m 10


    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in  /home/olh001/Python/download_station_info/data/new_stations_202206_gdsps/new_stations.obs \
                                                    --obs-index-out /home/olh001/Python/download_station_info/data/new_stations_202206_gdsps/new_stations-idx-added.obs \
                                                    --nnearest 1 \
                                                    --mod-files ~smco500/.suites/gdsps_20220621/components/forecast/surge_prog/constants/cmde/surge/gdsps/v1.0.0/bathy_v4_GoSBoF57.nc \
                                                    --mod-bathy-vname Bathymetry \
                                                    --bathy-min-m 10

    # giops
    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in   /home/olh001/Python/obs_to_grid_mapping/giops/gdsps_global_obs_v1.0.2.obs \
                                                --obs-index-out  /home/olh001/Python/obs_to_grid_mapping/giops/giops_global_obs_v1.0.2.obs \
                                                --nnearest 1 \
                                                --mod-files ~smco500/.suites/gdps/g1/constants/oce/repository/master/CONCEPTS/orca025/grids/bathy_ORCA025_LIM.nc \
                                                --mod-bathy-vname Bathymetry \
                                                --bathy-min-m 10

    # riops
    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in   /home/olh001/Python/obs_to_grid_mapping/giops/gdsps_global_obs_v1.0.2.obs \
                                                --obs-index-out  /home/olh001/Python/obs_to_grid_mapping/riops/riops_global_obs_v1.0.2.obs \
                                                --nnearest 1 \
                                                --mod-files /home/smco502/datafiles/constants/cmde/riops/v2.0.0/grids/bathy_meter.nc \
                                                --mod-bathy-vname Bathymetry \
                                                --bathy-min-m 10 \
                                                --dist-upper-bound 10000

    # gdsps old bathy for Anna
    python src/loadprogs/tools/find_repr_gridpts.py --obs-index-in  /home/olh001/Python/obs_to_grid_mapping/giops/giops_global_obs_v1.0.2.obs \
                                                    --obs-index-out /home/olh001/Python/obs_to_grid_mapping/giops/gdsps_global_obs_v1.0.2.obs \
                                                    --nnearest 1 \
                                                    --mod-files /home/sssm001/data/ppp5/u1/data/ppp4/maestro_hubs/gdsps/AC2019040512/pseudo-analysis/gridpt/forecast/gdsps/2019040509_001_1h \
                                                    --mod-bathy-vname SSH



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

    parser.add_argument("--mod-bathy-vname", help="Name of the bathymetry field in the file (only for nnearest=1)")

    parser.add_argument("--obs-dir", required=False, default=None, type=Path,
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

    parser.add_argument("--bathy-min-m", required=False, type=float,
                        help="Minimum depth considered to be ocean "
                             "(i.e. do not consider points with bathymetry < bathy-min-m)",
                        default=None)

    parser.add_argument("--bathy-max-m", required=False, type=float,
                    help="Maximum depth considered to be ocean "
                         "(i.e. do not consider points with bathymetry > bathy-min-m)",
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

    if args.obs_dir is not None and not args.obs_dir.exists():
        raise IOError(f"Not found: {args.obs_dir}")

    mod_files = args.mod_files

    if len(mod_files) == 0:
        raise IOError(f"No files found matching: {args.mod_files}")

    if args.dist_upper_bound_m is not None:
        args.dist_upper_bound_m = float(args.dist_upper_bound_m)

    args.mod_files = mod_files
    return args


def work(cmd_args: argparse.Namespace):
    # parameters for the observations
    config = argparse.Namespace()
    config.station_info = cmd_args.obs_index_in
    config.obs_dir = cmd_args.obs_dir
    config.obs_datatype = "txt"
    config.obs_do_filtering = False
    config.beg_time_obs = cmd_args.beg_time
    config.end_time_obs = cmd_args.end_time

    # if we are interested in the nearest neighbor, no need to load obs data
    if config.obs_dir is not None:
        stations = obs.load_station_data_from_obs_dir(config)

        if len(stations) == 0:
            raise IOError(f"No obs data found in {config.obs_dir} \n "
                           "If you are not optimizing gamma squared you can ommit this option: --obs-dir")
    else:
        stations = obs.load_station_data_from_obs_file(config.station_info)

    station_id_to_mod_indices = {}

    lons = None
    lats = None
    if cmd_args.nnearest > 1:
        # load model data for the stations
        mod_raw = mod.get_mod_timeseries_closest_to(
            stations=stations,
            data_files=cmd_args.mod_files,
            nnearest=cmd_args.nnearest, nomvar=cmd_args.nomvar,
            typvar=cmd_args.typvar,
            dist_upper_bound=cmd_args.dist_upper_bound_m
        )

    else:
        mod_raw = None
        station_id_to_mod_indices, lons, lats = mod.get_mod_indices_closest_to(stations,
                                                                   mod_bathy_file=cmd_args.mod_files[0],
                                                                   mod_bathy_vname=cmd_args.mod_bathy_vname,
                                                                   dist_upper_bound=cmd_args.dist_upper_bound_m,
                                                                   bathy_limit_min=cmd_args.bathy_min_m,
                                                                   bathy_limit_max=cmd_args.bathy_max_m)

    station_id_to_station = {
        s.station_id: s for s in stations
    }

    data = {
        "NO": [], "ID": [], "LAT": [], "LON": [], "DATA.I": [], "DATA.J": [],
    }

    if lons is not None:
        data["DATA.MODEL_LON"] = []
        data["DATA.MODEL_LAT"] = []

    if mod_raw is None:
        if len(station_id_to_mod_indices) == 0:
            raise ValueError("No representative gridcells found")

    for s in stations:
        # s = station_id_to_station[station_id]
        assert isinstance(s, Station)

        if s.station_id not in station_id_to_mod_indices:
            print(f"Did not find representative grid cell for {s}, skipping ...")
            continue
        
        station_id = s.station_id
        data["NO"].append(station_id)
        data["ID"].append(s.name)
        data["LON"].append(s.longitude)
        data["LAT"].append(s.latitude)

        print(f"Processing {station_id}")

        i_sel = None
        j_sel = None

        if mod_raw is not None:

            # skip stations outside of the model domain
            if station_id not in mod_raw.columns.unique(level="station_id"):
                continue

            df = mod_raw[station_id]

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
        else:
            # if using just the closest point
            i_sel, j_sel = station_id_to_mod_indices[station_id][0]

        data["DATA.I"].append(i_sel + 1)
        data["DATA.J"].append(j_sel + 1)
        data["DATA.MODEL_LON"].append(lons[i_sel, j_sel])
        data["DATA.MODEL_LAT"].append(lats[i_sel, j_sel])

    # save data to an obs file
    col_order = ["ID", "NO", "LAT", "LON", "DATA.I", "DATA.J"]
    if "DATA.MODEL_LON" in data:
        col_order += ["DATA.MODEL_LON", "DATA.MODEL_LAT"]
    obs_file.save_dataframe_to_obs(pd.DataFrame.from_dict(data)[col_order], out_file=cmd_args.obs_index_out)


def main():
    cmd_args = read_cmd_args()
    work(cmd_args=cmd_args)


if __name__ == '__main__':
    main()
