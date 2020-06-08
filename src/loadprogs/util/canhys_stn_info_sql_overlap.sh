#!/bin/bash

STATION_ID_TRANSLATION_DICT="/home/olh001/Python/loadprogs_python/stations_info/CanHys/stn.txt"
STATIONS_INFO_FILE="/home/olh001/Python/station_positions_vis/stations_storm_surge_1_30_subset.obs"
CANHYS_SQL_DIR="/home/olh001/data/eccc-ppp3/canhys_backup"
OUTPUT_TEXT_FILE="/home/siy000/projects/loadprogs_python/out/canhys_sql_info_overlap/"

declare -A translator
declare -a valid_real_ids

while read dict_row; do

	IFS="|" read -ra delimited <<< ${dict_row}
	
	canhys_id=${delimited[1]}
	real_id=${delimited[2]}

	translator[${canhys_id}]=${real_id}

done < ${STATION_ID_TRANSLATION_DICT}

while read info_row; do

	IFS="	" read -ra delimited <<< ${info_row}
	echo ${delimited[0]}

done < ${STATIONS_INFO_FILE}



#cat ${STATIONS_INFO_FILE} | while read line
#do
#	IFS="" read -ra my_array <<< ${dict_row}

#for filename in ${CANHYS_SQL_DIR}/*sql; do
#	echo ${filename}
#done
