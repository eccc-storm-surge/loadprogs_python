
def gamma2(obs_ts, mod_ts):
    """
    gamma squared for obs and mod timeseries
    """

    obs_ts = obs_ts.dropna()

    print("mod t-range: ", mod_ts.index[0], mod_ts.index[-1])
    print("obs t-range: ", obs_ts.index[0], obs_ts.index[-1])


    ind = obs_ts.index.intersection(mod_ts.index)
    obs_sel = obs_ts[ind]
    mod_sel = mod_ts[ind]
    assert len(mod_sel) > 0, "Could not find any corresponding (mod, obs) data in time"
    print(f"found {len(mod_sel)} (mod, obs) pairs matching in time.")

    bias = mod_sel - obs_sel

    score = (bias ** 2).mean() / obs_sel.var()
    return score
