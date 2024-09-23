#! /usr/bin/python3 -i

from .ssh import SSH
from .Slurm import Slurm
from .util import parse_cmd, job_id, ln2win
from pprint import pprint

import os

#
# Base class. Other params must be set on child class
class Sim :
    def __init__( self, dat_fn, ssh, debug ) :
        self.jid = -1

        # PROCEDURE : resolve file names
        from os.path import splitext, basename, dirname, abspath
        self.debug=debug
        fn, ext = splitext(dat_fn)
        ext = ext.replace(".","")
        chdir = dirname(fn)
        bn = basename(fn)

        # Validation
        if ext != "dat" :
            print(f"FAIL: Expecting a dat file. Extension found: {ext}")
            exit(-1)

        self.sr3 = f"{chdir}/{bn}.sr3"
        self.chdir = chdir
        self.basename = bn
        
        # PROCEDURE: Set default params in the child class
        self.params = {
                "chdir" : chdir,
                "wd" : chdir,
                "modelURI" : dat_fn,
                "logFile" : f"{chdir}/{bn}.log",
                "jobName" : bn,
                "account" : "geomec",
                "jobComment" : f"{bn}_comment",
            }

        # PROCEDURE : Connect ssh
        if not ssh : ssh = SSH( "reslogin", quiet=1, debug=0 )
        self.ssh = ssh


    #
    # wait: return only after job is done
    def run( self, wait=True ) :
        ssh = self.ssh

        cmd = parse_cmd( self.cmd_sh(), self.params )
        stdout, stderr, status = ssh.cmd(cmd)
        jid = job_id(stdout)

        print(f"[Sim-{jid}] Launched job ({self.basename})")

        self.jid = jid
        if not wait : return jid
        self.wait( jid )


    #
    # Return when $jid has finished
    def wait( self, jid ) :
        jid = self.jid
        if jid<0 : 
            print("# ERROR: no job id in the current object")
            return
        print(f"[Sim-{jid}] Waiting for job to finish ", end='', flush=True)

        slurm = Slurm(self.ssh)
        import time
        while True:
            time.sleep(0.5)
            if not self.is_running() : break
            print(".", end='', flush=True)

        print()
        print(f"[Sim-{jid}] The job took {self.elapsed_s()}s to run.")

    #
    # Delegate to Slurm
    def is_running( self ) :
        jid = self.jid
        if jid<0 : 
            print("# ERROR: no job id in the current object")
            return False

        slurm = Slurm(self.ssh)
        jobs = slurm.running_jobs( jid ) 
        if len(jobs) : return True
        return False

    #
    # Delegate to Slurm
    def elapsed_s( self ) :
        jid = self.jid
        if self.is_running() :
            print("Job still running.")
            return -1
        if jid<0 : return -1 # The error message has been issued in is_running

        slurm = Slurm(self.ssh)
        el = slurm.elapsed_s( jid )[0]
        return el


    #
    # Abstract method
    def cmd_sh(self) :
        print("[FAILED] From sim/Sim: cmd_sh must be implemented in child class")
        exit(-1)


#
# Each child class offers a set of default parameter.
#
class SimImex(Sim) :
    def __init__(self, dat_fn, ssh=None, debug=0) :
        Sim.__init__(self, dat_fn, ssh, debug) # Init the basic set of params

        # Refine the params
        self.params.update( {
            "solverNodes" : 1,
            "solverCores" : 12,
            "slurm" : "-p pre",
            "solverName" : "imex",
            "solverVersion" : "2023.10",
            "solverExtras" : ""
        } )
        
        if debug : pprint(self.params)

    def cmd_sh(self) :
        return ( r'source /etc/profile; '
                 r'sbatch -v --chdir "$chdir"  --job-name="$jobName"'
                 r' --ntasks=$solverNodes --cpus-per-task=$solverCores'
                 r' --account=$account '
                 r' --comment="$jobComment_$solverName_$solverVersion" $slurm'
                 r' $CMG_HOME/RunSim.sh $solverName $solverVersion "$modelURI" '
                 r' -wd "$wd" -wait -parasol $solverCores $solverExtras | tee $logFile' )

#
#
# USAGE
#
#
# sim = SimImex( dat_fn )
# jid = sim.run( wait = False )
