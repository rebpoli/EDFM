#!/usr/bin/env -S python3 

#%%
import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import ogsim

def xyz_coords_2p2k( DF ) :
    cx = DF.loc[:,0,0,"matrix",0]
    cy = DF.loc[0,:,0,"matrix",0]
    cz = DF.loc[0,0,:,"matrix",0]

    cx = cx.assign( X1=lambda dfx:dfx.DX.cumsum())
    cy = cy.assign( Y1=lambda dfy:dfy.DY.cumsum())
    cz = cz.assign( Z1=lambda dfz:dfz.DZ.cumsum())
    cx["X0"] = cx.X1.shift(1).fillna(0)
    cy["Y0"] = cy.Y1.shift(1).fillna(0)
    cz["Z0"] = cz.Z1.shift(1).fillna(0)


    # Create lists of coordinates - easier to manipulate
    X1 = cx.X1.to_list()
    Y1 = cy.Y1.to_list()
    Z1 = cz.Z1.to_list()
    return ( X1, Y1, Z1 )    

def xyz_coords_lgr( DF ) :
    cx = DF.loc[:,0,0,0]
    cy = DF.loc[0,:,0,0]
    cz = DF.loc[0,0,:,0]

    cx = cx.assign( X1=lambda dfx:dfx.DX.cumsum())
    cy = cy.assign( Y1=lambda dfy:dfy.DY.cumsum())
    cz = cz.assign( Z1=lambda dfz:dfz.DZ.cumsum())
    cx["X0"] = cx.X1.shift(1).fillna(0)
    cy["Y0"] = cy.Y1.shift(1).fillna(0)
    cz["Z0"] = cz.Z1.shift(1).fillna(0)


    # Create lists of coordinates - easier to manipulate
    X1 = cx.X1.to_list()
    Y1 = cy.Y1.to_list()
    Z1 = cz.Z1.to_list()
    return ( X1, Y1, Z1 )    

#%% PROCEDURE: Load coarse 2p2k grid and find coordinates

#TIMESTEPS = [0,25,50,75,100,150,200,250,300,350,400]
TIMESTEPS = [0, 400]

#fn = r"2P2K4-MW.dat"
#imex = ogsim.IMEX(fn)
#imex.run(nproc=12)
imex_2p2k = ogsim.IMEX(r"..\dat-2P2K\2P2K4-MW.sr3")
imex_2p2k.load_properties(
                    grid_properties=["SW", "KRSETN", "BLOCKPVOL"],
                    twophi2k=True, load_geometry=True, 
                    geometry_type='all',
                    timestep_idx=TIMESTEPS )
                    
props_2p2k = imex_2p2k.grid
props_2p2k = imex_2p2k.grid.assign_coords(**{"Offset in days":("Date", props_2p2k.coords["Offset in days"].values)})
df_2p2k = props_2p2k.swap_dims({"Date":"Offset in days"}).to_dataframe()
X1, Y1, Z1 = xyz_coords_2p2k( df_2p2k )

#%% PROCEDURE: Load fine LGR grid and find coordinates
imex_lgr = ogsim.IMEX(r"..\dat-LGR\01-LGR-MW.sr3")
imex_lgr.load_properties(
                    grid_properties=["SW", "KRSETN","BLOCKPVOL"], 
                    load_geometry=True, geometry_type='all',
                    timestep_idx=TIMESTEPS )
props_lgr = imex_lgr.grid
props_lgr = imex_lgr.grid.assign_coords(**{"Offset in days":("Date", props_lgr.coords["Offset in days"].values)})
df_lgr = props_lgr.swap_dims({"Date":"Offset in days"}).to_dataframe()
X1f, Y1f, Z1f = xyz_coords_lgr( df_lgr )

#%% PROCEDURE: Compute overlap maps

# X is the macroblock ; x is the fine block
# Build the map of contribution of each fine block into the coarse block
def build_overlap_map( X, x ) :
    Xx = np.zeros( [len(X), len(x)] )
    for i in range( len(X) ) :
        _x0 = 0
        if i : _x0 = X[i-1]
        _x1 = X[i]
        
        for j in range( len(x) ) :
            _x0f = 0
            if j : _x0f = x[j-1]
            _x1f = x[j]
            _l = _x1f - _x0f
          
            # Find the overlap
            if _x0f > _x1 : continue # no everlap
            if _x1f < _x0 : continue # no everlap
            if _x0f < _x0 : _x0f = _x0
            if _x1f > _x1 : _x1f = _x1

            Xx[i,j] = (_x1f - _x0f) / _l
    
    return Xx
        
Xx = build_overlap_map( X1, X1f )
Yy = build_overlap_map( Y1, Y1f )
Zz = build_overlap_map( Z1, Z1f )

#%%

nx,ny,nz = len(X1f), len(Y1f), len(Z1f)
shape_lgr = [ nx, ny, nz ]
FRAC_LGR = df_lgr.loc[:,:,:,0]["KRSETN"].to_numpy().reshape( shape_lgr )
FRAC_LGR = ( FRAC_LGR == 2 )

shape_2p2k = [ len(X1), len(Y1), len(Z1) ]
FRAME_2P2K = np.full( shape_2p2k, False ) 
FRAME_2P2K[:,:,0] = True

for ts in TIMESTEPS :
    print(f"Processing timestep {ts} ...")
    SWf = df_lgr.loc[:,:,:,ts]["SW"].to_numpy().reshape( shape_lgr )
    VPf = df_lgr.loc[:,:,:,ts]["BLOCKPVOL"].to_numpy().reshape( shape_lgr )
    VPf[FRAC_LGR] = 0 # we are only interested in matrix cells
    VWf = VPf * SWf
    
    SW = df_2p2k.loc[:,:,:,"matrix",ts]["SW"].to_numpy().reshape( shape_2p2k )
    VP = df_2p2k.loc[:,:,:,"matrix",ts]["BLOCKPVOL"].to_numpy().reshape( shape_2p2k )
    VP[FRAME_2P2K] = 0
    VW = VP * SW
    
    VP_from_fine = np.zeros_like(VP)
    VW_from_fine = np.zeros_like(VP)
    SW_from_fine = np.zeros_like(VP)
    
    # Map VW from the fine grid to the corse grid
    for I in range( len(Xx) ) :
        for J in range( len(Yy) ) :
            for K in range( len(Zz) ) :
                VWf_TOT = 0
                VPf_TOT = 0
                
                for i in range(nx) :
                    px = Xx[I,i]
                    if not px : continue
                    for j in range(ny) :s
                        pyx = Yy[J,j] * px
                        if not pyx : continue
                        for k in range(nz) :
                            pzyx = Zz[K,k] * pyx
                            if not pzyx : continue
                            VWf_TOT += VWf[i,j,k] * pzyx
                            VPf_TOT += VPf[i,j,k] * pzyx
                            
                # VW holds the water volume in the fine grid associated 
                # with the large grid cell I,J,K
                vw_ = VW[I,J,K]
                vp_ = VP[I,J,K]
                sw_ = vw_/vp_
                
                vwf_ = VWf_TOT
                vpf_ = VPf_TOT
                if vpf_ == 0 : swf_ = 0
                else : swf_ = vwf_ / vpf_
                
                VP_from_fine[I,J,K] = vpf_
                VW_from_fine[I,J,K] = vwf_
                SW_from_fine[I,J,K] = swf_
                #print(f"I,J,K:{I},{J},{K} -- VW,VP,SW={vw_:.1f},{vp_:.1f},{sw_:.5f} VWf,VPf,SWf={vwf_:.1f},{vpf_:.1f},{swf_:.5f}" )
                
                
                
                
                
# %%
