from multiprocessing import Process
from pathlib import Path

from main import main


if __name__ == '__main__':
    do_12_hourly = False
    do_36_hourly = False
    do_dc_101 = True

    procs = []

    # each 12h
    if do_12_hourly:
        main(config_path=Path("configs/rdsps/forecast/FC70E16V2.cfg"))
        main(config_path=Path("configs/rdsps/forecast/op_during_FC70E16V2.cfg"))

    # each 36h
    if do_36_hourly:
        paths = [
            "configs/rdsps/forecast_36h/FC70E16V2.cfg",
            "configs/rdsps/forecast_36h/op_during_FC70E16V2.cfg"
        ]

        procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    if do_dc_101:
        paths = [
            "configs/rdsps/forecast_36h/FC70E16V2_dc101.cfg",
        ]
        procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    # launch everything
    for p in procs:
        p.start()

