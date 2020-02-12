from multiprocessing import Process
from pathlib import Path
from main import main


if __name__ == '__main__':

    procs = []

    paths = [
        "configs/resps/phase_2_2019_parallel/exp_110.cfg",
        "configs/resps/phase_2_2019_parallel/par_120.cfg",
        "configs/resps/phase_2_2019_parallel/par_120lev.cfg",
        "configs/resps/phase_2_2019_parallel/par_120_apm.cfg",
        "configs/resps/phase_2_2019_parallel/par_120lev_apm.cfg",
    ]

    procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    # launch everything
    for p in procs:
        p.start()

