#ord_soumet= -cpus 128 -cm 256G  -t 21600 -jn merge_forcings_db -mach ppp8

# cmd line launch example: 
#           
#           ord_soumet ./scripts/launch_pyscript.sh -args $(pwd) src/loadprogs/tools/merge_nemo_forcings.py 

. r.load.dot /fs/ssm/eccc/cmd/cmds/apps/pixi/202607/00/pixi_0.75.0_all

work_dir=${1:-"/home/olh001/Python/loadprogs_python"}
cfg=${2?"Path to the script should be passed as second arg"}


echo "Launching ${pyscript} in ${work_dir}"

cd ${work_dir}

pixi run python -u ${pyscript}