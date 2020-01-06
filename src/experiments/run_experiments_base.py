from pathlib import Path
from main import main

from multiprocessing import Process
import argparse


debug = False

if __name__ == '__main__':
    processes = []

    parser = argparse.ArgumentParser()

    parser.add_argument("--cfg_paths", nargs="+")

    args = parser.parse_args()

    cfg_paths = args.cfg_paths

    if debug:
        for cp in cfg_paths:
            main(config_path=Path(cp))

    else:
        pl = [Process(target=main, kwargs=dict(config_path=Path(p)))
              for p in cfg_paths]
        processes.extend(pl)

        for p in processes:
            p.start()
