from pathlib import Path
from main import main

from multiprocessing import Process


do_pa = False
do_fc_default = True
do_fc_raw = False


debug = False

if __name__ == '__main__':
    processes = []

    if debug:
        main(config_path=Path("configs/rdsps/phase2_2019_parallel_run/rdsps_fc_ops_150.cfg"))
        raise Exception

    # run in parallel different cases
    if do_fc_default:
        cfg_paths = [
            "configs/rdsps/phase2_2019_parallel_run/rdsps_fc_ops_150.cfg",
            "configs/rdsps/phase2_2019_parallel_run/rdsps_fc_par_160.cfg"
        ]
        pl = [Process(target=main, kwargs=dict(config_path=Path(p))) for p in cfg_paths]
        processes.extend(pl)

    for p in processes:
        p.start()
