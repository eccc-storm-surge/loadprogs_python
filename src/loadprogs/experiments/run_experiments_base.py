#!/usr/bin/env python3

from pathlib import Path

# absolute import as it is supposed to be used as main (standalone launch script) only!
from loadprogs.main.main import main

from multiprocessing import Process
import argparse
from loadprogs.util import configs, constants
from loadprogs.util.log_utils import get_logger
import logging


def main(logger):
    parser = argparse.ArgumentParser(description="run experiment")

    cfg_arg_names = [
        "--cfg_paths",
        "--cfg",
        "--cfgs"
    ]

    parser.add_argument(*cfg_arg_names, nargs="+",
                        help="list of paths to the configuration files",
                        required=False)
    
    parser.add_argument("-d", "--debug", action="store_true",
                        default=False, required=False)

    parser.add_argument("--help_cfg", "--help-cfg", help="print list of configuration options (.cfg file) with descriptions and exit",
                        default=False, 
                        required=False, 
                        type=bool,
                        nargs="?", const=True) # when the option is there but the value is not specified

    args = parser.parse_args()

    if args.help_cfg:
        print("\nAvailable options for configuration files:\n")
        for k, v in constants.get_help().items():
            print(f"[{k}]\n")
            for vk in sorted(v):
                vv = "\n".join(f"\t\t{line.strip()}" for line in v[vk].split("\n"))
                print(f"""\t{vk}:\n{vv}\n""")
        return 0
        

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



if __name__ == '__main__':
    import time
    t0 = time.perf_counter()
    logger = get_logger(__name__)
    main(logger)
    logger.info(f"Execution time: {time.perf_counter() - t0}")
