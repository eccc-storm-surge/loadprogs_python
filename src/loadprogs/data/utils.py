# Utility functions for model/observation time series

import pandas as pd
import numpy as np
from scipy import ndimage


def remove_spikes(series: pd.Series, whis=1.5, inplace=False):
    """
    Fill spikes with NA
    :param series:
    :param whis:
    :param inplace:
    :return:
    """

    q3 = series.quantile(q=0.75)
    q1 = series.quantile(q=0.25)
    iqr = q3 - q1

    if not inplace:
        series_ = series.copy()
    else:
        series_ = series

    eliminate = series_.values > (whis * iqr + q3)
    eliminate = (series_.values < (-whis * iqr + q1)) | eliminate

    series_[eliminate] = np.nan

    # discard the days when outliers occur
    if np.any(eliminate):
        # discard the day with outlier
        day = pd.Timedelta(days=1)
        outlier_dates = series_.index[eliminate].floor(day).unique()

        for t in outlier_dates:
            t2 = t + day
            series_[(series_.index >= t) & (series_.index < t2)] = np.nan

    return series_


def remove_edges(series: pd.Series, inplace=False):
    """
    remove edge points (set nans) to the values at the edges of no-data regions
    Args:
        series: input time series
        inplace: if True the input timeseries will be modified in place

    Returns:
        timeseries with extended no-data regions to remove possible trends at the edges

    """
    eliminate = series.diff(periods=1).isnull() | series.diff(periods=-1).isnull()

    # special treatment of the edge points
    if len(series) >= 2:
        eliminate.iloc[0] = eliminate.iloc[1]
        eliminate.iloc[-1] = eliminate.iloc[-2]

    series_ = series
    if not inplace:
        series_ = series.copy()

    series_[eliminate] = np.nan
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
    Remove series from small continuous chunks
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