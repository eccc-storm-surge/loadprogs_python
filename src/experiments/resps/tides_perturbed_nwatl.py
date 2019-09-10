from multiprocessing import Process
from pathlib import Path
from main import main

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    import time
    t0 = time.perf_counter()
    procs = []

    paths = [
        # "configs/resps/tides_perturbed_nwatl/surge_tidesbc.cfg",
        # "configs/resps/tides_perturbed_nwatl/tidesbc_only.cfg",
        "configs/resps/tides_perturbed_nwatl/webtide.cfg",
        # "configs/resps/tides_perturbed/surgep_tidesnp.cfg"
    ]

    path_objs = [Path(p) for p in paths]
    assert all([po.exists() for po in path_objs]), "Some config files don't exist! "

    # procs += [Process(target=main, kwargs=dict(config_path=po)) for po in path_objs]

    for po in path_objs:
        main(config_path=po)

    # launch everything
    for p in procs:
        p.start()

    logger.info(f"Execution time: {time.perf_counter() - t0}")

