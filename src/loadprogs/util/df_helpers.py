
import pandas as pd

from .constants import COLNAME_TIME, COLNAME_TORIGIN

def apply_rolling(a_df: pd.DataFrame, rolling_period_hours: int, 
                  data_column=6) -> pd.DataFrame:
    
    result_db = []
    window = pd.Timedelta(hours=rolling_period_hours)
    for do, chunk in a_df.groupby(COLNAME_TORIGIN, sort=True):
        inp = chunk
        inp = inp.sort_values(COLNAME_TIME)
        chunk.loc[:, data_column] = inp[[COLNAME_TIME, data_column]].iloc[::-1, :].rolling(window, on=COLNAME_TIME).mean().loc[chunk.index, data_column].values
        result_db.append(chunk)
        
    return pd.concat(result_db, axis=0)