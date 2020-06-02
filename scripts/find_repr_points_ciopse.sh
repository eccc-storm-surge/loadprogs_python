#!/usr/bin/env bash

. ~olh001/.profile_python3

python src/tools/find_repr_gridpts.py \
      --obs-index-in /home/olh001/Python/station_positions_vis/stations_obs_ATL_1_30_v001_selected.obs \
      --obs-index-out ./data/ciopse_opt.obs \
      --mod-files /home/olh001/data/ppp3/ciopse/pa_links/*_* \
      --nomvar SSH \
      --typvar P@ \
      --obs-dir /home/olh001/data/ppp3/sse_obs/merged/2015_2018x \
      --beg-time 2015122600 \
      --end-time 2017010100 \
      --dist-upper-bound-m 20000
