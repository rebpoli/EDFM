#!/usr/bin/python3 

#%% Helper stuff

# TIMESTEPS = [0,25,50,75,100,150,200,250,300,350,400]
TIMESTEPS = [0,25,50,100,200,400]

from time import sleep
import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import ogsim

from skopt import gp_minimize, Optimizer
from skopt.space import Real
from joblib import Parallel, delayed
from multiprocessing import Pool

from sim import SimImex, SSH, Slurm

#
#
#
class MODEL:
    def __init__(self, sr3, _2p2k=False, ref_model=None, stdout=None) :
        self._2p2k = _2p2k
        self.ref_model = ref_model

        # Output file handl
        if stdout : self.ofh = open(stdout, "a")

        self.imex = ogsim.IMEX(sr3)
        imex = self.imex

        # PROCEDURE : Load properties of interest
        imex.load_properties(
                            grid_properties=["SW", "KRSETN","BLOCKPVOL"], 
                            twophi2k=_2p2k,
                            load_geometry=True,
                            geometry_type='all',
                            timestep_idx=TIMESTEPS
                            )

        # PROCEDURE : Organize grid properties into dataframe, indexed by "Offset in days"
        grid = imex.grid
        grid = grid.assign_coords(**{"Offset in days":("Date", grid.coords["Offset in days"].values)})
        self.df = grid.swap_dims({"Date":"Offset in days"}).to_dataframe()

        # PROCEDURE : resolve the X,Y,Z coordinates of each cell in the model.        
        self.resolve_xyz()
        self.build_overlaps()

    # 
    #
    #
    def resolve_xyz(self) :
        df = self.df
        if self._2p2k :
            cx = df.loc[:,0,0,"matrix",0]
            cy = df.loc[0,:,0,"matrix",0]
            cz = df.loc[0,0,:,"matrix",0]
        else :
            cx = df.loc[:,0,0,0]
            cy = df.loc[0,:,0,0]
            cz = df.loc[0,0,:,0]

        cx = cx.assign( X1=lambda dfx:dfx.DX.cumsum())
        cy = cy.assign( Y1=lambda dfy:dfy.DY.cumsum())
        cz = cz.assign( Z1=lambda dfz:dfz.DZ.cumsum())
        cx["X0"] = cx.X1.shift(1).fillna(0)
        cy["Y0"] = cy.Y1.shift(1).fillna(0)
        cz["Z0"] = cz.Z1.shift(1).fillna(0)

        # Create lists of coordinates - easier to manipulate
        self.X1 = cx.X1.to_list()
        self.Y1 = cy.Y1.to_list()
        self.Z1 = cz.Z1.to_list()

    #
    #
    #
    def build_overlaps(self) :
        ref = self.ref_model
        if not ref : return

        # Typically refX is the coarse model and trgX is the fine one
        def _build_Xx_map(refX, trgX) :
            Xx = np.zeros( [len(trgX), len(refX)] )
            for i in range( len(trgX) ) :
                _x0 = 0
                if i : _x0 = trgX[i-1]
                _x1 = trgX[i]
                
                for j in range( len(refX) ) :
                    _x0f = 0
                    if j : _x0f = refX[j-1]
                    _x1f = refX[j]
                    _l = _x1f - _x0f
                
                    # Find the overlap
                    if _x0f > _x1 : continue # no everlap
                    if _x1f < _x0 : continue # no everlap
                    if _x0f < _x0 : _x0f = _x0
                    if _x1f > _x1 : _x1f = _x1

                    Xx[i,j] = (_x1f - _x0f) / _l
            return Xx

        self.Xx = _build_Xx_map( ref.X1, self.X1 )
        self.Yy = _build_Xx_map( ref.Y1, self.Y1 )
        self.Zz = _build_Xx_map( ref.Z1, self.Z1 )

    def shape(self) :
        return [ len(self.X1), len(self.Y1), len(self.Z1) ]
    

    #
    # Compute the distance from the current model to a reference model
    #
    def distance_from_ref( self, ts ) :
        ref = self.ref_model

        ref_sw, ref_pv = ref.objective_arrays( ["SW", "BLOCKPVOL"], ts, frac_krsetn=2 )
        ref_vw = ref_pv * ref_sw

        trg_sw, trg_pv = self.objective_arrays( ["SW", "BLOCKPVOL"], ts, frame_k=0 )
        trg_vw = trg_pv * trg_sw

        # Calculate the volumes of the reference model in the target
        PV_from_ref = np.zeros_like(trg_pv)
        VW_from_ref = np.zeros_like(trg_pv)
        SW_from_ref = np.zeros_like(trg_pv)
        
        Xx,Yy,Zz = self.Xx, self.Yy, self.Zz
        for I in range( len(Xx) ) :
            for J in range( len(Yy) ) :
                for K in range( len(Zz) ) :
                    _vw, _pv, _sw = 0, 0, 0
                    # PROCEDURE : Compute the volumes of pore and water in the coarse mesh from the fine data.                    
                    for i in range(len(Xx[I])) :
                        px = Xx[I,i]
                        if not px : continue
                        for j in range(len(Yy[J])) :
                            pyx = Yy[J,j] * px
                            if not pyx : continue
                            for k in range(len(Zz[K])) :
                                pzyx = Zz[K,k] * pyx
                                if not pzyx : continue
                                _vw += ref_vw[i,j,k] * pzyx
                                _pv += ref_pv[i,j,k] * pzyx
                                    
                    VW_from_ref[I,J,K] += _vw
                    PV_from_ref[I,J,K] += _pv

                    # PROCEDURE : Compute the water saturation
                    if  PV_from_ref[I,J,K] == 0 :
                        SW_from_ref[I,J,K] = 0
                    else :
                        SW_from_ref[I,J,K] = VW_from_ref[I,J,K] / PV_from_ref[I,J,K]

        self.ref_arr = { 'sw':SW_from_ref, 'vw':VW_from_ref, 'pv':PV_from_ref }
        self.trg_arr = { 'sw':trg_sw,      'vw':trg_vw,      'pv':trg_pv }

        self.distance = {
            'sw' : abs( self.ref_arr['sw'] - self.trg_arr['sw'] ),
            'vw' : abs( self.ref_arr['vw'] - self.trg_arr['vw'] ),
            'pv' : abs( self.ref_arr['pv'] - self.trg_arr['pv'] )
        }

        self.distance_rel = {
            'sw' : self.distance['sw'] / ( self.ref_arr['sw'] + .0001),
            'vw' : self.distance['vw'] / ( self.ref_arr['vw'] + 1 ),
            'pv' : self.distance['pv'] / ( self.ref_arr['pv'] + 1 ),
        }

    #
    #
    #
    def objective_arrays( self, props, ts, frac_krsetn=None, frame_k=None ) :
        ret = []
        shape = self.shape()
        for p in props :
            if self._2p2k :
                pp = self.df.loc[:,:,:,"matrix",ts][p].to_numpy().reshape( shape )
                pp[np.isnan(pp)] = 0
            else :
                pp = self.df.loc[:,:,:,ts][p].to_numpy().reshape( shape )
                if frac_krsetn != None :
                    _sel = self.df.loc[:,:,:,0]["KRSETN"].to_numpy().reshape( shape )
                    _sel = ( _sel == frac_krsetn )
                    pp[_sel] = 0
            
            if frame_k != None :
                _sel = np.full( self.shape(), False ) 
                _sel[:,:,frame_k] = True
                pp[_sel] = 0
            
            ret.append( pp )
        return ret

    #
    #
    #
    def distance( self, timesteps ) :
        DIST = []
        OFH = self.ofh
        
        if OFH : 
            OFH.write(f"{'TS':^10s} | {'Cost':^10s}\n{25*'-'}\n")

        # PROCEDURE : Compute distance for each selected timestep
        for ts in timesteps :
            self.distance_from_ref(ts)
            dist = self.distance_rel['sw']
            dist = np.linalg.norm(dist)          
            DIST.append(dist)

            if OFH : OFH.write(f"{ts:^10d} | {dist:^10.3f}\n")

        # PROCEDURE : Get the L2 Norm of the distances
        ret = np.linalg.norm(DIST)

        if OFH : 
            OFH.write(25*'-')
            OFH.write("\n")
            OFH.write(f"{'Norm:':^10s} | {ret:^10.3f}\n")

        return ret

# from pyhpc import sendJob, setenv, jobs
import pprint
import re



import re
# Parses a template into a final dat to run
def parse_dat( pars ) :
    round_id = pars["$ROUND_ID"]
    run_id = pars["$RUN_ID"]

    chdir = pars["$CHDIR"]
    tpl = pars["$TEMPLATE"]

    # PROCEDURE : Read template
    tplfh = open(tpl,"r")
    lines = tplfh.readlines()
    tplfh.close()

    # PROCEDURE : Replace
    ret = ""
    for line in lines :
        # Replace the template tags
        # Fix the includes
        line = re.sub(r"^(\s*\*?include\s*('|\"))", r"\1../", line, flags=re.IGNORECASE) 
        ret += line

    for k, v in pars.items():
        ret = ret.replace( k, str(v) )

    # PROCEDURE : Write .dat
    ofn = f"{chdir}/run_{run_id}.dat"
    ofh = open(ofn, "w")
    ofh.write(ret)
    ofh.close()
    
    return ofn

#%% MAIN ROUTINE

# PROCEDURE: Load fine LGR (reference) grid
lgr_fn = r"../dat-LGR/01-LGR-MW.sr3"
print('{0:<50}'.format(f"Loading {lgr_fn} ...   "), end='', flush=True)
LGR = MODEL(lgr_fn)
print("[Done]")

#
# This is a parallel function
def cost_foo( X ) :
    if os.path.exists(X['stdout']) : os.remove(X['stdout'])

    # PROCEDURE : Calculate the cost function
    _mod = MODEL(X['sr3'], _2p2k = True, ref_model = LGR, stdout=X['stdout'])
    cost = _mod.distance(TIMESTEPS)
    return cost
        
    
# PROCEDURE : Initialize Optimizer /// Dimensions: DIFRAC, PERMI_FRACTURE
print('{0:<50}'.format(f"Initialize optimizer...   "), end='', flush=True)
optimizer = Optimizer(
    #           DIFRAC       log(PERM_FRAC)
    dimensions=[Real(1,50), Real(2,3)],
    random_state=1,
    base_estimator='gp',
    n_initial_points=10
)
print(f"[Done]")

# PROCEDURE : Open connection
print('{0:<50}'.format(f"Connect SSH...   "), end='', flush=True)
print(f"[Done]")

run_per_round = 30
n_rounds = 3

ssh = SSH( "reslogin" )
slurm = Slurm(ssh)

# PROCEDURE : Launch rounds .
for round_id in range(n_rounds) :
    print(f"Starting round {round_id} ...")

    # Create dir
    chdir    = "/dfs_geral_ep/res/santos/unbs/gger/er/er01/USR/bfq9/2024-PHD/EDFM/01-MULTIPHASE/python"
    template = f"{chdir}/2P2K4-MW.tpl"
    chdir    = f"{chdir}/history_match_2p2k4/round_{round_id}"
    import os
    try: os.mkdir(chdir)
    except: pass

    # Get next round from optimizer
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
            '$TEMPLATE'       : template,
        }
        X.append(r)

    # Launch the runs
    JID = []
    JOB = []
    for pars in X :
        dat_fn = parse_dat( pars )
        #
        sim = SimImex( dat_fn, ssh )
        jid = sim.run( wait = False )
        #

        if jid < 0 :
            print(f"[FAILED] Dat file {dat_fn} failed to run")
            JOB.append(None)
        else :
            JID.append(jid)
            JOB.append({'sr3':sim.sr3, 'stdout':f"{sim.chdir}/{sim.basename}.stdout" })

    # Wait every job to finish before moving on. Print graceful message
    while True :
        jobs = slurm.running_jobs(JID)
        print(f"\r{len(jobs):5d} jobs running ...", end='', flush=True)
        if not len(jobs) : break
        sleep(.5)
    print()

    # Calculate cost function (parallel - this can take a while)
    print("Calculating cost function...")
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

# %%






# # Run imex. Returns when the run is over
# def run_imex(fn) :
#     basename = re.sub(r"^.*/","",fn)
#     chdir = re.sub(r"(\/.+)/.+?$",r"\1",fn)
#     
#     windir = ln2win(chdir)
#     fid = re.sub(r"\.\S+$","",basename)
#     sr3_fn = f"{windir}/{fid}.sr3"
#     log_fn = f"{windir}/{fid}.log"
#     
#     params = {
#         "chdir" : f"{chdir}",
#         "wd" : f"{windir}",
#         "modelURI" : f"{fn}",
#         "jobName" : basename,
#         "solverNodes" : 1,
#         "solverCores" : 12,
#         "account" : "geomec",
#         "slurm" : "-p pre",
#         "jobComment" : fn,
#         "solverName" : "imex",
#         "solverVersion" : "2023.10",
#         "solverExtras" : ""
#     }
#     
#     setenv('','','',r'N:\.ssh\id_rsa')
#     id, stdout, stderr = sendJob(params)

#     print (f"O id do job é {id}")
#     if stdout :
#         for line in stdout: print(line)

#     print ("stderr:")
#     if stderr :
#         for line in stderr: print(line)

#     while (True) :
#         JOBS = {}
#         for i in jobs() : JOBS[i["id"]] = i
#         if not id in JOBS : break # Done
#         print(f"id:{id} // JOBS:{JOBS}")
#         sleep(1)

#     # Find whatever is useful in the log file
#     def summary(log_fn) :
#         print(f"Building summary for {log_fn}")
#         ret = f"---- SUMMARY FROM {log_fn} -------\n"
#         filt = ["Elapsed", "Date and Time", "IMEX", "Material Balances"]
#         file = open(log_fn, "r")
#         for line in file:
#             found = 0
#             for f in filt:
#                 if re.search(f, line): found=1 ; break
#             if found : ret += line
#         ret += f"---- ****||||**** -------\n"
#         print(ret)

#     summary(log_fn)
#     print("DONE")
#     
#     return sr3_fn
