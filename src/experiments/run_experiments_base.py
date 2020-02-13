#!/usr/bin/env python3

from pathlib import Path
from main import main

from multiprocessing import Process
import argparse
import logging


if __name__ == '__main__':
    import time
    t0 = time.perf_counter()

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="run experiment")

    parser.add_argument("--cfg_paths", nargs="+")
    parser.add_argument("-d", "--debug", action="store_true")

    args = parser.parse_args()

    cfg_paths = args.cfg_paths

    if args.debug:
        logger.setLevel(logging.DEBUG)

    processes = []

    pl = [Process(target=main, kwargs=dict(config_path=Path(p))) for p in cfg_paths]
    processes.extend(pl)

    for p in processes:
        p.start()

    logger.debug(f"Execution time: {time.perf_counter() - t0}")

