#!/usr/bin/env python3

from pathlib import Path

from joblib import Parallel, delayed
# absolute import as it is supposed to be used as main (standalone launch script) only!
from loadprogs.main.main import main as loadprogs_main

import argparse
from loadprogs.util import constants
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

    parser.add_argument("-f", "--force", action="store_true",
                        default=False, required=False, help="force rerun of loadprogs if present")

    parser.add_argument("-allow-missing-model", "--allow-missing-model",
                        default=False, required=False, help="Allow missing model data", 
                        action="store_true")


    parser.add_argument("--help_cfg", "--help-cfg", 
                        help="print list of configuration options (.cfg file) with descriptions and exit",
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

    if cfg_paths is None:
        logger.info("No configs provided ...")
        cfg_paths = ()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    for p in cfg_paths:
        loadprogs_main(config_path=Path(p), debug=args.debug, 
                       force=args.force, allow_missing_mod_data=args.allow_missing_model)


if __name__ == '__main__':
    import time
    t0 = time.perf_counter()
    logger = get_logger(__name__)
    main(logger)
    logger.info(f"Execution time: {time.perf_counter() - t0}")
