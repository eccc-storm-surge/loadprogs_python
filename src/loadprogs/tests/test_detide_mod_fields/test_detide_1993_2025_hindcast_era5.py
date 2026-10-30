
from pathlib import Path
import argparse
import pandas as pd
from loadprogs.tools import detide_mod_fields
from loadprogs.tools import detide_mod_fields_reconstruct
import fasteners



def process_year(y, inp_dir, out_dir, reconstruct_client=None):
        

        args = argparse.Namespace(
            **dict(
                input_file_type="nc_onefile",
                input_file_path=inp_dir / f"SSH_y{y}.nc",
                out_dir=out_dir,
                twl_nomvar="sossheig",
                lat_nomvar="lat",
                lon_nomvar="lon",
                surge_nomvar="etas",
                rayleigh=0.9,
                nworkers_per_job=256,
                threads_per_worker=8,
                njobs=4,
                chunk_npoints_x=10,
                chunk_npoints_y=10,
                detide_batch_size=40,
                max_worker_memory="20.8GB",
                filename_suffix="_000",
                mask_file=None,
                mask_nomvar="SSH",
                time_dim_name="time_counter"
            )
        )

        coef_file_pth = out_dir / detide_mod_fields.get_out_filename(args, 
                                                                     prefix="utide-coefs", 
                                                                     suffix=".parquet")

        if coef_file_pth.exists():
            print(f"{coef_file_pth} already exists, skipping coef calculation")
        else:
            detide_mod_fields.work(args)


        # call reconstruct, but first need  to implement one netcdf file per dataset.

        out_dir_surge = out_dir / "etas"
        out_dir_surge.mkdir(parents=True, exist_ok=True)
        
        args = argparse.Namespace(
                **dict(
                    inp_dir=inp_dir,
                    inp_file_suffix=f"{y}.nc",
                    inp_filetype="nc",
                    out_dir=out_dir_surge,
                    twl_nomvar="sossheig",
                    tide_coef_file=coef_file_pth,
                    out_filetype="nc",
                    walltime_minutes=150,
                    offset_hours=0,
                    atomic_work_minutes=30 # do one file in 30 minuts, for sure
                )
        )

        detide_mod_fields_reconstruct.work(args, client=reconstruct_client)


def main():
    inp_dir = Path("/home/olh001/Python/anemoi-stormsurge/training-data/gdsps-hindcast/era5-grid/netcdf")
    y_beg = 1993
    y_end = 2025

    reconstruct_client = detide_mod_fields_reconstruct.get_client(args=None)


    for y in range(y_beg, y_end + 1):

        out_dir = Path(f"test_data/utide_analysis/gdsps-hindcast-era5/{y}")
        done_file = out_dir / f"{out_dir.name}.done"
        
        if done_file.exists():
            print(f"done file already exists, skipping: year={y}")
            continue
        
        lock_file = out_dir / f"{out_dir.name}.lock"
        lock = fasteners.InterProcessLock(lock_file)
        acquired = lock.acquire(blocking=False)

        if acquired:
            try:
                print(f"working on year {y} from {y_beg}-{y_end} period.")
                out_dir.mkdir(parents=True, exist_ok=True)

                process_year(y, inp_dir, out_dir, reconstruct_client=reconstruct_client)
                print(f"done with year {y} from {y_beg}-{y_end} period.")
                
                done_file.touch()
            finally:
                lock.release()

    


if __name__ == "__main__":
    main()
