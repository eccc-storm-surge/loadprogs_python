from loadprogs.tools.detide_mod_fields import work
from pathlib import Path
import argparse
import pandas as pd

def test_nemo36():
    out_dir = Path("test_data/utide_analysis/ciopse/nemo36")
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    args = argparse.Namespace(
        **dict(
            inp_dir=Path("/home/yls000/data/sitestore8/maestro/IC5/nemo36_pa_e_ois/hub/gridpt/anal/ciops"),
            out_dir=out_dir,
            twl_nomvar="SSH",
            lat_nomvar="lat",
            lon_nomvar="lon",
            surge_nomvar="etas",
            t_exp_beg=pd.Timestamp(2024, 6, 30, 1),
            # t_exp_end=pd.Timestamp(2022, 7, 1),
            t_exp_end=pd.Timestamp(2024, 9, 30),
            dt_exp_hours=pd.Timedelta(hours=1),
            rayleigh=0.9,
            nworkers_per_job=256,
            threads_per_worker=8,
            njobs=4,
            chunk_npoints_x=10,
            chunk_npoints_y=10,
            detide_batch_size=40,
            max_worker_memory="20.8GB",
            filename_suffix="_000",
            t_origin_hours=pd.Timedelta(hours=0),
            lead_hour_min=pd.Timedelta(hours=0),
            lead_hour_max=pd.Timedelta(hours=1), # not inclusive
            mask_file=None,
            mask_nomvar="SSH",
            time_dim_name="time"
        )
    )
    work(args)

def test_nemo4():
    out_dir = Path("test_data/utide_analysis/ciopse/nemo4_iodef_z0_1x10m3_ahmt_32_csmc_3")
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    args = argparse.Namespace(
        **dict(
            inp_dir=Path("/home/yls000/data/sitestore8/maestro/IC5/nemo4_iodef_z0_1x10m3_ahmt_32_csmc_3/hub/gridpt/anal/ciops_ssh"),
            out_dir=out_dir,
            twl_nomvar="SSH",
            lat_nomvar="lat",
            lon_nomvar="lon",
            surge_nomvar="etas",
            t_exp_beg=pd.Timestamp(2024, 6, 30, 1),
            # t_exp_end=pd.Timestamp(2022, 7, 1),
            t_exp_end=pd.Timestamp(2024, 9, 30),
            dt_exp_hours=pd.Timedelta(hours=1),
            rayleigh=0.9,
            nworkers_per_job=256,
            threads_per_worker=8,
            njobs=4,
            chunk_npoints_x=10,
            chunk_npoints_y=10,
            detide_batch_size=40,
            max_worker_memory="20.8GB",
            filename_suffix="_000",
            t_origin_hours=pd.Timedelta(hours=0),
            lead_hour_min=pd.Timedelta(hours=0),
            lead_hour_max=pd.Timedelta(hours=1), # not inclusive
            mask_file=None,
            mask_nomvar="SSH",
            time_dim_name="time"
        )
    )
    work(args)

def main():
    test_nemo36()
    test_nemo4()


if __name__ == "__main__":
    main()
