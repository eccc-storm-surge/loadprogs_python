"""
* For GESPS abd Adcirc take loadprogs outputs and compute daily max
* For JRC data get obs data from the previous point and insert data 
* the resulting data should be the usable in surge_validation
"""
from convert_gesla_to_loadprogs import exclude_periods
from pathlib import Path
import pandas as pd
import numpy as np
import csv
from loadprogs.util import constants

SKIP_SHORT_IDS = [] # skip due to duplicates



def save_to_loadprogs_file(df, pth):
    """
    Save dataframe df to the file pth in the form of loadprogs output

    Args:
        df (_type_): _description_
        pth (_type_): _description_
    """
    df.to_csv(pth, float_format="%.7f",
                            date_format=constants.OUT_TIME_FORMAT,
                            na_rep=str(np.nan),
                            index=False, header=False, 
                            quoting=csv.QUOTE_NONE)



def compute_daily_max_impl(inp_pth, out_pth):
    """
    file fmt example

    0,san_francisco_ca-551a-usa-uhslc,37.8070000,-122.4650000,201301010000,-0.0178170,-0.0287506
    0,san_francisco_ca-551a-usa-uhslc,37.8070000,-122.4650000,201301010100,0.0080246,0.0349640
    0,san_francisco_ca-551a-usa-uhslc,37.8070000,-122.4650000,201301010200,0.0072624,0.0362508
    0,san_francisco_ca-551a-usa-uhslc,37.8070000,-122.4650000,201301010300,0.0648618,0.0037878
    0,san_francisco_ca-551a-usa-uhslc,37.8070000,-122.4650000,201301010400,0.0653951,0.0132821
    0,san_francisco_ca-551a-usa-uhslc,37.8070000,-122.4650000,201301010500,0.0298876,-0.0257300
    0,san_francisco_ca-551a-usa-uhslc,37.8070000,-122.4650000,201301010600,0.0248505,-0.0101059
    0,san_francisco_ca-551a-usa-uhslc,37.8070000,-122.4650000,201301010700,-0.0012427,0.0222249

    Args:
        inp_pth (Path): input loadprogs file / hourly
        out_pth (Path): output loadprogs file / daily max
    """
    df_inp = pd.read_csv(inp_pth, sep=",", header=None, converters={4: str})
    df_inp[4] = pd.to_datetime(df_inp[4], format=r"%Y%m%d%H%M")

    df_inp["day"] = pd.to_datetime(df_inp[4].dt.date)

    df_out = df_inp.groupby([0, 1, 2, 3, "day"]).agg(
        o_max = (5, "max"),
        m_max = (6, "max")
    )
    df_out = df_out.reset_index()
    df_out["day"] = pd.to_datetime(df_out.reset_index()["day"])
    df_out = df_out[[0, 1, 2, 3, "day", "o_max", "m_max"]]
    save_to_loadprogs_file(df_out, out_pth)
    return df_out

def compute_daily_max(lbl_to_inp, lbl_to_out):
    """
    Use loadprogs outputs to compute daily max values and save in loadprogs format
    """

    lbl_to_df = {}
    
    for lbl, inp_pth in lbl_to_inp.items():
        out_pth = lbl_to_out[lbl]
        lbl_to_df[lbl] = compute_daily_max_impl(inp_pth=inp_pth, out_pth=out_pth)

    return lbl_to_df


def get_data_for_station(pth: Path):
    """
    Parse data from pth / provided by JRC

    Args:
        pth (Path): _description_
    """
    df = pd.read_csv(pth, sep=r"\s+", skiprows=2, 
                     header=None)
    
    col_to_name = {0: "year", 1: "month", 2: "day", 3: "hour"}

    df["time"] = pd.to_datetime(
        df.rename(col_to_name, axis="columns")[list(col_to_name.values())])

    return df.set_index("time")

def add_obs_to_mod_data(mod_dir_path: Path, template_df: pd.DataFrame, 
                        stnlist_file: Path,
                        stid_col=1, time_col="day"):
    
    df_list = [] 

    stnlist_df = pd.read_csv(stnlist_file)

    stid_to_pth = {}
    for p in mod_dir_path.iterdir():
        stn_index = int(p.name.split("_")[1])
        stid = stnlist_df.loc[stn_index - 1, "FILE NAME"]
        stid_to_pth[stid] = p
        print(f"{stid} => {p}")

    for stid, data in template_df.groupby(stid_col):
        if stid in stid_to_pth:
            p = stid_to_pth[stid]

            mod = get_data_for_station(p)

            data["m_max"] = mod.loc[data[time_col], :].iloc[:, -1].values
            data[stid_col] = stid
            df_list.append(data)

    return pd.concat(df_list)


def main():

    jrc_stnlist = Path("data/model/daily_max/SurgeMIP_stnlist.csv")

    label_to_inp_pth = {
        "ECCC_GDSPS": Path("/home/olh001/Python/surgemip/data/loadprogs/SURGEMIP_SURGE/merged_ECCC_GDSPS_2013-2018.dat"),
        "UND-ANL_GADCIRC-btp": Path("/home/olh001/Python/surgemip/data/loadprogs/SURGEMIP_SURGE/merged_UND-ANL_GADCIRC-btp_2013-2018.dat")
    }

    jrc_dir = Path("/home/olh001/Python/surgemip/data/model/daily_max/JRC_dailyMaxSurgeLevel")

    dailymax_out_dir = Path("data/loadprogs/SURGEMIP_SURGE_DAILYMAX/")
    dailymax_out_dir.mkdir(parents=True, exist_ok=True)
    label_to_dailymax_out_pth = {
        label: dailymax_out_dir / pth.name for label, pth in label_to_inp_pth.items()
    }

    lbl_to_df = compute_daily_max(label_to_inp_pth, label_to_dailymax_out_pth)

    # add obs column to jrc data
    jrc_label = "JRC"
    save_to_loadprogs_file(
        add_obs_to_mod_data(jrc_dir, lbl_to_df["ECCC_GDSPS"], stnlist_file=jrc_stnlist), 
        dailymax_out_dir / f"merged_{jrc_label}_2013-2018.dat"
    )


if __name__ == "__main__":
    main()

