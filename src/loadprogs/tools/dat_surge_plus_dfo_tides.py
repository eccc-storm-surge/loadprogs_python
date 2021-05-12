"""
Add DFO tides from the operational sqlite file to the surge created in .dat file by loadprog

"""
import argparse
from collections import namedtuple
from pathlib import Path
import pandas as pd

from loadprogs.util.match_io import read_dat


def work(params):
    dat_inp = read_dat(params.src_surge_dat)
    pass


def main():
    parser = argparse.ArgumentParser(description="Add DFO tides from an sqlite file to the .dat file containing surge, "
                                                 "and save the updated .dat file")

    parser.add_argument("--src_surge_dat", required=True, type=Path,
                        help="Path to the input dat file with surge")
    parser.add_argument("--src_tide_sqlite", required=True,
                        type=Path, help="Path to the input sqlite file with tides")

    parser.add_argument("--dst_twl_dat", type=Path, required=True,
                        help="destination file twl_dat=surge_dat+tide_sqlite")

    args = parser.parse_args()

    work(args)


def test():
    Args = namedtuple("Args", "src_surge_dat src_tide_sqlite dst_twl_dat")

    params = Args(src_surge_dat=Path(""),
                  src_tide_sqlite=Path(""),
                  dst_twl_dat=Path("data/tests/dat_surge_plus_dfo_tides.dat"))

    params.dst_twl_dat.mkdir(parents=True, exist_ok=True)

    work(params)


if __name__ == '__main__':
    main()
