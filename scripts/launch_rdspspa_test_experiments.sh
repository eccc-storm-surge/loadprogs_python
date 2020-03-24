#!/bin/bash
. /fs/homeu1/eccc/cmd/cmde/olh001/.profile_python3

RDSPS_TXTOBS_CONFIG_FILE="configs/rdsps_pa/rdsps_pa_2780_test_txt.cfg"
RDSPS_SQLOBS_CONFIG_FILE="configs/rdsps_pa/rdsps_pa_2780_test_sqlite.cfg"

export PYTHONPATH=src:${PYTHONPATH}

python src/experiments/run_experiments_base.py \
	--cfg_paths ${RDSPS_TXTOBS_CONFIG_FILE} ${RDSPS_SQLOBS_CONFIG_FILE} \
	--debug
