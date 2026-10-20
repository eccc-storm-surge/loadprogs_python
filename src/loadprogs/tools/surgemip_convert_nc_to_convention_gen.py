from pathlib import Path
import pandas as pd
import xarray

from convert_gesla_to_loadprogs import exclude_periods

STNID_COLNAME = "StnID"
TIME_COLNAME = "Valid_Hindcast_time(YYYYMMDDHH)"
WATERLEVEL_COLNAME = "Water_level"
DEFAULT_DATE_FORMAT = r"%Y%m%d%H"


def main(raw_pth: Path, out_pth: Path,
         t_beg=None, t_end=None, field_name="waterlevel"):
    """
    Args:
        t_beg, t_end: time interval to select, t_beg - inclusive; t_end - not inclusive
    """

    out_pth.unlink(missing_ok=True)

    station_info = pd.read_csv(raw_pth / "SurgeMIP_stnlist.csv")
    print(station_info["FILE NAME"])

    nc_time_dim_name = "time"

    inp_files = list(raw_pth.glob("*.nc"))
    df = xarray.open_mfdataset(inp_files, concat_dim=nc_time_dim_name, 
                               combine="nested", 
                               data_vars="minimal").sortby(nc_time_dim_name).to_dataframe()


    if t_beg is not None:
        df = df.loc[df.index.get_level_values(nc_time_dim_name) >= t_beg, :]

    if t_end is not None:
        df = df.loc[df.index.get_level_values(nc_time_dim_name) < t_end, :]


    # exclude data for some periods if requested
    t_column = df.index.get_level_values(nc_time_dim_name)
    excl = t_column.map(lambda t: False).to_numpy()

    for (t1, t2) in exclude_periods:
        excl = excl | ((t_column >= t1) & (t_column <= t2))

    df = df.loc[~excl, :]

    df[STNID_COLNAME] = df.index.get_level_values("node").map(
        lambda node_idx: station_info["FILE NAME"].iloc[node_idx])
    
    df = df.reorder_levels(["node", nc_time_dim_name]).reset_index().rename({
        nc_time_dim_name: TIME_COLNAME, 
        field_name: WATERLEVEL_COLNAME}, axis="columns")

    df = df[[STNID_COLNAME, TIME_COLNAME, WATERLEVEL_COLNAME]]
    df.to_csv(out_pth, date_format=DEFAULT_DATE_FORMAT, index=False)


def test():
    raw_pth = Path("data/model/raw/GESLA_1hr_Argonne_CFSv2_Reanalysis/twl")
    out_pth = Path("data/model/clean/hourly/adcirc_cfsv2.csv")
    
    t_beg = pd.Timestamp(2013, 1, 1)
    t_end = pd.Timestamp(2019, 1, 1)
    
    main(raw_pth=raw_pth, out_pth=out_pth, t_beg=t_beg, t_end=t_end, field_name="twl")


if __name__ == "__main__":
    test()

