OBS_HEADER = """Obs 3.1\nStorm surge observation stations\n"""
FLOAT_FORMAT = ".6f"

DATA_COLUMN_WIDTH = 15
ID_COLUMN_WIDTH = 30

import pandas as pd

def save_dataframe_to_obs(df: pd.DataFrame, out_file="stations_Obs.obs"):
    """
    Save dataframe in obs format, adding the states if provided
    :param df: should have columns (NO, ID, LON, LAT, DATA.I and DATA.J) ,
               LON and LAT - are the real station coordinates
               DATA.I and DATA.J - corresponding indices to those coordinates on the model grid
               ID is the station name and NO is the station id.

    input dataframe with
    col0:
    col1: station id
    col2: station name
    col3: i
    col4: j


    :param lons:
    :param lats:
    :param out_file:
    :param station_states:
    """
    with open(out_file, "w") as f:
        f.write(OBS_HEADER)

        # fmt_id = "{:<" + str(ID_COLUMN_WIDTH) + "}"
        # fmt_data_header = "{:<" + str(DATA_COLUMN_WIDTH) + "}"
        # fmt_coord = "{:<" + str(DATA_COLUMN_WIDTH) + FLOAT_FORMAT + "}"
        # fmt_data_int = "{:<" + str(DATA_COLUMN_WIDTH) + "d" + "}"
        # fmt_data_str = "{:<" + str(DATA_COLUMN_WIDTH) + "s" + "}"

        # header = ["ID", "NO", "LAT", "LON", "DATA.I", "DATA.J", ]

        f.write(df.to_string(index_names=False,
                             index=False,
                             formatters={
                                 "ID": lambda tok: f'"{tok}"'
                             }))


        # f.write((fmt_id + len(header[1:]) * fmt_data_header + "\n").format(*header))
        #
        # for i, row in df.iterrows():
        #
        #     f.write(fmt_id.format("\"" + str(row["ID"]) + "\""))
        #     f.write(fmt_data_str.format(row["NO"]))
        #
        #     f.write(fmt_coord.format(df["LAT"]))
        #     f.write(fmt_coord.format(df["LON"]))
        #
        #     f.write(fmt_data_int.format(row["DATA.I"]))
        #     f.write(fmt_data_int.format(row["DATA.J"]))
        #     f.write("\n")
