
from pathlib import Path
import argparse
import pandas as pd
from loadprogs.tools import detide_mod_fields
from loadprogs.tools import detide_mod_fields_reconstruct
import fasteners

def main():
    
    out_dir = Path("test_data/utide_analysis/riops-2014-2024")
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    inp_dir = Path("/home/fdu000/.suites/riops/creg12pe_nemo4/hub/ppp7/netcdf/trial/riops/oce/")

    # reconstruct_client = detide_mod_fields_reconstruct.get_client(args=None)

    for year in range(2014, 2025):

        done_file = out_dir / f"{year}.done"
        
        if done_file.exists():
            print(f"done file already exists, skipping: year={year}")
            continue
        
        lock_file = out_dir / f"{year}.lock"
        lock = fasteners.InterProcessLock(lock_file)
        acquired = lock.acquire(blocking=False)

        if not acquired:
            print(f"lock file already exists, skipping: year={year}")
            continue


        files = sorted(inp_dir.glob(f"{year}*1h_grid_T.nc"), key=lambda x: x.name)
        t_exp_beg = pd.to_datetime(files[0].name.split("_")[0], format=r"%Y%m%d%H")
        t_exp_end = pd.to_datetime(files[-1].name.split("_")[0], format=r"%Y%m%d%H")

        # 1. Tidal harmonic analysis parameters
        args = argparse.Namespace(
            **dict(
                # Use multifile if passing a glob/directory of daily files
                inp_dir = inp_dir,
                input_file_type="nc",
                #input_file_path=str(inp_dir / "*.nc"),
                out_dir=out_dir,
                twl_nomvar="zos",
                lat_nomvar="nav_lat",
                lon_nomvar="nav_lon",
                surge_nomvar="etas",
                t_exp_beg=t_exp_beg,
                t_exp_end=t_exp_end,
                rayleigh=0.9,
                nworkers_per_job=256,
                threads_per_worker=4,
                njobs=8,
                chunk_npoints_x=50, 
                chunk_npoints_y=50,
                detide_batch_size=40,
                max_worker_memory="20.8GB",
                filename_suffix="_1h_grid_T.nc",
                mask_file=None,
                mask_nomvar="SSH",
                t_origin_hours=pd.Timedelta(hours=0),
                lead_hour_min=pd.Timedelta(hours=0), 
                lead_hour_max=pd.Timedelta(hours=24*10+1), 
                time_dim_name="time_counter",
                dt_exp_hours=pd.Timedelta(hours=24*10)
            
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
                inp_files=files,
                # Match the NEMO file ending pattern for the target year
                inp_file_suffix="_1h_grid_T.nc",
                inp_filetype="nc",
                out_dir=out_dir_surge,
                twl_nomvar="zos",
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
