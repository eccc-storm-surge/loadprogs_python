#!/usr/bin/env bash

# Copy required scripts in all folder

# Take as input the version of the target ssm

if [[ -z $1 ]]; then
  echo 'Usage: ./scripts/create_ssm.sh [version]'
  exit 1
fi

# this scrpt should be executed from the project root
cd $(dirname "${0}")/..

SSM_NAME=loadprogs
PLAT=all
VERSION=$1
SSM_FULLNAME=${SSM_NAME}_${VERSION}_${PLAT}

SSM_BASE=data
SSM_TEST=${HOME}/ssm/${SSM_NAME}
SSM_OFFICIEL=/fs/ssm/eccc/cmd/cmde/wave/${SSM_NAME}
SSM_create_tag=0

mkdir -p ${SSM_BASE}

SSM_WORK=${SSM_BASE}/${SSM_FULLNAME}
echo "Work path: $SSM_WORK"
rm -rf $SSM_WORK

srcdir=.
echo "Project path: $srcdir"

# post-install script
POSTINSTALLSCRIPT='#!/bin/bash -p

# Running install script
set -x
domainHome=$1
packageHome=${2}

# create profiles
packageName=$(basename ${packageHome})
profileDirPath=${packageHome}/etc/profile.d
profilePath=${profileDirPath}/${packageName}.sh


mkdir -p ${profileDirPath}

cat > ${profilePath} << EOF
#export path to the lib
export PYTHONPATH=${packageHome}/lib:\${PYTHONPATH}
EOF
'


cd $srcdir
if [[ -n $(git status --untracked-files=no --porcelain) ]]; then
  echo 'Aborting: repository is not clean'
  exit 1
fi

if [ "${SSM_create_tag}" = 1 ]; then
  if [[ -n $(git tag -l "$VERSION") ]]; then
    git tag -d $VERSION
  fi
  git tag $VERSION
fi

mkdir -p $SSM_WORK/bin $SSM_WORK/lib $SSM_WORK/.ssm.d

echo "Copie des scripts python ..."
cp $srcdir/src/experiments/run_experiments_base.py $SSM_WORK/bin/
cp -r $srcdir/src/*  $SSM_WORK/lib/

chmod 755  $SSM_WORK/bin/*

echo "Creation du fichier control.json"
cat << EOF > $SSM_WORK/.ssm.d/control.json
{
   "name": "$SSM_NAME",
   "version": "$VERSION",
   "platform": "$PLAT",
   "maintainer": "CMDE: Oleksandr Huziy",
   "summary": "Matching obs and model sea surface levels and detiding with ttide.",
   "description": "python scripts for loading (and detiding if required) matching obs and model data"
}
EOF
cat $SSM_WORK/.ssm.d/control.json


echo "Creating post-install script."
mkdir -p ${SSM_WORK}/.ssm.d/
echo "${POSTINSTALLSCRIPT}" > ${SSM_WORK}/.ssm.d/post-install
chmod 555 ${SSM_WORK}/.ssm.d/post-install

[ -d ${SSM_WORK}/etc ] ||  mkdir -p  ${SSM_WORK}/etc/profile.d


cd $SSM_WORK/..

tar cvfzh ${SSM_FULLNAME}.ssm ${SSM_FULLNAME}

# rm -r $SSM_WORK


echo "Install test"
echo "If new: ssm created -d ${SSM_TEST}/master"
echo "ssm install -d ${SSM_TEST}/master -f ${SSM_BASE}/${SSM_NAME}_${VERSION}_all.ssm"
echo "ssm created -d ${SSM_TEST}/${VERSION}"
echo "ssm publish -d ${SSM_TEST}/master -p ${SSM_NAME}_${VERSION}_all -P ${SSM_TEST}/${VERSION} -pp all"
echo "Install real"
echo "If new: ssm created -d ${SSM_OFFICIEL}/master"
echo "ssm install -d ${SSM_OFFICIEL}/master -f ${SSM_BASE}/${SSM_NAME}_${VERSION}_all.ssm"
echo "ssm created -d ${SSM_OFFICIEL}/${VERSION}"
echo "ssm publish -d ${SSM_OFFICIEL}/master -p ${SSM_NAME}_${VERSION}_all -P ${SSM_OFFICIEL}/${VERSION} -pp all"
