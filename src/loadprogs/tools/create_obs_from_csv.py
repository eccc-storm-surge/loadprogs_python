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

    args = parser.parse_args()

    cols = (args.no_col, args.id_col, args.la_col, args.lo_col)
    df = pd.read_csv(args.csv, sep="|", header=None, usecols=cols)
    name_map = {
        args.id_col: "ID", args.no_col: "NO", args.lo_col: "LON", args.la_col: "LAT"
    }

    df["DATA.I"] = -1
    df["DATA.J"] = -1

    df = df.rename(name_map, copy=False, axis=1)

    obs_file.save_dataframe_to_obs(df, out_file=args.obs)


if __name__ == '__main__':
    main()
