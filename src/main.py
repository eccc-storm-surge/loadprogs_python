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
    for k, v in config.items():
        logger.debug(f"{k} => {v}, ({type(v)})")

    # Load obs (the list of stations is from the .obs file)
    obs_config_ns.obs_datatype = config["obs_datatype"]
    stations = obs.load_station_data_from_obs_dir(obs_config_ns)

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

    origin_dates_of_interest = mod.get_list_of_origin_dates(model_points, run_freq_dt=timedelta(hours=config.run_freq_hours))
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

            # align model and observation timeseries in time
            mod_data.loc[:, f"{s.station_id}_obs"] = obs_data[mod_data["time"]].values
            mod_data.dropna(inplace=True)

            if config.remove_anal_period_mean:
                mod_data = mod.remove_analysis_period_mean(mod_data, station=s, mod_member_keys=mod_member_keys, config=config)

            # select only runs run_freq_hours apart (usually it is 36h)
            mod_data = mod_data.loc[mod_data["date_of_origin"].isin(origin_dates_of_interest), :]

            rmse = np.linalg.norm(mod_data[f"{s.station_id}_obs"] - mod_data.loc[:, mod_member_keys].mean(axis=1)) / (len(mod_data)) ** 0.5
            logger.debug(f"rmse({s.station_id})={rmse}")

            logger.debug(f"{s.station_id}: found {len(mod_data[s.station_id + '_obs'])} corresponding data values")

            for row_index, row in mod_data.iterrows():
                line = out_line_format.format(
                    int(row["valid_hour"]),
                    s.station_id,
                    s.latitude, s.longitude,
                    row["time"].strftime("%Y%M%d%H"),
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
