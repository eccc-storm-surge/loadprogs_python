

from pathlib import Path
import sqlite3
import pandas as pd

"""
# Canhys schema
$ sqlite3 /home/swav000/data/ppp5/rarc/CANHYS/2021010100_sql .schema
CREATE TABLE datavalue(
  sourceid INT,
  siteid INT,
  variableid INT,
  datetimeutc TEXT,
  datavalue REAL
);

"""

TIME_COL = "datetimeutc"

def main():
    exp_dt = pd.Timedelta(hours=6)
    inp_dir = Path("/home/olh001/Python/download_station_info/data/ushlc/fast_2019-2022")
    out_dir = Path(f"data/uhslc/{inp_dir.name}_canhys")

    out_dir.mkdir(parents=True, exist_ok=True)

    df_list = []
    print("Reading input data ...")
    for inp_pth in list(inp_dir.iterdir()):
        if not inp_pth.name.startswith("X"):
            continue
        
        print(f"reading {inp_pth}")
        try:
            df = pd.read_csv(inp_pth, header=None, sep=r"\s+")
        except pd.errors.EmptyDataError:
            print(f"No data in {inp_pth}, skipping ...")
            continue

        date_colnames = {0: "year", 1: "month", 2: "day", 3: "hour", 4: "minute"}
        df.rename(date_colnames, axis="columns", inplace=True)
        df[TIME_COL] = pd.to_datetime(df[list(date_colnames.values())])
        df.rename({5: "datavalue"}, axis="columns", inplace=True)
        df["siteid"] = int(inp_pth.name[1:-4])
        df["sourceid"] = 12
        df["variableid"] = 100
        df.drop(list(date_colnames.values()), inplace=True, axis="columns")
        df_list.append(df)

    print("Finished reading input data!")
    df_all = pd.concat(df_list, axis="index")

    df_all["t_exp"] = (df_all[TIME_COL] - exp_dt / 2).dt.ceil(exp_dt)
    print(f"saving data to {out_dir}")
    for t_exp, data in df_all.groupby("t_exp"):
        out_pth = out_dir / f"{t_exp:%Y%m%d%H}_sql"
        out_pth.unlink(missing_ok=True)
        data.drop("t_exp", axis="columns", inplace=True)

        print(f"Saving {out_pth}")

        with sqlite3.connect(out_pth) as con:
            data.to_sql("datavalue", con=con, index=False)
        
        
if __name__ == "__main__":
    main()
