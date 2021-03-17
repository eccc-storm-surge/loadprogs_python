#!/usr/bin/env python

"""
Create basic .obs file from csv
"""

import argparse
from pathlib import Path
import pandas as pd
from loadprogs.util import obs_file


def main():
    parser = argparse.ArgumentParser(description="create a basis .obs file, to then populate with model_related data")
    parser.add_argument("--csv", required=True, help="Path to the input csv file", type=Path)
    parser.add_argument("--no-col",
                        required=True, help="Index (0-based) of the NO column data in the input file", type=int)
    parser.add_argument("--id-col",
                        required=True, help="Index (0-based) of the ID column data in the input file", type=int)
    parser.add_argument("--la-col",
                        required=True, help="Index (0-based) of the LAT column data in the input file", type=int)
    parser.add_argument("--lo-col",
                        required=True, help="Index (0-based) of the LON column data in the input file", type=int)
    parser.add_argument("--obs",
                        required=True, help="Path to the output .obs file", type=Path)

    parser.add_argument("--select_st_ids", help="space-separated list of station ids (NO column) to select from the csv file",
                        required=False, default=None, nargs="+", type=str)

    parser.add_argument("--skip-rows", help="Number of row to skip at the start of the file.", required=False,
                        default=0, type=int)

    args = parser.parse_args()

    cols = (args.no_col, args.id_col, args.la_col, args.lo_col)
    df = pd.read_csv(args.csv, sep="|", header=None, usecols=cols,
                     skiprows=args.skip_rows,
                     converters={args.no_col: lambda tok: tok.lstrip("0")})
    name_map = {
        args.id_col: "ID",
        args.no_col: "NO",
        args.lo_col: "LON",
        args.la_col: "LAT"
    }

    df["DATA.I"] = -1
    df["DATA.J"] = -1

    df = df.rename(name_map, copy=False, axis=1)

    print(args.select_st_ids)

    print(df.head())
    # for no in df["NO"]:
    #     print(no)

    # select only stations of interest
    if args.select_st_ids is not None:
        df = df[df["NO"].isin(args.select_st_ids)]

    obs_file.save_dataframe_to_obs(df, out_file=args.obs)


if __name__ == '__main__':
    main()
