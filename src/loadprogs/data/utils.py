# Utility functions for model/observation time series

import pandas as pd
import numpy as np
from scipy import ndimage


def remove_spikes(series: pd.Series, thresh_std_fraction=0.9, inplace=False):
    """
    Fill spikes with NA
    :param series:
    :param thresh_std_fraction:
    :param inplace:
    :return:
    """
    diff = series.diff().bfill().abs()
    stde = series.std()

    series_ = series
    if not inplace:
        series_ = series.copy()

    series_[diff >= thresh_std_fraction * stde] = np.nan

    return series_


def strip_nans(series: pd.Series):
    """
    Remove nans in the beginning and end of the timeseries
    :param series:
    """

    indices = np.where(~series.isnull())[0]
    i_min, i_max = indices.min(), indices.max()

    return series.iloc[i_min: i_max + 1]


def remove_small_chunks(series: pd.Series, lowest_duration_hours=24, inplace=False):
    """
    Remove data from small continuous chunks
    :param series: assume that it is sorted by time
    :param lowest_duration_hours:
    :param inplace:
    :return:
    """
    #

    labels = pd.Series(data=ndimage.label((~series.isnull()).values)[0], index=series.index)

    #print(series.head(600))

    series_ = series
    if not inplace:
        series_ = series.copy()

    label_counts = series_.groupby(labels).count()

    # assumes that the input series is hourly
    series_.loc[label_counts.loc[labels].values < lowest_duration_hours] = np.nan

    return series_


def break_into_chunks(dataframe: pd.DataFrame, max_chunk_size=1500, eliminate_nodata_chunks_using_cols=("detided", "mod")):
    """
    :param eliminate_nodata_chunks_using_cols:
    :param dataframe:
    :param max_chunk_size: 
    :return: list of series objects broken into chunks 
    """

    res = []
    for i_left in range(0, len(dataframe), max_chunk_size):
        i_right = min(i_left + max_chunk_size, len(dataframe)) - 1

        chunk = dataframe.iloc[i_left:i_right + 1, :]
        if eliminate_nodata_chunks_using_cols is not None:
            eliminate = True

            for c in eliminate_nodata_chunks_using_cols:
                eliminate = np.all(chunk[c].isnull().values) and eliminate

            if eliminate:
                continue

        res.append(chunk)

    return res


def remove_leading_trailing_nans(df: pd.DataFrame, focus_col="twl"):
    """
    Creates a copy of the input df
    :param df:
    :param focus_col:
    :return: subset of the supplied dataset
    """
    focus_data = df[focus_col]
    i_arr = np.where(focus_data.notna().values)[0]

    i_min = min(i_arr)
    i_max = max(i_arr)



    return df.iloc[i_min:i_max + 1, :]