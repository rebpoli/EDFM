#! /usr/bin/python3 -i

from util import launch
from pprint import pprint

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

jid, ssh = launch( params )

# Follow up...
slurm = Slurm(ssh)
import time
while True:
    time.sleep(0.5)
    jobs = slurm.squeue( jid )
    pprint(jobs)
    if ( not jobs ) : break

print(f"The job took {elapsed_s(jid)} s to run.")
