"""
Initially intended for creating climatology for GESPS spinup runs.
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict
import xarray
from dask.diagnostics.progress import ProgressBar
from typing import List

from loadprogs.tools.setmiss import Method, constant_impl, nearest_impl


import dask
from dask.distributed import Client, LocalCluster, as_completed


coord_names = {
    "time_name": "time",
    "depth_name": "depth",
    "lat_name": "lat",
    "lon_name": "lon"
}



def merge(inp_pths: List[Path], out_pth: Path, field_to_fillvalue: dict | None = None):

    if field_to_fillvalue is None:
        field_to_fillvalue = {}

    dim_order = ("time", "j", "i")

    print(f"Prep to merge {inp_pths} into {out_pth}")
    
    ds_inp = xarray.open_mfdataset(inp_pths, 
                                data_vars="minimal", 
                                parallel=False,
                                preprocess=process)

    dim_order = [
        coord_names["time_name"], "j", "i"
    ]
    
    if len(ds_inp.dims) == 4:
        dim_order.insert(1, coord_names["depth_name"]) 

    ds_inp = ds_inp.transpose(*dim_order)
    ds_inp.encoding["unlimited_dims"] = ["time"]

    for field_name, fill_value in field_to_fillvalue.items():
        if field_name in ds_inp:
            if fill_value == "nn":
                ds_inp = nearest_impl(ds_inp, coord_names=coord_names)
                assert not ds_inp[field_name].isnull().any()
            elif isinstance(fill_value, (int, float)):
                ds_inp = constant_impl(ds_inp, fill_value=fill_value)

    return ds_inp.to_netcdf(out_pth, compute=True)


def get_inp_file_name(t: pd.Timestamp, t_format: str,
                      prefix: str = "", suffix: str = ""):
    return f"{prefix}{t:{t_format}}{suffix}"


def process(ds: xarray.Dataset):
    """
    remove depth dimension prior to concatenating files
    """
    dims_to_squeeze = ["depth"]

    dims_to_squeeze = list(set(dims_to_squeeze).intersection(
        {n for n, s in ds.sizes.items() if s == 1}))

    if len(dims_to_squeeze) > 0:
        ds = ds.squeeze(dim=dims_to_squeeze, drop=True)
    return ds


def main():
    n_workers = 48
    cluster = LocalCluster(
        n_workers=n_workers,          # Total number of processes (workers)
        threads_per_worker=1, # Number of threads inside each process
    )

    client = Client(cluster) # Starts a local cluster
    src_dir = Path("/home/sssm001/.suites/gesps-add-etas/generate-forcings-db/hub/ppp7/netcdf/forcings_db_links")
    dst_dir = Path("test_data/atm-forcing-clim-2025-2026_v1")

    out_prefix = "GEPS_"
    var_list = ("GL", "UIW", "VIW", "SALW", "TM", "PN", "tU", "tV")

    inp_prefix = ""
    inp_suffix = "_000.nc"

    # missing values replaced with these
    field_to_fillvalue = {
        "GL": 0,
        "UIW": 0, 
        "VIW": 0,
        "SALW": "nn",
        "TM": "nn",
    }



    # for input time selection
    t_beg = pd.Timestamp(2025, 4, 1, 0)
    t_end = pd.Timestamp(2026, 3, 31, 12)
    dt = pd.Timedelta(hours=12)

    # date format in the input file name
    inp_date_format = r"%Y%m%d%H"
    

    in_dates = list(pd.date_range(t_beg, t_end, freq=dt))

    month_to_dates = defaultdict(list)

    for t in in_dates:
        month_to_dates[t.month].append(t)



    print(f"{len(month_to_dates) = }")
    for m, mdates in month_to_dates.items():
        print(f"{len(mdates)} dates/files for month {m:02d}")


    dst_dir.mkdir(exist_ok=True, parents=True)

    
    write_jobs = []
    for m, mdates in month_to_dates.items():
        for vname in var_list:

            if vname != "SALW":
                continue

            out_pth = dst_dir / f"{out_prefix}{vname}_m{m:02d}.nc"
            
            inp_pths = [
                src_dir / get_inp_file_name(mdate, inp_date_format, 
                                            prefix=inp_prefix, 
                                            suffix=f"_{vname}{inp_suffix}") for mdate in mdates
            ]

            for inp in inp_pths:
                assert inp.exists()

            if out_pth.exists():
                out_pth.unlink()
                print(f"Already exists, will overwrite: {out_pth}")

            wj = merge(inp_pths, out_pth, field_to_fillvalue=field_to_fillvalue)
            
            if wj is not None:
                write_jobs.append(wj)
            # print(f"{out_pth} <--- {inp_pths}")
    

    if len(write_jobs) > 0:
        dask.compute(write_jobs)

    print(f"Executed delayed jobs: {len(write_jobs)}")
    

if __name__ == "__main__":
    main()
