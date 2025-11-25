# gesps (usr grid) for resps comparison, subjective eval
python src/loadprogs/tools/find_repr_gridpts.py \
        --obs-index-in  /home/olh001/Python/obs_to_grid_mapping/gesps/gesps_global_obs_v2.0.0.obs \
        --obs-index-out /home/olh001/Python/obs_to_grid_mapping/gesps/usr-grid/gesps-usr-grid_all.obs \
        --nnearest 1 \
        --mod-files /home/sssm001/constants/cmde/surge/gesps/post-processing/HAT-LAT-gesps-baroclinic-20020101-20201231_bc10_8tcs_usr-grid.fst \
        --mod-bathy-vname HAT
