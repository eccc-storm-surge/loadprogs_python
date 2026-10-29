
from pathlib import Path
import argparse
import pandas as pd
from loadprogs.tools import detide_mod_fields
from loadprogs.tools import detide_mod_fields_reconstruct
import fasteners

def main():
    
    out_dir = Path("test_data/utide_analysis/gdsps-hindcast-orca12")
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    inp_dir = Path("/home/jit000/data/ppp8/gdsps/data")

    # 1. Tidal harmonic analysis parameters
    args = argparse.Namespace(
        **dict(
            # Use multifile if passing a glob/directory of daily files
            inp_dir = inp_dir,
            input_file_type="nc",
            #input_file_path=str(inp_dir / "*.nc"),
            out_dir=out_dir,
            twl_nomvar="sossheig",
            lat_nomvar="nav_lat",
            lon_nomvar="nav_lon",
            surge_nomvar="etas",
            t_exp_beg=pd.Timestamp(2023, 1, 1, 0),
            t_exp_end=pd.Timestamp(2023, 12, 31),
            rayleigh=0.9,
            nworkers_per_job=256,
            threads_per_worker=8,
            njobs=8,
            chunk_npoints_x=50, 
            chunk_npoints_y=50,
            detide_batch_size=40,
            max_worker_memory="20.8GB",
            filename_suffix=".nc",
            mask_file=None,
            mask_nomvar="SSH",
            t_origin_hours=pd.Timedelta(hours=0),
            lead_hour_min=pd.Timedelta(hours=0), 
            lead_hour_max=pd.Timedelta(hours=25), 
            time_dim_name="time_counter",
            dt_exp_hours=pd.Timedelta(hours=24)
        
        )
    )

    coef_file_pth = out_dir / detide_mod_fields.get_out_filename(
        args, prefix="utide-coefs", suffix=".parquet"
    )

    if coef_file_pth.exists():
        print(f"{coef_file_pth} already exists, skipping coef calculation")
    else:
        detide_mod_fields.work(args)

    # 2. Residual surge reconstruction parameters
    out_dir_surge = out_dir / "etas"
    out_dir_surge.mkdir(parents=True, exist_ok=True)

    args_recon = argparse.Namespace(
        **dict(
            inp_dir=inp_dir,
            # Match the NEMO file ending pattern for the target year
            inp_file_suffix=".nc",
            inp_filetype="nc",
            out_dir=out_dir_surge,
            twl_nomvar="sossheig",
            surge_nomvar="etas",
            tide_coef_file=coef_file_pth,
            out_filetype="nc",
            walltime_minutes=150,
            offset_hours=0,
            atomic_work_minutes=30,
            nnodes=5,
            total_cpu_per_node=256,
            threads_per_worker=8,
            total_memory = "700GB"
        )
    )

    
    detide_mod_fields_reconstruct.work(args_recon, client=None)


if __name__ == "__main__":
    main()
