
from pathlib import Path
import pandas as pd
from loadprogs.util import obs_file

"""
Convert GESLA obs to loadprogs format
use file names as station ids as site code is duplicated
convert only stations specified in stnlist.csv
"""

# 0 - no quality control
# 1 - correct value 
# 2 - interpolated value
# 3 - doubtful value
# 4 - isolated spike or wrong value
# 5 - missing value
ACCEPTABLE_QC_VALUES = [0, 1, 2]
QC_FLAG_COLUMN = 3

LON_TOKEN = "LONGITUDE"
LAT_TOKEN = "LATITUDE"
SITE_NAME_TOKEN = "SITE NAME"
COUNTRY_TOKEN = "COUNTRY"
NULL_VALUE_TOKEN = "NULL VALUE"

TIME_COLNAME = "time"

# periods to exclude, inclusive
exclude_periods = (
    (pd.Timestamp(2017, 9, 1), pd.Timestamp(2017, 12, 31, 23, 59)), 
)


def extract_value(token, line, func = lambda x: x):
    return func(line.split(token)[-1].strip())


async def convert_file(inp_f: Path, out_dir: Path, exclude_periods=()):
    print(f"Converting {inp_f} ...")

    stid = inp_f.name
    out_f = out_dir / f"X{stid}.dat"
    lon = None
    lat = None
    site_name = "unknown_site_name"
    country = "unknown_country"

    null_value = None
    # get station coordinates
    with inp_f.open() as f:
        for line in f:
            line = line.strip()
            
            # skip empty lines
            if len(line) == 0:
                continue

            # only check lines starting with #
            if not line.startswith("#"):
                break

            if LON_TOKEN in line:
                lon = extract_value(LON_TOKEN, line, float)
            elif LAT_TOKEN in line:
                lat = extract_value(LAT_TOKEN, line, float)
            elif SITE_NAME_TOKEN in line:
                site_name = extract_value(SITE_NAME_TOKEN, line)
            elif COUNTRY_TOKEN in line:
                country = extract_value(COUNTRY_TOKEN, line)
            elif NULL_VALUE_TOKEN in line:
                null_value = extract_value(NULL_VALUE_TOKEN, line, float)


    if not out_f.exists():
        df = pd.read_csv(inp_f, 
                        parse_dates=[[0, 1]],
                        sep=r"\s+", 
                        comment="#",
                        header=None)

        df = df.loc[df.iloc[:, QC_FLAG_COLUMN].isin(ACCEPTABLE_QC_VALUES), :]

        df = df.loc[df[2] != null_value, :]

        # blacklist requested periods
        df.rename({"0_1": TIME_COLNAME}, axis="columns", inplace=True)
        excl = df[TIME_COLNAME].map(lambda t: False)

        for (t1, t2) in exclude_periods:
            excl = excl | df[TIME_COLNAME].between(t1, t2, inclusive="both")
            
        df = df.loc[~excl, :]
        
        df.iloc[:, :2].to_csv(out_f, index=False, 
                            date_format=r"%Y %m %d %H %M",
                            header=False, 
                            sep="\t", 
                            float_format=r"%.4f")
    else:
        print(f"Exists, won't recreate: {out_f}")
        
    return {
        "NO": inp_f.name, 
        "LON": lon, 
        "LAT": lat, 
        "ID": site_name,
        "DATA.country": country,
        "DATA.I": -1,
        "DATA.J": -1
    }


async def main():
    inp_dir = Path("/home/olh001/Python/surgemip/data/obs/GESLA3")
    inp_stn_list_pth = Path("data/obs/stnlist.csv")
    
    out_dir = inp_dir.parent / f"{inp_dir.name}_loadprogs_v4"
    out_obs_file = inp_dir.parent / "gesla3_surgemip.obs"

    # ===========

    out_dir.mkdir(exist_ok=True, parents=True)

    select_station_ids = pd.read_csv(inp_stn_list_pth).iloc[:, 0].values

    inp_files = [inp_dir / stid for stid in select_station_ids]
    
    st_info = await asyncio.gather(
        *[convert_file(inp_f, out_dir, exclude_periods=exclude_periods) for inp_f in inp_files]
    )

    df = pd.DataFrame.from_records(st_info)

    obs_file.save_dataframe_to_obs(df, out_obs_file)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
