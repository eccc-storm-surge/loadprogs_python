
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

import numexpr 
numexpr.set_num_threads(8)

import xarray
import utide
import zarr
import shutil
import cProfile


DATE_FORMAT = r"%Y%m%d%H"
DATE_FORMAT_escaped = DATE_FORMAT.replace(r"%", r"%%")

def parse_date(tok):
    return pd.to_datetime(tok, format=DATE_FORMAT)

def parse_dt_hours(tok):
    return pd.Timedelta(hours=int(tok))

def read_cmd_args():
    parser = argparse.ArgumentParser(description="detide model outputs on grids")
    
    parser.add_argument("--inp_dir", required=True, type=Path,
                        help="path to the input directory")

    parser.add_argument("--out_dir", required=True, type=Path,
                        help="path to the output directory")
    
    # total water level field name
    parser.add_argument("--twl_nomvar", required=False, default="SSH", type=str,
                        help="total water level field name")
    
    # storm surge field name in the output file
    parser.add_argument("--detided_nomvar", required=False, default="etas", type=str,
                        help="total water level field name")

    # select experiments corresponding files
    parser.add_argument("--t_exp_beg", required=True, type=parse_date,
                        help=f"select beg exp date, inclusive, derived from the file name prefix, format={DATE_FORMAT_escaped}")
    
    parser.add_argument("--t_exp_end", required=True, type=parse_date,
                        help=f"select end exp date, inclusive, derived from the file name prefix, format={DATE_FORMAT_escaped}")

    parser.add_argument("--dt_exp_hours", required=True, type=parse_dt_hours,
                        help="frequency (in hours) of experiment files to take into account")

    parser.add_argument("--filename_suffix", required=False, default="", 
                        help="suffix of files to be treated, e.g. to select a particular member: suffix=_001")

    parser.add_argument("--t_origin_hours", required=False, default=pd.Timedelta(hours=0), 
                        type=parse_dt_hours,
                        help="t_origin wrt t_exp in hours (can be +/- or 0), dt=t_origin-t_exp")
    

    # selecting by forecast hour = (t - t_origin); where t_origin = t_exp + t_origin_hours
    parser.add_argument("--lead_hour_min", required=False, default=None,
                        type=parse_dt_hours,
                        help="minimum lead hour to be used for detiding (inclusive)")
    parser.add_argument("--lead_hour_max", required=False, default=None, 
                        type=parse_dt_hours,
                        help="maximum lead hour to be used for detiding (inclusive)")
    


    # spatial mask to select detiding region
    parser.add_argument("--mask_file", required=False, default=None, type=Path,
                        help="path to the file containing mask field, for region of interest of detiding")
    
    parser.add_argument("--mask_nomvar", required=False, default="SSH", type=str,
                        help="field name from which to take the mask, for region of interest of detiding")

    # Raileigh criterion
    parser.add_argument("--rayleigh", required=False, default=0.9, type=float,
                        help="rayleigh parameter for detiding")


    # chunking to avoid filling up memory
    parser.add_argument("--chunk_npoints", required=False, default=100, type=int,
                        help="number of points per chunk")

    parser.add_argument("--max_rechunk_memory", required=False, default="40G",
                        help="maximum memory to be used for rechunking")
 


    parser.add_argument("--time_dim_name", required=False, default="time", type=str,
                        help="time dimension name in the input files")

    parser.add_argument("--lat_nomvar", required=False, default="time", type=str,
                        help="latitude variable name in the input files")


    args = parser.parse_args()

    assert isinstance(args.inp_dir, Path)
    assert isinstance(args.out_dir, Path)

    print(args)
    return args



def get_out_filename(args: argparse.Namespace, prefix="", suffix=".nc"):
    """ generate output file name based on exp beg/end time and frequency

    Args:
        args (argparse.Namespace): command line arguments
        prefix (str, optional): custom prefix to append to the file name, default is empyt "".

    Returns:
        str: _description_
    """
    if prefix != "":
        prefix += "_"

    nhours = args.dt_exp_hours.total_seconds() // 3600
    return f"{prefix}{args.t_exp_beg:{DATE_FORMAT}}_{args.t_exp_end:{DATE_FORMAT}}_{nhours}h{suffix}"


def read_mask(mask_pth, mask_nomvar):
    with xarray.open_dataset(mask_pth) as ds:
        return ds[mask_nomvar].compute()


def read_data(args):
    assert isinstance(args.inp_dir, Path)
    assert isinstance(args.filename_suffix, str)

    assert args.inp_dir.exists(), f"should exist: {args.inp_dir}"
    assert args.inp_dir.is_dir(), f"should be a directory: {args.inp_dir}"

    if not args.out_dir.exists():
        args.out_dir.mkdir(exist_ok=True, parents=True)


    
    files: list[Path] = []
    arrays: list[xarray.DataArray] = []
    file_to_texp: dict[Path, pd.Timestamp] = {}
    texp_to_torigin: dict[pd.Timestamp, pd.Timestamp] = {}

    # select files
    for t_exp in pd.date_range(args.t_exp_beg, args.t_exp_end, freq=args.dt_exp_hours):
        print(f"{t_exp = }")

        t_origin = t_exp + args.t_origin_hours
        texp_to_torigin[t_exp] = t_origin

        print(f"{t_exp:{DATE_FORMAT}}*{args.filename_suffix}")
        current_files = [
            f for f in args.inp_dir.glob(f"{t_exp:{DATE_FORMAT}}*{args.filename_suffix}")
        ]

        print(f"{current_files = }")
        for f in current_files:
            file_to_texp[f] = t_exp

        files += current_files

    # select by time from each file
    for f in files:
        t_exp = file_to_texp[f]
        t_origin = texp_to_torigin[t_exp]
        t_min = t_origin + args.lead_hour_min
        t_max = t_origin + args.lead_hour_max
        with xarray.open_dataset(f, chunks="auto") as ds:
            ds = ds.squeeze()
            vars_to_drop = [vname for vname, v in ds.variables.items() if v.size <= 1]
            if len(vars_to_drop) > 0:
                ds = ds.drop_vars(vars_to_drop)

            arr = ds[args.twl_nomvar]
            
        t = arr.coords[args.time_dim_name]
        arr = arr.sel({
            args.time_dim_name: (t >= t_min) & (t <= t_max)})
        
        arrays.append(arr)

    return xarray.concat(arrays, dim=args.time_dim_name, 
                         coords="minimal")
    


def utide_wrap(t, u, lat, rayleigh, verbose=False, noop=False):
    """
    wrapper to utide, detide 1D timeseries u at lat

    Args:
        t (np.ndarray): _description_. Defaults to None.
        u (np.ndarray): _description_. Defaults to None.
        lat (_type_, optional): _description_. Defaults to None.
        rayleigh (_type_, optional): _description_. Defaults to None.
        verbose (bool, optional): _description_. Defaults to False.
        noop (bool, optional): _description_. Defaults to False.

    Returns:
        _type_: _description_
    """
    if noop:
        return u
    
    coef = utide.solve(t=t, u=u - u.mean(), lat=lat, Rayleigh_min=rayleigh, verbose=verbose)
    return u - utide.reconstruct(t, coef=coef, verbose=verbose).h    


def detide_timeseries(time, ts_data, mask, latitude, rayleigh=0.9):
    """

    Args:
        time (_type_): _description_
        ts_data (_type_): _description_
        mask (_type_): if mask is true, the point is masked
        latitude (_type_): _description_
        rayleigh (_type_): _description_

    Returns:
        _type_: detided vector
    """

    # do nothing if all data is masked
    if mask.all():
        return ts_data

    res = ts_data.copy()
    
    # pr = cProfile.Profile()
    # pr.enable()

    time = time.squeeze()

    print(f"{mask.shape = }")
    print(f"{ts_data.shape = }")
    print(f"{latitude.shape = }")
    print(f"{mask = }")
    print(f"{rayleigh = }")

    # avoid division by 0
    _lat = 0 if latitude == 0 else latitude
    
    return utide_wrap(t=time,
                      u=ts_data, lat=_lat, rayleigh=rayleigh)
    

def process_block(subset_array, mask, args=argparse.Namespace()):
    anomaly = subset_array - subset_array.mean(dim=args.time_dim_name)

    # split in space
    anomaly = anomaly.chunk({dim: 1 for dim in anomaly.dims if dim != args.time_dim_name})

    print(f"{anomaly.shape = }")
    print(f"{mask.shape = }")

    # anomaly = xarray.apply_ufunc(detide_timeseries, 
    #                              anomaly.coords[args.time_dim_name], anomaly, mask, anomaly.coords[args.lat_nomvar], 
    #                              input_core_dims=[[args.time_dim_name], [args.time_dim_name], [], []],
    #                              kwargs={"rayleigh": args.rayleigh}, 
    #                              dask="parallelized")
    return anomaly

def work(args):
    """Main work is done in this method

    Args:
        args (argparse.Namespace): command line arguments
    """
    mask = None
    if args.mask_file is not None:
        mask = read_mask(args.mask_file, args.mask_nomvar)


    data = read_data(args)

    # combine input mask and data-mask
    data_mask = data.isel({args.time_dim_name: 0}).isnull()
    if mask is not None:
        mask = data_mask & (mask < 0.5)
    else:
        mask = data_mask

    print(data)

    chunking = {
        args.twl_nomvar: {
            args.time_dim_name: data.sizes[args.time_dim_name],
            "i": 100,
            "j": 100
        }
    }
    chunked_store = args.out_dir / get_out_filename(args, suffix=".zarr", prefix="chunked_")

    if chunked_store.exists():
        shutil.rmtree(chunked_store)

    import rechunker
    rechunked_plan = rechunker.rechunk(
        data.to_dataset(), target_chunks=chunking,
        max_mem=args.max_rechunk_memory,
        target_store=chunked_store
    )
    
    rechunked_data = rechunked_plan.execute()
    zarr.consolidate_metadata(rechunked_data.store)
    rechunked_data = xarray.open_zarr(rechunked_data.store)


    print("rechunked_data, before unify: ")
    print(rechunked_data)


    rechunked_data = xarray.unify_chunks(rechunked_data)[0]

    print("rechunked_data, after unify: ")
    print(rechunked_data)
    # rechunked_data = data.chunk(chunking)
    
    print(f"{np.unique(rechunked_data.chunks['j']) = }")
    print(f"{np.unique(rechunked_data.chunks['i']) = }")
    print(f"{np.unique(rechunked_data.chunks[args.time_dim_name]) = }")

    # detided = xarray.map_blocks(
    #     process_block, rechunked_data, 
    #     args=(mask, ), 
    #     kwargs={"args": args}
    # )

    
    rechunked_data.coords[args.time_dim_name].persist()
    rechunked_data.coords[args.lat_nomvar].persist()
    

    

    # debug
    # rechunked_data.persist()

    print(f"{rechunked_data.chunksizes = }")
    
    detided = xarray.apply_ufunc(
        detide_timeseries, 
        rechunked_data.coords[args.time_dim_name], 
        rechunked_data[args.twl_nomvar], 
        mask, rechunked_data.coords[args.lat_nomvar],
        # input_core_dims=[[args.time_dim_name], [args.time_dim_name], [], []],
        # output_core_dims=[[args.time_dim_name]],
        kwargs={"rayleigh": 0.9},
        keep_attrs=True,
        dask="parallelized",
        output_dtypes=[np.float32]
    ).transpose(*data.dims)

    

    # saving data to output file
    detided.name = args.surge_nomvar
    
    print(f"{detided = }")
    
    out_file = args.out_dir / get_out_filename(args)
    
    print(f"Saving detided water level to {out_file}")


    from dask.distributed import Client
    
    with Client(n_workers=60, threads_per_worker=1, dashboard_address=":8787") as client:
        numexpr.set_num_threads(8)
        print(f"{client.dashboard_link = }", flush=True)
        detided.where(~mask).to_netcdf(out_file)
        
    rechunked_data.close()
    print(f"finished saving {out_file}")


def main():
    args = read_cmd_args()
    work(args)


def test():
    inp_dir = Path("/home/sssm001/data/ppp5/maestro_archives/gesps_v001_final_cycles_V2/gridpt/gesps.f.output_pre-level/")
    args = argparse.Namespace(
        **dict(
            inp_dir=inp_dir,
            out_dir=Path("data/gesps-detide-fields-test/"),
            twl_nomvar="SSH",
            lat_nomvar="lat",
            surge_nomvar="etas",
            t_exp_beg=pd.Timestamp(2021, 10, 18),
            t_exp_end=pd.Timestamp(2021, 10, 19),
            dt_exp_hours=pd.Timedelta(hours=12),
            rayleigh=0.9,
            chunk_npoints=1000,
            max_rechunk_memory="20G",
            filename_suffix="_000",
            t_origin_hours=pd.Timedelta(hours=-144),
            lead_hour_min=pd.Timedelta(hours=0),
            lead_hour_max=pd.Timedelta(hours=12),
            mask_file=None,
            mask_nomvar="SSH",
            time_dim_name="time"
        )
    )

    work(args)


if __name__ == "__main__":
    run_test = True
    if run_test:
        test()
    else:
        main()
