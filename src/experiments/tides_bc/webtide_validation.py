from multiprocessing import Process
from pathlib import Path

from main import main


if __name__ == '__main__':
    do_12_hourly = False
    do_36_hourly = True

    procs = []

    paths = [
        "configs/webtide_validation/tidecor_nwatl.cfg",
        "configs/webtide_validation/prog_tides_nwatl.cfg",
        "configs/webtide_validation/tidecor_hrglobal.cfg",
        "configs/webtide_validation/prog_tides_hrglobal.cfg"
    ]

    # main(config_path=Path(paths[0]))

    procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    for p in procs:
        p.start()

