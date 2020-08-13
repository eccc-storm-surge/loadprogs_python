import configparser
import logging

from argparse import Namespace
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .config_interpolation import ExtendedEnvInterpolation

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


MIN_NHOURS_FOR_DETIDING_DEFAULT = 2160


def parse_config_settings(config_path, cfg_overrides: dict):
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
    _config.beg_time_mod = datetime.strptime(mod_config.get("datestart_mod", fallback=dummy_date), "%Y%m%d%H") \
        .replace(tzinfo=timezone.utc)

    _config.end_time_mod = datetime.strptime(mod_config.get("dateend_mod", fallback=dummy_date), "%Y%m%d%H") \
        .replace(tzinfo=timezone.utc)

    assert _config.end_time_mod >= _config.beg_time_mod, "datestart_mod should be less or equal than dateend_mod"

    _config.mod_dir = Path(mod_config["mod_dir"]).expanduser()

    _config.b2b_freq_hours = int(mod_config["b2b_freq_hours"])
    _config.run_freq_hours = int(mod_config["run_freq_hours"])
    _config.dt_texp_from_tbeg = timedelta(hours=mod_config.getint("dt_texp_from_tbeg_hours", fallback=0))

    msg = f"""back to back frequency should be less or equal to run_freq_hours,
              but got {_config.b2b_freq_hours} and {_config.run_freq_hours}, respectively"""
    assert _config.b2b_freq_hours <= _config.run_freq_hours, msg

    _config.mod_nomvar = mod_config.get("mod_nomvar", fallback="ETAS")

    _config.detide_mod = mod_config.getboolean("detide_mod", fallback=False)
    _config.detide_mod_constituents = mod_config.get("detide_mod_constituents", fallback=None)

    if _config.detide_mod_constituents is not None:
        _config.detide_mod_constituents = [tok.strip() for tok in _config.detide_mod_constituents.split(",")]

    _config.mod_do_filtering = mod_config.getboolean("mod_do_filtering", fallback=False)
    _config.n_members = mod_config.getint("n_members", fallback=0)

    _config.min_nhours_for_detiding_mod = mod_config.getint("min_nhours_for_detiding",
                                                            fallback=MIN_NHOURS_FOR_DETIDING_DEFAULT)


    # --------------------------------------------

    # --------------------------------------------
    # Observation configurations
    # --------------------------------------------
    _config.obs_datatype = obs_config.get("obs_datatype", fallback="txt")

    _config.beg_time_obs = None
    if "datestart_obs" in obs_config:
        _config.beg_time_obs = datetime.strptime(obs_config["datestart_obs"], "%Y%m%d%H") \
            .replace(tzinfo=timezone.utc)
    
    _config.end_time_obs = None
    if "dateend_obs" in obs_config:
        _config.end_time_obs = datetime.strptime(obs_config["dateend_obs"], "%Y%m%d%H") \
            .replace(tzinfo=timezone.utc)

    _config.station_info = Path(obs_config["station_info"]).expanduser()
    _config.obs_dir = Path(obs_config["obs_dir"]).expanduser()

    if _config.obs_datatype in ["sqlite", "canhys"]:
        _config.translator_path = Path(obs_config.get("canhys_station_id_translation_dict"))
        _config.translator_path = _config.translator_path.expanduser()

    _config.detide_obs = obs_config.getboolean("detide_obs", fallback=True)
    _config.obs_do_filtering = obs_config.getboolean("detide_obs_filtering", fallback=False)

    _config.min_nhours_for_detiding_obs = obs_config.getint("min_nhours_for_detiding",
                                                            fallback=MIN_NHOURS_FOR_DETIDING_DEFAULT)

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
    _config.remove_anal_period_mean = misc_config.getboolean("remove_anal_period_mean", fallback=True)
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
