#ord_soumet= -mach ppp5 -cpus 80 -t 21600


# Example launching for list of dates
#   for t in $(gen_dates.sh 2025090100 2025090200 24); do 
#        echo $t; ord_soumet scripts/run_se202509.sh -args $(pwd) ${t:0:-2} 0; 
#   done


. r.load.dot /fs/ssm/eccc/cmd/cmds/fstpy/bundle/2025.8.1 \
             /fs/ssm/eccc/cmd/cmds/env/python/py310_2023.07.28_all \
             /fs/ssm/eccc/mrd/rpn/libs/20250804

export PYTHONPATH=./src:${PYTHONPATH}


set -u -e

wrk_dir=${1:?"work dir is not set"}
exp_date=${2:?"exp date is not set"}
delay_days=${3?"delay days is the third arg"}
test_run=${4:-1}

exp_date=$(echo ${exp_date} | tr -d ':') # hcron date contains colons

cd ${wrk_dir}

opts=""
if [ "${test_run}" = "1" ]; then
    opts="--test-run"
fi


for dd in $(seq 1 ${delay_days}); do
    python src/loadprogs/experiments/se202509.py --date ${exp_date} \
                                                 --delay-days ${dd} ${opts}
done