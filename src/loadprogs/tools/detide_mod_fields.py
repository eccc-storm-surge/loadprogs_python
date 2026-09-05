import sys
import argparse
import time
from pathlib import Path
import cftime
import pandas as pd
import numpy as np
import utide
import shutil

from functools import wraps, partial
import itertools as itt

import zarr
import xarray

import dask
from dask.distributed import Client, LocalCluster, as_completed
from dask_jobqueue.pbs import PBSCluster
from dask.distributed import progress, secede, rejoin

import pyarrow
import pyarrow.parquet as pq
import pyarrow.compute as pc
from multiprocessing import Pool

import cmcio

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


    parser.add_argument("--nworkers_per_job", required=False, default=60, type=int,
                        help="number of dask workers for processing per job")

    
    parser.add_argument("--njobs", required=False, default=1, type=int,
                        help="number of jobs for processing, number of jobs/nodes spun up by dask server")

    parser.add_argument("--detide_batch_size", required=False, default=5, type=int,
                        help="number of experiments to process in each batch (size of a dask bas partition,"
                        " in number of tiles)")


    parser.add_argument("--threads-per-worker", required=False, default=1, type=int,
                            help="Number of threads per worker, give more to give more memory to a worker")
    
    

    # chunking to avoid filling up memory
    parser.add_argument("--chunk_npoints_x", required=False, default=100, type=int,
                        help="number of points per chunk in x direction")

    parser.add_argument("--chunk_npoints_y", required=False, default=100, type=int,
                        help="number of points per chunk in y direction")

    parser.add_argument("--max_rechunk_memory", required=False, default="40G",
                        help="maximum memory to be used for rechunking")

    parser.add_argument("--time_dim_name", required=False, default="time", type=str,
                        help="time dimension name in the input files")

    parser.add_argument("--lat_nomvar", required=False, default="lat", type=str,
                        help="latitude variable name in the input files, need for standard files as well to access in parsed xarray")

    parser.add_argument("--lon_nomvar", required=False, default="lon", type=str,
                        help="latitude variable name in the input files, need for standard files as well to access in parsed xarray")


    args = parser.parse_args()

    assert isinstance(args.inp_dir, Path)
    assert isinstance(args.out_dir, Path)

    print(args)
    return args




def bunch_to_frame(b, i=0, j=0):
    """
    convert bunch object containing utide coefficients to
    pandas dataframe for storing
    """
    df = pd.DataFrame.from_dict({k: v for k, v in b.items() 
                                 if isinstance(v, np.ndarray) and len(v) == len(b["name"])})


    additional_columns = ["aux", "mean", "slope"]
    for c in additional_columns:
        df[c] = [b[c]] * len(b["name"])

    df["i"] = i
    df["j"] = j
    df = df.set_index(["i", "j", "name"])
    return df


def strap_bunch(b, i=0, j=0):
    """
    convert bunch object containing utide coefficients to
    dict for storing
    """
    res = {"i": i, "j": j}
    nconstit = len(b["name"])
    d: dict = {k: v for k, v in b.items() 
             if isinstance(v, np.ndarray) and len(v) == nconstit}
    
    additional_columns = ["aux", "mean", "slope"]
    for c in additional_columns:
        d[c] = b[c]

    res["bunch"] = d
    return res

def bunch_to_table(b, i=0, j=0):
    """
    convert bunch object containing utide coefficients to
    pandas dataframe for storing
    """

    nrows = len(b["name"])
    d: dict = {k: v for k, v in b.items() 
             if isinstance(v, np.ndarray) and len(v) == nrows}


    
    additional_columns = ["aux", "mean", "slope"]
    for c in additional_columns:
        d[c] = [b[c]] * nrows

    d["i"] = [i] * nrows
    d["j"] = [j] * nrows
    
    return pyarrow.table(d)




def get_default_utide_frame_meta():
    t = pd.date_range("2001-01-01 00:00", 
                      "2001-02-01 00:00", 
                      freq=pd.Timedelta(hours=1))
    
    x = np.sin((t - t[0]).total_seconds() / (3600 * 12))
    c = utide.solve(t, x, lat=45)

    return bunch_to_frame(c)


def df_to_dict(df_coef, i=0, j=0):
    """
    convert pandas dataframe read from storage to utide bunch 
    to be used in the reconstruct function
    """
    res = {}
    df_sel = df_coef.xs(i, level="i").xs(j, level="j")
    res["name"] = df_sel.index.values
    for cn in df_sel:
        v = df_sel[cn].values
        dup = isinstance(v[0], (dict, list, tuple, np.ndarray)) or len(np.unique(v)) == 1
        res[cn] = v[0] if dup else v
    return res


def table_to_dict(table_coef, i=0, j=0):
    """
    convert pyarrow table read from storage to utide bunch 
    to be used in the reconstruct function
    """
    res = {}
    expr = ((pc.field("i") == i) & (pc.field("j") == j))
    t_sel = table_coef.filter(expr)
    res["name"] = t_sel["name"].to_numpy()
    for cn in t_sel.column_names:
        v = t_sel[cn].to_numpy()
        dup = isinstance(v[0], (dict, list, tuple, np.ndarray)) or len(np.unique(v)) == 1
        res[cn] = v[0] if dup else v
    return res


def get_out_filename(args: argparse.Namespace, prefix="", suffix=".nc"):
    """ generate output file name based on exp beg/end time and frequency

    Args:
        args (argparse.Namespace): command line arguments
        prefix (str, optional): custom prefix to append to the file name, default is empty "".

    Returns:
        str: _description_
    """
    if prefix != "":
        prefix += "_"

    nhours = int(args.dt_exp_hours.total_seconds() // 3600)
    prefix = f"{prefix}chunking_x_{args.chunk_npoints_x}_y_{args.chunk_npoints_y}_"
    return f"{prefix}{args.t_exp_beg:{DATE_FORMAT}}_{args.t_exp_end:{DATE_FORMAT}}_{nhours}h{suffix}"


def read_mask(mask_pth, mask_nomvar):
    with xarray.open_dataset(mask_pth) as ds:
        return ds[mask_nomvar].compute()



def extract_coords_from_dataset(ds: xarray.Dataset, args):

    if ">>" in ds.variables:
        ds = ds.rename({"^^": args.lat_nomvar,
                        ">>": args.lon_nomvar,
                        "fst_>>_i": "x", "fst_>>_j": "y",
                        "fst_^^_i": "x", "fst_^^_j": "y", 
        })

        ds = ds.set_coords(args.lon_nomvar).set_coords(args.lat_nomvar)

    return {
        args.lat_nomvar: ds[args.lat_nomvar].load(), 
        args.lon_nomvar: ds[args.lon_nomvar].load()
    }


def read_spatial_coords(args):
    """
    """

    pth = next(f for f in args.inp_dir.glob(f"{args.t_exp_beg:{DATE_FORMAT}}*{args.filename_suffix}"))
    print(f"Reading coordinates from {pth}")

    ds = cmcio.open_fst(pth)[0]

    return extract_coords_from_dataset(ds, args)

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
    file_to_torigin: dict[Path, pd.Timestamp] = {}

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

        assert len(current_files) > 0, f"no files found for {t_exp:{DATE_FORMAT}}*{args.filename_suffix}"
        print(f"{current_files = }")
        for f in current_files:
            file_to_texp[f] = t_exp
            file_to_torigin[f] = texp_to_torigin[t_exp]

        files += current_files

    t_epsilon = pd.Timedelta(microseconds=1)


    with Pool(processes=20) as pool:
        opened_datasets = pool.map(cmcio.open_fst, files)


    datasets = []
    for ds_list, f in zip(opened_datasets, files):
        ds = ds_list[0]  # Extract the first (and likely only) dataset from the list
        print("Selecting time period from file:", f)
        t_origin = file_to_torigin[f]
        t_min = t_origin + args.lead_hour_min
        t_max = t_origin + args.lead_hour_max

        ds = ds.sel({
            args.time_dim_name: slice(t_min, t_max - t_epsilon)})

        datasets.append(ds)
        

    print(f"Concatenating {len(datasets)} datasets along dimension '{args.time_dim_name}'")
    ds = xarray.concat(datasets,
                       data_vars="minimal", 
                       coords="minimal",
                       dim=args.time_dim_name)


    print(ds)
    ds = ds.assign_coords(extract_coords_from_dataset(ds, args))
    ds = ds.squeeze(drop=True)
    print(f"Final dataset shape: {ds.sizes}, dimensions: {ds.dims}, coordinates: {list(ds.coords)}")
    return ds[args.twl_nomvar]


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
        np.ndarray: tide timeseries from u
    """
    if noop:
        return u
    lat = 1e-6 if lat == 0 else lat
    lat = float(lat)
    coef = utide.solve(t=t, u=u - u.mean(), lat=lat, Rayleigh_min=rayleigh, verbose=verbose)
    return utide.reconstruct(t, coef=coef, verbose=verbose).h



def utide_solve(t, u, lat, rayleigh, verbose=False) -> dict:
    """
    return tide coefficients
    """
    lat = 1e-6 if lat == 0 else lat
    lat = float(lat)
    anomaly = u - u.mean()

    return utide.solve(t=t, u=anomaly, 
                        lat=lat, Rayleigh_min=rayleigh, verbose=verbose)


def utide_reconstruct(t, coef: dict) -> np.ndarray:
    """
    return tide coefficients
    """
    return utide.reconstruct(t, coef).h



def skip_block(slices: tuple[slice, slice, slice], data_path: Path, ssh_name: str) -> bool:
    """
    Check if a block of data should be skipped based on the presence of valid data.

    Args:
        slices (tuple[slice, slice, slice]): Slices defining the block to check.
        data_path (Path): Path to the Zarr dataset.
        ssh_name (str): Name of the SSH variable in the dataset.

    Returns:
        bool: True if the block should be skipped, False otherwise.
    """
    assert data_path.exists(), f"should exist: {data_path}"
    
    ds = zarr.open_group(data_path, mode="r")
    arr: zarr.Array = ds.get_array(ssh_name)
    vals = np.ascontiguousarray(arr[slices])

    att_name = "fst_mask_fill"
    fill_value = arr.metadata.attributes.get(att_name, np.nan)
    if isinstance(fill_value, (str, int, float)):
        fill_value = float(fill_value)

    if  np.isnan(fill_value) and hasattr(arr.metadata, "fill_value"):
        if isinstance(arr.metadata.fill_value, (str, int, float)):
            fill_value = float(arr.metadata.fill_value)
        
    good = ~np.isclose(vals[0], fill_value) & (~np.isnan(vals[0]))
    good = good & (~np.isclose(vals.min(axis=0), vals.max(axis=0)))

    del ds, arr, vals
    return not good.any()


def compute_coefs_for_block(
        slices: tuple[slice, slice, slice],
        data_path: Path, 
        ssh_name: str,                     
        lat_name: str, 
        t_name: str, 
        rayleigh=0.9) -> pyarrow.Table | None:
    """
    assuming shapes time,i,j
    returns:
        pyarrow.Table with utide coefficients
    """

    assert data_path.exists(), f"should exist: {data_path}"
    
    ds = zarr.open_group(data_path, mode="r")
    arr: zarr.Array = ds.get_array(ssh_name)
    vals = np.ascontiguousarray(arr[slices])
    t_arr = ds.get_array(t_name)
    t_values = t_arr[slices[0]]
    units = t_arr.attrs.get("units")
    calendar = t_arr.attrs.get("calendar", "standard")

    t = cftime.num2date(t_values, units=units, calendar=calendar)

    lats = np.ascontiguousarray(ds.get_array(lat_name)[slices[1:]])

    att_name = "fst_mask_fill"
    fill_value = arr.metadata.attributes.get(att_name, np.nan)
    if isinstance(fill_value, (str, int, float)):
        fill_value = float(fill_value)

    if  np.isnan(fill_value) and hasattr(arr.metadata, "fill_value"):
        if isinstance(arr.metadata.fill_value, (str, int, float)):
            fill_value = float(arr.metadata.fill_value)

    good = ~np.isclose(vals[0], fill_value) & (~np.isnan(vals[0]))
    good = good & (~np.isclose(vals.min(axis=0), vals.max(axis=0)))

    # there are always valid data as all non-valid data blocks are skipped in the previous step   
    i_arr, j_arr = np.where(good)

    i_offset, j_offset = slices[-2].start, slices[-1].start

    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", module="utide")

         # 1. TELL DASK TO IGNORE THIS WORKER'S HEARTBEAT TEMPORARILY
        secede() 
        try:

            dict_all: dict[str, list] | None = None
            for i, j in zip(i_arr, j_arr):
                time_series = np.ascontiguousarray(vals[:, i, j])
                bunch = utide_solve(t, time_series, lats[i, j], rayleigh=rayleigh)
                
                d = strap_bunch(bunch, i + i_offset, j + j_offset)

                if dict_all is None:
                    dict_all = {k: [v,] for k, v in d.items()}
                else:
                    for k, v in d.items():
                        dict_all[k].append(v)
        finally:
            rejoin()

        
    assert dict_all is not None, "No valid data found for the given slices."

    nrows = 0
    for k, v in dict_all.items():
        if not isinstance(v, list):
            raise ValueError(f"Expected list for key '{k}', but got {type(v)}")
        if nrows == 0:
            nrows = len(v)
            assert nrows > 0, "No rows found in the data."
        else:
            if len(v) != nrows:
                raise ValueError(f"Inconsistent row counts: key '{k}' has {len(v)} rows, expected {nrows}")

            
    
    del ds, arr, vals, t_arr, t_values, lats
    return pyarrow.Table.from_pydict(dict_all)
    


def time_this(func):
    """Decorator that prints the execution time of a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)  # Executes your function
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        print(f"⏱️  [Timing] '{func.__name__}' took {execution_time:.6f} seconds")
        
        return result  # Returns the actual function output
    return wrapper



def get_cluster(args, local_cluster=False, dashboard_address=None) -> PBSCluster | LocalCluster:
    """
    Get a Dask cluster for distributed computing.

    Args:
        args (argparse.Namespace): Command line arguments.
        local_cluster (bool): Whether to use a local cluster.

    Returns:
        dask.distributed.Cluster: The Dask cluster.
    """
    if local_cluster:
        cluster = LocalCluster(
            n_workers=args.nworkers, 
            memory_limit=args.max_worker_memory,
            threads_per_worker=1,
            dashboard_address=dashboard_address
        )
    else:
        total_cpu = args.nworkers_per_job
        total_memory = "700GB"
        cluster = PBSCluster(
            cores=total_cpu,                     # Total CPU requested per PBS job
            processes=total_cpu // args.threads_per_worker,                # Total processes requested per PBS job
            memory=total_memory,                    # Total RAM requested per PBS job
            resource_spec=f"select=1:ncpus={total_cpu}:mem={total_memory}", # Matches your system qsub/qstat specs
            walltime="03:00:00",
            queue="development",
            # Worker terminates if scheduler is missing for 60 seconds
            # death_timeout=60,
            dashboard_address=None  # Optional: specify a dashboard address for monitoring
        )

    return cluster
    
def rechunk_data(data, chunked_store, args):
    """
    rechunk data for tide analysis with tiles and complete along time dimension 
    and save to zarr
    Args:
        data (xarray.DataArray): input data to be rechunked
        args (argparse.Namespace): command line arguments
        chunked_store (Path): destination path to .zarr dataset
    Returns:
        Path: The path to the rechunked data.
    """
    chunking = {
        args.twl_nomvar: {
            args.time_dim_name: data.sizes[args.time_dim_name],
            "x": args.chunk_npoints_x,
            "y": args.chunk_npoints_y
        }
    }
    
    try:
        # re-chunking input data
        # 1. Force Dask to use its high-performance P2P network shuffling
        with dask.config.set({"array.rechunk.method": "p2p", "distributed.p2p.storage.disk": True}):
            rechunked_data = data.chunk(chunking[args.twl_nomvar])
            rechunked_data.to_zarr(chunked_store, mode="w")

        print(f"Finished re-chunking data to {chunking[args.twl_nomvar]}")
    except Exception as e:
        print(f"Error during rechunking: {e}")

        if chunked_store.exists():
            shutil.rmtree(chunked_store)
        raise e


def compute_tide_coefficients(client, chunked_store, args):
    """
    Args:
        client (dask.distributed.Client): dask client
        chunked_store (Path): path to the zarr store containing chunked data
        args (argparse.Namespace): command line arguments
    Returns:
        coef_table (pyarrow.Table): table containing utide coefficients
    """
   
    ds = zarr.open_group(chunked_store, mode="r")  # Ensure the store is open
    chunks = ds.get_array(args.twl_nomvar).write_chunk_sizes  # Access the chunk shape directly
        
    chunk_idx = [(0, ) + tuple(int(i) for i in np.cumsum(v[:-1])) for v in chunks]
    beg_indices = list(itt.product(*list(chunk_idx)))
    shapes = list(itt.product(*chunks))    

    assert len(shapes) == len(beg_indices)

    chunk_slices = [
        tuple(slice(ibeg, ibeg + sz) for ibeg, sz in zip(idx_bag, shape))  
        for idx_bag, shape in zip(beg_indices, shapes)
    ]   

    print(f"{len(chunk_slices) = }")
    print(f"{chunk_slices[0] = }; {shapes[0] = }")
    print(" ... ")
    print(f"{chunk_slices[-1] = }; {shapes[-1] = }")

    skip_inj = partial(skip_block, data_path=chunked_store, ssh_name=args.twl_nomvar)

    skip_slices_futures = client.map(skip_inj, chunk_slices)
    skip_slices = client.gather(skip_slices_futures)
    # to balance workload between workers skip all-invalid blocks
    chunk_slices = [s for s, skip in zip(chunk_slices, skip_slices) if not skip]
    del skip_slices_futures, skip_slices
    
    compute_inj = partial(compute_coefs_for_block,
                            data_path=chunked_store,
                            ssh_name=args.twl_nomvar,                
                            lat_name=args.lat_nomvar, 
                            t_name=args.time_dim_name,
                            rayleigh=args.rayleigh)

    futures = client.map(compute_inj, chunk_slices)
    ac = as_completed(futures)
    
    del futures

    results = []
    nprocessed = 0
    for batch in ac.batches():
        
        batch_results = client.gather(batch)

        # batch is in the zip to clear futures from memory after processing
        for future, result in zip(batch, batch_results):
            nprocessed += 1
            
            if result is not None:
                results.append(result)

        if nprocessed % 10 == 0:
            print(f"Processed {nprocessed} chunks of {len(chunk_slices)}," 
                  f" collected {len(results)} results so far...")


    return results


def compute_tide_coefficients_entry(args, local_cluster=False):
    """
    Args:
        args (argparse.Namespace): command line arguments
        local_cluster (bool): whether to use a local cluster or a PBS cluster
    Returns:
        pyarrow.Table: table containing utide coefficients
    """

    chunked_store = args.out_dir / get_out_filename(args, suffix=".zarr", prefix="chunked_")
    chunked_store = chunked_store.absolute()
    data = None
    if not chunked_store.exists():
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

        data = data.where(~mask)

    with get_cluster(args, local_cluster=local_cluster) as cluster:

        if not local_cluster:
            cluster.scale(jobs=args.njobs)  # Scale to the number of jobs specified

        # 1. Broadly extend network timeouts to handle high chunk density
        dask.config.set({
            "distributed.comm.timeouts.connect": "60s",      # Default is 30s
            "distributed.comm.timeouts.tcp": "120s",          # Give long tasks breathing room
            "distributed.scheduler.work-stealing": False,     # Turn off work-stealing overhead during P2P
            "distributed.admin.tick.limit": "5s",             # Prevent false-positive warning interruptions
        })

        # 2. Prevent the client from dropping the connection while writing shards
        dask.config.set({"distributed.comm.retry.count": 5})   # Auto-retry dropped packets instead of throwing CommClosedError

    
        with Client(cluster) as client:
    
            print(f"{client.dashboard_link = }", flush=True)

            if data is not None:
                # re-align inupt data for faster tidal analysis
                rechunk_data(data, chunked_store, args)
            else:
                print("Required chunk data already exists, won't re-read the original files")
            
            tb_list = compute_tide_coefficients(client, chunked_store, args)

    return pyarrow.concat_tables(tb_list)


@time_this
def work(args):
    """Main work is done in this method

    Args:
        args (argparse.Namespace): command line arguments
    """

    coef_file = args.out_dir / get_out_filename(args, prefix="utide-coefs", suffix=".parquet")
     
    if coef_file.exists():
        print(f"utide coefficients already computed, reading from {coef_file}")
        coef_table = pq.read_table(coef_file)
    else:
        print(f"Computing utide coefficients for all chunks, saving to parquet: {coef_file = }")
        coef_table = compute_tide_coefficients_entry(args, local_cluster=False)

        print(f"computed utide coefficients for all chunks, saving to parquet: {len(coef_table) = }")   
        pq.write_table(coef_table, coef_file)
        print(f"Saved utide coefficients to {coef_file}")

    
    print("Saving tide data as fields in netcdf format for diagnostics...")
    save_tide_data_as_fields_cdf(coef_table, args, 
                                 coef_file.with_suffix(".nc"))




def save_tide_data_as_fields_cdf(tb_coef: pyarrow.Table, 
                                 args: argparse.Namespace, 
                                 out_file: Path):
    """
    Args:
        tb_coef (pyarrow.Table): table containing utide coefficients
        args (argparse.Namespace): command line arguments
        out_file (Path): path to the output netcdf file
        
    Save amplitude and phase as fields into a netcdf file for diags
    """

    coords = read_spatial_coords(args)

    out_file.unlink(missing_ok=True)

    names_col = pc.struct_field(tb_coef["bunch"], "name")
    cnames = np.unique(np.concatenate(names_col.to_pylist()))

    params = ["amp", "phs", "amp_ci", "phs_ci"]
    param_utide_map = {
        "amp": "A",
        "phs": "g",
        "amp_ci": "A_ci",
        "phs_ci": "g_ci"
    }

    field_dict = {
        f"{cname}_{param}": (coords[args.lat_nomvar].dims, np.zeros(coords[args.lat_nomvar].shape)) 
        for cname in cnames for param in params
    }

    i_arr, j_arr = tb_coef.column("i").to_numpy(), tb_coef.column("j").to_numpy()
    bunch_arr = tb_coef.column("bunch").to_pylist()

    for i, j, bunch in zip(i_arr, j_arr, bunch_arr):
        for cindex, cname in enumerate(bunch["name"]):
            for param in params:
                field_dict[f"{cname}_{param}"][1][i, j] = bunch[param_utide_map[param]][cindex]

    ds_out = xarray.Dataset(
        data_vars=field_dict,
        coords=coords
    )

    ds_out.to_netcdf(out_file, mode="w")

    


def main():
    args = read_cmd_args()
    work(args)
    

def test():
    inp_dir = Path("/home/sssm001/data/ppp7/u2/maestro/gesps_v001_final_cycles_V2/gridpt/gesps.f.output_pre-level/")
    args = argparse.Namespace(
        **dict(
            inp_dir=inp_dir,
            out_dir=Path("test_data/gesps-detide-fields-test/"),
            twl_nomvar="SSH",
            lat_nomvar="lat",
            lon_nomvar="lon",
            surge_nomvar="etas",
            t_exp_beg=pd.Timestamp(2021, 10, 18),
            t_exp_end=pd.Timestamp(2022, 6, 1),
            # t_exp_end=pd.Timestamp(2021, 10, 19),
            dt_exp_hours=pd.Timedelta(hours=12),
            rayleigh=0.9,
            nworkers_per_job=256,
            threads_per_worker=8,
            njobs=8,
            chunk_npoints_x=10,
            chunk_npoints_y=10,
            detide_batch_size=40,
            max_worker_memory="20.8GB",
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
