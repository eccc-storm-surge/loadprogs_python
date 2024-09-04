
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


def extact_value(token, line, func = lambda x: x):
    return func(line.split(token)[-1].strip())


async def convert_file(inp_f: Path, out_dir: Path):
    print(f"Converting {inp_f} ...")

    stid = inp_f.name
    out_f = out_dir / f"X{stid}.dat"

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
                lon = extact_value(LON_TOKEN, line, float)
            elif LAT_TOKEN in line:
                lat = extact_value(LAT_TOKEN, line, float)
            elif SITE_NAME_TOKEN in line:
                site_name = extact_value(SITE_NAME_TOKEN, line)
            elif COUNTRY_TOKEN in line:
                country = extact_value(COUNTRY_TOKEN, line)
            elif NULL_VALUE_TOKEN in line:
                null_value = extact_value(NULL_VALUE_TOKEN, line, float)


    if not out_f.exists():
        df = pd.read_csv(inp_f, 
                        parse_dates=[[0, 1]], 
                        sep=r"\s+", 
                        comment="#",
                        header=None)

        df = df.loc[df.iloc[:, QC_FLAG_COLUMN].isin(ACCEPTABLE_QC_VALUES), :]

        df = df.loc[df[2] != null_value, :]
        
        df.iloc[:, :2].to_csv(out_f, index=False, 
                            date_format=r"%Y %m %d %H %M",
                            header=None, sep="\t", float_format=r"%.4f")
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
    
    out_dir = inp_dir.parent / f"{inp_dir.name}_loadprogs"
    out_obs_file = inp_dir.parent / "gesla3_surgemip.obs"

    
    # ===========

    out_dir.mkdir(exist_ok=True, parents=True)

    select_station_ids = pd.read_csv(inp_stn_list_pth).iloc[:, 0].values

    inp_files = [inp_dir / stid for stid in select_station_ids]
    
    st_info = await asyncio.gather(
        *[convert_file(inp_f, out_dir) for inp_f in inp_files]
    )

    df = pd.DataFrame.from_records(st_info)

    obs_file.save_dataframe_to_obs(df, out_obs_file)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
