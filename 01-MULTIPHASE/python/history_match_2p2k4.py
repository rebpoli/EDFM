#!/usr/bin/env -S python3 

#%% UPDATE TESTCASE CONFIGURATION

TIMESTEPS = [0,25,50,75,100,150,200,250,300,350,400]
#TIMESTEPS = [0, 50]

#%% HELPER FUNCTIONS
import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import ogsim

#
#
#
class MODEL:
    def __init__(self, sr3, _2p2k=False, ref_model=None) :
        self._2p2k = _2p2k
        self.ref_model = ref_model

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
        print(f"SHAPE-Yy: {np.shape(self.Yy)}")

    def shape(self) :
        return [ len(self.X1), len(self.Y1), len(self.Z1) ]
    

    #
    # Compute the distance from the current model to a reference model
    #
    def distance_from_ref( self, ts ) :
        print(f"Processing timestep {ts} ...")

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

                                # Increment.
                                VW_from_ref[I,J,K] += ref_vw[i,j,k] * pzyx
                                PV_from_ref[I,J,K] += ref_pv[i,j,k] * pzyx

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
        for ts in timesteps :
            self.distance_from_ref(ts)
            dist = _2P2K.distance_rel['sw']
            dist = np.linalg.norm(dist)          
            print(f"{ts:10d} {dist:.3f}")
            DIST.append(dist)
        return np.linalg.norm(DIST)

            

###%% PROCEDURE: Load fine LGR grid and find coordinates
LGR = MODEL(r"..\dat-LGR\01-LGR-MW.sr3")
_2P2K = MODEL(r"..\dat-2P2K\2P2K4-MW.sr3", _2p2k = True, ref_model = LGR)

for ts in TIMESTEPS :
    _2P2K.distance_from_ref(ts)
       

#%%
#!/usr/bin/env -S python3 
from pyhpc import sendJob, setenv, jobs
import pprint
import re

# Converts a linux path to a windows path
def ln2win(fn) :
    ret = re.sub(r"/dfs_geral_ep/", r"\\\\dfs.petrobras.biz/cientifico/", fn)
    #ret = re.sub(r"/", r"\\", ret)
    return ret

# Run imex. Returns when the run is over
def run_imex(fn) :
    basename = re.sub(r"^.*/","",fn)
    chdir = re.sub(r"(\/.+)/.+?$",r"\1",fn)
    
    windir = ln2win(chdir)
    fid = re.sub(r"\.\S+$","",basename)
    sr3_fn = f"{windir}/{fid}.sr3"
    log_fn = f"{windir}/{fid}.log"
    
    params = {
        "chdir" : f"{chdir}",
        "wd" : f"{windir}",
        "modelURI" : f"{fn}",
        "jobName" : basename,
        "solverNodes" : 1,
        "solverCores" : 12,
        "account" : "geomec",
        "slurm" : "-p pre",
        "jobComment" : fn,
        "solverName" : "imex",
        "solverVersion" : "2023.10",
        "solverExtras" : ""
    }
    
    setenv('','','',r'N:\.ssh\id_rsa')
    id, stdout, stderr = sendJob(params)

    print (f"O id do job é {id}")
    if stdout :
        for line in stdout: print(line)

    print ("stderr:")
    if stderr :
        for line in stderr: print(line)

    from time import sleep
    while (True) :
        JOBS = {}
        for i in jobs() : JOBS[i["id"]] = i
        if not len(JOBS) : break # Done
        j = JOBS[id]
        print(f"Job '{j["name"]}' ({j["id"]}) => {j['state']}")
        sleep(.2)

    # Find whatever is useful in the log file
    def summary(log_fn) :
        print(f"Building summary for {log_fn}")
        ret = f"---- SUMMARY FROM {log_fn} -------\n"
        filt = ["Elapsed", "Date and Time", "IMEX", "Material Balances"]
        file = open(log_fn, "r")
        for line in file:
            found = 0
            for f in filt:
                if re.search(f, line): found=1 ; break
            if found : ret += line
        ret += f"---- ****||||**** -------\n"
        print(ret)

    summary(log_fn)
    print("DONE")
    
    return sr3_fn

#
# TEST ROUTINE
#
#fn = r"/dfs_geral_ep/res/santos/unbs/gger/er/er01/USR/bfq9/SIM/TESTE/punq/PUNQ_MOD.dat"
#fn = "/dfs_geral_ep/res/santos/unbs/gger/er/er01/USR/bfq9/2024-PHD/EDFM/01-MULTIPHASE/python/history_match_2p2k4/round_0/run_0.dat"
# run_imex(fn)

#%%
import re

# Parses a template into a final dat to run
def parse_tpl( params, tpl, chdir, run_id ) :
    print("Parsing tpl .....", end="")
    # PROCEDURE : we are going to work on windows!
    tpl = ln2win(tpl)
    chdir = ln2win(chdir)
    # PROCEDURE : Read
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

    for k, v in params.items():
        ret = ret.replace( k, str(v) )

        # PROCEDURE : Write
    ofn = f"{chdir}/run_{run_id}.dat"
    ofh = open(ofn, "w")
    ofh.write(ret)
    ofh.close()
    
    print("[ok]")
    return ofn

chdir = "/dfs_geral_ep/res/santos/unbs/gger/er/er01/USR/bfq9/2024-PHD/EDFM/01-MULTIPHASE/python/history_match_2p2k4"
round_id = 0
run_id = 0
tpl = f"{chdir}/2P2K4-MW.tpl"
round_dir = f"{chdir}/round_{round_id}"

print("Creating dir .....", end="")
import os
try: os.mkdir(ln2win(round_dir))
except: pass
print("[ok]")

params = {
    '$DIFRAC' : 4,
    '$PERMI_MATRIX' : 100,
    '$PERMI_FRACTURE' : 250
}

fn = parse_tpl( params, tpl, round_dir, run_id )

#%%
sr3_fn = run_imex(fn)
#%%
print("OBJECTIVE FUNCTION: ")
if sr3_fn :
    _2P2K = MODEL(sr3_fn, _2p2k = True, ref_model = LGR)
    dist = _2P2K.distance(TIMESTEPS)
    print(f"COST: {dist:.3f}")
