

from pathlib import Path
from loadprogs.main.main import main as loadprogs_main
from loadprogs.util.constants import OptionNames
import pandas as pd
import pytz

import argparse


def read_cmd_args():
    parser = argparse.ArgumentParser(description="subjective evaluation 2025/09")

    
    parser.add_argument("--date", type=lambda tok: pd.to_datetime(tok, format=r"%Y%m%d", utc=True),
                        help=r"run date (when the loadprogs is run), in format %Y%m%d",
                        default=pd.Timestamp.now(tz=pytz.utc))

    parser.add_argument("--delay-days", type=lambda tok: pd.Timedelta(days=int(tok)),
                        default=pd.Timedelta(days=0),
                        help="delay in days into the past to select model outputs and obs. If n, look for n days before --date")
    
    parser.add_argument("--test-run", action="store_true",
                        help="uses TEST_HUB to store results")

    return parser.parse_args()


def main():
    """
    Select data for subjective evaluation of GESPS against RESPS
    use one year back of obs data to level.
    """
    
    args = read_cmd_args()
    TEST_HUB = None
    if args.test_run:
        TEST_HUB = Path("data/se-GESPS-RESPS-202509")
    

    # 
    exp_duration = pd.Timedelta(days=16)
    exp_hour_list = [0, 12] 
    obs_duration = pd.Timedelta(days=365) 

    exp_date = args.date - args.delay_days

    common_opts = {
        OptionNames.obs.OBS_DIR: Path("~swav000/data/ppp5/rarc/CANHYS"),
        OptionNames.obs.CANHYS_ID_TRANSLATION_DICT: Path("/fs/ssm/eccc/cmd/cmda/ade/external/canhys/1.4.1/cfg/stn.txt"),
    }

    system_to_opts = {
        "RESPS": {
            OptionNames.obs.STATION_INFO: Path("/home/swav000/projets/se-GESPS-RESPS-202509/resps/stations_obs_ATL_1_12.obs"),
            OptionNames.misc.OUTPUT_TXT: False,
            OptionNames.misc.OUTPUT_SQLITE: True,
            OptionNames.mod.DATA_DIR: Path("~swav000/data/ppp5/rarc/RESPS/operation.forecasts.resps"),
            OptionNames.mod.NOMVAR: "SSH"

        },
        "GESPS": {
            OptionNames.obs.STATION_INFO: Path("/home/olh001/Python/obs_to_grid_mapping/gesps/usr-grid/gesps-usr-grid_CanUS.obs"),
            OptionNames.misc.OUTPUT_TXT: False,
            OptionNames.misc.OUTPUT_SQLITE: True,
            OptionNames.mod.DATA_DIR: Path("~swav000/data/ppp5/rarc/GESPS/parallel.forecasts.gesps.usr"),
            OptionNames.mod.NOMVAR: "SSH",
            OptionNames.mod.MOD_IP1: 66060288
        }
    }

    system_to_cfg_path = {
        "RESPS": Path("/home/swav000/projets/se-GESPS-RESPS-202509/resps/twl.cfg"),
        "GESPS": Path("/home/swav000/projets/se-GESPS-RESPS-202509/gesps/twl.cfg")
    }


    for run_hour in exp_hour_list:
        
        exp_time = exp_date + pd.Timedelta(hours=run_hour)

        common_opts.update({
            OptionNames.mod.MOD_BEG_DATE: exp_time,
            OptionNames.mod.MOD_END_DATE: exp_time,
            OptionNames.obs.OBS_END_DATE: exp_time + exp_duration,
            OptionNames.obs.OBS_BEG_DATE: exp_time + exp_duration - obs_duration,
        })

        for label, overrides in system_to_opts.items():
            cfg = system_to_cfg_path[label]
            overrides.update(common_opts)

            if TEST_HUB is not None:
                out_dir = TEST_HUB / label 
            else:
                out_dir = cfg.parent / "data"

            out_dir.mkdir(exist_ok=True, parents=True)

            # create data link near the .cfg files
            overrides[OptionNames.misc.OUT_FILE_SQLITE] = out_dir / f"{exp_time:%Y%m%d%H}.sqlite"
            overrides[OptionNames.misc.OUT_DIR] = out_dir
            overrides[OptionNames.misc.LABEL] = label

            loadprogs_main(config_path=cfg, cfg_overrides=overrides, force=True)

    # cleanup
    # for system_id, opts in system_to_opts.items():
    #     data_dir = Path(opts[OptionNames.mod.DATA_DIR]).expanduser()
    #     print(f"cleanup {data_dir = } for {system_id = } and {exp_date = }")
    #     for f in data_dir.glob(f"{exp_date:%Y%m%d}*"):
    #         print(f"to remove: {f}")


      
    

if __name__ == "__main__":
    main()
