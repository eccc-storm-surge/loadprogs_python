
from loadprogs.tools.detide_mod_fields import work
from pathlib import Path
import argparse
import pandas as pd

def test():
    out_dir = Path("test_data/utide_analysis/ciopsw/nemo36")
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    args = argparse.Namespace(
        **dict(
            inp_dir=Path("/home/jot000/data/ppp8/maestro_archives/nemo36_pa_w_ois/gridpt/anal/ciops/"),
            out_dir=out_dir,
            twl_nomvar="SSH",
            lat_nomvar="lat",
            lon_nomvar="lon",
            surge_nomvar="etas",
            t_exp_beg=pd.Timestamp(2022, 6, 30, 1),
            # t_exp_end=pd.Timestamp(2022, 7, 1),
            t_exp_end=pd.Timestamp(2022, 9, 30),
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

if __name__ == "__main__":
    test()
