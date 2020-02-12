"""
Remove tides, using simulated tides
works with fst files, outputs fst files
"""
from multiprocessing.pool import Pool
from pathlib import Path

from rpnpy.librmn import all as rmn
from rpnpy.rpndate import RPNDate

rmn.fstopt(rmn.FSTOP_MSGLVL, rmn.FSTOPI_MSG_FATAL)


def add_files_par(args):
    a, b, c, nomvar, typvar = args
    add_files(a, b, c, nomvar=nomvar, typvar=typvar)


def add_files(a: Path, b: Path, c: Path, nomvar="ETAS", typvar="P@"):
    """
    :param a:
    :param b:
    :param c:

    save (a + b) to c
    treat mask correctly
    use dates and meta from a
    """

    fu_a = rmn.fstopenall(str(a))
    fu_b = rmn.fstopenall(str(b))
    fu_c = rmn.fstopenall(str(c), rmn.FILE_MODE_RW)

    keys_a = rmn.fstinl(fu_a)

    for key_a in keys_a:
        rec_a = rmn.fstluk(key_a)

        # modify only etas (P@)
        if rec_a["nomvar"] == nomvar and rec_a["typvar"] == typvar:
            keys_b = rmn.fstinl(fu_b, datev=rec_a["datev"], nomvar=nomvar, typvar=typvar)
            assert len(keys_b) == 1
            rec_b = rmn.fstluk(keys_b[0])

            rec_a["d"] += rec_b["d"]

        rmn.fstecr(fu_c, rec_a)

    rmn.fstcloseall(fu_a)
    rmn.fstcloseall(fu_b)
    rmn.fstcloseall(fu_c)
    print(f"{a} => {c} .. ok!")


def add_tides(fst_src: Path, fst_tides: Path, tides_member="000", fst_dst: Path = None):
    """

    :param fst_src: source directory containing fst files
    :param fst_dst: dest directory containing fst files (tides are removed)
    :param fst_tides: fst directory containing tides only data in fst format
    :param tides_member: member from fst_tide to be used to remove tides
    """

    if fst_dst is None:
        fst_dst = fst_src.parent / (fst_src.name + "+t0")
        fst_dst.mkdir(exist_ok=True, parents=True)

    tides_files = [f for f in fst_tides.iterdir() if f.name.endswith(tides_member)]
    tides_files_map = {f.name.split("_")[0]: f for f in tides_files}

    inputs = []

    for src in fst_src.iterdir():
        tides_file = tides_files_map[src.name.split("_")[0]]
        dst = fst_dst / src.name
        if dst.exists():
            print(f"Exists, won't redo: {dst}")
            continue

        inputs.append([src, tides_file, dst, "ETAS", "P@"])

        # add_files(src, tides_file, dst, nomvar="ETAS", typvar="P@")

    pool = Pool(processes=10)
    pool.map(add_files_par, inputs)


def main():

    #  root_dir = Path("/home/olh001/.suites/resps_tides_perturb_nwatl_O1M2_invert_scaling/forecast/hub/eccc-ppp2/gridpt")

    root_dir = Path("/home/olh001/.suites/resps_tides_perturb_nwatl_O1M2K1N2S2_invert_scaling/forecast/hub/eccc-ppp2/gridpt")
    to_add_tides = [
        root_dir / "prog_surge",
    ]
    tides = root_dir / "prog_tides"

    tides_member = "000"

    for src in to_add_tides:
        add_tides(fst_src=src, fst_tides=tides, tides_member=tides_member)


if __name__ == '__main__':
    main()

