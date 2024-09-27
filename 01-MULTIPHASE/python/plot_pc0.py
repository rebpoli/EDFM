#!/usr/bin/env -S python3

import h5py
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from paper import *

CFG_LIST = [ "LGR MW Cap Cont", "LGR OW Cap Cont", "LGR WW Cap Cont",
             "LGR MW $P_c=0$", "LGR OW $P_c=0$", "LGR WW $P_c=0$" ]

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

#     tau = cfg['tau']
#     rf_2_3 = cfg["rf_2_3"]
#     ax.scatter( tau, rf_2_3, c=c, marker="o", s=3, zorder=100 )

ax.set_xlabel("Days")
ax.set_ylabel(r"Recovery factor (\%)")
ax.set_ylim(0,80)

cm = 1/2.54
fig.set_size_inches(10*cm, 6*cm)

ax.set_xlim(0,400)
leg = ax.legend(loc='lower right', bbox_to_anchor=(.99, 0.2))
leg.get_frame().set_linewidth(.3)

fig.subplots_adjust( left=0.09, right=0.95, bottom=0.15, top=0.97, wspace=.18, hspace=.06 )
fig.savefig("png/pc0-xlin.png", dpi=500)

ax.set_xlim(1e-1,2000)
ax.set_xscale('log')
leg = ax.legend(loc='upper left', bbox_to_anchor=(.06, .96))
leg.get_frame().set_linewidth(.3)

fig.subplots_adjust( left=0.09, right=0.95, bottom=0.15, top=0.97, wspace=.18, hspace=.06 )
fig.savefig("png/pc0-xlog.png", dpi=500)
