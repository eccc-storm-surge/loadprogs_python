from multiprocessing import Process
from pathlib import Path

from main import main


if __name__ == '__main__':
    procs = []

    paths = [
        "configs/webtide_debug/tidecor_hrglobal.cfg",
    ]

    # main(config_path=Path(paths[0]))

    procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    for p in procs:
        p.start()

