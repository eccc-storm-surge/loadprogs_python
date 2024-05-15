import configparser
import logging

from argparse import Namespace
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np

import pytz

from .config_interpolation import ExtendedEnvInterpolation
from .constants import OptionNames
from . import constants

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


MIN_NHOURS_FOR_DETIDING_DEFAULT = 2160

NOTEXISTING_PATH = "__does_not_exist__"


def parse_config_settings(config_path, cfg_overrides: dict = None):
    logger.info(f"Processing {config_path} ...")

    if config_path is None:
        config_path = Path("configs/gem5_research_cycle/rdsps_pseudo-analysis_experimental.cfg")

    _config = Namespace()

    cparser = configparser.ConfigParser(inline_comment_prefixes=("#", ";"),
                                        interpolation=ExtendedEnvInterpolation())
    cparser.read(config_path)

    mod_config = cparser["mod"]
    obs_config = cparser["obs"]
    misc_config = cparser["misc"]

    # for when the dates from the config are not used
    dummy_date = "1900010100"

    # --------------------------------------------
    # Model configurations
    # --------------------------------------------
    
    _config.beg_time_mod = datetime.strptime(
        mod_config.get(OptionNames.mod.MOD_BEG_DATE, fallback=dummy_date), "%Y%m%d%H").replace(tzinfo=pytz.utc)

    _config.end_time_mod = datetime.strptime(
        mod_config.get(OptionNames.mod.MOD_END_DATE, fallback=dummy_date), "%Y%m%d%H").replace(tzinfo=pytz.utc)

    assert _config.end_time_mod >= _config.beg_time_mod, \
            f"{OptionNames.mod.MOD_BEG_DATE} should be less or equal than {OptionNames.mod.MOD_END_DATE}"

    _config.mod_dir = Path(mod_config[OptionNames.mod.DATA_DIR]).expanduser()

    _config.b2b_max_lead_hours = mod_config.getint(OptionNames.mod.B2B_MAX_LEAD_HOUR)

    _config.b2b_blend_hours = mod_config.getint(OptionNames.mod.B2B_BLEND_HOURS, fallback=0) # blending period when stitching forecasts
    _config.run_freq_hours = mod_config.getint(OptionNames.mod.RUN_FREQ_HOURS)
    
    _config.dt_texp_from_tbeg = timedelta(
        seconds=int(mod_config.getfloat(OptionNames.mod.DT_TEXP_TBEG, fallback=0) * 3600))

    # msg = f"""back to back frequency should be less or equal to run_freq_hours,
    #           but got {_config.b2b_freq_hours} and {_config.run_freq_hours}, respectively"""
    # assert _config.b2b_freq_hours <= _config.run_freq_hours, msg

    _config.mod_nomvar = mod_config.get(OptionNames.mod.NOMVAR, fallback="ETAS")
    _config.mod_typvar = mod_config.get(OptionNames.mod.TYPVAR, fallback="P@")
    # select any typvar
    if _config.mod_typvar.strip() == "*":
        _config.mod_typvar = " "

    # mod detiding options
    _config.detide_mod = mod_config.getboolean(OptionNames.mod.DETIDE, fallback=False)
    _config.detide_mod_constituents = mod_config.get(OptionNames.mod.DETIDE_CONSTITUENTS, fallback=None)

    if _config.detide_mod_constituents is not None:
        _config.detide_mod_constituents = [tok.strip() for tok in _config.detide_mod_constituents.split(",")]

    # minimum tide frequency to consider when detiding
    _config.mod_detide_min_tide_frequency_hz = mod_config.getfloat(
        OptionNames.common.DETIDE_MIN_TIDE_FREQ_HZ, fallback=-np.Inf)
    _config.mod_detide_rayleigh = mod_config.getfloat(
        OptionNames.common.DETIDE_RAYLEIGH, fallback=constants.DEFAULT_DETIDE_RAYLEIGH
    )


    _config.mod_do_filtering = mod_config.getboolean(OptionNames.mod.DETIDE_FILTERING, fallback=False)

    _config.n_members = mod_config.getint(OptionNames.mod.N_MEMBERS, fallback=0)

    # typos and backward compatibility
    if "nmembers" in mod_config:
        _config.n_members = mod_config.getint("nmembers", fallback=0)

    _config.min_nhours_for_detiding_mod = mod_config.getint(OptionNames.mod.MIN_NHOURS_FOR_DETIDING,
                                                            fallback=MIN_NHOURS_FOR_DETIDING_DEFAULT)

    _config.mod_external_tides = Path(mod_config.get(OptionNames.mod.EXTERNAL_TIDES, fallback=NOTEXISTING_PATH))

    if _config.mod_external_tides.name != NOTEXISTING_PATH:
        assert _config.mod_external_tides.exists(), f"{_config.mod_external_tides} should exist!"

    _config.mod_external_debias = Path(mod_config.get(OptionNames.mod.EXTERNAL_DEBIAS, fallback=NOTEXISTING_PATH))

    if _config.mod_external_debias.name != NOTEXISTING_PATH:
        assert _config.mod_external_debias.exists(), f"{_config.mod_external_debias} should exist!"



    # debias using the following formula:
    # FC = FC - mean(PA-Obs), (the mean is over avg_nhours, before the forecast start)
    _config.mod_external_debias_avg_nhours = mod_config.getint(OptionNames.mod.EXTERNAL_DEBIAS_AVG_NHOURS, fallback=5 * 24)

    # number of processes used for reading model data
    _config.mod_read_nprocs = mod_config.getint(OptionNames.mod.READ_NPROCS, fallback=1)

    # minimum lead hour to consider (lead hours less than this will be discarded)
    _config.b2b_min_lead_hour = mod_config.getint(OptionNames.mod.B2B_MIN_LEAD_HOUR, fallback=0)


    # sqlite file containing reference shifts subtracted from model data
    _config.mod_ref_shift_path = mod_config.get(OptionNames.mod.REF_SHIFT_PATH, fallback=NOTEXISTING_PATH)
    _config.mod_ref_shift_path = Path(_config.mod_ref_shift_path).expanduser()
    if _config.mod_ref_shift_path.name != NOTEXISTING_PATH:
        assert _config.mod_ref_shift_path.exists(), f"Could not find {_config.mod_ref_shift_path}"
        _config.mod_ref_shift_key_field = mod_config.get(OptionNames.mod.REF_SHIFT_KEY_FIELD, fallback="StnId")
        _config.mod_ref_shift_val_field = mod_config.get(OptionNames.mod.REF_SHIFT_VAL_FIELD, fallback="mwl2cd")

    # window size in hours for the rolling mean
    _config.mod_apply_rolling_mean_hours = mod_config.getint(OptionNames.mod.APPLY_ROLLING_MEAN_HOURS, 0)

    # --------------------------------------------

    # --------------------------------------------
    # Observation configurations
    # --------------------------------------------
    _config.obs_datatype = obs_config.get(OptionNames.obs.OBS_DATATYPE, fallback="txt")

    _config.beg_time_obs = None
    if OptionNames.obs.OBS_BEG_DATE in obs_config:
        _config.beg_time_obs = datetime.strptime(
            obs_config[OptionNames.obs.OBS_BEG_DATE], "%Y%m%d%H").replace(tzinfo=timezone.utc)
    
    _config.end_time_obs = None
    if OptionNames.obs.OBS_END_DATE in obs_config:
        _config.end_time_obs = datetime.strptime(
            obs_config[OptionNames.obs.OBS_END_DATE], "%Y%m%d%H").replace(tzinfo=timezone.utc)

    if None not in [_config.beg_time_obs, _config.end_time_obs]:
        if _config.beg_time_obs >= _config.end_time_obs:
            msg = f"""
                    ERROR, Configuration problem:
                    Expect start date to be before the end date, but got:
                        {OptionNames.obs.OBS_BEG_DATE} = {_config.beg_time_obs}
                        {OptionNames.obs.OBS_END_DATE} = {_config.end_time_obs}
                   """
            raise ValueError(msg)


    _config.station_info = Path(obs_config["station_info"]).expanduser()
    _config.obs_dir = Path(obs_config["obs_dir"]).expanduser()
    _config.transpose_mod_indices = obs_config.getboolean("obs_transpose_mod_indices", fallback=False)

    if _config.obs_datatype in ["sqlite", "canhys"]:
        _config.translator_path = Path(obs_config.get("canhys_station_id_translation_dict"))
        _config.translator_path = _config.translator_path.expanduser()
        
        # comma-separated list of variable ids for the canhys db
        _config.variable_id = obs_config.get(OptionNames.obs.OBS_VARIABLE_ID, fallback="100") # 100 - water lev, 200 - streamflow , 300- temperature


    # obs detiding options
    _config.detide_obs = obs_config.getboolean("detide_obs", fallback=False)

    _config.detide_obs_constituents = obs_config.get("detide_obs_constituents", fallback=None)
    if _config.detide_obs_constituents is not None:
        _config.detide_obs_constituents = [tok.strip() for tok in _config.detide_obs_constituents.split(",")]
    
    _config.min_nhours_for_detiding_obs = obs_config.getint("min_nhours_for_detiding",
                                                            fallback=MIN_NHOURS_FOR_DETIDING_DEFAULT)

    # minimum tide frequency to consider when detiding
    _config.obs_detide_min_tide_frequency_hz = obs_config.getfloat(
        OptionNames.common.DETIDE_MIN_TIDE_FREQ_HZ, fallback=-np.Inf)
    
    _config.obs_detide_rayleigh = obs_config.getfloat(
        OptionNames.common.DETIDE_RAYLEIGH, fallback=constants.DEFAULT_DETIDE_RAYLEIGH
    )

    _config.obs_do_filtering = obs_config.getboolean("detide_obs_filtering", fallback=False)
    _config.obs_do_qc = obs_config.getboolean(OptionNames.obs.OBS_PERFORM_QC, fallback=False)

    # window size in hours for the rolling mean
    _config.obs_apply_rolling_mean_hours = obs_config.getint(OptionNames.obs.APPLY_ROLLING_MEAN_HOURS, 0)


    # --------------------------------------------

    # --------------------------------------------
    # Miscellaneous configurations
    # --------------------------------------------
    _config.label = misc_config.get("label", fallback="")

    _config.out_dir = Path(misc_config.get("prepared_for_scoring_dir", fallback=".")).expanduser()
    _config.out_file = _config.out_dir / ("surge_" + _config.label + ".dat")
    _config.output_txt = misc_config.getboolean("output_txt", fallback=True)

    # allow either output_sql or output_sqlite parameter names, means the same thing
    _config.output_sqlite = misc_config.getboolean("output_sql", fallback=False)
    _config.output_sqlite = misc_config.getboolean("output_sqlite", fallback=_config.output_sqlite)
    if _config.output_sqlite:
        _config.out_file_sqlite = _config.out_dir / (_config.out_file.name[:-4] + ".sqlite")

    _config.plot_detiding_diag = misc_config.getboolean("plot_detiding_diag", fallback=True)

    # for backward compatibility
    if "remove_anal_period_mean" in misc_config:
        _config.remove_analysis_period_mean = misc_config.getboolean("remove_anal_period_mean", fallback=True)
    else:
        _config.remove_analysis_period_mean = misc_config.getboolean(OptionNames.misc.REMOVE_ANALYSIS_PERIOD_MEAN, fallback=True)

    # check if b2b_max_lead_hour is set
    if _config.remove_analysis_period_mean:
        if _config.b2b_max_lead_hours is None:
            msg = f"""{OptionNames.mod.B2B_MAX_LEAD_HOUR} not found in {config_path}
                  (it was renamed from b2b_freq_hours, please update your configs) 
                  """
            logger.error(msg)
            raise ValueError(msg)
    
    # wether to sort outputs
    _config.sort_output = misc_config.getboolean(OptionNames.misc.SORT_OUTPUT, fallback=False)

    _config.keep_nan = misc_config.getboolean("keep_nan", fallback=False)

    # --------------------------------------------

    # apply overrides if provided
    cfg_overrides = dict() if cfg_overrides is None else cfg_overrides
    _config.__dict__.update(cfg_overrides)

    return _config


if __name__ == "__main__":
    import time

    t0 = time.perf_counter()

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # debug code for running module directly
    cfg = parse_config_settings(config_path=Path(
        "configs/rdsps/migration_2019_par/rdsps_fc_ops_160_test.cfg"))
    print(cfg)
    print(f"Execution time: {time.perf_counter() - t0} seconds.")
