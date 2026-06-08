
from pathlib import Path
import pandas as pd
import xarray

MOD_STNID_COLIDX = 0
MOD_TIME_COLIDX = 1

STNID_COLNAME = "StnID"

DEFAULT_DATE_FORMAT = r"%Y%m%d%H"


def main():
    raw_pth = Path("data/model/raw/predictions_50KM.zarr")
    out_pth = Path("data/model/clean/hourly/google_predictions_50KM.csv")

    out_columns = {
        "station_name": STNID_COLNAME,
         "time": "Valid_Hindcast_time(YYYYMMDDHH)", 
         "predictions_gesla_sea_level": "Water_level"
    }


    with xarray.open_zarr(raw_pth) as ds:
        df = ds.to_dataframe(dim_order=("station_name", "time")).reset_index()
        assert isinstance(df, pd.DataFrame)
        df[list(out_columns)].rename(out_columns, axis="columns").to_csv(out_pth, date_format=DEFAULT_DATE_FORMAT, index=False)


if __name__ == "__main__":
    main()

