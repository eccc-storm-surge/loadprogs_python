
Introduction
======
Port of the loadprogs_base.ksh (the one that was using MATLAB before) to the Python implementation.

using the T_tide port to Python from here: https://github.com/moflaher/ttide_py.git


Usage
=========
To load the scripts and modules into your environment:

```
. r.load.dot ~sssm001/ssm/loadprogs/2.0.0
```

If you do not have your own python environment, the following could be used:

```
. r.load.dot ~sssm001/ssm/surgepy/1.0.0
```

To read model outputs from standard RPN files, `rpnpy` is used:

```
. r.load.dot eccc/mrd/rpn/libs/19.5 eccc/mrd/rpn/MIG/ENV/x/rpnpy/2.1-u1.rc11
```


Notes
=====

1. Version 2.0.0 is using different format of the configuration files. Each file has 3 sections: mod, obs and misc. If you want to use the old format of the configuration files, please, use version 1.0.0 of the code (does not have CanHys support).

1. Now can ingest CanHys observations feed.

1. The python version of the loadprogs works directly with the storm surge model outputs and not txt as is done in the MATLAB version at the moment.
