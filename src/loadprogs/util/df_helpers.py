
import pandas as pd

from .constants import COLNAME_TIME, COLNAME_TORIGIN

def apply_rolling(a_df: pd.DataFrame, rolling_period_hours: int, 
                  data_column: int | str = 6) -> pd.DataFrame:
    
    result_db = []
    prev_chunk = None
    window = pd.Timedelta(hours=rolling_period_hours)
    for do, chunk in a_df.groupby(COLNAME_TORIGIN, sort=True):
        inp = chunk
        if prev_chunk is not None:
            inp = pd.concat([inp, prev_chunk[prev_chunk[COLNAME_TIME] < chunk[COLNAME_TIME].min()]])

        inp = inp.sort_values(COLNAME_TIME)

        chunk.loc[:, data_column] = inp[[COLNAME_TIME, data_column]].rolling(window, on=COLNAME_TIME).mean().loc[chunk.index, data_column].values
        result_db.append(chunk)
        
        prev_chunk = chunk
    return pd.concat(result_db, axis=0)