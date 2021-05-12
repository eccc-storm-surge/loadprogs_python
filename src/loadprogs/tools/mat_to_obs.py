"""
Convert matlab file from Pengcheng to obs file
"""
import argparse
from collections import namedtuple
from pathlib import Path
from scipy.io.matlab import loadmat
import pandas as pd

from loadprogs.util import obs_file


def main():
    parser = argparse.ArgumentParser(description="create a basis .obs file, to then populate with model_related data")
    parser.add_argument("--mat", required=True, help="Path to the input matlab file", type=Path)
    parser.add_argument("--obs", required=True, help="Path to the output obs file", type=Path)

    args = parser.parse_args()
    assert args.mat.exists()

    args.obs.parent.mkdir(exist_ok=True, parent=True)
    work(args)


def work(args):
    data = loadmat(args.mat)["St"][0, 0]

    lon = data[1]
    lat = data[2]

    st_names = ["".join([c for c in s]) for s in data[3][0]]
    st_countries = ["".join([c for c in s]).strip() for s in data[6][0]]

    i_j_distance = data[7]
    print(i_j_distance)

    df = pd.DataFrame.from_dict(
        {
            "NO": range(len(st_names)),
            "ID": st_names,
            "LAT": lat.squeeze(),
            "LON": lon.squeeze(),
            "DATA.I": i_j_distance[:, 0].squeeze().astype(int),
            "DATA.J": i_j_distance[:, 1].squeeze().astype(int),
            "DATA.D": i_j_distance[:, 2].squeeze(),
            "DATA.COUNTRY": st_countries
        }
    )

    obs_file.save_dataframe_to_obs(df, out_file=args.obs)


def test():
    pth = Path("/fs/site4/eccc/mrd/rpnenv/pwa001/eORCA12_TS20/S3_TS20.mat")
    Args = namedtuple("Args", "mat obs")
    args = Args(mat=pth, obs=Path("data/test_gdpsps_global_obs.obs"))
    work(args)


if __name__ == '__main__':
    # main()
    test()
