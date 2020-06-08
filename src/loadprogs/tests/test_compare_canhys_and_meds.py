import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd


def read_ts_from_file(p: Path):
    col_names = ["year", "month", "day", "hour", "minute", "twl"]
    df = pd.read_csv(p, sep=r"\s+", header=None, names=col_names)
    df["time"] = pd.to_datetime(df[col_names[:-1]])
    df.sort_values("time", inplace=True)
    df.set_index("time", drop=False, inplace=True)
    return df


def test():
    canhys_file_path = Path("~/ksh/sel_data_for_station_canhys/X2780.dat")
    canhys_file_path = canhys_file_path.expanduser()

    meds_file_path = Path("~/data/ppp3/sse_obs/merged/2019_on_20200106/X2780.dat")
    meds_file_path = meds_file_path.expanduser()

    chys = read_ts_from_file(canhys_file_path)
    meds = read_ts_from_file(meds_file_path)
    print(chys.head())
    tslice = slice("2019-11-15", "2019-11-20")

    fig = plt.figure()
    ax = chys.loc[tslice, :].plot(y=["twl"], label=["CanHys", ], ax=fig.gca())
    meds.loc[tslice, :].plot(y=["twl"], label=["MEDS", ], ax=ax)
    fig.savefig("test_canhys_obs.png")


def main():
    test()


if __name__ == '__main__':
    main()
