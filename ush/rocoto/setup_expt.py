#!/usr/bin/env python

###############################################################
# < next few lines under version control, D O  N O T  E D I T >
# $Date$
# $Revision$
# $Author$
# $Id$
###############################################################

import os
import sys
import glob
import shutil
import socket
from datetime import datetime, timedelta
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import workflow_utils as wfu

global expdir, configdir, comrot, pslot, resdet, resens, nens, cdump, idate, edate, gfs_cyc


def makedirs_if_missing(d):
    if not os.path.exists(d):
        os.makedirs(d)


def create_EXPDIR():

    makedirs_if_missing(expdir)
    configs = glob.glob(f'{configdir}/config.*')
    if len(configs) == 0:
        msg = f'no config files found in {configdir}'
        raise IOError(msg)
    for config in configs:
        shutil.copy(config, expdir)

    return


def create_COMROT():

    idatestr = idate.strftime('%Y%m%d%H')
    cymd = idate.strftime('%Y%m%d')
    chh = idate.strftime('%H')

    makedirs_if_missing(comrot)

    # Link ensemble member initial conditions
    enkfdir = f'enkf{cdump}.{cymd}/{chh}'
    makedirs_if_missing(os.path.join(comrot, enkfdir))
    for i in range(1, nens + 1):
        makedirs_if_missing(os.path.join(comrot, enkfdir, f'mem{i:03d}'))
        os.symlink(os.path.join(icsdir, idatestr, f'C{resens}', f'mem{i:03d}', 'INPUT'),
                   os.path.join(comrot, enkfdir, f'mem{i:03d}', 'INPUT'))

    # Link deterministic initial conditions
    detdir = f'{cdump}.{cymd}/{chh}'
    makedirs_if_missing(os.path.join(comrot, detdir))
    os.symlink(os.path.join(icsdir, idatestr, f'C{resdet}', 'control', 'INPUT'),
               os.path.join(comrot, detdir, 'INPUT'))

    # Link bias correction and radiance diagnostics files
    for fname in ['abias', 'abias_pc', 'abias_air', 'radstat']:
        os.symlink(os.path.join(icsdir, idatestr, f'{cdump}.t{chh}z.{fname}'),
                   os.path.join(comrot, detdir, f'{cdump}.t{chh}z.{fname}'))

    return


def edit_baseconfig():

    base_config = f'{expdir}/config.base'

    here = os.path.dirname(__file__)
    top = os.path.abspath(os.path.join(
        os.path.abspath(here), '../..'))

    if os.path.exists(base_config):
        os.unlink(base_config)

    print(f'\nSDATE = {idate}\nEDATE = {edate}')
    with open(base_config + '.emc.dyn', 'rt') as fi:
        with open(base_config, 'wt') as fo:
            for line in fi:
                line = line.replace('@MACHINE@', machine.upper()) \
                    .replace('@PSLOT@', pslot) \
                    .replace('@SDATE@', idate.strftime('%Y%m%d%H')) \
                    .replace('@FDATE@', fdate.strftime('%Y%m%d%H')) \
                    .replace('@EDATE@', edate.strftime('%Y%m%d%H')) \
                    .replace('@CASEENS@', f'C{resens}') \
                    .replace('@CASECTL@', f'C{resdet}') \
                    .replace('@NMEM_ENKF@', f'{nens}') \
                    .replace('@HOMEgfs@', top) \
                    .replace('@BASE_GIT@', base_git) \
                    .replace('@DMPDIR@', dmpdir) \
                    .replace('@NWPROD@', nwprod) \
                    .replace('@COMROOT@', comroot) \
                    .replace('@HOMEDIR@', homedir) \
                    .replace('@STMP@', stmp) \
                    .replace('@PTMP@', ptmp) \
                    .replace('@NOSCRUB@', noscrub) \
                    .replace('@ACCOUNT@', account) \
                    .replace('@QUEUE@', queue) \
                    .replace('@QUEUE_SERVICE@', queue_service) \
                    .replace('@PARTITION_BATCH@', partition_batch) \
                    .replace('@EXP_WARM_START@', exp_warm_start) \
                    .replace('@MODE@', 'cycled') \
                    .replace('@CHGRP_RSTPROD@', chgrp_rstprod) \
                    .replace('@CHGRP_CMD@', chgrp_cmd) \
                    .replace('@HPSSARCH@', hpssarch) \
                    .replace('@gfs_cyc@', f'{gfs_cyc}')
                if expdir is not None:
                    line = line.replace('@EXPDIR@', os.path.dirname(expdir))
                if comrot is not None:
                    line = line.replace('@ROTDIR@', os.path.dirname(comrot))
                if 'ICSDIR' in line:
                    continue
                fo.write(line)

    print('')
    print(f'EDITED:  {expdir}/config.base as per user input.')
    print(f'DEFAULT: {expdir}/config.base.emc.dyn is for reference only.')
    print('Please verify and delete the default file before proceeding.')
    print('')

    return


if __name__ == '__main__':

    description = '''Setup files and directories to start a GFS parallel.
Create EXPDIR, copy config files
Create COMROT experiment directory structure,
link initial condition files from $ICSDIR to $COMROT'''

    parser = ArgumentParser(description=description, formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--pslot', help='parallel experiment name', type=str, required=False, default='test')
    parser.add_argument('--resdet', help='resolution of the deterministic model forecast', type=int, required=False, default=384)
    parser.add_argument('--resens', help='resolution of the ensemble model forecast', type=int, required=False, default=192)
    parser.add_argument('--comrot', help='full path to COMROT', type=str, required=False, default=None)
    parser.add_argument('--expdir', help='full path to EXPDIR', type=str, required=False, default=None)
    parser.add_argument('--idate', help='starting date of experiment, initial conditions must exist!', type=str, required=True)
    parser.add_argument('--edate', help='end date experiment', type=str, required=True)
    parser.add_argument('--icsdir', help='full path to initial condition directory', type=str, required=False)
    parser.add_argument('--configdir', help='full path to directory containing the config files', type=str, required=False, default=None)
    parser.add_argument('--nens', help='number of ensemble members', type=int, required=False, default=20)
    parser.add_argument('--cdump', help='CDUMP to start the experiment', type=str, required=False, default='gdas')
    parser.add_argument('--gfs_cyc', help='GFS cycles to run', type=int, choices=[0, 1, 2, 4], default=1, required=False)
    parser.add_argument('--partition', help='partition on machine', type=str, required=False, default=None)
    parser.add_argument('--start', help='restart mode: warm or cold', type=str, choices=['warm', 'cold'], required=False, default='cold')

    args = parser.parse_args()

    machine = wfu.detectMachine()

    configdir = args.configdir
    if not configdir:
        configdir = os.path.abspath(os.path.dirname(__file__) + '/../parm/config')

    pslot = args.pslot
    idate = datetime.strptime(args.idate, '%Y%m%d%H')
    edate = datetime.strptime(args.edate, '%Y%m%d%H')
    icsdir = args.icsdir
    resdet = args.resdet
    resens = args.resens
    comrot = args.comrot if args.comrot is None else os.path.join(args.comrot, pslot)
    expdir = args.expdir if args.expdir is None else os.path.join(args.expdir, pslot)
    nens = args.nens
    cdump = args.cdump
    gfs_cyc = args.gfs_cyc
    partition = args.partition
    start = args.start

    # Set restart setting in config.base
    if start == 'cold':
      exp_warm_start = '.false.'
    elif start == 'warm':
      exp_warm_start = '.true.'

    # Set FDATE (first full cycle)
    fdate = idate + timedelta(hours=6)

    # Set machine defaults
    if machine == 'WCOSS_DELL_P3':
      base_git = '/gpfs/dell2/emc/modeling/noscrub/emc.glopara/git'
      base_svn = '/gpfs/dell2/emc/modeling/noscrub/emc.glopara/git'
      dmpdir = '/gpfs/dell3/emc/global/dump'
      nwprod = '${NWROOT:-"/gpfs/dell1/nco/ops/nwprod"}'
      comroot = '${COMROOT:-"/gpfs/dell1/nco/ops/com"}'
      homedir = '/gpfs/dell2/emc/modeling/noscrub/$USER'
      stmp = '/gpfs/dell3/stmp/$USER'
      ptmp = '/gpfs/dell3/ptmp/$USER'
      noscrub = '/gpfs/dell2/emc/modeling/noscrub/$USER'
      account = 'GFS-DEV'
      queue = 'dev'
      queue_service = 'dev_transfer'
      partition_batch = ''
      if partition in ['3p5']:
        queue = 'dev2'
        queue_service = 'dev2_transfer'
      chgrp_rstprod = 'YES'
      chgrp_cmd = 'chgrp rstprod'
      hpssarch = 'YES'
    elif machine == 'WCOSS_C':
      base_git = '/gpfs/hps3/emc/global/noscrub/emc.glopara/git'
      base_svn = '/gpfs/hps3/emc/global/noscrub/emc.glopara/svn'
      dmpdir = '/gpfs/dell3/emc/global/dump'
      nwprod = '${NWROOT:-"/gpfs/hps/nco/ops/nwprod"}'
      comroot = '${COMROOT:-"/gpfs/hps/nco/ops/com"}'
      homedir = '/gpfs/hps3/emc/global/noscrub/$USER'
      stmp = '/gpfs/hps2/stmp/$USER'
      ptmp = '/gpfs/hps2/ptmp/$USER'
      noscrub = '/gpfs/hps3/emc/global/noscrub/$USER'
      account = 'GFS-DEV'
      queue = 'dev'
      queue_service = 'dev_transfer'
      partition_batch = ''
      chgrp_rstprod = 'YES'
      chgrp_cmd = 'chgrp rstprod'
      hpssarch = 'YES'
    elif machine == 'HERA':
      base_git = '/scratch1/NCEPDEV/global/glopara/git'
      base_svn = '/scratch1/NCEPDEV/global/glopara/svn'
      dmpdir = '/scratch1/NCEPDEV/global/glopara/dump'
      nwprod = '/scratch1/NCEPDEV/global/glopara/nwpara'
      comroot = '/scratch1/NCEPDEV/rstprod/com'
      homedir = '/scratch1/NCEPDEV/global/$USER'
      stmp = '/scratch1/NCEPDEV/stmp2/$USER'
      ptmp = '/scratch1/NCEPDEV/stmp4/$USER'
      noscrub = '$HOMEDIR'
      account = 'fv3-cpu'
      queue = 'batch'
      queue_service = 'service'
      partition_batch = ''
      chgrp_rstprod = 'YES'
      chgrp_cmd = 'chgrp rstprod'
      hpssarch = 'YES'
    elif machine == 'ORION':
      base_git = '/work/noaa/global/glopara/git'
      base_svn = '/work/noaa/global/glopara/svn'
      dmpdir = '/work/noaa/global/glopara/dump'
      nwprod = '/work/noaa/global/glopara/nwpara'
      comroot = '/work/noaa/global/glopara/com'
      homedir = '/work/noaa/global/$USER'
      stmp = '/work/noaa/stmp/$USER'
      ptmp = '/work/noaa/stmp/$USER'
      noscrub = '$HOMEDIR'
      account = 'fv3-cpu'
      queue = 'batch'
      queue_service = 'service'
      partition_batch = 'orion'
      chgrp_rstprod = 'NO'
      chgrp_cmd = 'ls'
      hpssarch = 'NO'

    if args.icsdir is not None and not os.path.exists(icsdir):
        msg = f'Initial conditions do not exist in {icsdir}'
        raise IOError(msg)

    # COMROT directory
    if args.icsdir is None:
       create_comrot = False
    else:
       create_comrot = True
       if os.path.exists(comrot):
           print()
           print(f'COMROT already exists in {comrot}')
           print()
           overwrite_comrot = input('Do you wish to over-write COMROT [y/N]: ')
           create_comrot = True if overwrite_comrot in ['y', 'yes', 'Y', 'YES'] else False
           if create_comrot:
              shutil.rmtree(comrot)

    if create_comrot:
        create_COMROT()

    # EXP directory
    create_expdir = True
    if os.path.exists(expdir):
        print()
        print(f'EXPDIR already exists in {expdir}')
        print()
        overwrite_expdir = input('Do you wish to over-write EXPDIR [y/N]: ')
        create_expdir = True if overwrite_expdir in ['y', 'yes', 'Y', 'YES'] else False
        if create_expdir:
            shutil.rmtree(expdir)

    if create_expdir:
        create_EXPDIR()
        edit_baseconfig()

    sys.exit(0)
