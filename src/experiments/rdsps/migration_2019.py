from pathlib import Path
from main import main

from multiprocessing import Process

debug = False

if __name__ == '__main__':
    processes = []

    # run in parallel different cases
    cfg_paths = [
        "configs/rdsps/migration_2019/rdsps_fc_ops_160.cfg",
        "configs/rdsps/migration_2019/rdsps_fc_par_170.cfg"
    ]

    if debug:
        for cp in cfg_paths:
            main(config_path=Path(cp))

    else:
        pl = [Process(target=main, kwargs=dict(config_path=Path(p))) for p in cfg_paths]
        processes.extend(pl)

        for p in processes:
            p.start()
