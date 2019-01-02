from pathlib import Path

import pandas as pd
from data import obs
from typing import List


def get_member_id_from_file_path(fpath: Path):
    return fpath.name.split("_")[-1]


def map_stations_to_grid_indices(stations: List[obs.Station], stations_info_file):
    """
    :param stations:
    :param stations_info_file: Path to the file that contains correspondence between station ids and the (I, J) coordinates
            of the corresponding grid cells, (I, J) indices are assumed to be 1-based as in Fortran or MATLAB.
    :return: dict relating station_id to the corresponding grid indices, 0-based as in Python and C in the returned dictionaries
    """

    df = pd.read_csv(stations_info_file, skiprows=2, header=0, sep="\s+")

    obs_mod_map = {}
    for s in stations:
        place = df["NO"] == int(s.station_id)
        i = df["DATA.I"][place].values[0]
        j = df["DATA.J"][place].values[0]

        obs_mod_map[s.station_id] = (i - 1, j - 1)

    return obs_mod_map



def get_mod_timeseries(stations, mod_data_path: Path,
                       station_id_to_grid_indices,
                       mod_nomvar="ETAS",
                       start_time=None, end_time=None, member_ids=("", )):
    """
    Read all the files in mod_data_path and store data in a pd.DataFrame
    remove the time mean

    member id is derived from the last part (after the last underscore) of the output file name
    :param stations:
    :param mod_data_path: (folder with simulation files)
    :param station_id_to_grid_indices:
    :return:
    """
    from rpnpy.librmn import all as rmn
    from rpnpy.rpndate import RPNDate

    data_dict = {
        (s.station_id, member_id): [] for s in stations for member_id in member_ids
    }
    data_dict["time"] = []
    data_dict["valid_hour"] = []

    for f_index, data_file in enumerate(mod_data_path.iterdir()):

        member_id = get_member_id_from_file_path(data_file)

        # get all data from a file in memory
        funit = rmn.fstopenall(str(data_file))

        keys = rmn.fstinl(funit, typvar="P@", nomvar=mod_nomvar)

        # filter the keys by date first first, if required
        dates = [RPNDate(rmn.fstprm(k)["datev"]).toDateTime() for k in keys]

        if start_time is not None or end_time is not None:
            keys_filt = []
            dates_filt = []
            for k, d in zip(keys, dates):
                if start_time is not None:
                    if d < start_time:
                        continue

                if end_time is not None:
                    if d > end_time:
                        continue

                keys_filt.append(k)
                dates_filt.append(d)

            keys = keys_filt
            dates = dates_filt

        records = [rmn.fstluk(k) for k in keys]

        for s in stations:
            i, j = station_id_to_grid_indices[s.station_id]
            data_dict[(s.station_id, member_id)].extend([rec["d"][i, j] for rec in records])

        data_dict["time"].extend(dates)
        data_dict["valid_hour"].extend([int(rec["deet"] * rec["npas"] / 3600.0) for rec in records])

        rmn.fstcloseall(funit)

    for i, d in enumerate(data_dict["time"]):
        assert d != 0, f"time[{i}]={d}"

    df = pd.DataFrame.from_dict(data_dict)

    # take out the time mean
    for c in df:
        if c in ["time", "valid_hour"]:
            continue

        df[c] -= df[c].mean(skipna=True)

    # sorting, useful for debugging
    # df.sort_values(["time", "valid_hour"], inplace=True)

    return df


def main():
    pass


if __name__ == '__main__':
    main()