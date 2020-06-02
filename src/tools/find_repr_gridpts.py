
"""
Find representative grid points for stations by minimising
a performance score (gamma^2) from historical simulation

"""
import argparse
from pathlib import Path

from data import mod, obs


def read_cmd_args():
    parser = argparse.ArgumentParser(description="run experiment")

    parser.add_argument("--obs-index-in", required=True, type=Path,
                        help="path to a file containing obs station metadata (coordinates, ids, names)")

    parser.add_argument("--obs-index-out", required=True, type=Path,
                        help="path to a file containing obs station "
                             "metadata (coordinates, ids, names) + model grid indices starting from 1")

    parser.add_argument("--mod-files", required=True,
                        help="Path pattern (*,?) to the model output files")

    parser.add_argument("--obs-dir", required=True, type=Path,
                        help="Path to the directory with tide gauge data")

    parser.add_argument("--nnearest", default=9, type=int,
                        help="Number of nearest grid points used for the search of the most representative")

    parser.add_argument("--detide_mod", action="store_true")
    parser.add_argument("--detide_obs", action="store_true")

    parser.add_argument("--nomvar", required=False, default="ETAS",
                        help="Variable name in the model outputs")

    parser.add_argument("--typvar", required=False, default="P@",
                        help="Variable type in the model outputs")

    parser.add_argument("--beg-time", required=False, help="start time of the analysis period",
                        default=None)
    parser.add_argument("--end-time", required=False, help="end time of the analysis period",
                        default=None)


    args = parser.parse_args()
    print(args)

    # sanity checks
    if not args.obs_index_in.exists():
        raise IOError(f"Not found: {args.obs_index_in}")

    if not args.obs_dir.exists():
        raise IOError(f"Not found: {args.obs_dir}")

    mod_path_pattern = Path(str(args.mod_files))
    mod_dir = mod_path_pattern.parent

    mod_files = list(mod_dir.glob(mod_path_pattern.name))

    if len(mod_files) == 0:
        raise IOError(f"No files found matching: {args.mod_files}")

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
        nnearest=9, nomvar=cmd_args.nomvar,
        typvar=cmd_args.typvar
    )

    print(mod_raw.head())

if __name__ == '__main__':
    main()
