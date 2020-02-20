import argparse
import csv
import datetime
import logging
import sqlite3
import pandas as pd
from pathlib import Path

# Custom modules
import constants


def main():

    st_info = pd.read_csv(constants.STATIONS_INFO_FILE, skiprows=2,
                                              usecols=(1,),
                                              names=["real"],
                                              header=0,
                                              sep=r"\s+").astype(str)

    st_info["real"] = st_info["real"].map(lambda x: x.zfill(5))

    #print(st_info.head().to_string())
    #print(st_info.dtypes)

    """
    Example stations info file
    >>> print(st_info.head().to_string())
        real
    0  8443970
    1  8418150
    2  8413320
    3  8410140
    4    00065
    """

    translator = pd.read_csv(constants.STATION_ID_TRANSLATION_DICT, usecols=(1, 2, 3),
                                                          names=["canhys", "real", "station_name"],
                                                          sep="|").astype(str)

    #print(translator.head().to_string())                                                          
    #print(translator.dtypes)                                        

    """
    Example CanHys information file
    >>> print(translator.head().to_string())
    canhys     real                    station_name
    0  10002  05AA008        Crowsnest River At Frank
    1  10004  05AA011       Mill Creek Near The Mouth
    2  10006  05AA022  Castle River Near Beaver Mines
    3  10008  05AA024       Oldman River Near Brocket
    4  10012  05AA028  Castle River At Ranger Station
    """

    canhys_real_ids_and_name = st_info.merge(translator, left_on="real", right_on="real")
    empty_start_and_end_date = pd.DataFrame({"start_date":[], "end_date":[]})
    
    final_df = canhys_real_ids_and_name.join(empty_start_and_end_date) \
                                       .fillna(value=-1) \
                                       .reindex(columns=["canhys", "real", "station_name", "start_date", "end_date"]) \
                                       .astype({"start_date": "int32", "end_date": "int32"})
    print(final_df)

    stations_checklist = set(canhys_real_ids_and_name["canhys"])

    for sql_file in constants.CANHYS_SQL_DIR.iterdir():
        print(f"file: {sql_file}")
        conn = sqlite3.connect(str(sql_file))
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT DISTINCT(siteid) FROM datavalue")
        except sqlite3.OperationalError:
            continue

        for st_id, in cursor.fetchall():
            st_id = str(st_id)

            if st_id not in stations_checklist:
                #print(f"skipping {st_id}")
                continue

            foo = pd.read_sql(sql=f'''SELECT min(datetimeutc) FROM datavalue
                                      WHERE siteid={st_id}
                                      UNION ALL
                                      SELECT max(datetimeutc) FROM datavalue
                                      WHERE siteid=({st_id});''',
                              con=conn,
                              columns=["datetimeutc"]).rename(index={0:"start", 1:"end"}).to_dict(orient="dict")["min(datetimeutc)"]

            start, end = map(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S"), foo.values())
            row_selection = (final_df.canhys == st_id)

            df_start = final_df.loc[row_selection, "start_date"].iat[0]
            df_end = final_df.loc[row_selection, "end_date"].iat[0]

            if df_start == -1 or df_start > start:
                final_df.loc[row_selection, "start_date"] = start
            
            if df_end == -1 or df_end < start:
                final_df.loc[row_selection, "end_date"] = end

    print(final_df.to_string())


if __name__ == "__main__":
    import time
    t0 = time.perf_counter()
    main()
    print(f"Execution time: {time.perf_counter() - t0}")

