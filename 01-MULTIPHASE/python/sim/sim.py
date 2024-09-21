#! /usr/bin/python3 -i

from ssh import SSH
from pprint import pprint
import re

sh_cmd = ( 
           r'source /etc/profile; '
           r'sbatch -v --chdir "$chdir"  --job-name="$jobName"'
           r' --ntasks=$solverNodes --cpus-per-task=$solverCores'
           r' --account=$account '
           r' --comment="$jobComment_$solverName_$solverVersion" $slurm'
           r' $CMG_HOME/RunSim.sh $solverName $solverVersion "$modelURI" '
           r' -wd "$wd" -wait -parasol $solverCores $solverExtras | tee $logFile'
       )


#
# Converts a linux path to a windows path
#
def ln2win(fn) :
    import re
    ret = re.sub(r"/dfs_geral_ep/", r"\\\\dfs.petrobras.biz/cientifico/", fn)
    #ret = re.sub(r"/", r"\\", ret)
    return ret

#
#
#
def parse_cmd( params ) :
    ret = sh_cmd
    for k, v in params.items():
        ret = ret.replace( "$"+k, str(v))
    return ret

#
#
#
def job_id( stdout ) :
    import re
    m = re.search(r"job\s+(\d+)",stdout)
    if m : return int(m.groups()[0]) 
    return -1

#
# 
#
def elapsed_s( myjobs = "" ) :
    global ssh # must have a working ssh
    if not isinstance(myjobs, list):
        myjobs = [myjobs] 
    myjobs = [ str(i) for i in myjobs if i ] # Lets work with strings
    if not myjobs : return

    ret = []

    for jid in myjobs :
        cc = f"sacct -a -j {jid} --format=user%10,jobname%10,node%10,start%10,end%10,elapsed%10,MaxRS"
        stdout, stderr, status = ssh.cmd(cc)
        for l in stdout.splitlines() :
            m = re.search( r"(\d\d):(\d\d):(\d\d)", l ) 
            if m :
                h_, min_, sec_ = m.groups()
                sec_ = int(sec_)
                sec_ += int(min_)*60 + int(h_)*60*60
                ret.append(sec_)
                break

    return ret

#
#
#
def squeue( myjobs = "" ) :
    global ssh # must have a working ssh
    if not isinstance(myjobs, list):
        myjobs = [myjobs] 
    myjobs = [ str(i) for i in myjobs if i ] # Lets work with strings

    import os
    user = os.getlogin()

    jobs = []
    sq = (f"squeue -h -u {user} "+r' --format "%A;%M;%N;%P;%T;%V;%o;%a;%j"  --sort=-S')
    ssh.cmd( sq )
    for l in ssh.stdout.splitlines() :
        ll = l.split(';')
        print(f"myjobs:{myjobs}")
        if len(myjobs) :
            jid = ll[0]
            if not jid in myjobs : continue

        jobs.append( { 'id':           ll[0],
                        'age':         ll[1],
                        'nodes' :      ll[2],
                        'partition':   ll[3],
                        'state':       ll[4],
                        'startTime':   ll[5],
                        'command':     ll[6],
                        'account':     ll[7],
                        'name':        ll[8]
                        })
    return jobs

#
# MAIN
#
chdir = "/u/bfq9/dfs/bfq9/2024-PHD/EDFM/01-MULTIPHASE/python/history_match_2p2k4/round_0"
basename = "run_0"
params = {
    "chdir" : chdir,
    "wd" : ln2win(chdir),
    "modelURI" : f"{chdir}/{basename}.dat",
    "logFile" : f"{chdir}/{basename}.log",
    "jobName" : basename,
    "solverNodes" : 1,
    "solverCores" : 12,
    "account" : "geomec",
    "slurm" : "-p pre",
    "jobComment" : "run_0_comment",
    "solverName" : "imex",
    "solverVersion" : "2023.10",
    "solverExtras" : ""
}

    
# stdout, stderr, status = ssh.cmd( "sbatch ls" ) #, deb=1, quiet=0 )

cmd = parse_cmd(params)
ssh = SSH( "reslogin" )
ssh.cmd(cmd)
jid = job_id(ssh.stdout)
if jid < 0 : jid = ""

import time
while True:
    time.sleep(0.5)
    jobs = squeue( jid )
    pprint(jobs)
    if ( not jobs ) : break

ssh.cmd(f"cat {chdir}/slurm-{jid}.out")
print(ssh.stdout)

print(f"The job took {elapsed_s(jid)} s to run.")
