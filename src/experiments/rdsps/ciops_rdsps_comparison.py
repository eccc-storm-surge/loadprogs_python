from pathlib import Path
from main import main

from multiprocessing import Process

debug = False

if __name__ == '__main__':
    processes = []

    # run in parallel different cases
    cfg_paths = [
        "configs/rdsps/ciops/ciopse_201907.cfg",
        "configs/rdsps/ciops/rdsps_201907.cfg"
        # "configs/rdsps/ciops_2016/ciopse_201907.cfg",
        # "configs/rdsps/ciops_2016/rdsps_201907.cfg"
    ]

    if debug:
        for cp in cfg_paths:
            main(config_path=Path(cp))

    else:
        pl = [Process(target=main, kwargs=dict(config_path=Path(p))) for p in cfg_paths]
        processes.extend(pl)

        for p in processes:
            p.start()
