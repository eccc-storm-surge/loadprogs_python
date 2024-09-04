

from pathlib import Path
import pandas as pd

def main():
    inp_pth = Path("data/model/hourly")
    out_pth = Path("data/model/clean")

    stnlist_pth = Path("data/obs/stnlist.csv")

    out_pth.mkdir(exist_ok=True, parents=True)

    df_stn_list = pd.read_csv(stnlist_pth, skiprows=1, header=None)

    print(df_stn_list.head())
    
    for f_inp in inp_pth.iterdir():
        f_out = out_pth / f_inp.name

        for sep in [",", r"\s+"]:
            try:
                df_mod = pd.read_csv(f_inp, sep=sep, converters={0: str})

                if len(df_mod.columns) <= 1 or "StnID" not in df_mod:
                    raise ValueError
                

                print(df_mod.head())
                print(df_mod.columns)


                n_records_per_station = len(df_mod) / len(df_stn_list)


                print(df_stn_list.iloc[df_mod.index // n_records_per_station, 2])
                print(df_mod["StnID"])

                assert (df_stn_list.iloc[df_mod.index // n_records_per_station, 2].values == df_mod["StnID"].values).all()

                df_mod["StnID"] = df_stn_list.iloc[df_mod.index // n_records_per_station, 0].values

                print(f"Saving clean model data to: {f_out}")
                df_mod.to_csv(f_out, index=False)

            except ValueError as ve:
                print(ve)

        


if __name__ == "__main__":
    main()
