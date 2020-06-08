from multiprocessing import Process
from pathlib import Path
from loadprogs.main import main

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    import time
    t0 = time.perf_counter()
    procs = []

    debug = False

    paths = [
        "configs/resps/tides_perturbed_nwatl_detided_m2o1/surge_tidesbc.cfg",
        "configs/resps/tides_perturbed_nwatl_detided_m2o1/tidesbc_only.cfg",
        "configs/resps/tides_perturbed_nwatl_detided_m2o1/webtide.cfg",
        "configs/resps/tides_perturbed_nwatl_detided_m2o1/surge0_tidesbc.cfg",
        "configs/resps/tides_perturbed_nwatl_detided_m2o1/surge_tidesbc0.cfg",
        # "configs/resps/tides_perturbed/surgep_tidesnp.cfg"
        # "configs/resps/tides_perturbed_nwatl/surge_only.cfg"
    ]

    path_objs = [Path(p) for p in paths]

    for po in path_objs:
        assert po.exists(), f"{po} does not exist!"

    if debug:
        for po in path_objs:
            main(config_path=po)
    else:
        procs += [Process(target=main, kwargs=dict(config_path=po)) for po in path_objs]

        # launch everything
        for p in procs:
            p.start()

    logger.info(f"Execution time: {time.perf_counter() - t0}")
