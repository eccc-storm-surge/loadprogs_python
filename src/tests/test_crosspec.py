
from scipy.io import loadmat

import matplotlib.pyplot as plt

from util.crosspec import crosspec


def test_all():
    mat_file_path = "/fs/site2/dev/eccc/cmd/e/olh001/detide_water_levels/data_for_scoring_rdsps_pseudo-analysis_experimental_2016121500_2017022818_v03/Etaprogs.mat"

    x = loadmat(mat_file_path)

    print(x["Obs"][0][0][4])

    plt.plot(x["Obs"][0][0][4][0])

    plt.figure()

    f0, p0 = crosspec(500, x["Obs"][0][0][4][0])
    plt.plot(f0, p0, color="b")

    f1, p1 = crosspec(500, x["Obs"][0][0][8][0])
    plt.plot(f1, p1, color="r")

    plt.show()


if __name__ == '__main__':
    test_all()