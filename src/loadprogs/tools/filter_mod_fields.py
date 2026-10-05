"""
Tidal filter as in NEMO/fortran, by K. Thompson
"""
import pandas as pd
import xarray
from pathlib import Path
import cmcio
import numpy as np


class FilterParams:
    
    def __init__(self, K=None, Mu=None, H=None) -> None:
        self.K: xarray.DataArray = K
        self.H: xarray.DataArray = H
        self.Mu: xarray.DataArray = Mu
    
    @classmethod
    def from_dataset(cls, 
                     ds: xarray.Dataset, 
                     filter_step_seconds=3600.,
                     kappa_input_step_seconds=3600.):

        kappa = ds["kappa"] * filter_step_seconds / kappa_input_step_seconds
        omdt = ds["freq"] * filter_step_seconds

        n = len(kappa)
        n2 = n * 2


        K = np.zeros(n2)
        H = np.zeros(n2)
        M = np.zeros((n2, n2))

        K[::2] = 2.0 * kappa
        H[::2] = 1.0

        cos_vals = np.cos(omdt)
        sin_vals = np.sin(omdt)

        # Set up index grids for block coordinates
        idx = np.arange(n2)
        even = (idx % 2 == 0)
        odd = (idx % 2 == 1)

        # Map the 2x2 rotation blocks efficiently
        M[np.ix_(even, even)] = np.diag(cos_vals)
        M[np.ix_(even, odd)]  = np.diag(-sin_vals)
        M[np.ix_(odd, even)]  = np.diag(sin_vals)
        M[np.ix_(odd, odd)]   = np.diag(cos_vals)

        # 3. Second Loop & Matrix Multiplication: Completely Vectorized
        # KH(ji, jj) = K(ji) * H(jj) is mathematically a Vector Outer Product
        KH = np.outer(K, H)

        Eye = np.eye(n2, n2)



        

def init_filter(ds_constituents: xarray.Dataset):
    """
    compute constant filter params independent of time or position
    
    Args:
        ds_constituents: dataset containing frequencies and kappa for each constituent
    Returns:

    """
    pass    
    

def apply_filter():
    pass




def process_chunk(
        t_beg: pd.Timestamp, 
        t_end: pd.Timestamp,
        flt_dt: pd.Timedelta,
        ds_constit: xarray.Dataset, 
        ssh: xarray.DataArray,
        ds_flt_state_beg: xarray.Dataset,
        is_compute_surge_tide: bool = True):
    """

    Compute state vectors at t_end using state vector at t_beg
    by advancing the filter with ssh

    Args:
        flt_state_beg: initial filter state vectors
                valid at t_beg.
        ds_constit: constituent frequencies and corresponding kappa values
        flt_dt: filter time step (should be the same as time frequency of ssh)
        is_compute_surge_tide: if intermediate, tide and surge calculations are necessary
    Returns:
        ds_flt_state_end: filter state vectors valid at t_end, as xarray.Dataset 
        if is_compute_surge_tide is True:
            compute and return (ssht, etas)

    """

    pass


def main():

    args = {
        "nemo_restart_in_path": Path(
            "/home/sssm001/.suites/gesps-add-etas/catchup-with-ops/hub/ppp7/gridpt/restart/gesps.f.oce/2026033112_012_000.nc"),
        "t_beg": pd.Timestamp(2026, 4, 1),
        "t_end": pd.Timestamp(2026, 4, 1, 12),
        "flt_dt": pd.Timedelta(hours=1),
        "flt_s_out_dir": Path("test_data/tide_filter/test-gesps"),
        "constituents_path": Path(
            "/home/sssm001/.suites/gesps-add-etas/catchup-with-ops/constants/cmde/surge/gesps/tfilt/t_freq_gdsps_20260630.nc"), # gesps uses gdsps parameters
        "ssh_exp_dir": Path(
            "/home/sssm001/.suites/gesps-add-etas/catchup-with-ops/hub/ppp7/work/20260407000000/main/depot.f/gesps.f.output_pre-level"),
        "t_exp_beg": pd.Timestamp(2026, 4, 7),
        "t_exp_end": pd.Timestamp(2026, 4, 7),
        "dt_exp_hours": pd.Timedelta(hours=12),
        "exp_fname_suffix": "_000",
        "is_compute_surge_tides": True, 
        "n_t_chunks": 1
    }

    with xarray.open_dataset(args["constituents_path"]) as ds_constituents:
        print(ds_constituents)
        pass




if __name__ == "__main__":
    main()
