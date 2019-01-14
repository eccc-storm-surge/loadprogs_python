# Ported from MATLAB code written by Natacha Bernier

import numpy as np

from numpy import pi


eps = .00000000001

import matplotlib.pyplot as plt
def crosspec(m: int, x):
    """

    :param m:
    :param x: time series to get the power spectre
    """

    x1 = np.asarray(x)

    if x1.shape[-1] % 2 != 0:
        x1 = x1[:-1]

    x1[np.isnan(x1)] = 0

    dx1 = np.fft.fft(x1)
    n = len(dx1)

    delOmega = 2 * pi / float(n)
    p = 2 * n // m

    Omega = np.arange(-p, p + 1, 1) * delOmega + eps
    freq = np.arange(0, pi + delOmega, delOmega)

    # W = (sin(M*Omega/4)./sin(Omega/2)).^4 .*(1-2/3*sin(Omega/2).^2).*6/(pi*M^3);
    W = (np.sin(m * Omega / 4.0) / np.sin(Omega / 2.)) ** 4 * (1 - 2. / 3. * np.sin(Omega / 2.) ** 2) * 6 / (pi * m ** 3)
    W /= W.sum() * delOmega

    # compute the power spectrum
    instx1 = np.abs(dx1) ** 2


    # [INSTX1(n-p+2:n); INSTX1(1:n/2+p+1)]
    instartx1 = list(instx1[n - p + 1:n]) + list(instx1[0:n // 2 + p + 1])

    Pxx1 = delOmega * np.convolve(instartx1, W) / (2 * pi * len(x1))
    Pxx1 = 2 * Pxx1[2 * p - 1: n // 2 + 2 * p]

    return freq / (2. * pi), Pxx1