#!/usr/bin/env bash

v=2.6.2
./scripts/create_ssm.sh ${v}
ssm created -d ~/ssm/loadprogs/${v}
ssm install -f data/loadprogs_${v}_all.ssm -d ~/ssm/loadprogs/${v}
ssm publish -p loadprogs_${v}_all -d ~/ssm/loadprogs/${v} -P ~/ssm/loadprogs/${v} -pp all
ssm listd -d ~/ssm/loadprogs/${v} -pp all
