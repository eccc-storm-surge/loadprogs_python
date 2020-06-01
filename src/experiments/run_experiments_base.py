#!/usr/bin/env python3

from pathlib import Path
from main import main

from multiprocessing import Process, Lock
import argparse
import logging


if __name__ == '__main__':
    import time
    t0 = time.perf_counter()

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="run experiment")

    parser.add_argument("--cfg_paths", nargs="+")
    parser.add_argument("-d", "--debug", action="store_true",
                         default=False, required=False)

    args = parser.parse_args()

    cfg_paths = args.cfg_paths

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if not args.debug:
        processes = []
        pl = [Process(target=main, kwargs=dict(config_path=Path(p))) for p in cfg_paths]
        processes.extend(pl)

        for p in processes:
            p.start()
    else:
        for p in cfg_paths:
            main(config_path=Path(p))



    logger.info(f"Execution time: {time.perf_counter() - t0}")
