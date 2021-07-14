
from collections import OrderedDict


COLNAME_TIME = "time"
COLNAME_STID = "station_id"
COLNAME_VALID_HOUR = "valid_hour"  # aka lead time
COLNAME_TORIGIN = "date_of_origin"
COLNAME_TWL = "twl" # total water level

OUT_TIME_FORMAT = "%Y%m%d%H%M"


class OptionNames(object):
    
    class obs(object):
        OBS_DATATYPE = "obs_datatype"
        OBS_BEG_DATE = "datestart_obs"
        OBS_END_DATE = "dateend_obs"

    class mod(object):
        MOD_BEG_DATE = "datestart_mod"
        MOD_END_DATE = "dateend_mod"
        DATA_DIR = "mod_dir"
        B2B_FREQ_HOURS = "b2b_freq_hours"
        B2B_BLEND_HOURS = "b2b_blend_hours"
        B2B_MIN_LEAD_HOUR = "b2b_min_lead_hour"
        RUN_FREQ_HOURS = "run_freq_hours"
        DT_TEXP_TBEG = "dt_texp_from_tbeg_hours"
        NOMVAR = "mod_nomvar"
        TYPVAR = "mod_typvar"
        DETIDE = "detide_mod"
        DETIDE_CONSTITUENTS = "detide_mod_constituents"
        DETIDE_FILTERING = "detide_mod_filtering"
        N_MEMBERS = "n_members"
        MIN_NHOURS_FOR_DETIDING = "min_nhours_for_detiding"
        EXTERNAL_TIDES = "mod_external_tides"
        EXTERNAL_DEBIAS = "mod_external_debias"
        EXTERNAL_DEBIAS_AVG_NHOURS = "mod_external_debias_avg_nhours"
        READ_NPROCS = "mod_read_nprocs"


    class misc(object):
        pass


def get_help():
    """
    to be used to provide help on options in the .cfg files
    """
    
    return OrderedDict([
        ("mod", OrderedDict([
            (OptionNames.mod.MOD_BEG_DATE, r"Date of the first model experiment to process (inclusive), format %Y%m%d%H"),
            (OptionNames.mod.MOD_END_DATE, r"Date of the last model experiment to process (inclusive), format %Y%m%d%H"), 
            (OptionNames.mod.DATA_DIR, "Path to the folder containing model outputs"),
            (OptionNames.mod.B2B_FREQ_HOURS, """Maximum lead hour to be used for back to back timeseries construction,
                                                not inclusive, i.e. when 12, then the max lead used for back to back is 11."""),
            (OptionNames.mod.RUN_FREQ_HOURS, "Interval in hours between consequent experiments to be scored, the value should be the same\n" 
                                            f"as {OptionNames.mod.B2B_FREQ_HOURS}"),
            (OptionNames.mod.DT_TEXP_TBEG, "difference in hours (possibly float) between the simulation start \n"
                                           "and experiment date (contained in file names) in each file, default is 0"),
            (OptionNames.mod.NOMVAR, "Variable name in the model output files, default is ETAS"),
            (OptionNames.mod.DETIDE, """Flag to disable/enable detiding of model outputs (0/1 or False/True respectively)
                                     default is 0"""),
            (OptionNames.mod.DETIDE_CONSTITUENTS, """Comma-separated list of constituents,
                                                  default None - constituents determined automatically"""),
            (OptionNames.mod.TYPVAR, "TYPVAR to filter variables in fst files, default is P@, not used for netcdf files, to select all typvar use *")
        ])), 
        ("obs", OrderedDict([
            (OptionNames.obs.OBS_DATATYPE, "Type of observation files, possible values: txt (default), sqlite"),
            (OptionNames.obs.OBS_BEG_DATE, r"Start date of observation data in format %Y%m%d%H, inclusive"),
            (OptionNames.obs.OBS_END_DATE, r"End date of observation data in format %Y%m%d%H, inclusive"),
        ])),
        ("misc", OrderedDict([

        ]))
    ])
