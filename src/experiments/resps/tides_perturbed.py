from multiprocessing import Process
from pathlib import Path
from main import main

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    import time
    t0 = time.clock()
    procs = []

    paths = [
        "configs/resps/tides_perturbed/surge_tidesbc.cfg",
        # "configs/resps/tides_perturbed/tidesbc_only.cfg",
        # "configs/resps/tides_perturbed/webtide.cfg",
        # "configs/resps/tides_perturbed/surgep_tidesnp.cfg"
    ]

    # procs += [Process(target=main, kwargs=dict(config_path=Path(p))) for p in paths]

    # debug
    for p in paths:
        main(config_path=Path(p))

    # launch everything
    for p in procs:
        p.start()

    logger.info(f"Execution time: {time.clock() - t0}")

