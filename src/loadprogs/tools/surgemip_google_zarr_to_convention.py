
from pathlib import Path
import pandas as pd
import xarray
import numpy as np
from convert_gesla_to_loadprogs import exclude_periods

MOD_STNID_COLIDX = 0
MOD_TIME_COLIDX = 1

STNID_COLNAME = "StnID"

DEFAULT_DATE_FORMAT = r"%Y%m%d%H"


def main():
    raw_pth = Path("data/model/raw/predictions_50KM.zarr")
    out_pth = Path("data/model/clean/hourly/google_predictions_50KM.csv")


    inp_time_dim_name = "time"



    out_columns = {
        "station_name": STNID_COLNAME,
         inp_time_dim_name: "Valid_Hindcast_time(YYYYMMDDHH)", 
         "predictions_gesla_sea_level": "Water_level"
    }


    with xarray.open_zarr(raw_pth) as ds:

        t = ds[inp_time_dim_name]
        excl = np.zeros_like(t, dtype=bool)
        for (t1, t2) in exclude_periods:
            excl = excl | ((t.values >= t1) & (t.values <= t2))

        ds = ds.sel({inp_time_dim_name: ~excl})

        df = ds.to_dataframe(dim_order=("station_name", inp_time_dim_name)).reset_index()
        assert isinstance(df, pd.DataFrame)
        df[list(out_columns)].rename(out_columns, axis="columns").to_csv(out_pth, 
                                                                         date_format=DEFAULT_DATE_FORMAT, 
                                                                         index=False)


if __name__ == "__main__":
    main()

