from pathlib import Path
from loadprogs.main import main

from multiprocessing import Process


do_pa = False
do_fc_default = False
do_fc_raw = True

if __name__ == '__main__':
    processes = []
    if do_pa:
        main(config_path=Path("configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_pa_ops_140.cfg"))
        main(config_path=Path("configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_pa_par_150.cfg"))

    # run in parallel different cases
    if do_fc_default:
        # main(config_path=Path("configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_fc_ops_140.cfg"))
        cfg_paths = [
            "configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_fc_ops_140.cfg",
            "configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_fc_par_150.cfg"
        ]
        pl = [Process(target=main, kwargs=dict(config_path=Path(p))) for p in cfg_paths]
        processes.extend(pl)

    if do_fc_raw:
        # main(config_path=Path("configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_fc_ops_140_raw.cfg"))
        cfg_paths = [
            "configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_fc_ops_140_raw.cfg",
            "configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_fc_par_150_raw.cfg"
        ]

        pl = [Process(target=main, kwargs=dict(config_path=Path(p))) for p in cfg_paths]
        processes.extend(pl)

    for p in processes:
        p.start()
