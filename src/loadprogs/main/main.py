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

import logging
import numpy as np
import sqlite3
import pandas as pd

from datetime import timedelta
from pathlib import Path

# Custom modules
from ..util import match_io
from ..data import obs
from ..data import mod
from ..util.plot_ts_and_spectre import plot_ts_and_spectre
from ..util.configs import parse_config_settings
from ..util import constants
from ..util import log_utils


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


def main(config_path: Path = None, cfg_overrides: dict = None,
         allow_missing_mod_data: bool = False, debug: bool = False):
    """
    Entry point for processing a given simulation
    Args:
        debug: if True debug mode is on
        allow_missing_mod_data: if True allows model data to be missing, otherwise fails
        config_path: path to the loadprogs config file
        cfg_overrides: config properties to be overriden, useful for embedded use for monitoring
    """

    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not config_path.exists():
        raise IOError(f"cfg file does not exist: {config_path}")

    config = parse_config_settings(config_path, cfg_overrides)

    # attach debug property to the config
    config.debug = debug

    for k, v in vars(config).items():
        logger.info(f"{k} => {v}, ({type(v)})")

    config.out_dir.mkdir(exist_ok=True, parents=True)

    # do nothing if the output file already exists
    if config.output_txt and config.out_file.exists():
        logger.info(f"Already exists, won't redo:\n{config.out_file}")
        logger.info(f"Setting output_txt option to False (remove the file to rerun)")
        config.output_txt = False

    if config.output_sqlite and config.out_file_sqlite.exists():
        logger.info(f"Already exists, won't redo:\n{config.out_file_sqlite}")
        logger.info(f"Setting output_sqlite option to False (remove the file to rerun)")
        config.output_sqlite = False

    if not (config.output_txt or config.output_sqlite):
        logger.info(f"No output requested, exiting!")
        return

    # remove the tides file if exists already
    tides_file = config.out_file.parent / f"tides_{config.out_file.name}"
    if tides_file.exists():
        logger.info(f"The tides file {tides_file} will be overwritten!")
        tides_file.unlink()

    # valid_hour, station_id, lat, lon, date_of_validity, obs_value, mod_value_1, ..., mod_value_n
    member_ids = ["{:03d}".format(i) for i in range(config.n_members)] if config.n_members >= 1 else [""]
    out_line_format = "{:.7f} {:<7} {:.7f} {:.7f} {:<10} {:.7f}" + " {:.7f}" * len(member_ids) + "\n"

    # Load obs (the list of stations is from the .obs file)
    stations = obs.load_station_data_from_obs_dir(config)
    

    mod_member_keys = [mod.get_mod_col_name(member_id=member_id) for member_id in member_ids]
    # Load mod corresponding to obs and take out time avg (the model data is loaded from rpn files)
    station_to_model_grid_map = mod.map_stations_to_grid_indices(stations, config.station_info,
                                                                 transpose_indices=config.transpose_mod_indices)

    model_points = mod.get_mod_timeseries_cfg(config,
                                              station_id_to_grid_indices=station_to_model_grid_map,
                                              member_ids=member_ids,
                                              allow_missing=allow_missing_mod_data)

    if len(model_points) == 0:
        msg = f"Could not find {config.mod_nomvar} in {config.mod_dir}, please check your data or load_progs config file.."
        raise IOError(msg)

    mod_groups_by_station = model_points.groupby(constants.COLNAME_STID)

    for k, g in mod_groups_by_station:
        logger.debug(f"{k} ({type(k)}) => {g}")

    conn = None

    # load external tides (from other sources if supplied)
    external_tides_groups_by_station = None
    if config.mod_external_tides.exists():
        logger.info(f"Using externally provided tides from: {config.mod_external_tides}")
        external_tides = match_io.read_dat(config.mod_external_tides)

        logger.debug("external tides: \n %s \n", external_tides.head())

        external_tides_groups_by_station = external_tides.groupby(constants.COLNAME_STID)

    # load external data for debiasing (usually mod-obs matches from a corresponding PA simulation)
    external_debias_groups_by_station = None
    if config.mod_external_debias.exists():
        external_debias = match_io.read_dat(config.mod_external_debias)
        external_debias_groups_by_station = external_debias.groupby(constants.COLNAME_STID)

    # Dump corresponding obs and mod data into a file for scoring
    for s in stations:

        logger.info("\n--------------------\n processing station  '%s' (%s)"
                    "\n--------------------\n", s.name, s.station_id)

        member_id_to_mod_tides = {}

        # get model data for corresponding station
        mod_data = mod_groups_by_station.get_group(s.station_id).copy()

        # check if there are obs data available for the station first, 
        # fill with nans if it is the case,
        # this is to still output model data even when obs are missing
        if s.get_data_len_since() == 0:
            logger.info("No data found for %s (%s) station! \n",
                        s.name, s.station_id
                        )

            dummy = mod_data.drop_duplicates(subset=(constants.COLNAME_TIME))
            dummy = dummy.set_index(constants.COLNAME_TIME)
            dummy = np.nan * dummy.loc[:, mod_member_keys[0]].to_frame()
            dummy.columns = [constants.COLNAME_TWL]

            s.assign_data(dummy)

        # detide observation data if specified in config file
        if config.detide_obs:
            try:

                obs_data = s.get_detided_series(do_filtering=config.obs_do_filtering, 
                                                constituents=config.detide_obs_constituents)

                n_valid_obs = len(obs_data.dropna())
                if n_valid_obs < config.min_nhours_for_detiding_obs:
                    logger.info(f"Not enough obs data for {s.station_id} ({n_valid_obs},"
                                f" but obs:min_nhours_for_detiding={config.min_nhours_for_detiding_obs})")
                    obs_data.loc[:] = np.nan

                logger.debug(" obs (after detiding): \n %s \n", obs_data)
            except ValueError as ve:
                logger.debug(ve)
                msg = """Smth went wrong during detiding of %s,
                         re-run with --debug option to get more information.
                         Skipping %s!
                """
                logger.info(msg, s.station_id, s.station_id)
                continue

            # diags for detiding
            if config.plot_detiding_diag:
                msg = f"plotting timeseries for {s.station_id}"
                logging.info(msg)
                # Create time series and power spectrum plots for observational data
                plot_ts_and_spectre(hourly_series=obs_data.asfreq("1H"),
                                    data_label="{}_{}".format(config.label, s.station_id),
                                    img_dir=config.out_dir,
                                    subplot_titles=None,
                                    raw_data=s.data["twl-mean"].asfreq("1H"),
                                    tides=s.data["tides"].asfreq("1H"),
                                    sup_title=f"OBS : {s.name} ({s.station_id})")

                # Create tidal constituents csv file for observational data
                s.ttidecon.classic_style(to_file=str(config.out_dir / f"{s.station_id}_obs_tides.csv"))

        else:
            # still remove the long-term mean
            obs_data = s.data[constants.COLNAME_TWL] - np.nanmean(s.data[constants.COLNAME_TWL].values)

        # detide model time series if requested
        if config.detide_mod:

            mod_data_twl = mod.get_mod_twl_for_b2b(mod_data, config=config, mod_member_keys=mod_member_keys)


            # initializations
            t_unique = mod_data[constants.COLNAME_TIME].drop_duplicates()

            logger.debug("\n ==== t_unique ==== \n %s \n", t_unique)

            mod_tides = pd.Series(index=t_unique)
            mod_to_filter = pd.Series(index=t_unique)
            mod_tides.loc[:] = 0.
            mod_to_filter.loc[:] = 0.
            mod_ttide_con = None

            logger.debug("\n ==== mod_data_twl ==== \n %s \n", mod_data_twl.head())

            for c in mod_member_keys:

                if config.mod_external_tides.exists():  # tides are provided externally

                    if config.mod_do_filtering:
                        logger.info("No filtering is applied to the model outputs when tides are externally provided!")
                        logger.info(f"Ignoring: config.mod_do_filtering={config.mod_do_filtering}, setting it to False")
                        config.mod_do_filtering = False

                    mod_tides = external_tides_groups_by_station.get_group(s.station_id)
                    mod_tides = mod_tides.set_index(constants.COLNAME_TIME)
                    mod_tides = mod_tides.iloc[:, -1]
                    mod_to_filter = mod_tides * 0

                    logger.debug("tides used for detiding %s: \n %s \n", s.station_id, mod_tides.head(n=50))

                else:
                    assert s.latitude is not None, "Latitude is required for detiding"

                    mod_tides, mod_to_filter, mod_ttide_con = obs.get_tides_and_filter_hourly(
                        data=mod_data_twl.loc[:, c].to_frame(),
                        latitude=s.latitude,
                        constituents=config.detide_mod_constituents,
                        do_filtering=config.mod_do_filtering, do_cleanup=False, 
                        detide_min_frequency_hz=config.mod_detide_min_tide_frequency_hz)

                # remove longterm mean
                # mod_data.loc[:, c] -= mod_data_twl[c].mean()

                # get the union index
                t_index = pd.to_datetime(mod_tides.index.union(t_unique))
                logger.debug("\nt_index\n %s", t_index)

                # mod_tides = mod_tides.reindex(t_index).interpolate(method="time", limit=2, limit_direction="both")
                # mod_to_filter = mod_to_filter.reindex(t_index).interpolate(method="time", limit=2, limit_direction="both")

                # import pickle
                # pickle.dump(mod_data, open("mod_data_before.bin", "wb"))
                # pickle.dump(mod_tides, open("mod_tides.bin", "wb"))
                # pickle.dump(mod_to_filter, open("mod_to_filter.bin", "wb"))

                # detiding
                logger.debug(mod_data[constants.COLNAME_TIME])
                logger.debug(mod_tides.index)

                # reindex to handle absence of tides for the remainder of the last forecast
                mod_tides = mod_tides.reindex(t_index)
                
                mod_data.loc[:, c] -= mod_tides.loc[mod_data[constants.COLNAME_TIME]].values
                member_id_to_mod_tides[c] = mod_tides

                # filtering
                if config.mod_do_filtering:
                    mod_to_filter = mod_to_filter.reindex(t_index)
                    member_id_to_mod_tides[c] += mod_to_filter  # attribute whatever is filtered to tides !!
                    mod_data.loc[:, c] -= mod_to_filter.loc[mod_data[constants.COLNAME_TIME]].values

                
                # diags for detiding
                if config.plot_detiding_diag:
                    msg = f"plotting timeseries for mod at {s.station_id}"
                    logging.info(msg)

                    plot_ts_and_spectre(hourly_series=mod_data_twl[c]
                                                      - mod_data_twl[c].mean() - mod_tides.loc[mod_data_twl.index]
                                                      - mod_to_filter.loc[mod_data_twl.index],
                                        data_label="mod_{}_{}".format(config.label, s.station_id),
                                        img_dir=config.out_dir,
                                        subplot_titles=None,
                                        raw_data=mod_data_twl[c] - mod_data_twl[c].mean(),
                                        tides=mod_tides.asfreq("1H"),
                                        sup_title=config.label.upper() + f": {s.name} ({s.station_id})")

                    logger.debug("\n mod_tides: \n %s \n", mod_tides.head())
                    logger.debug("\n mod_data: \n %s \n", mod_data.head())
                    logger.debug("\n mod_to_filter: \n %s \n", mod_to_filter.head())

                    if mod_ttide_con is not None:
                        mod_ttide_con.classic_style(to_file=str(config.out_dir / f"{s.station_id}_mod_tides.csv"))

        #  debugging
        logger.debug(
            "obs time which is not in mod_data[time]: %s",
            obs_data.index.difference(mod_data[constants.COLNAME_TIME])
        )

        # align model and observation timeseries in time

        logger.debug("(obs) before reindex: \n %s \n", obs_data.head())

        obs_data = obs_data.reindex(pd.to_datetime(obs_data.index.union(mod_data[constants.COLNAME_TIME].drop_duplicates())))
        logger.debug("\n === obs_data.index === \n, %s", obs_data.index)
        logger.debug("\n === mod_data[time] === \n, %s", mod_data[constants.COLNAME_TIME].drop_duplicates())

        # interpolation in case model data is not in obs data time at all
        obs_data = obs_data.interpolate(method="time", limit=2, limit_direction="backward")

        logger.debug("(obs) after reindex: \n %s \n", obs_data.head())

        mod_data.loc[:, f"{s.station_id}_obs"] = obs_data[mod_data[constants.COLNAME_TIME]].values.squeeze()

        logger.info(f"mod_data types: \n %s \n", mod_data.dtypes)

        # obs data to be saved
        obs_sql_data = obs_data.copy().to_frame(name="obs")

        logger.info("\n obs_sql_data \n %s \n", obs_sql_data.head())

        obs_sql_data.reset_index(inplace=True)
        if len(obs_sql_data) > 0:
            obs_sql_data.loc[:, constants.COLNAME_TIME] = s.station_id

        # forecast start dates based on run_freq_hours
        origin_dates_of_interest = mod.get_list_of_origin_dates(mod_data,
                                                                run_freq_dt=timedelta(hours=config.run_freq_hours))

        if not config.keep_nan:
            logger.debug("mod_data (before dropna): \n %s \n", mod_data[mod_member_keys[0]].head())
            mod_data.dropna(inplace=True)
            logger.debug("mod_data (after dropna): \n %s \n", mod_data[mod_member_keys[0]].head())
            logger.debug("mod_data (after dropna): \n %s \n", mod_data[mod_member_keys[0]].describe())

        # remove analysis period mean from the mod and obs
        if config.remove_anal_period_mean and len(mod_data) > 0:
            mod_data = mod.remove_analysis_period_mean(mod_data, station=s,
                                                       mod_member_keys=mod_member_keys, config=config)

        # select only runs run_freq_hours apart (usually it is 36h)
        mod_data = mod_data.loc[mod_data[constants.COLNAME_TORIGIN].isin(origin_dates_of_interest), :]

        # debias
        if external_debias_groups_by_station is not None:
            deb_data = external_debias_groups_by_station.get_group(s.station_id)
            mod.debias(mod_data, deb_data,
                       avg_period=timedelta(hours=config.mod_external_debias_avg_nhours),
                       mod_member_keys=mod_member_keys)

        rmse = np.linalg.norm(
            mod_data[f"{s.station_id}_obs"] - mod_data.loc[:, mod_member_keys].mean(axis=1)) / (len(mod_data)) ** 0.5
        logger.debug(f"rmse({s.station_id})={rmse}")
        logger.debug(f"{s.station_id}: found {len(mod_data[s.station_id + '_obs'])} corresponding data values")
        logger.debug(f"Resulting dataframe:\n{mod_data.head()}")

        if config.output_txt:
            with config.out_file.open("a") as fout:
                for row_index, row in mod_data.iterrows():
                    line = out_line_format.format(
                        row[constants.COLNAME_VALID_HOUR],
                        s.station_id,
                        s.latitude, s.longitude,
                        row[constants.COLNAME_TIME].strftime(constants.OUT_TIME_FORMAT),
                        row[f"{s.station_id}_obs"], *[row[k] for k in mod_member_keys]
                    )
                    fout.write(line)

            # write tides in a separate file
            if len(member_id_to_mod_tides) > 0:

                with tides_file.open("a") as fout:
                    # assuming all the members have the same index
                    t_arr = member_id_to_mod_tides[mod_member_keys[0]].index
                    for t in t_arr:
                        line = out_line_format.format(
                            0,
                            s.station_id,
                            s.latitude, s.longitude,
                            t.strftime(constants.OUT_TIME_FORMAT),
                            -1.0,  # TODO: put observed tides in here
                            *[member_id_to_mod_tides[k][t] for k in mod_member_keys]
                        )
                        fout.write(line)

        if config.output_sqlite:
            mod_sql_data = mod.prepare_mod_sql_data(mod_data, mod_member_keys, stn=s)

            logger.info(f"mod_sql_data types: \n %s \n", mod_sql_data.dtypes)

            conn = sqlite3.connect(config.out_file_sqlite)
            mod_sql_data.to_sql(name="data", con=conn, index=False, if_exists="append")
            obs_sql_data.to_sql(name="obs", con=conn, index=False, if_exists="append")

    if config.output_sqlite:
        conn.close()

    logger.info(f"Finished processing {config_path} .")
    logger.info(f"Output file: {config.out_file} .")
    return obs.get_stid_to_stname_map(stations)


if __name__ == '__main__':
    logger = log_utils.get_logger(__name__)
    # main_levelling_v01()
    import time

    t0 = time.perf_counter()
    main_pn_vs_p0()
    logger.info(f"Execution time: {time.perf_counter() - t0}")
