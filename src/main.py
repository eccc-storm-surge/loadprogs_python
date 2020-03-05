"""
Convert obs and model data into a text file where lines contain 1 record of obs and model data


example:

$ head surge_rdsps_pseudo-analysis_experimental.dat
  1   8443970 42.3600009 71.0500009 201612232200 -0.0857397 -0.1144047
  2   8443970 42.3600009 71.0500009 201612232300 -0.0982237 -0.1194047
  3   8443970 42.3600009 71.0500009 201612240000 -0.1089077 -0.1364047
  4   8443970 42.3600009 71.0500009 201612240100 -0.1184387 -0.1434047
  5   8443970 42.3600009 71.0500009 201612240200 -0.1278157 -0.1354047
  6   8443970 42.3600009 71.0500009 201612240300 -0.1375877 -0.1424047
  1   8418150 43.6600009 70.2500009 201612232200 -0.0437227 -0.1044837
  2   8418150 43.6600009 70.2500009 201612232300 -0.0562497 -0.1124837
  3   8418150 43.6600009 70.2500009 201612240000 -0.0686327 -0.1164837
  4   8418150 43.6600009 70.2500009 201612240100 -0.0808897 -0.1194837

Explanation:
col 0: validity hour since the start of the simulation
col 1: station id
col 2: latitude
col 3: longitude
col 4: date of validity of the record
col 5: observed value
col 6: modelled value
[col 7: modelled value]
[...]
"""

from argparse import Namespace
import configparser
import logging
import numpy as np
import pandas as pd
import shutil
import sqlite3

from datetime import datetime, timezone, timedelta
from pathlib import Path

# Custom modules
from data import obs
from data import mod
from data.obs import Station
from util.plot_ts_and_spectre import plot_ts_and_spectre

from util.configs import parse_config_settings

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def main_pn_vs_p0():
    # with p0 - old
    main(config_path=Path("configs/PN_vs_P0/rdsps_forecast_P0.cfg"))

    # with pn - new
    main(config_path=Path("configs/PN_vs_P0/rdsps_forecast_PN.cfg"))


def main_levelling_v01():
    # with levelling
    main(config_path=Path("configs/rdsps_pa/rdsps_pa_lev.cfg"))

    # without levelling
    main(config_path=Path("configs/rdsps_pa/rdsps_pa_nolev.cfg"))


def main(config_path: Path = None):

    config = parse_config_settings(config_path)

    # do nothing if the output file already exists
    if config.out_file.exists():
        logging.info(f"(INFO) Already exists, won't redo:\n{config.out_file}")
    else:
        config.out_dir.mkdir(exist_ok=True, parents=True)

    # valid_hour, station_id, lat, lon, date_of_validity, obs_value, mod_value_1, ..., mod_value_n
    member_ids = ["{:03d}".format(i) for i in range(config.n_members)] if config.n_members >= 1 else [""]
    out_line_format = "{:5d} {:<7} {:.7f} {:.7f} {:<10} {:.7f}" + " {:.7f}" * len(member_ids) + "\n"

    # Load obs (the list of stations is from the .obs file)
    stations = obs.load_station_data_from_obs_dir(config)

    mod_member_keys = [mod.get_mod_col_name(member_id=member_id) for member_id in member_ids]
    # Load mod corresponding to obs and take out time avg (the model data is loaded from rpn files)
    station_to_model_grid_map = mod.map_stations_to_grid_indices(stations, config.station_info)

    model_points = mod.get_mod_timeseries(stations=stations,
                                          mod_data_path=config.mod_dir,
                                          station_id_to_grid_indices=station_to_model_grid_map,
                                          start_time=config.beg_time_mod,
                                          end_time=config.end_time_mod,
                                          member_ids=member_ids, mod_nomvar=config.mod_nomvar,
                                          run_freq_hours=config.b2b_freq_hours,
                                          dt_texp_from_tbeg=config.dt_texp_from_tbeg)

    '''
    >>> print(model_points)
                               time  valid_hour station_id      mod_            date_of_origin
    0     2019-10-29 10:00:00+00:00           1       2780 -0.061921 2019-10-29 09:00:00+00:00
    1     2019-10-29 11:00:00+00:00           2       2780 -0.055385 2019-10-29 09:00:00+00:00
    2     2019-10-29 12:00:00+00:00           3       2780 -0.049778 2019-10-29 09:00:00+00:00
    3     2019-10-29 13:00:00+00:00           4       2780 -0.049955 2019-10-29 09:00:00+00:00
    4     2019-10-29 14:00:00+00:00           5       2780 -0.049552 2019-10-29 09:00:00+00:00
    ...                         ...         ...        ...       ...                       ...
    13117 2019-12-04 20:00:00+00:00         239       2780  0.071544 2019-11-24 21:00:00+00:00
    13118 2019-12-04 21:00:00+00:00         240       2780  0.054046 2019-11-24 21:00:00+00:00
    13119 2019-12-04 22:00:00+00:00         241       2780  0.045281 2019-11-24 21:00:00+00:00
    13120 2019-12-04 23:00:00+00:00         242       2780  0.043560 2019-11-24 21:00:00+00:00
    13121 2019-12-05 00:00:00+00:00         243       2780  0.040359 2019-11-24 21:00:00+00:00

    [13122 rows x 5 columns]
    '''

    # forecast start dates based on run_freq_hours
    origin_dates_of_interest = mod.get_list_of_origin_dates(model_points, run_freq_dt=timedelta(hours=config.run_freq_hours))

    '''
    >>> print(origin_dates_of_interest)
    DatetimeIndex(['2019-10-29 09:00:00+00:00', '2019-10-30 21:00:00+00:00',
               '2019-11-01 09:00:00+00:00', '2019-11-02 21:00:00+00:00',
               '2019-11-04 09:00:00+00:00', '2019-11-05 21:00:00+00:00',
               '2019-11-07 09:00:00+00:00', '2019-11-08 21:00:00+00:00',
               '2019-11-10 09:00:00+00:00', '2019-11-11 21:00:00+00:00',
               '2019-11-13 09:00:00+00:00', '2019-11-14 21:00:00+00:00',
               '2019-11-16 09:00:00+00:00', '2019-11-17 21:00:00+00:00',
               '2019-11-19 09:00:00+00:00', '2019-11-20 21:00:00+00:00',
               '2019-11-22 09:00:00+00:00', '2019-11-23 21:00:00+00:00'],
              dtype='datetime64[ns, UTC]', freq='36H')
    '''

    if len(model_points) == 0:
        msg = f"Could not find {config.mod_nomvar} in {config.mod_dir}, please check your data or load_progs config file.."
        raise IOError(msg)

    with config.out_file.open("w") as fout:
        mod_groups_by_station = model_points.groupby("station_id")

        for k, g in mod_groups_by_station:
            logger.debug(f"{k} ({type(k)}) => {g}")

        logger.debug(mod_groups_by_station.head())
        for c in mod_groups_by_station:
            logger.debug(c)

        # Dump corresponding obs and mod data into a file for scoring
        for s in stations:
            logger.debug(f"{s.station_id}, {type(s.station_id)}")

            '''
            >>> print(s.data)
            time                       twl
            2019-02-22 22:00:00+00:00  2.66
            2019-02-22 23:00:00+00:00  2.09
            2019-02-23 00:00:00+00:00  1.36
            2019-02-23 01:00:00+00:00  0.63
            2019-02-23 02:00:00+00:00  0.08
            ...                         ...
            2019-11-24 20:00:00+00:00  1.64
            2019-11-24 21:00:00+00:00  1.03
            2019-11-24 22:00:00+00:00  0.58
            2019-11-24 23:00:00+00:00  0.38
            2019-11-25 00:00:00+00:00  0.50

            [6012 rows x 1 columns]
            '''

            # get model data for corresponding station
            mod_data = mod_groups_by_station.get_group(s.station_id).copy()

            # detide observation data if specified in config file
            if config.detide_obs:
                obs_data = s.get_detided_series(do_filtering=config.obs_do_filtering)

                # diags for detiding
                if config.plot_detiding_diag:
                    msg = f"plotting timeseries for {s.station_id}"
                    logging.info(msg)
                    # Create time series and power spectrum plots for observational data
                    plot_ts_and_spectre(hourly_series=obs_data,
                                        data_label="{}_{}".format(config.label, s.station_id),
                                        img_dir=config.out_dir,
                                        subplot_titles=None,
                                        raw_data=s.data["twl-mean"],
                                        tides=s.data["tides"],
                                        sup_title=f"OBS : {s.name} ({s.station_id})")

                    # Create tidal constituents csv file for observational data
                    s.ttidecon.classic_style(to_file=str(config.out_dir / f"{s.station_id}_obs_tides.csv"))

            else:
                # still remove the long-term mean
                obs_data = s.data["twl"] - np.nanmean(s.data["twl"].values)

            '''
            >>> print(obs_data)
            time
            2019-02-22 22:00:00+00:00    1.126598
            2019-02-22 23:00:00+00:00    0.556598
            2019-02-23 00:00:00+00:00   -0.173402
            2019-02-23 01:00:00+00:00   -0.903402
            2019-02-23 02:00:00+00:00   -1.453402
                                            ...
            2019-11-24 20:00:00+00:00    0.106598
            2019-11-24 21:00:00+00:00   -0.503402
            2019-11-24 22:00:00+00:00   -0.953402
            2019-11-24 23:00:00+00:00   -1.153402
            2019-11-25 00:00:00+00:00   -1.033402
            Name: twl, Length: 6012, dtype: float64
            '''

            # deprecated
            # mod_data[f"{s.station_id}_obs"] = obs_data[mod_data["time"]].values

            # Newer note (20190502): this is changed to be as in the MATLAB version of loadprogs, i.e. remove mean of
            # the observed data in the aligned table

            # take the time mean over the same time points as the model (unless there is missing data)
            # Note: some time points will be added to the mean few times in a similar way as the model has
            # several values for the same time (with different lead times), this does not change the scores,
            # but makes the scatter plots
            # obs_data = obs_data.reindex(mod_data["time"])

            # remove the mean over the current period from the data (to be more consistent with mod)
            # if obs_remove_anal_period_mean:
            #    obs_data -= obs_data.mean(skipna=True, axis=0)
            #

            # detide model time series if requested
            if config.detide_mod:

                mod_data_twl = mod.get_mod_twl_for_b2b(mod_data, config=config)

                for c in mod_member_keys:
                    mod_tides, mod_to_filter, mod_ttide_con = obs.get_tides_and_filter_hourly(data=mod_data_twl.loc[:, c].to_frame(),
                                                                                              constituents=config.detide_mod_constituents)
                    # remove longterm mean
                    mod_data.loc[:, c] -= mod_data_twl[c].mean()
                    # detiding
                    mod_data.loc[:, c] -= mod_tides.loc[mod_data["time"]].values
                    # filtering
                    if config.mod_do_filtering:
                        mod_data.loc[:, c] -= mod_to_filter.loc[mod_data["time"]].values

                    # diags for detiding
                    if config.plot_detiding_diag:
                        msg = f"plotting timeseries for mod at {s.station_id}"
                        logging.info(msg)

                        plot_ts_and_spectre(hourly_series=mod_data_twl[c] - mod_data_twl[c].mean() - mod_tides.loc[mod_data_twl.index]
                                                          - mod_to_filter.loc[mod_data_twl.index],
                                            data_label="mod_{}_{}".format(config.label, s.station_id),
                                            img_dir=config.out_dir,
                                            subplot_titles=None,
                                            raw_data=mod_data_twl[c] - mod_data_twl[c].mean(),
                                            tides=mod_tides,
                                            sup_title=config.label.upper() + f": {s.name} ({s.station_id})")

                        mod_ttide_con.classic_style(to_file=str(config.out_dir / f"{s.station_id}_mod_tides.csv"))

            print(mod_data.to_string()); quit()
            '''
            >>> print(mod_data); print(obs_data)
                                       time  valid_hour station_id      mod_            date_of_origin
            0     2019-10-29 10:00:00+00:00           1       2780 -0.061921 2019-10-29 09:00:00+00:00
            1     2019-10-29 11:00:00+00:00           2       2780 -0.055385 2019-10-29 09:00:00+00:00
            2     2019-10-29 12:00:00+00:00           3       2780 -0.049778 2019-10-29 09:00:00+00:00
            3     2019-10-29 13:00:00+00:00           4       2780 -0.049955 2019-10-29 09:00:00+00:00
            4     2019-10-29 14:00:00+00:00           5       2780 -0.049552 2019-10-29 09:00:00+00:00
            ...                         ...         ...        ...       ...                       ...
            13117 2019-12-04 20:00:00+00:00         239       2780  0.071544 2019-11-24 21:00:00+00:00
            13118 2019-12-04 21:00:00+00:00         240       2780  0.054046 2019-11-24 21:00:00+00:00
            13119 2019-12-04 22:00:00+00:00         241       2780  0.045281 2019-11-24 21:00:00+00:00
            13120 2019-12-04 23:00:00+00:00         242       2780  0.043560 2019-11-24 21:00:00+00:00
            13121 2019-12-05 00:00:00+00:00         243       2780  0.040359 2019-11-24 21:00:00+00:00

            [13122 rows x 5 columns]
            time
            2019-02-22 22:00:00+00:00    1.126598
            2019-02-22 23:00:00+00:00    0.556598
            2019-02-23 00:00:00+00:00   -0.173402
            2019-02-23 01:00:00+00:00   -0.903402
            2019-02-23 02:00:00+00:00   -1.453402
                                           ...
            2019-11-24 20:00:00+00:00    0.106598
            2019-11-24 21:00:00+00:00   -0.503402
            2019-11-24 22:00:00+00:00   -0.953402
            2019-11-24 23:00:00+00:00   -1.153402
            2019-11-25 00:00:00+00:00   -1.033402
            Name: twl, Length: 6012, dtype: float64
            '''

            # align model and observation timeseries in time
            mod_data.loc[:, f"{s.station_id}_obs"] = obs_data[mod_data["time"]].values
            mod_data.dropna(inplace=True)

            obs_mod_shared_timestamps = set(mod_data["time"])

            print(mod_data.to_string()); quit()
            '''
            >>> print(mod_data)
                                      time  valid_hour station_id      mod_            date_of_origin  2780_obs
            0    2019-10-29 10:00:00+00:00           1       2780 -0.061921 2019-10-29 09:00:00+00:00  0.006598
            1    2019-10-29 11:00:00+00:00           2       2780 -0.055385 2019-10-29 09:00:00+00:00 -0.663402
            2    2019-10-29 12:00:00+00:00           3       2780 -0.049778 2019-10-29 09:00:00+00:00 -1.173402
            3    2019-10-29 13:00:00+00:00           4       2780 -0.049955 2019-10-29 09:00:00+00:00 -1.393402
            4    2019-10-29 14:00:00+00:00           5       2780 -0.049552 2019-10-29 09:00:00+00:00 -1.203402
            ...                        ...         ...        ...       ...                       ...       ...
            9185 2019-11-25 00:00:00+00:00         195       2780  0.183814 2019-11-16 21:00:00+00:00 -1.033402
            8954 2019-11-25 00:00:00+00:00         207       2780  0.153682 2019-11-16 09:00:00+00:00 -1.033402
            8723 2019-11-25 00:00:00+00:00         219       2780  0.200927 2019-11-15 21:00:00+00:00 -1.033402
            8492 2019-11-25 00:00:00+00:00         231       2780 -0.026832 2019-11-15 09:00:00+00:00 -1.033402
            8261 2019-11-25 00:00:00+00:00         243       2780  0.123881 2019-11-14 21:00:00+00:00 -1.033402

            [9855 rows x 6 columns]
            '''

            if config.remove_anal_period_mean:
                mod_data = mod.remove_analysis_period_mean(mod_data, station=s, mod_member_keys=mod_member_keys, config=config)

            # select only runs run_freq_hours apart (usually it is 36h)
            mod_data = mod_data.loc[mod_data["date_of_origin"].isin(origin_dates_of_interest), :]

            """
            >>> print(mod_data)
                                       time  valid_hour station_id      mod_            date_of_origin  2780_obs
            0     2019-10-29 10:00:00+00:00           1       2780 -0.038372 2019-10-29 09:00:00+00:00  0.006894
            1     2019-10-29 11:00:00+00:00           2       2780 -0.031836 2019-10-29 09:00:00+00:00 -0.663106
            2     2019-10-29 12:00:00+00:00           3       2780 -0.026229 2019-10-29 09:00:00+00:00 -1.173106
            3     2019-10-29 13:00:00+00:00           4       2780 -0.026405 2019-10-29 09:00:00+00:00 -1.393106
            4     2019-10-29 14:00:00+00:00           5       2780 -0.026003 2019-10-29 09:00:00+00:00 -1.203106
            ...                         ...         ...        ...       ...                       ...       ...
            11033 2019-11-25 00:00:00+00:00          99       2780  0.102251 2019-11-20 21:00:00+00:00 -1.033106
            10340 2019-11-25 00:00:00+00:00         135       2780  0.291601 2019-11-19 09:00:00+00:00 -1.033106
            9647  2019-11-25 00:00:00+00:00         171       2780  0.176919 2019-11-17 21:00:00+00:00 -1.033106
            8954  2019-11-25 00:00:00+00:00         207       2780  0.177231 2019-11-16 09:00:00+00:00 -1.033106
            8261  2019-11-25 00:00:00+00:00         243       2780  0.147431 2019-11-14 21:00:00+00:00 -1.033106

            [3368 rows x 6 columns]
            """

            rmse = np.linalg.norm(mod_data[f"{s.station_id}_obs"] - mod_data.loc[:, mod_member_keys].mean(axis=1)) / (len(mod_data)) ** 0.5
            logger.debug(f"rmse({s.station_id})={rmse}")

            logger.debug(f"{s.station_id}: found {len(mod_data[s.station_id + '_obs'])} corresponding data values")

            for row_index, row in mod_data.iterrows():
                line = out_line_format.format(
                    int(row["valid_hour"]),
                    s.station_id,
                    s.latitude, s.longitude,
                    row["time"].strftime("%Y%m%d%H"),
                    row[f"{s.station_id}_obs"], *[row[k] for k in mod_member_keys]
                )
                fout.write(line)

            if config.output_sql:
                sql_out_dir = config.out_dir / ("surge_" + config.label + ".sqlite")
                mod_sql_data = mod.prepare_mod_sql_data(mod_data, mod_member_keys, stn=s)
                conn = sqlite3.connect(sql_out_dir)
                mod_sql_data.to_sql(name="data", con=conn, index=False, if_exists='append')

    logger.info(f"Finished processing {config_path} .")


if __name__ == '__main__':
    # main_levelling_v01()
    import time
    t0 = time.perf_counter()
    main_pn_vs_p0()
    logger.debug(f"Execution time: {time.perf_counter() - t0}")
