#!/usr/bin/python3 

import sim
template_fn, sr3_ref_fn = sim.util.init()
DEBUG = sim.shared.DEBUG 
VERBOSE = sim.shared.VERBOSE

TIMESTEPS = [0,25,50,100,200,400]
DEBUG and print(f"# D: Timestep selection: {TIMESTEPS}.")

#
# MAIN
#

from time import sleep
import os, sys, re
from skopt import gp_minimize, Optimizer
from skopt.space import Real
from multiprocessing import Pool
from sim import SimImex, SSH, Slurm, ScopeWatch, util
from Model import Model


#
# This is a parallel function
def cost_foo( X ) :
    global LGR
    if os.path.exists(X['stdout']) : os.remove(X['stdout'])

    # PROCEDURE : Calculate the cost function
    _mod = Model(   X['sr3'],
                    _2p2k = True,
                    ref_model = LGR,
                    stdout=X['stdout'],
                    timesteps=TIMESTEPS)

    cost = _mod.distance()
    return cost
        

# PROCEDURE: Load fine LGR (reference) grid
with ScopeWatch(f"Loading {os.path.basename(sr3_ref_fn)} ...") :
    LGR = Model(sr3_ref_fn, timesteps=TIMESTEPS)

# 
with ScopeWatch("Initialize optimizer ...") :
    optimizer = Optimizer(
        #           DIFRAC       log(PERM_FRAC)
        dimensions=[Real(1,50), Real(2,3)],
        random_state=1,
        base_estimator='gp',
        n_initial_points=10
    )

# 
with ScopeWatch("Connect ssh ...") :
    ssh = SSH( "reslogin", quiet=not VERBOSE, debug=DEBUG )
    slurm = Slurm(ssh)

#
# MAIN LOOP : Launch rounds .
run_per_round = 30
n_rounds = 5
for round_id in range(n_rounds) :
    print(f"Starting round {round_id} ...")
    chdir = util.setup_round_dir( template_fn, round_id )

    # Get next round from optimizer
    with ScopeWatch("Generating next runs ...") :
        x = optimizer.ask(n_points=run_per_round)

    X = []

    for i in range(len(x)) :
        par = x[i]
        r = {
            '$DIFRAC'         : par[0],
            '$PERMI_MATRIX'   : 100,
            '$PERMI_FRACTURE' : 10**par[1],
            '$RUN_ID'         : i,
            '$ROUND_ID'       : round_id,
            '$CHDIR'          : chdir,
            '$TEMPLATE'       : template_fn,
        }
        X.append(r)

    # Launch the runs
    JID = []
    JOB = []
    with ScopeWatch("Launching jobs ...") :
        for pars in X :
            dat_fn = util.parse_dat( pars )
            #
            sim = SimImex( dat_fn, ssh )
            jid = sim.run( wait = False )
            #

            if jid < 0 :
                print(f"# F: Dat file {dat_fn} failed to run")
                JOB.append(None)
            else :
                JID.append(jid)
                JOB.append({'sr3':sim.sr3, 'stdout':f"{sim.chdir}/{sim.basename}.stdout" })

    # Wait every job to finish before moving on. Print graceful message
    with ScopeWatch("Waiting for the jobs to finish ...", hold_stdout=False) :
        print()
        while True :
            jobs = slurm.running_jobs(JID)
            print('{0:<53}'.format(f"\r{len(jobs):5d} jobs running ..."), end='', flush=True)
            if not len(jobs) : break
            sleep(.5)

    # Calculate cost function (parallel - this can take a while)
    with ScopeWatch("Calculatint cost functions ...") :
        with Pool(100) as p: 
            y = p.map(cost_foo, JOB)
            
    # Info
    print(f"Cost of each run -- ROUND: {round_id}:")
    print(f"{'RUN ID':^10s} {'DIFRAC':^10s} {'PERMI_MATRIX':^20s} {'PERMI_FRACTURE':^20s} {'COST':^10s}")
    for i in range(len(y)) :
        print(f"{X[i]['$RUN_ID']:^10d} {X[i]['$DIFRAC']:^10.2f} {X[i]['$PERMI_MATRIX']:^20.2f} {X[i]['$PERMI_FRACTURE']:^20.2f} {y[i]:^.2f}")
    print("-------")
    
    # PROCEDURE : Update optimizer with information
    print(f"Update optimizer ...")
    optimizer.tell(x,y)

