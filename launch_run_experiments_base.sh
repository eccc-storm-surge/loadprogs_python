#!/bin/bash
. ~olh001/.profile_python3

# RDSPS_160_CONFIG_FILE="configs/rdsps/migration_2019_par/rdsps_fc_ops_160_test.cfg"
RDSPS_160_CONFIG_FILE="configs/rdsps/migration_2019_par/cpop_20191217_new_format/rdsps_fc_ops_160.cfg"

export PYTHONPATH=./src:${PYTHONPATH}

/usr/bin/time -v python ./src/loadprogs/experiments/run_experiments_base.py \
--cfg_paths ${RDSPS_160_CONFIG_FILE} \
--debug
