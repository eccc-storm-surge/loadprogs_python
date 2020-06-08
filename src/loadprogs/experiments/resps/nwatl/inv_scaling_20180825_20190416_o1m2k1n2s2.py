from multiprocessing import Process
from pathlib import Path
from loadprogs.main import main


# Note: to have scores of more independent forecasts, create a link to the forecasts every 36h
# for the final cycles a full forecast of 240h was performed every 36h

if __name__ == '__main__':

    procs = []

    twl_dir = Path("configs/resps/resps_perturb_tides_nwatl_m2o1k1n2s2_invert_scaling/twl")

    paths = [

        # twl
        twl_dir / "surge_tidesbc0.cfg",
        twl_dir / "surge0_tidesbc.cfg",
        twl_dir / "surge_tidesbc.cfg",
        twl_dir / "webtide.cfg",
        twl_dir / "tidesbc_only.cfg",
        twl_dir / "surge_only.cfg",
        twl_dir / "surge_only_plus_t0.cfg",

    ]

    procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    # launch everything
    for p in procs:
        p.start()

    for p in procs:
        p.join()
        if p.exitcode != 0:
            raise Exception(f"{p.name} did not finish successfully. Error code = {p.exitcode}")
