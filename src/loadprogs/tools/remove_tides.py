
"""
Can be used to subtract masked fields
examples:

    python src/loadprogs/tools/remove_tides.py --src_a /home/sbd000/data/ppp4/IC3_CIOPS/East/control/FCST/winter2020 \
                                               --dst ~/data/ppp4/CI3/ciopse/ETAS/ --nv_a SSH --nv_b SSHT --nv_c ETAS
"""

import argparse
from multiprocessing import Pool
from pathlib import Path

from rpnpy.librmn import all as rmn

from loadprogs.util import log_utils
from joblib import Parallel, delayed


def diff(inp_files, file_c, name_a, name_b, name_c):
    logger = log_utils.get_logger(__name__)

    fu_inp = rmn.fstopenall([str(f) for f in inp_files])
    keys_a = rmn.fstinl(fu_inp, nomvar=name_a)

    fu_out = None
    try:
        if len(keys_a) == 0:
            logger.info("Not found %s in %s, skipping", name_a, inp_files)
            return

        fu_out = rmn.fstopenall(str(file_c), rmn.FILE_MODE_RW)

        for key_a in keys_a:
            rec_a = rmn.fstluk(key_a)
            rec_b = rmn.fstlir(fu_inp, nomvar=name_b, ip1=rec_a["ip1"], ip2=rec_a["ip2"], ip3=rec_a["ip3"],
                               typvar=rec_a["typvar"], datev=rec_a["datev"])

            assert rec_b is not None
            
            rec_c = rec_a.copy()
            rec_c["nomvar"] = name_c
            if rec_a["typvar"] == "@@":
                rec_c["d"] = rec_a["d"] * rec_b["d"]
            else:
                rec_c["d"] = rec_a["d"] - rec_b["d"]

            rmn.fstecr(fu_out, rec_c)

            # check whether to write coordinates
            ig = [rec_a[key] for key in ["ig1", "ig2", "ig3"]]
            request = dict(zip(["ip1", "ip2", "ip3"], ig))
            coord_keys = rmn.fstinl(fu_out, **request)

            # write coords if requested
            if len(coord_keys) == 0:
                coord_keys = rmn.fstinl(fu_inp, **request)
                for key in coord_keys:
                    rmn.fstecr(fu_out, rmn.fstluk(key))

    finally:
        rmn.fstcloseall(fu_inp)
        if fu_out is not None:
            rmn.fstcloseall(fu_out)


def gen_inp_out_paths(args):
    for f_inp_a in args.src_a.iterdir():
        f_inp_b = args.src_b / f_inp_a.name
        inp_files = {f_inp_a, f_inp_b}
        out_file = args.dst / f_inp_a.name

        yield inp_files, out_file


def main():
    parser = argparse.ArgumentParser(description="Remove field b from field a: c=a-b")
    parser.add_argument("--src_a", required=True, help="Path to the input dir", type=Path)
    parser.add_argument("--src_b", required=False, default=None,
                        help="Path to the input dir (use src_a if not specified)",
                        type=Path)

    parser.add_argument("--dst", required=True, help="destination directory for the difference files", type=Path)

    parser.add_argument("--nv_a", required=True, help="variable name in file a")
    parser.add_argument("--nv_b", required=True, help="variable name in file b")
    parser.add_argument("--nv_c", required=True, help="variable name in file c")

    args = parser.parse_args()

    if args.src_b is None:
        args.src_b = args.src_a

    assert args.dst.is_dir()

    # cleanup the output directory
    for f in args.dst.iterdir():
        f.unlink(missing_ok=True)

    # use 10 jobs in parallel for processing
    Parallel(n_jobs=10)(
        delayed(diff)(*inp, args.nv_a, args.nv_b, args.nv_c) for inp in gen_inp_out_paths(args)
    )


if __name__ == '__main__':
    main()