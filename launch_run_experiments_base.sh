#!/bin/bash
. /fs/homeu1/eccc/cmd/cmde/olh001/.profile_python3

RDSPS_160_CONFIG_FILE="configs/rdsps/migration_2019_par/rdsps_fc_ops_160_test.cfg"

export PYTHONPATH=.:${PYTHONPATH}

python src/experiments/run_experiments_base.py \
--cfg_paths ${RDSPS_160_CONFIG_FILE} \
--debug
