"""
Subtract .dat1 - .dat2 and save it to .dat3 
    *.dat? are the files output from loadprogs
"""

from pathlib import Path
import csv
import numpy as np
from loadprogs.util.match_io import read_dat, col_index_to_name_map
from loadprogs.util import constants


def diff(p1: Path, p2: Path, p_res: Path):
    idx_cols = [col_index_to_name_map[i] for i in range(5)]
    df1 = read_dat(p1).set_index(idx_cols)
    df2 = read_dat(p2).set_index(idx_cols)

    df_res = (df1 - df2).reset_index()

    df_res.to_csv(p_res,
            mode="w", 
            float_format="%.7f",
            date_format=constants.OUT_TIME_FORMAT,
            na_rep=str(np.nan),
            index=False, header=False, 
            quoting=csv.QUOTE_NONE)


def main():
    out_dir = Path("data/loadprogs/SURGEMIP_TIDES/")
    out_dir.mkdir(exist_ok=True, parents=True)

    inp_dir_twl = Path("data/loadprogs/SURGEMIP_TWL")
    inp_dir_srg = Path("data/loadprogs/SURGEMIP_SURGE")
    for twl in inp_dir_twl.glob("merged*.dat"):
        srg = inp_dir_srg / twl.name
        tde = out_dir / twl.name

        if tde.exists():
            print(f"{tde} already exists, skipping ... ")
            continue
        
        diff(
            twl, srg, tde
        )
        

if __name__ == "__main__":
    main()
