#!/usr/bin/env -S python3 


import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from paper import *
import ogsim


CFG_LIST = [ "LGR MW Cap Cont", "LGR OW Cap Cont",
             "LGR WW Cap Cont",
             "LGR MW Cap Discont", "LGR OW Cap Discont", "LGR WW Cap Discont" ]


fig, ax = plt.subplots(1, 1, sharex=True)
paperfig(fig)

#
# POCEDURE : Plot recovery factor in res
#
for l in CFG_LIST :
    grp = df[df.label == l]
    cfg = CFG[l]
    ls = cfg['ls']
    c = cfg['c']

    ax.plot(grp.index, grp["RF"], label=l, ls=ls, c=c)

    tau = cfg['tau']
    rf_2_3 = cfg["rf_2_3"]
    ax.scatter( tau, rf_2_3, c=c, marker="o", s=3, zorder=100 )

ax.set_xlabel("Days")
ax.set_ylabel(r"Recovery factor (\%)")
ax.set_xlim(0,400)
ax.set_ylim(0,80)
leg = ax.legend(loc='lower right', bbox_to_anchor=(.99, 0.2))
leg.get_frame().set_linewidth(.3)

# PROCEDURE : Close figure
cm = 1/2.54
fig.set_size_inches(10*cm, 6*cm)
fig.subplots_adjust( left=0.09, right=0.95, bottom=0.15, top=0.97, wspace=.18, hspace=.06 )
fig.savefig("png/rf.png", dpi=500)
