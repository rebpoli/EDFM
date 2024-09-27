#!/usr/bin/env -S python3 


import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from paper import *
import ogsim


CFG_LIST = [ "LGR MW Cap Cont", "LGR OW Cap Cont", "LGR WW Cap Cont",
             "2P2K4 MW $P_c=0$" , "2P2K4 OW $P_c=0$",  "2P2K4 WW $P_c=0$"  ]

ALPHA = [ 0.5, 0.5, 0.5, 1, 1, 1 ]

fig, ax = plt.subplots(1, 1, sharex=True)
paperfig(fig)

#
# POCEDURE : Plot recovery factor in res
#
i=0
for l,a in zip( CFG_LIST, ALPHA ) :
    grp = df[df.label == l]
    cfg = CFG[l]
    ls = cfg['ls']
    c = cfg['c']

    ax.plot(grp.index, grp["RF"], label=l, ls=ls, c=c, alpha=a)

#     tau = cfg['tau']
#     rf_2_3 = cfg["rf_2_3"]
#     ax.scatter( tau, rf_2_3, c=c, marker="o", s=3, zorder=100, alpha=a )

ax.set_xlabel("Days")
ax.set_ylabel(r"Recovery factor (\%)")
ax.set_ylim(0,80)

cm = 1/2.54
fig.set_size_inches(10*cm, 6*cm)

ax.set_xlim(0,400)
leg = ax.legend(loc='lower right', bbox_to_anchor=(.99, 0.1))
leg.get_frame().set_linewidth(.3)

fig.subplots_adjust( left=0.09, right=0.95, bottom=0.15, top=0.97, wspace=.18, hspace=.06 )
fig.savefig("png/rf-2p2k-pc0-xlin.png", dpi=500)

ax.set_xlim(1e-1,2000)
ax.set_xscale('log')
leg = ax.legend(loc='upper left', bbox_to_anchor=(.06, .96))
leg.get_frame().set_linewidth(.3)

fig.subplots_adjust( left=0.09, right=0.95, bottom=0.15, top=0.97, wspace=.18, hspace=.06 )
fig.savefig("png/rf-2p2k-pc0-xlog.png", dpi=500)
