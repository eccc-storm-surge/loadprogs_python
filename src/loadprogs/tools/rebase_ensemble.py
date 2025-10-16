

"""
Rebase ensemle using the control from the .dat and spred from folder of std files

"""
from pathlib import Path
from loadprogs.data import mod, obs

import pandas as pd
import numpy as np
import csv
from loadprogs.util import constants


def main():
    nprocs = 3
    n_members = 21

    t_beg = pd.Timestamp("2021-10-27 00:00:00").tz_localize("UTC")
    t_end = pd.Timestamp("2022-05-31 00:00:00").tz_localize("UTC")
    run_freq_hours = 36
    # base_dat_pth = Path("/home/olh001/Python/loadprogs_python_experiments/data/ci4/gesps/final-cycles/regional/data_for_scoring_gesps_prog_surge_new_v2_2021102700_2022061400-leveled/surge_gesps_prog_surge_new_v2.dat")
    base_dat_pth = Path("/home/olh001/Python/loadprogs_python_experiments/data/ci4/gesps/final-cycles/regional/data_for_scoring_gesps_prog_surge_new_v2_2021102700_2022061400/surge_gesps_prog_surge_new_v2.dat")
    base_dat_sep = ","
    rebase_cache_dir = base_dat_pth.parent / "rebase_cache"

    mod_dir = Path("/home/pat003/data/ppp6/maestro_archives_surgever/gesps_v001_final_cycles_V2_filtered/gridpt/filtered/")
    mod_nomvar = "ETAS"
    mod_typvar = "P@"
    ctrl_member = "000"

    obs_transpos_obs_indices = 0
    stinfo_pth = Path("/home/olh001/Python/obs_to_grid_mapping/gesps/gesps_east-coast-domain.obs")


    # Load mod corresponding to obs and take out time avg (the model data is loaded from rpn files)
    station_meta = obs.read_station_metadata(stinfo_pth)

    if obs_transpos_obs_indices == 0:
        indices = zip(station_meta["DATA.I"] - 1, station_meta["DATA.J"] - 1)
    else:
        indices = zip(station_meta["DATA.J"] - 1, station_meta["DATA.I"] - 1)
    
    station_meta = dict(zip(station_meta["NO"], indices))

    # Load the model data
    mod_data_ctrl = mod.get_mod_timeseries_field(
        mod_dir, mod_nomvar=mod_nomvar, mod_typvar=mod_typvar, 
        start_time=t_beg, end_time=t_end, run_freq_hours=run_freq_hours,
        member_ids=(ctrl_member, ), nprocs=nprocs, station_id_to_grid_indices=station_meta, 
        cache_dir=rebase_cache_dir)


    print("time")
    print(f"{mod_data_ctrl['time']}")
    
    print("station_id")
    print(f"{mod_data_ctrl['station_id']}")

    index_levels = ["time", "valid_hour", "station_id"]

    mod_data_ctrl = mod_data_ctrl.set_index(index_levels)

    
    for stid in mod_data_ctrl.index.get_level_values("station_id").unique():
        query = f" valid_hour >= 0 and  valid_hour < {run_freq_hours} and  '{stid}' == station_id"

        print(f"{ mod_data_ctrl.query(query)['mod_000'] = }")
        print(f"{ mod_data_ctrl.query(query)['mod_000'].mean() = }")

        mod_data_ctrl.loc[(slice(None), slice(None), stid), "mod_000"] -= mod_data_ctrl.query(query)["mod_000"].mean()
        print(f"{stid = }")
        print(f"{ mod_data_ctrl.query(query)['mod_000'].mean() = }")
    


    print(f"{mod_data_ctrl.index = }")
    out_dat_pth = base_dat_pth.parent / f"{base_dat_pth.stem}_rebased{base_dat_pth.suffix}"
    out_dat_pth.unlink(missing_ok=True)

    base_dat = pd.read_csv(base_dat_pth, sep=base_dat_sep, header=None, converters={4: str, 1:str})
    base_dat[4] = pd.to_datetime(base_dat[4], format=r"%Y%m%d%H%M", utc=True)


    colnames = {0: "valid_hour", 
                1: "station_id", 
                4: "time", 
                5: "obs"}
    
    colnames.update({i + 6: f"mod_{i:03d}" for i in range(n_members)})

    base_dat.rename(columns=colnames, inplace=True)

    column_order = base_dat.columns.copy()

    base_dat = base_dat.set_index(index_levels)

    print(f"{base_dat.index = }")

    # base[mod_i] = base[mod_000] + (base[mod_i] - ctrl[mod_000])
    sel_rows = base_dat.index.intersection(mod_data_ctrl.index)

    print(f"{sel_rows = }")

    for i in range(1, n_members):
        colname = f"mod_{i:03d}"
        base_dat.loc[sel_rows, colname] = base_dat.loc[sel_rows, "mod_000"] + (base_dat.loc[sel_rows, colname] - mod_data_ctrl.loc[sel_rows, "mod_000"])

    base_dat.reset_index()[column_order].to_csv(out_dat_pth, 
                                                float_format="%.7f",
                                                date_format=constants.OUT_TIME_FORMAT,
                                                na_rep=str(np.nan),
                                                index=False, header=False, 
                                                quoting=csv.QUOTE_NONE)



if __name__ == "__main__":
    main()
