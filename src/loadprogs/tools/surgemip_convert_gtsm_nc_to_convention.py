from pathlib import Path
import pandas as pd
import xarray
from loadprogs.tools import surgemip_convert_nc_to_convention_gen as conv

STNID_COLNAME = "StnID"
TIME_COLNAME = "Valid_Hindcast_time(YYYYMMDDHH)"
WATERLEVEL_COLNAME = "Water_level"
DEFAULT_DATE_FORMAT = r"%Y%m%d%H"


def main():
    raw_pth = Path("data/model/raw/GTSM_v001")
    out_pth = Path("data/model/clean/hourly/gtsm_001.csv")

    conv.main(raw_pth=raw_pth, out_pth=out_pth)

if __name__ == "__main__":
    main()

