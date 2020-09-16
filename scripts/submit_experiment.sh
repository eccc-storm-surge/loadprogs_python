#ord_soumet= -t 21600 -cpus 40 -cm 160G

# usage:
#   ord_soumet scripts/submit_experiment.sh -args "=-config configs/gdsps/fc_201904_202006_twl.cfg =-project_root $(true_path .)"

config="i_do_not_exist"
project_root="i_do_not_exist"

eval $(cclargs $0 "[script to launch verification of different experiments in parallel]"\
  -project_root "~/Python/loadprogs_python/" "~/Python/loadprogs_python/"  [verification script to be run] \
  -config "i_do_not_exist" "i_do_not_exist"  [path to the config used by the verification script] \
  -nosubmit "0" "0" "[put 1 if need to run interactively]" \
  ++ $*)


. ~olh001/.profile_python3

cd ${project_root} || exit

export PYTHONPATH=./src:${PYTHONPATH}

python src/loadprogs/experiments/run_experiments_base.py --cfg ${config}


