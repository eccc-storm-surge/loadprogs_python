#!/usr/bin/env python3
from pathlib import Path
import argparse
import xarray
import itertools as itt
import pyresample
from enum import Enum
import numpy as np

class Method(Enum):
    NEAREST = "nearest"
    CONSTANT = "constant"
    SKIP = "skip"




def read_cmd_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-files", required=True,
                        nargs="+", 
                        help="path(s) to input files")

    parser.add_argument("--dst-dir", required=False, type=Path, default=Path("."),
                        help="path to the destination directory")

    parser.add_argument("--dst-fn-prefix", required=False, default="",
                        help="prefix of output file names")

    parser.add_argument("--known-varnames", required=False, nargs="+", default=None,
                        help="List of known variable names to be considered, "
                             "other variables will be ignored if specified")

    parser.add_argument("--method", required=False, default=Method.NEAREST, 
                        type=Method, 
                        help="try to fill missing values")

    
    return parser.parse_args()



def  constant_impl(dsi, fill_value) -> xarray.Dataset:
    """
    fill missing value points with fill_value
    """
    
    for v, da in dsi.variables.items():
        da = dsi[v]

        # check if filling is required
        if da.notnull().all():
            print(f"No missing found for {v}, skipping ...")
            continue
        else:
            print(f"Filling missing for variable={v}")

        dsi[v] = da.where(da.notnull(), fill_value)

    return dsi


def nearest_impl(dsi, 
                 coord_names: dict, 
                 memo_var_level_to_grids = {}) -> xarray.Dataset:
    """
    Args:
        memo_var_level_to_grids: dict for caching on level and variable name
    """

    depth_name = coord_names["depth_name"]
    time_name = coord_names["time_name"]
    lon_name = coord_names["lon_name"]
    lat_name = coord_names["lat_name"]

    
    for v, _ in dsi.variables.items():
        
        da = dsi[v].copy()

        # check if filling is required
        if da.notnull().all():
            print(f"No missing found for {v}, skipping ...")
            continue

        idx = None
        if time_name in da.coords:
            idx = da.coords[time_name]

        if depth_name in da.coords:
            idx = da.coords[depth_name] if idx is None else itt.product(idx, da.coords[depth_name])
        
        
        grid_keys = [] # for reusing grids on the same vert level for the same variable
        da_2d_store = []
        if idx is None:
            grid_key = (v, )
            da_2d_store.append(da)
            grid_keys.append(grid_key)
        else:
            for item in idx:
                if len(item) == 0:
                    crit = {time_name: item}
                    grid_key = (v, )
                elif len(item) == 2:
                    crit = dict(zip([time_name, depth_name], item))
                    grid_key = (v, depth_name, item[1].values.item())
                else:
                    raise ValueError(f"Not sure how to handle item={item}; len(item)={len(item)}")
                
                da_2d_store.append(da.sel(crit))
                grid_keys.append(grid_key)
                
        for grid_key, dai in zip(grid_keys, da_2d_store):
            bad = dai.isnull()
            
            if not bad.any() or bad.all():
                continue

            if not grid_key in memo_var_level_to_grids:
                lon_, lat_ = [dai.coords[k] for k in [lon_name, lat_name]]
                lon_src, lat_src = lon_.values[~bad], lat_.values[~bad]
                lon_dst, lat_dst = lon_.values[bad], lat_.values[bad]

                src_grid = pyresample.SwathDefinition(lons=lon_src, lats=lat_src)
                dst_grid = pyresample.SwathDefinition(lons=lon_dst, lats=lat_dst)
                
                memo_var_level_to_grids[grid_key] = (src_grid, dst_grid)


            src_grid, dst_grid = memo_var_level_to_grids[grid_key]

            dst_val_1d = pyresample.kd_tree.resample_nearest(src_grid, dai.values[~bad], 
                        dst_grid, radius_of_influence=1e10)

            # print(bad.shape, dai.shape, bad.sum())                    
            dai.values[bad] = dst_val_1d
        
        dsi[v] = da

    return dsi
                


def nearest(args, coord_names):
    """
    fill missing with nearest non-missing
    """
    memo_var_level_to_grids = {} # for caching on level and variable name
    for inp in args.src_files:
        inp = Path(inp)
        with xarray.open_dataset(inp) as dsi:
            dsi = nearest_impl(dsi, coord_names, memo_var_level_to_grids)
            dsi.load().to_netcdf(args.dst_dir / f"{args.dst_fn_prefix}{inp.name}")


def work(args):

    coord_names = dict(
        depth_name = "depth",
        time_name = "time",
        lon_name = "lon",
        lat_name = "lat")

    if args.method == Method.NEAREST:
        nearest(args, coord_names=coord_names)
    elif args.method == Method.CONSTANT:
        raise NotImplementedError("")
    else:
        raise NotImplementedError(f"Method {args.method} not implemented yet.")



def main():
    args = read_cmd_args()    
    work(args)


if __name__ == "__main__":
    import time
    t0 = time.time()
    main()
    print(f"filling na took {time.time() - t0} seconds")