import numpy as np
import pandas as pd


s_size = 4
w = 2 * np.pi / 12
m = np.zeros((s_size, s_size))
k = 0
m[0, 0] = 1
m[1, 1] = 1
k += 2
m[k, k] = np.cos(w)
m[k + 1, k] = np.sin(w)
m[k, k + 1] = -np.sin(w)
m[k + 1, k + 1] = np.cos(w)

h = np.array([1, 0, 1, 0])

kappa = 1 / (200 * 24)
k = np.array([2 * kappa, 0, 2 * kappa, 0])
m_update = np.matmul(np.eye(s_size) - np.outer(k, h), m)

t = np.arange(100000)
x = 13 + np.sin(2 * np.pi / 12 * t)

df = pd.DataFrame.from_dict({
    "x": x
})
df.index = t



def tfilter(_x):
    s_prev = np.zeros((s_size))
    res = np.zeros_like(_x)
    for i, xi in enumerate(_x):
        s_curr = np.matmul(m_update, s_prev) + k * xi
        res[i] = np.matmul(h, s_curr)
        s_prev = s_curr
    return res


df["xf"] = tfilter(x)

df["x - xf"] = df["x"] - df["xf"]
print(df.iloc[:, :].mean())
print(m)
