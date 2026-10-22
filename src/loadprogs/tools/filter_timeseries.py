#!/usr/bin/env python
# coding: utf-8


import numpy as np
import pandas as pd
from netCDF4 import Dataset
import matplotlib.pyplot as plt


def filt_init(n_freq, w_ar, kappa):
    n = 2 * n_freq
    m = np.zeros((n, n))
    K = np.zeros((n,))
    H = np.zeros((n,))
    for k in range(0,n,2):
        i = int( k / 2)
        w = w_ar[i]; cs = np.cos(w); sn = np.sin(w)
        m[k    , k    ] = cs
        m[k + 1, k    ] = sn
        m[k    , k + 1] = -sn
        m[k + 1, k + 1] = cs

        H[k    ] = 1
        H[k + 1] = 0

        K[k    ] = 2 * kappa[i]
        K[k + 1] = 0

    m_update = np.matmul(np.eye(n) - np.outer(K, H), m)

    return m_update, K, H




def tfilter(_x):
    s_prev = np.zeros((s_size))
    res = np.zeros_like(_x)
    for i, xi in enumerate(_x):
        s_curr = np.matmul(m_update, s_prev) + k * xi
        res[i] = np.matmul(h, s_curr)
        s_prev = s_curr
    return res


nc = Dataset('t_freq_gdsps.nc')
omega = nc['freq'][:]
w = omega * 3600.
kappa = nc['kappa'][:]
#kappa *= 10
tides=nc['Tname'][:]
nc.close()
n_freq = omega.shape[0]

#n_freq = 1
#w = [ 2 * np.pi / 12, ]
#kappa = [ 1 / (2 * 24), ]

s_size = 2 * n_freq
m_update, k, h = filt_init(n_freq, w, kappa)

nc = Dataset('fundy.nc')
t = list(nc['time_counter'][:])
x = np.squeeze(np.transpose(nc['zos'][:].data))
nc.close()

#t = np.arange(100000)
#x = np.sin(2 * np.pi / 12 * t)
#print(x)

df = pd.DataFrame.from_dict({
    "x": x
})
df.index = t

df["xf"] = tfilter(x)

df["x - xf"] = df["x"] - df["xf"]

plt.plot(t,x,            label = 'original signal', color = 'black', linestyle = 'solid')
plt.plot(t,df['xf'],     label = 'filtered signal', color = 'red',   linestyle = '--')
plt.plot(t,df['x - xf'], label = 'residual signal', color = 'green', linestyle = ':')
plt.xlabel('Time (h)')
plt.ylabel('Amplitude (m)')
plt.legend()
plt.show()

