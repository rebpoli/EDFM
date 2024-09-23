import numpy as np
import ogsim

#
#
#
class Model :
    def __init__(self, sr3, _2p2k=False, ref_model=None, stdout=None, timesteps=None) :
        self._2p2k = _2p2k
        self.ref_model = ref_model
        self.timesteps = timesteps

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
                            timestep_idx=timesteps
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
    def distance( self ) :
        timesteps = self.timesteps
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

