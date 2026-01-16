import configparser
import logging

from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

import pytz

from loadprogs.util.config_interpolation import ExtendedEnvInterpolation
from loadprogs.util.constants import OptionNames
from loadprogs.util import constants

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


MIN_NHOURS_FOR_DETIDING_DEFAULT = 2160

# NOTEXISTING_PATH = "__does_not_exist__"

"""
Options priority: 
    overrides dict > config files > fallback defaults
"""


class BaseConv(object):
    def __init__(self, cfg_section: configparser.SectionProxy, cfg_overrides: dict | None = None):
        """ 
        Args:       
            cfg_section (configparser.SectionProxy): source data section
            opt_name (str): option name
            get_method (str): method name of  configparser.SectionProxy for getting option value
                get[default], getint, getfloat, getboolean
            fallback (_type_, optional): _description_. Defaults to None.
        """
        self.cfg_section: configparser.SectionProxy = cfg_section
        self.cfg_overrides: dict = cfg_overrides if cfg_overrides is not None else dict()
        

    def conv(self, opt_name: str, fallback=None, get_method="get", required=True):
        """ 
        raw string, assert that the option value is available.

        Returns:
            str: option value
        """
        if opt_name in self.cfg_overrides:
            return self.cfg_overrides[opt_name]
        
        value = getattr(self.cfg_section, get_method)(opt_name, fallback=fallback)
        if required:
            assert value is not None, f"{opt_name} is not set in the configs (section: {self.cfg_section.name}) and default is not provided"
        return value

    # alias for conv method
    get = conv    

    def time(self, opt_name: str, fallback=None, required=True) -> datetime:
        """
        Get datetime option

        Args:
            opt_name (str): option name
            fallback (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        tok = self.conv(opt_name, fallback=fallback, required=required)

        if not required and tok is None:
            return tok

        if isinstance(tok, datetime):
            return tok

        return datetime.strptime(tok, r"%Y%m%d%H").replace(tzinfo=pytz.utc)

    def path(self, opt_name, fallback=None, missing_ok: bool = True, required=True) -> Path:
        tok = self.conv(opt_name, fallback=fallback, required=required)

        if not required and tok is None:
            return tok

        p = tok
        # in case we get it from overrides as path object
        if not isinstance(p, Path):
            p = Path(tok)
            
        p = p.expanduser()

        if not missing_ok:
            assert p.exists(), f"Does not exist {p}"
        return p

    def bool(self, opt_name, fallback=None, required=True) -> bool:
        return self.conv(opt_name, fallback=fallback, get_method="getboolean", required=required)
        
        
    def int(self, opt_name, fallback=None, required=True) -> int:
        return self.conv(opt_name, fallback=fallback, get_method="getint", required=required)

    def float(self, opt_name, fallback=None, required=True) -> float:
        return self.conv(opt_name, fallback=fallback, get_method="getfloat", required=required)
    
    def list(self, opt_name, fallback=None, required=True, sep=",", prefix="") -> list:
        """list of options

        Args:
            opt_name (str): _description_
            fallback (typing.Any, optional): _description_. Defaults to None.
            required (bool, optional): _description_. Defaults to True.
            sep (str, optional): _description_. Defaults to ",".
            prefix (str, optional): _description_. Defaults to "".

        Returns:
            list: _description_
        """
        tok = self.conv(opt_name, fallback=fallback, required=required)
        
        if not required and tok is None:
            return tok
        
        return [f"{prefix}{s.strip()}" for s in tok.split(sep)]




def parse_config_settings(config_path, cfg_overrides: dict | None = None) -> Namespace:
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

    if cfg_overrides is None:
        cfg_overrides = dict()


    # --------------------------------------------
    # Model configurations
    # --------------------------------------------
    m = BaseConv(mod_config, cfg_overrides)
    _config.beg_time_mod = m.time(OptionNames.mod.MOD_BEG_DATE)
    _config.end_time_mod = m.time(OptionNames.mod.MOD_END_DATE)

    assert _config.end_time_mod >= _config.beg_time_mod, \
            f"{OptionNames.mod.MOD_BEG_DATE} should be less or equal than {OptionNames.mod.MOD_END_DATE}"
    
    _config.mod_dir = m.path(OptionNames.mod.DATA_DIR, missing_ok=False)
    _config.b2b_max_lead_hours = m.int(OptionNames.mod.B2B_MAX_LEAD_HOUR)

    _config.b2b_blend_hours = m.int(OptionNames.mod.B2B_BLEND_HOURS, fallback=0) # blending period when stitching forecasts
    _config.run_freq_hours = m.int(OptionNames.mod.RUN_FREQ_HOURS)
    
    _config.dt_texp_from_tbeg = timedelta(
        seconds=int(m.float(OptionNames.mod.DT_TEXP_TBEG, fallback=0) * 3600))

    # msg = f"""back to back frequency should be less or equal to run_freq_hours,
    #           but got {_config.b2b_freq_hours} and {_config.run_freq_hours}, respectively"""
    # assert _config.b2b_freq_hours <= _config.run_freq_hours, msg

    _config.mod_nomvar = m.get(OptionNames.mod.NOMVAR, fallback="ETAS")
    _config.mod_typvar = m.get(OptionNames.mod.TYPVAR, fallback="P@")
    _config.mod_ip1 = m.int(OptionNames.mod.MOD_IP1, fallback=-1)

    # select any typvar
    if _config.mod_typvar.strip() == "*":
        _config.mod_typvar = " "

    # the form of model data
    # if point_txt - then 1 text file contains all timeseries data identified by the station id
    # if field the data should be 2d and either in standard or netcdf files.
    _config.mod_datatype = m.get(OptionNames.mod.MOD_DATATYPE, fallback="field")

    # Path to the directory containing cached model data
    _config.mod_cache_dir = m.path(OptionNames.mod.MOD_CACHE_DIR, missing_ok=True, required=False)
    
    # list of members to be detided
    _config.mod_detide_members = m.list(OptionNames.mod.MOD_DETIDE_MEMBERS, required=False, prefix="mod_")
    

    # mod detiding options
    _config.detide_mod = m.bool(OptionNames.mod.DETIDE, fallback=False)
    
    _config.detide_mod_constituents = m.list(OptionNames.mod.DETIDE_CONSTITUENTS, fallback=None, required=False)
    
    # minimum tide frequency to consider when detiding
    _config.mod_detide_min_tide_frequency_hz = m.float(
        OptionNames.common.DETIDE_MIN_TIDE_FREQ_HZ, fallback=-np.Inf)
    
    _config.mod_detide_rayleigh = m.float(
        OptionNames.common.DETIDE_RAYLEIGH, fallback=constants.DEFAULT_DETIDE_RAYLEIGH
    )


    _config.mod_do_filtering = m.bool(OptionNames.mod.DETIDE_FILTERING, fallback=False)

    _config.n_members = m.int(OptionNames.mod.N_MEMBERS, fallback=0)

    # typos and backward compatibility
    if "nmembers" in mod_config:
        raise ValueError(f"nmembers option name is deprecated, use {OptionNames.mod.N_MEMBERS}")

    _config.min_nhours_for_detiding_mod = m.int(OptionNames.mod.MIN_NHOURS_FOR_DETIDING,
                                                            fallback=MIN_NHOURS_FOR_DETIDING_DEFAULT)

    _config.mod_external_tides = m.path(OptionNames.mod.EXTERNAL_TIDES, 
                                        fallback=None, required=False, missing_ok=False)

    _config.mod_external_debias = m.path(OptionNames.mod.EXTERNAL_DEBIAS, 
                                        fallback=None, required=False, missing_ok=False)

    # flag to output (True) or not (False) tides computed from model time series
    _config.mod_output_tides = m.bool(OptionNames.mod.MOD_OUTPUT_TIDES, fallback=False)

    # debias using the following formula:
    # FC = FC - mean(PA-Obs), (the mean is over avg_nhours, before the forecast start)
    _config.mod_external_debias_avg_nhours = m.int(OptionNames.mod.EXTERNAL_DEBIAS_AVG_NHOURS, fallback=5 * 24)

    # number of processes used for reading model data
    _config.mod_read_nprocs = m.int(OptionNames.mod.READ_NPROCS, fallback=1)

    # minimum lead hour to consider (lead hours less than this will be discarded)
    _config.b2b_min_lead_hour = m.int(OptionNames.mod.B2B_MIN_LEAD_HOUR, fallback=0)


    # sqlite file containing reference shifts subtracted from model data
    _config.mod_ref_shift_path = m.path(OptionNames.mod.REF_SHIFT_PATH, fallback=None,
                                        required=False, missing_ok=False)
    
    if _config.mod_ref_shift_path is not None:
        _config.mod_ref_shift_key_field = m.get(OptionNames.mod.REF_SHIFT_KEY_FIELD, fallback="StnId")
        _config.mod_ref_shift_val_field = m.get(OptionNames.mod.REF_SHIFT_VAL_FIELD, fallback="mwl2cd")

    # window size in hours for the rolling mean
    _config.mod_apply_rolling_mean_hours = m.int(OptionNames.mod.APPLY_ROLLING_MEAN_HOURS, fallback=0)

    # --------------------------------------------

    # --------------------------------------------
    # Observation configurations
    # --------------------------------------------

    o = BaseConv(obs_config, cfg_overrides)

    _config.obs_datatype = o.get(OptionNames.obs.OBS_DATATYPE, fallback="txt")

    # remove mean for the (beg_time_obs-end_time_obs) period
    _config.obs_remove_mean = o.bool(OptionNames.obs.OBS_REMOVE_MEAN, fallback=False)

    _config.beg_time_obs = o.time(OptionNames.obs.OBS_BEG_DATE, fallback=None, required=False)
    _config.end_time_obs = o.time(OptionNames.obs.OBS_END_DATE, fallback=None, required=False)
    
    if None not in [_config.beg_time_obs, _config.end_time_obs]:
        if _config.beg_time_obs >= _config.end_time_obs: # type: ignore
            msg = f"""
                    ERROR, Configuration problem:
                    Expect start date to be before the end date, but got:
                        {OptionNames.obs.OBS_BEG_DATE} = {_config.beg_time_obs}
                        {OptionNames.obs.OBS_END_DATE} = {_config.end_time_obs}
                   """
            raise ValueError(msg)

    _config.station_info = o.path(OptionNames.obs.STATION_INFO)
    _config.obs_dir = o.path(OptionNames.obs.OBS_DIR)
    _config.transpose_mod_indices = o.bool("obs_transpose_mod_indices", fallback=False)

    if _config.obs_datatype in ["sqlite", "canhys"]:
        _config.translator_path = o.path(OptionNames.obs.CANHYS_ID_TRANSLATION_DICT, missing_ok=False)
        
        # comma-separated list of variable ids for the canhys db
        _config.variable_id = o.int(OptionNames.obs.OBS_VARIABLE_ID, fallback=100) # 100 - water lev, 200 - streamflow , 300- temperature


    # obs detiding options
    _config.detide_obs = o.bool("detide_obs", fallback=False)

    _config.detide_obs_constituents = o.list("detide_obs_constituents", fallback=None, required=False)
    
    _config.min_nhours_for_detiding_obs = o.int("min_nhours_for_detiding",
                                                fallback=MIN_NHOURS_FOR_DETIDING_DEFAULT)

    # minimum tide frequency to consider when detiding
    _config.obs_detide_min_tide_frequency_hz = o.float(
        OptionNames.common.DETIDE_MIN_TIDE_FREQ_HZ, fallback=-np.Inf)
    
    _config.obs_detide_rayleigh = o.float(
        OptionNames.common.DETIDE_RAYLEIGH, fallback=constants.DEFAULT_DETIDE_RAYLEIGH
    )

    _config.obs_do_filtering = o.bool("detide_obs_filtering", fallback=False)
    _config.obs_do_qc = o.bool(OptionNames.obs.OBS_PERFORM_QC, fallback=False)

    # window size in hours for the rolling mean
    _config.obs_apply_rolling_mean_hours = o.int(OptionNames.obs.APPLY_ROLLING_MEAN_HOURS, 0)


    # --------------------------------------------

    # --------------------------------------------
    # Miscellaneous configurations
    # --------------------------------------------
    misc = BaseConv(misc_config, cfg_overrides)
    _config.label = misc.get(OptionNames.misc.LABEL, fallback="")

    _config.out_dir = misc.path(OptionNames.misc.OUT_DIR, fallback=Path("."), missing_ok=True)
    out_file_txt = _config.out_dir / ("surge_" + _config.label + ".dat")
    _config.out_file_txt = misc.path(OptionNames.misc.OUT_FILE_TXT, fallback=out_file_txt)
    _config.output_txt = misc.bool(OptionNames.misc.OUTPUT_TXT, fallback=True)

    # allow either output_sql or output_sqlite parameter names, means the same thing
    _config.output_sqlite = misc.bool("output_sql", fallback=False)
    _config.output_sqlite = misc.bool(OptionNames.misc.OUTPUT_SQLITE, fallback=_config.output_sqlite)

    out_file_sqlite = _config.out_dir / (_config.out_file_txt.stem + ".sqlite")
    _config.out_file_sqlite = misc.path(OptionNames.misc.OUT_FILE_SQLITE, fallback=out_file_sqlite, missing_ok=True)
        

    _config.plot_detiding_diag = misc.bool("plot_detiding_diag", fallback=False)

    # for backward compatibility
    if "remove_anal_period_mean" in misc_config:
        raise ValueError(f"remove_anal_period_mean option is deprecated, use {OptionNames.misc.REMOVE_ANALYSIS_PERIOD_MEAN} instead.")
    
    _config.remove_analysis_period_mean = misc.bool(OptionNames.misc.REMOVE_ANALYSIS_PERIOD_MEAN, fallback=True)

    # check if b2b_max_lead_hour is set
    if _config.remove_analysis_period_mean:
        if _config.b2b_max_lead_hours is None:
            msg = f"""{OptionNames.mod.B2B_MAX_LEAD_HOUR} not found in {config_path}
                  (it was renamed from b2b_freq_hours, please update your configs) 
                  """
            logger.error(msg)
            raise ValueError(msg)
    
    # wether to sort outputs
    _config.sort_output = misc.bool(OptionNames.misc.SORT_OUTPUT, fallback=False)

    _config.keep_nan = misc.bool("keep_nan", fallback=False)

    # --------------------------------------------

    return _config


if __name__ == "__main__":
    import time

    t0 = time.perf_counter()
    import log_utils
    logger = log_utils.get_logger("test-config-read")

    logger.setLevel(logging.DEBUG)
    logger.info(Path(".").absolute())

    # debug code for running module directly
    cfg = parse_config_settings(config_path=Path(
        "configs/rdsps/migration_2019_par/rdsps_fc_ops_160_test.cfg"))
    for k, v in cfg.__dict__.items():
        print(f"{k} => {v}")

    print(f"Execution time: {time.perf_counter() - t0} seconds.")
