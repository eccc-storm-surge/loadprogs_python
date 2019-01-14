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
from _datetime import datetime, timezone
from pathlib import Path
from data import obs
from data import mod
from util.plot_ts_and_spectre import plot_ts_and_spectre


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


def main(config_path: Path=None):
    if config_path is None:
        config_path = Path("configs/gem5_research_cycle/rdsps_pseudo-analysis_experimental.cfg")

    config = configparser.ConfigParser(inline_comment_prefixes=("#", ";"),
                                       interpolation=configparser.ExtendedInterpolation())
    config_data = "[top]\n" + config_path.open().read()
    config.read_string(config_data)
    config = config["top"]

    beg_time = datetime.strptime(config["datestart"], "%Y%m%d%H").replace(tzinfo=timezone.utc)
    end_time = datetime.strptime(config["dateend"], "%Y%m%d%H").replace(tzinfo=timezone.utc)
    n_members = int(config["nmembers"])

    out_dir = Path(config["prepared_for_scoring_dir"])
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / ("surge_" + config["label"] + ".dat")

    date_format = "%Y%m%d%H"

    plot_detiding_diag = True
    if "plot_detiding_diag" in config:
        plot_detiding_diag = config["plot_detiding_diag"].strip() != "0"

    # valid_hour, station id, lat, lon, date of validity, obs value, mod value 1, ..., mod value n
    out_line_format = "{:5d} {:<7} {:.7f} {:.7f} {:<10} {:.7f}" + " {:.7f}" * n_members + "\n"

    member_ids = ["{:03d}".format(i) for i in range(n_members)] if n_members > 1 else [""]

    for k, v in config.items():
        print(f"{k} => {v}, ({type(v)})")

    # Load obs and do de-tiding (the list of stations is from the .obs file)
    stations = obs.load_station_data_from_dir(Path(config["obs_dir"]), config["station_info"])

    # Load mod corresponding to obs and take out time avg (the model data is loaded from rpn files)
    station_to_model_grid_map = mod.map_stations_to_grid_indices(stations, config["station_info"])
    model_points = mod.get_mod_timeseries(stations, Path(config["mod_dir"]),
                                          station_id_to_grid_indices=station_to_model_grid_map,
                                          start_time=beg_time,
                                          end_time=end_time)

    with out_file.open("w") as fout:
        # Dump corresponding obs and mod data into a file for scoring
        for s in stations:
            mod_data = model_points.copy()

            obs_data = s.get_detided_series(do_filtering=True)

            # take into account some obs that might have
            # 30 minutes in their time stamps not 00 (i.e NL)
            obs_data = obs_data.asfreq("30T").fillna(method="ffill", limit=1)

            # remove the mean over the current period from the data (to be more consistent with mod)
            obs_data -= obs_data.mean(skipna=True, axis=0)

            # deprecated
            # mod_data[f"{s.station_id}_obs"] = obs_data[mod_data["time"]].values
            obs_data = obs_data.reindex(mod_data["time"])
            mod_data[f"{s.station_id}_obs"] = obs_data[mod_data["time"]].values

            #  diags for detiding
            if plot_detiding_diag:
                plot_ts_and_spectre(obs_data, config["label"],
                                    img_dir=out_dir,
                                    subplot_titles=None,
                                    raw_data=s.data["twl-mean"],
                                    tides=s.data["tides"])

            mod_data.dropna(inplace=True)

            print(f"{s.station_id}: found {len(mod_data[s.station_id + '_obs'])} corresponding data values")

            for row_index, row in mod_data.iterrows():
                line = out_line_format.format(
                    int(row["valid_hour"]),
                    s.station_id,
                    s.latitude, s.longitude,
                    row["time"].strftime(date_format),
                    row[f"{s.station_id}_obs"], *[row[(s.station_id, member_id)] for member_id in member_ids]  # extend for ensembles
                )
                fout.write(line)


if __name__ == '__main__':
    # main_levelling_v01()
    main_pn_vs_p0()