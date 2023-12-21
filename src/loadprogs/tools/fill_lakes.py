__my_doc = """
Fill isolated lakes and create a new bathymetry file.
"""

import argparse
from pathlib import Path
import fstpy
from skimage import measure
import numpy as np
import pandas as pd
from typing import Tuple
import xarray

def read_cmd_args():
    parser = argparse.ArgumentParser(description=__my_doc)

    parser.add_argument("--mask-inp", required=False, type=Path,
                        help="path to a standard file containing @@ field with initial mask")

    parser.add_argument("--mask-inp-name", required=False, type=str, default="SSH",
                            help="name of the mask field to read from --mask-inp standard file")

    parser.add_argument("--bathy-inp", required=True, type=Path,
                        help="path to the input netcdf bathymetry file")
    
    parser.add_argument("--bathy-inp-name", required=False, 
                        type=str, default="Bathymetry", 
                        help="name of the bathymetry field in the "
                             "netcdf file sepcified in --bathy-inp")

    parser.add_argument("--bathy-out", required=True, type=Path,
                        help="path to the output netcdf bathymetry file")
    

    parser.add_argument("--max-lake-size-grdpts", required=False, type=int, default=0,
                        help="maximum lake size in gridpoints to be filled/removed")
    
    parser.add_argument("--nbdy-to-check", required=False, type=int, default=4,
                    help="number of boundary points to check for north folding or east-west periodicity")
    

    parser.add_argument("--min-bathy-limit", required=False, 
                        type=float, default=-np.Inf, const=-np.Inf,
                        help="Minimum bathymetry value to be considered as valid")


    args = parser.parse_args()

    
    assert args.bathy_inp.exists(), f"should exist: {args.bathy_inp}"

    return args

def get_stdll(dfm: pd.DataFrame, ipdict) -> Tuple[np.ndarray]:
    """
    read 2d lon and lat arrays corresponding to ipdict
    """
    cnames = [">>", "^^"]
    sel = dfm["nomvar"].isin(cnames)

    for k, v in ipdict.items():
        print(k, v)
        sel = sel & (dfm.loc[:, k] == v)

    # read in coords data into memory
    dfc = fstpy.compute(dfm.loc[sel, :])
    
    lons, lats = [dfc.loc[dfc["nomvar"] == cn, "d"].iloc[0] for cn in cnames]
    return lons, lats

def get_cdfll(pth: Path):
    """
    read 2d lon and lat arrays from netcdf, as lon/lat in standard file are 0 for eliminated procs
    """
    with xarray.open_dataset(pth) as ds:
        return [ds[k].values for k in ["nav_lon", "nav_lat"]]


def simplify_equivalences(equiv_map: dict) -> dict:
    res = {}
    for k, v in equiv_map.items():
        while v in equiv_map:
            v = equiv_map[v]
        res[k] = v

    return res


def work(args):
    

    lons, lats = get_cdfll(args.bathy_inp)

    if args.min_bathy_limit == -np.Inf:
        print(f"Using mask file to define wet regions: {args.mask_inp}")
        assert args.mask_inp.exists(), f"should exist: {args.mask_inp}"
        dfm = fstpy.StandardFileReader(args.mask_inp, decode_metadata=True).to_pandas()
        sel = (dfm["nomvar"] == args.mask_inp_name) & (dfm["typvar"] == "@@")
        df_sel = dfm.loc[sel, :].iloc[0:1, :]
        msk = fstpy.compute(df_sel)["d"].iloc[0]

        # try to align the mask and the bathymetry fields
        if msk.shape != lons.shape:
            msk = msk.T

        assert msk.shape == lons.shape, f"Mask and bathymetry shapes mismatch: {msk.shape = } and {lons.shape = }"

    else:
        print(f"Using bathymetry to define wet regions: bathy >= {args.min_bathy_limit} considered wet")
        with xarray.open_dataset(args.bathy_inp) as ds:
           vals = ds[args.bathy_inp_name].values
           msk = vals >= args.min_bathy_limit
 


    labels = measure.label(msk, connectivity=1)
    

    # get matrix boundary
    bdy_msk = np.ones_like(msk, dtype=bool)
    n = args.nbdy_to_check

    i_2d, j_2d = np.indices(bdy_msk.shape)

    assert n < min(*msk.shape), f"--nbdy-to-check ({n}) " \
                                 "exceeds grid dimensions ({msk.shape})"
    if n > 0:
        bdy_msk[n:-n, n:-n] = False

    i_1d = i_2d[bdy_msk]
    j_1d = j_2d[bdy_msk]
    lon_1d = lons[bdy_msk]
    lat_1d = lats[bdy_msk]
    colors_1d = labels[bdy_msk]
    
    # list of sets of equivalent colors
    equiv_colors = {}

    bdy_info = pd.DataFrame.from_dict({
        "i": i_1d, "j": j_1d,
        "lon": np.round(lon_1d * 10 ** 6), "lat": np.round(lat_1d * 10 ** 6),
        "color": colors_1d
    })
    
    for c, g in bdy_info.groupby(["lon", "lat"]):
        if len(g) >= 2 and len(g["color"].drop_duplicates()) > 1:
            current_colors = sorted(g["color"])
            equiv_colors.update({ci: current_colors[0] for ci in current_colors[1:]})

    # simplify equivalent colors if needed
    equiv_colors = simplify_equivalences(equiv_map=equiv_colors)

    for c1, c2 in equiv_colors.items():
        labels[labels == c1] = c2

    region_props = measure.regionprops(labels)

    to_fill = np.zeros_like(msk, dtype=bool)
    for props in region_props:
        # renamed in the latest versions of skimage to num_pixels
        if props.area <= args.max_lake_size_grdpts:
            to_fill[labels == props.label] = True

    print(f"n={to_fill.sum()} points to fill")

    with xarray.open_dataset(args.bathy_inp) as ds:
        vals = ds[args.bathy_inp_name].values
        vals[to_fill] = 0.0 # fill selected lakes

        ds[args.bathy_inp_name] = (ds[args.bathy_inp_name].dims, vals)
        ds["regions"] = (ds[args.bathy_inp_name].dims, labels.astype(np.float32))
        ds.to_netcdf(args.bathy_out)


def main():
    args = read_cmd_args()
    work(args)


def test():
    data_root = Path("/home/olh001/Python/loadprogs_python/data/gdsps/fill-bathy")
    args = argparse.Namespace()
    args.mask_inp = data_root / "2023021400_"
    args.mask_inp_name = "SSH"
    args.bathy_inp = data_root / "bathy64TS.nc"
    args.bathy_inp_name = "Bathymetry"
    args.bathy_out = data_root / "bathy65TS_test.nc"
    args.nbdy_to_check = 4
    args.max_lake_size_grdpts = 10000
    args.min_bathy_limit = -np.Inf

    assert not args.bathy_out.exists(), f"Output already exists, please move or rm: {args.bathy_out}"

    work(args)

if __name__ == "__main__":

    is_test = True

    if is_test:
        test()
    else:
        main()

