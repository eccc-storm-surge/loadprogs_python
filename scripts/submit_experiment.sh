#ord_soumet= -t 21600 -cpus 40 -cm 160G

# usage:
#   ord_soumet scripts/submit_experiment.sh -args "=-config configs/gdsps/fc_201904_202006_twl.cfg =-project_root $(true_path .)"

config="i_do_not_exist"
project_root="i_do_not_exist"

eval $(cclargs $0 "[script to launch verification of different experiments in parallel]"\
  -project_root "/home/${USER}/Python/loadprogs_python/" "/home/${USER}/Python/loadprogs_python/"  "[verification script to be run]" \
  -config "i_do_not_exist" "i_do_not_exist"  "[path to the config used by the verification script]" \
  -nosubmit "0" "0" "[put 1 if need to run interactively]" \
  ++ $*)


. r.load.dot /fs/ssm/eccc/cmd/cmds/apps/pixi/202607/00/pixi_0.75.0_all

cd ${project_root} || exit


pixi run --offline python -u src/loadprogs/experiments/run_experiments_base.py --cfg ${config}


