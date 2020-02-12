#!/usr/bin/env python3

from pathlib import Path
from main import main

from multiprocessing import Process
import argparse
import logging


if __name__ == '__main__':
    processes = []

    parser = argparse.ArgumentParser(description="run experiment")

    parser.add_argument("--cfg_paths", nargs="+")
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-c", "--canhys", action="store", type=Path)

    args = parser.parse_args()

    cfg_paths = args.cfg_paths

    if args.debug:
        for cp in cfg_paths:
            main(config_path=Path(cp))

    else:
        pl = [Process(target=main, kwargs=dict(config_path=Path(p)))
              for p in cfg_paths]
        processes.extend(pl)

        for p in processes:
            p.start()
