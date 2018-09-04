from pathlib import Path

import pandas as pd
from data import obs
from typing import List


def map_stations_to_grid_indices(stations: List[obs.Station], stations_info_file):
    """
    :param stations:
    :param stations_info_file: Path to the file that contains correspondence between station ids and the (I, J) coordinates
            of the corresponding grid cells, (I, J) indices are assumed to be 1-based as in Fortran or MATLAB.
    :return: dict relating station_id to the corresponding grid indices, 0-based as in Python and C in the returned dictionarys
    """

    df = pd.read_csv(stations_info_file, skiprows=2, header=0, sep="\s+")
    print(df.columns)

    print(df.head())

    obs_mod_map = {}
    for s in stations:
        place = df["NO"] == s.station_id
        i = df["DATA.I"][place].values[0]
        j = df["DATA.J"][place].values[0]

        obs_mod_map[s.station_id] = (i, j)

    return obs_mod_map


def get_mod_timeseries(stations, mod_data_path: Path, station_id_to_grid_indices, mod_nomvar="ETAS",
                       start_time=None, end_time=None):
    """
    Read all the files in mod_data_path and store data in a pd.DataFrame
    remove the time mean
    :param stations:
    :param mod_data_path: (folder with simulation files)
    :param station_id_to_grid_indices:
    :return:
    """
    from rpnpy.librmn import all as rmn
    from rpnpy.rpndate import RPNDate

    data_dict = {
        s.station_id: [] for s in stations
    }
    data_dict["time"] = []
    data_dict["valid_hour"] = []

    for f_index, data_file in enumerate(mod_data_path.iterdir()):
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
            data_dict[s.station_id].extend([rec["d"][i, j] for rec in records])

        data_dict["time"].extend(dates)
        data_dict["valid_hour"].extend([int(rec["deet"] * rec["npas"] / 3600.0) for rec in records])

        rmn.fstcloseall(funit)

    df = pd.DataFrame.from_dict(data_dict)

    # take out the time mean
    for s in stations:
        df[s.station_id] -= df[s.station_id].mean(skipna=True)

    return df


def main():
    pass


if __name__ == '__main__':
    main()