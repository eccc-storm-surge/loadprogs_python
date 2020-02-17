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

import configparser
from datetime import datetime, timezone, timedelta
from pathlib import Path

from data import obs

from data import mod
from data.obs import Station

from util.plot_ts_and_spectre import plot_ts_and_spectre
import numpy as np

import logging

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

    logging.info(f"Processing {config_path} ...")

    if config_path is None:
        config_path = Path("configs/gem5_research_cycle/rdsps_pseudo-analysis_experimental.cfg")

    config = configparser.ConfigParser(inline_comment_prefixes=("#", ";"),
                                       interpolation=configparser.ExtendedInterpolation())
    config_data = "[top]\n" + config_path.open().read()
    config.read_string(config_data)
    config = config["top"]

    beg_time = datetime.strptime(config["datestart"], "%Y%m%d%H").replace(tzinfo=timezone.utc)
    end_time = datetime.strptime(config["dateend"], "%Y%m%d%H").replace(tzinfo=timezone.utc)

    beg_time_obs = datetime.strptime(config["datestart_obs"], "%Y%m%d%H").replace(tzinfo=timezone.utc)

    mod_nomvar = "ETAS"
    if "mod_nomvar" in config:
        mod_nomvar = config["mod_nomvar"]

    if "nmembers" in config:
        n_members = int(config["nmembers"])
    else:
        n_members = 0

    run_freq_hours = int(config["run_freq_hours"])
    b2b_freq_hours = int(config["b2b_freq_hours"])

    msg = f"back to back frequency should be less or equal to run_freq_hours, but got {b2b_freq_hours} and {run_freq_hours}, respectively"
    assert b2b_freq_hours <= run_freq_hours, msg

    # whether to detide observed time series
    detide_obs = True
    if "detide_obs" in config:
        detide_obs = (int(config["detide_obs"]) == 1)

    # whether to detide model timeseries
    detide_mod = False
    if "detide_mod" in config:
        detide_mod = int(config["detide_mod"]) == 1

    detide_mod_constituents = None
    if detide_mod:
        if "detide_mod_constituents" in config:
            detide_mod_constituents = config["detide_mod_constituents"].split(",")

    dt_texp_from_tbeg = timedelta(hours=0)
    if "dt_texp_from_tbeg_hours" in config:
        dt_texp_from_tbeg = timedelta(hours=int(config["dt_texp_from_tbeg_hours"]))

    out_dir = Path(config["prepared_for_scoring_dir"])
    out_dir.mkdir(exist_ok=True, parents=True)
    out_file = out_dir / ("surge_" + config["label"] + ".dat")

    # do nothing if the output file already exists
    if out_file.exists():
        logger.info(f"(INFO) Already exists, won't redo:\n{out_file}")
        return

    date_format = "%Y%m%d%H"

    plot_detiding_diag = True
    if "plot_detiding_diag" in config:
        plot_detiding_diag = config["plot_detiding_diag"].strip() != "0"

    remove_anal_period_mean = True
    if "remove_anal_period_mean" in config:
        remove_anal_period_mean = int(config["remove_anal_period_mean"])

    obs_do_filtering = False
    mod_do_filtering = False

    if "detide_obs_filtering" in config:
        obs_do_filtering = (int(config["detide_obs_filtering"]) == 1)

    if "detide_mod_filtering" in config:
        mod_do_filtering = (int(config["detide_mod_filtering"]) == 1)

    # valid_hour, station id, lat, lon, date of validity, obs value, mod value 1, ..., mod value n

    member_ids = ["{:03d}".format(i) for i in range(n_members)] if n_members >= 1 else [""]
    out_line_format = "{:5d} {:<7} {:.7f} {:.7f} {:<10} {:.7f}" + " {:.7f}" * len(member_ids) + "\n"

    for k, v in config.items():
        logger.debug(f"{k} => {v}, ({type(v)})")

    # Load obs and do de-tiding (the list of stations is from the .obs file)
    stations = obs.load_station_data_from_dir(Path(config["obs_dir"]).expanduser(),
                                              config["station_info"],
                                              beg_time_obs=beg_time_obs,
                                              do_filtering=obs_do_filtering)

    mod_member_keys = [mod.get_mod_col_name(member_id=member_id) for member_id in member_ids]

    # Load mod corresponding to obs and take out time avg (the model data is loaded from rpn files)
    station_to_model_grid_map = mod.map_stations_to_grid_indices(stations, config["station_info"])

    mod_dir = Path(config["mod_dir"]).expanduser()
    model_points = mod.get_mod_timeseries(stations, mod_dir,
                                          station_id_to_grid_indices=station_to_model_grid_map,
                                          start_time=beg_time,
                                          end_time=end_time,
                                          member_ids=member_ids, mod_nomvar=mod_nomvar,
                                          run_freq_hours=b2b_freq_hours,
                                          dt_texp_from_tbeg=dt_texp_from_tbeg)

    origin_dates_of_interest = mod.get_list_of_origin_dates(model_points, run_freq_dt=timedelta(hours=run_freq_hours))

    if len(model_points) == 0:
        msg = f"Could not find {mod_nomvar} in {mod_dir}, please check your data or load_progs config file.."
        raise IOError(msg)

    with out_file.open("w") as fout:
        mod_groups_by_station = model_points.groupby("station_id")

        for k, g in mod_groups_by_station:
            logger.debug(f"{k} ({type(k)}) => {g}")

        logger.debug(mod_groups_by_station.head())
        for c in mod_groups_by_station:
            logger.debug(c)

        # Dump corresponding obs and mod data into a file for scoring
        for s in stations:
            logger.debug(f"{s.station_id}, {type(s.station_id)}")

            mod_data = mod_groups_by_station.get_group(s.station_id).copy()

            if detide_obs:
                obs_data = s.get_detided_series(do_filtering=obs_do_filtering)
            else:
                # still remove the long-term mean
                obs_data = s.data["twl"] - np.nanmean(s.data["twl"].values)

            # diags for detiding
            if plot_detiding_diag and detide_obs:
                msg = f"plotting timeseries for {s.station_id}"
                logging.info(msg)
                plot_ts_and_spectre(obs_data,
                                    "{}_{}".format(config["label"], s.station_id),
                                    img_dir=out_dir,
                                    subplot_titles=None,
                                    raw_data=s.data["twl-mean"],
                                    tides=s.data["tides"],
                                    sup_title=f"OBS : {s.name} ({s.station_id})")

                s.ttidecon.classic_style(to_file=str(out_dir / f"{s.station_id}_obs_tides.csv"))

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
            if detide_mod:
                logger.info("Detiding model outputs.")
                assert not any(mod_data["time"].isna())

                # for b2b operations
                select_crit = mod_data["valid_hour"] <= b2b_freq_hours
                select_crit = select_crit & (mod_data["valid_hour"] > 0) # remove t=0
                mod_data_twl = mod_data.loc[select_crit, :]
                mod_data_twl.sort_values("time", inplace=True)
                logger.debug(mod_data_twl.head())

                mod_data_twl.set_index("time", inplace=True)

                for c in mod_member_keys:
                    mod_tides, mod_to_filter, mod_ttide_con = obs.get_tides_and_filter_hourly(
                        mod_data_twl.loc[:, c].to_frame(), constituents=detide_mod_constituents)

                    # remove longterm mean
                    mod_data.loc[:, c] -= mod_data_twl[c].mean()
                    # detiding
                    mod_data.loc[:, c] -= mod_tides.loc[mod_data["time"]].values

                    # filtering
                    if mod_do_filtering:
                        mod_data.loc[:, c] -= mod_to_filter.loc[mod_data["time"]].values

                    # diags for detiding
                    if plot_detiding_diag:
                        msg = f"plotting timeseries for mod at {s.station_id}"
                        logging.info(msg)

                        plot_ts_and_spectre(
                            mod_data_twl[c] - mod_data_twl[c].mean() - mod_tides.loc[mod_data_twl.index] -
                            mod_to_filter.loc[mod_data_twl.index],
                            "mod_{}_{}".format(config["label"], s.station_id),
                            img_dir=out_dir,
                            subplot_titles=None,
                            raw_data=mod_data_twl[c] - mod_data_twl[c].mean(),
                            tides=mod_tides, sup_title=config["label"].upper() + f": {s.name} ({s.station_id})")

                        mod_ttide_con.classic_style(to_file=str(out_dir / f"{s.station_id}_mod_tides.csv"))

            # align model and observation timeseries in time
            mod_data.loc[:, f"{s.station_id}_obs"] = obs_data[mod_data["time"]].values

            mod_data.dropna(inplace=True)

            if remove_anal_period_mean:
                tmean = mod_data.loc[(mod_data["valid_hour"] <= b2b_freq_hours) & (mod_data["valid_hour"] > 0), f"{s.station_id}_obs"].mean()
                mod_data.loc[:, f"{s.station_id}_obs"] -= tmean

                logger.debug(f"tmean({s.station_id})={tmean}")

                # mean to be removed from each member calculated based on the control member, which is assumed
                # to be the first in the list

                where_cond = (mod_data["valid_hour"] <= b2b_freq_hours) & (mod_data["valid_hour"] > 0)
                tmean = mod_data.loc[where_cond, mod_member_keys[0]].mean()

                for cn in mod_member_keys:
                    mod_data.loc[:, cn] -= tmean  # remove long time mean only of the control member

            # select only runs run_freq_hours apart (usually it is 36h)
            mod_data = mod_data.loc[mod_data["date_of_origin"].isin(origin_dates_of_interest), :]

            rmse = np.linalg.norm(mod_data[f"{s.station_id}_obs"] - mod_data.loc[:, mod_member_keys].mean(axis=1)) / (
                len(mod_data)) ** 0.5
            logger.debug(f"rmse({s.station_id})={rmse}")

            logger.debug(f"{s.station_id}: found {len(mod_data[s.station_id + '_obs'])} corresponding data values")

            for row_index, row in mod_data.iterrows():
                line = out_line_format.format(
                    int(row["valid_hour"]),
                    s.station_id,
                    s.latitude, s.longitude,
                    row["time"].strftime(date_format),
                    row[f"{s.station_id}_obs"], *[row[k] for k in mod_member_keys]
                )
                fout.write(line)

    logger.info(f"Finished processing {config_path} .")


if __name__ == '__main__':
    # main_levelling_v01()
    import time
    t0 = time.perf_counter()
    main_pn_vs_p0()
    logger.debug(f"Execution time: {time.perf_counter() - t0}")
