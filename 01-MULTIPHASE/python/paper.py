import sys, os

import pandas as pd
from scipy.interpolate import interp1d
import ogsim

import matplotlib.pyplot as plt
if os.path.isfile( 'paper.mplstyle' ) :
    plt.style.use('default')   ## reset!
    plt.style.use('paper.mplstyle')

##
#
# Helper function to set default figure style that the mpldtyle template is not able to cover
#
def paperfig( fig ) :
    for i, ax in enumerate(fig.axes):
        ax.set_axisbelow(True)
        ax.grid(which='major', linestyle='-', lw=.5, alpha=1, color="0.6")
        ax.grid(which='minor', linestyle='-', lw=.2, alpha=1, color="0.8")
#         ax.yaxis.set_major_locator(plt.MultipleLocator(5))
#         ax.yaxis.set_minor_locator(plt.MultipleLocator(.5))
#         ax.xaxis.set_minor_locator(plt.MultipleLocator(0.02))


#
#
#
def die_if_uptodate( in_files, out_files ) :
    INM  = [ os.path.getmtime(x) for x in in_files ]

    may_skip = True
    for f in out_files : 
        if not os.path.isfile(f) : may_skip = False

    if may_skip :
        OUTM = [ os.path.getmtime(x) for x in out_files ]
        if max(INM) < min(OUTM)  :
          print()
          print("########################################")
          print("Files are up to date ... Skipping.")
          print("########################################")
          print()
          print()
          exit(0)

#
# 
#
import pandas as pd
import os
def load_csv_or_die( fn ) :
    if not os.path.isfile( fn ) :
        print(f"# F: Cannot find file '{fn}'...")
        exit(-1)

    df = pd.read_csv( fn, sep="\t" )
    return df;

#
# CONFIGURATIONS FOR THE PLOTS
#
CFG = {
        "LGR MW Cap Cont": { 'fn' : "../dat-LGR-long2/01-LGR-MW.sr3" , 'c' : 'r', 'ls': '--' },
        "LGR OW Cap Cont": { 'fn' : "../dat-LGR-long2/01-LGR-OW.sr3" , 'c' : 'g', 'ls': '--' },
        "LGR WW Cap Cont": { 'fn' : "../dat-LGR-long2/01-LGR-WW.sr3" , 'c' : 'b', 'ls': '--' },

        "LGR MW $P_c=0$": { 'fn' : "../dat-LGR-long2/01-LGR-MW-PC0.sr3" , 'c' : 'r', 'ls': '-' },
        "LGR OW $P_c=0$": { 'fn' : "../dat-LGR-long2/01-LGR-OW-PC0.sr3" , 'c' : 'g', 'ls': '-' },
        "LGR WW $P_c=0$": { 'fn' : "../dat-LGR-long2/01-LGR-WW-PC0.sr3" , 'c' : 'b', 'ls': '-' },

        "LGR MW Cap Discont" : { 'fn' : "../dat-LGR-long2/01-LGR-MW-nocapcont.sr3" , 'c' : 'r', 'ls':'-' },
        "LGR OW Cap Discont" : { 'fn' : "../dat-LGR-long2/01-LGR-OW-nocapcont.sr3" , 'c' : 'g', 'ls':'-' },
        "LGR WW Cap Discont" : { 'fn' : "../dat-LGR-long2/01-LGR-WW-nocapcont.sr3" , 'c' : 'b', 'ls':'-' },

        "2P2K4 MW Cap Cont": { 'fn' : "../dat-2P2K/2P2K4-MW.sr3" , 'c' : 'r', 'ls': '-' },
        "2P2K4 OW Cap Cont": { 'fn' : "../dat-2P2K/2P2K4-OW.sr3" , 'c' : 'g', 'ls': '-' },
        "2P2K4 WW Cap Cont": { 'fn' : "../dat-2P2K/2P2K4-WW.sr3" , 'c' : 'b', 'ls': '-' },

        "2P2K4 MW $P_c=0$": { 'fn' : "../dat-2P2K/2P2K4-MW-Pc0.sr3" , 'c' : 'r', 'ls': '-' },
        "2P2K4 OW $P_c=0$": { 'fn' : "../dat-2P2K/2P2K4-OW-Pc0.sr3" , 'c' : 'g', 'ls': '-' },
        "2P2K4 WW $P_c=0$": { 'fn' : "../dat-2P2K/2P2K4-WW-Pc0.sr3" , 'c' : 'b', 'ls': '-' },
}

oil_str = "Oil Volume SC SCTR"


#
# PROCEDURE : Prepare database
#
dfs = []
for l in CFG :
    cfg=CFG[l]
    fn = cfg['fn']
    print(f"Reading '{fn}' ...")
    sr3 = ogsim.IMEX(fn)
    sec = sr3.read_timeseries('SECTORS')

    # Troca o indice para "offset in days"
    sec = sec.sel(origin='RES')
    sec = sec.assign_coords(**{"Offset in days":("Date", sec.coords["Offset in days"].values)})
    df  = sec.swap_dims({"Date":"Offset in days"})[oil_str].to_dataframe()

    # Calcula Recovery factor
    v0 = df.iloc[0][oil_str]
    df['RF'] = ( 1 - df[oil_str]/v0 ) * 100

    # Registra
    df['label'] = l
    dfs.append(df)

df = pd.concat(dfs)
print(df)

#
# PROCEDURE: find time constant
#
data = []
# for l, grp in df.groupby("label") :
#     c = CFG[l]['c']

#     # PROCEDURE: find time constant
#     rf=grp["RF"]
#     time=grp.index

#     print(f"Processing {l} ...")
#     f=interp1d( rf, time, kind="cubic" )

#     rf_max = grp["RF"].max()
#     rf_2_3 = rf_max * 2 / 3
#     tau = f(rf_2_3)

#     CFG[l]["rf_2_3"] = rf_2_3
#     CFG[l]["tau"] = tau

#     data.append( { "label" : l , "rf_2_3" : rf_2_3, "tau" : tau, "rf_max":rf_max } )

# TIME_CONSTANT = pd.DataFrame( data )
# TIME_CONSTANT.to_excel( "png/time_constant.xlsx" )
