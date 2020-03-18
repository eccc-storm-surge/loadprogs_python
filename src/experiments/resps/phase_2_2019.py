from multiprocessing import Process
from pathlib import Path
from main import main


# Note: to have scores of more independent forecasts, create a link to the forecasts every 36h
# for the final cycles a full forecast of 240h was performed every 36h

if __name__ == '__main__':

    procs = []

    # each 36h
    paths = [
        # "configs/resps/phase_2_2019_fc/E2CPL60E16V1.cfg",
        # "configs/resps/phase_2_2019_fc/exp_during_E2CPL60E16V1.cfg",
        "configs/resps/phase_2_2019_fc/E2CPL60H17V1.cfg",
        "configs/resps/phase_2_2019_fc/exp_during_E2CPL60H17V1.cfg"
    ]

    procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    # launch everything
    for p in procs:
        p.start()

