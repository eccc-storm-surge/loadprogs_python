#!/bin/bash
DEPS_SIY=~siy000/projects/
. ~/.profile
. ~olh001/.profile_python3

RDSPS_160_CONFIG_FILE="${DEPS_SIY}/loadprogs_python/configs/rdsps/migration_2019_par/rdsps_fc_ops_160.cfg"
RDSPS_170_CONFIG_FILE="${DEPS_SIY}/loadprogs_python/configs/rdsps/migration_2019_par/rdsps_fc_par_170.cfg"

export PYTHONPATH=${DEPS_SIY}/loadprogs_python/src:${PYTHONPATH}

python ${DEPS_SIY}/loadprogs_python/src/experiments/run_experiments_base.py \
--cfg_paths ${RDSPS_160_CONFIG_FILE} ${RDSPS_170_CONFIG_FILE} \
--debug

