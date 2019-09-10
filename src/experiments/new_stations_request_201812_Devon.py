from multiprocessing import Process
from pathlib import Path

from main import main


if __name__ == '__main__':
    paths = [
        "configs/check_stations_201812/new_stations_request_201812_Devon.cfg",
    ]

    procs = []
    procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    for p in procs:
        p.start()

