from multiprocessing import Process
from pathlib import Path
from main import main


# Note: to have scores of more independent forecasts, create a link to the forecasts every 36h
# for the final cycles a full forecast of 240h was performed every 36h

if __name__ == '__main__':

    procs = []

    paths = [
        "configs/resps/migration_2019_par_cycle/resps_120_ops.cfg",
        "configs/resps/migration_2019_par_cycle/resps_130_par.cfg"
    ]

    procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    # launch everything
    for p in procs:
        p.start()

    for p in procs:
        p.join()
        if p.exitcode != 0:
            raise Exception(f"{p.name} did not finish successfully. Error code = {p.exitcode}")
