#!/usr/bin/env python3

from pathlib import Path
from main import main

from multiprocessing import Process
import argparse


debug = True

if __name__ == '__main__':
    processes = []

    parser = argparse.ArgumentParser()

    parser.add_argument("--cfg_paths", nargs="+")
    parser.add_argument("--debug", nargs="?", type=int, default=0)

    args = parser.parse_args()

    cfg_paths = args.cfg_paths
    debug = args.debug == 1

    if debug:
        for cp in cfg_paths:
            main(config_path=Path(cp))

    else:
        pl = [Process(target=main, kwargs=dict(config_path=Path(p)))
              for p in cfg_paths]
        processes.extend(pl)

        for p in processes:
            p.start()
