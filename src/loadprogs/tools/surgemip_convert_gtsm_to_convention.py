
from pathlib import Path
import pandas as pd
import xarray

MOD_STNID_COLIDX = 0
MOD_TIME_COLIDX = 1

STNID_COLNAME = "StnID"

DEFAULT_DATE_FORMAT = r"%Y%m%d%H"


def main():
    raw_pth = Path("data/model/raw/GTSM")
    out_pth = Path("data/model/clean/hourly/gtsm.csv")

    stn_info_pth = Path("data/obs/gesla3_surgemip.obs")

    # to find the correspondence between partial and complete unique station IDs
    stn_info = pd.read_csv(stn_info_pth, sep=r"\s+", skiprows=2) 

    
    out_columns = {
        "StnID": STNID_COLNAME,
        "Valid_Hindcast_time": "Valid_Hindcast_time(YYYYMMDDHH)", 
        "WaterLevel": "Water_level"
    }

    out_pth.unlink(missing_ok=True)

    for inp_file in raw_pth.glob("*.csv"):
        print(f"Converting {inp_file} to {out_pth}")

        df = pd.read_csv(inp_file, converters={"StnID": str}).rename(out_columns, axis="columns")
        current_short_id = df[STNID_COLNAME].iloc[0]
        mark_token = f"_{current_short_id}_"
        current_name = inp_file.stem.split(mark_token)[1]

        stn_selection = (stn_info["ID"] == current_name)

        # there were multiple christmas
        # and partial id shortened to x=vE+14
        if stn_selection.sum() > 1:
            stn_selection = stn_selection & (stn_info["NO"].str.contains(f"-{current_short_id.lower()}-"))

        df[STNID_COLNAME] = stn_info.loc[stn_selection, "NO"].iloc[0]

        assert isinstance(df, pd.DataFrame)
        df[list(out_columns.values())].to_csv(out_pth, 
                                    date_format=DEFAULT_DATE_FORMAT, 
                                    index=False, mode="a", header=not out_pth.exists())


if __name__ == "__main__":
    main()

