

from pathlib import Path
import pandas as pd
import numpy as np

from convert_gesla_to_loadprogs import exclude_periods

MOD_STNID_COLIDX = 0
MOD_TIME_COLIDX = 1

STNID_COLNAME = "StnID"

DEFAULT_DATE_FORMAT = r"%Y%m%d%H"
DATE_FORMATS = [
    DEFAULT_DATE_FORMAT
]

def date_parser(t_tok):
    """Date parser

    Args:
        t_tok (str): _description_

    Returns:
        pd.Timestamp: _description_
    """
    for fmt in DATE_FORMATS:
        try:
            return pd.to_datetime(t_tok, format=fmt)
        except ValueError:
            pass

def main():
    """
    stations in the station station list are supposed to be ordered the same
    as in model output files.

    Raises:
        ValueError: _description_
    """
    inp_pth = Path("data/model/hourly")
    out_pth = Path("data/model/clean/hourly")

    stnlist_pth = Path("data/obs/stnlist.csv")

    out_pth.mkdir(exist_ok=True, parents=True)

    df_stn_list = pd.read_csv(stnlist_pth, skiprows=1, header=None)
    df_stn_list.rename({2: STNID_COLNAME}, axis="columns", inplace=True)

    converters = {
        MOD_STNID_COLIDX: str, 
        MOD_TIME_COLIDX: str
    }

    print(df_stn_list.head())
    
    for f_inp in inp_pth.iterdir():
        f_out = out_pth / f_inp.name
        print(f"Cleaning {f_inp} => {f_out}")
        for sep in [",", r"\s+"]:
            try:
                df_mod = pd.read_csv(f_inp, sep=sep, converters=converters)
                
                if len(df_mod.columns) <= 1 or STNID_COLNAME not in df_mod:
                    raise ValueError
                
                df_mod.iloc[:, MOD_TIME_COLIDX] = pd.to_datetime(df_mod.iloc[:, MOD_TIME_COLIDX], format=DEFAULT_DATE_FORMAT)

                print(df_mod.head())
                print(df_mod.columns)

                # exclude data for some periods if requested
                excl = df_mod.iloc[:, MOD_TIME_COLIDX].map(lambda t: False).to_numpy()

                for (t1, t2) in exclude_periods:
                    excl = excl | df_mod.iloc[:, MOD_TIME_COLIDX].between(t1, t2, inclusive="both").to_numpy()


                print(f"Excluding {df_mod.loc[excl, :]}")

                df_mod = df_mod.loc[~excl, :]
                
                # remove stations that exist in outputs but not in the selected lisd
                df_mod = df_mod.loc[df_mod[STNID_COLNAME].isin(df_stn_list[STNID_COLNAME]).to_numpy(), :]
                df_mod.index = pd.Index(data=range(len(df_mod))) # after removing data the index should be updated
                
                
                n_records_per_station = len(df_mod) / len(df_stn_list)

                print(f"{n_records_per_station = }, {len(df_mod) = }, {len(df_stn_list) = }, {(df_mod.index // n_records_per_station).max() = }")
                print(f"{len(df_stn_list) = }; {df_stn_list.columns = }")
                print(df_stn_list.iloc[df_mod.index // n_records_per_station, 2])
                print(df_mod[STNID_COLNAME])

                
                
                # make sure the order of stations in the list is the same as in the data files
                assert np.all(df_stn_list.iloc[df_mod.index // n_records_per_station, 2].values == df_mod[STNID_COLNAME].values)

                df_mod[STNID_COLNAME] = df_stn_list.iloc[df_mod.index // n_records_per_station, 0].values

                print(f"Saving clean model data to: {f_out}")

                for (t1, t2) in exclude_periods:
                    print(f"Checking period {t1} .. {t2}")
                    count_between = sum(df_mod.iloc[:, MOD_TIME_COLIDX].between(t1, t2))
                    assert count_between == 0, f"{count_between = }"

                df_mod.to_csv(f_out, index=False, date_format=DEFAULT_DATE_FORMAT)

            except ValueError as ve:
                print(ve)

        


if __name__ == "__main__":
    main()
