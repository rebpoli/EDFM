#!/usr/bin/env -S python3


import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from paper import *
import ogsim

CFG = [
    { 
        'l' : "01-LGR-MW",
        'fn' : "../dat/01-LGR-MW.sr3" 
    },
    { 
        'l' : "01-LGR-OW",
        'fn' : "../dat/01-LGR-OW.sr3" 
    },
    { 
        'l' : "01-LGR-WW",
        'fn' : "../dat/01-LGR-WW.sr3" 
    },
# ]

# CFG = [
    { 
        'l' : "01-LGR-MW No Cap Cont",
        'fn' : "../dat/01-LGR-MW-nocapcont.sr3" 
    },
    { 
        'l' : "01-LGR-OW No Cap Cont",
        'fn' : "../dat/01-LGR-OW-nocapcont.sr3" 
    },
    { 
        'l' : "01-LGR-WW No Cap Cont",
        'fn' : "../dat/01-LGR-WW-nocapcont.sr3" 
    },
]


dfs = []

oil_str = "Oil Volume SC SCTR"

for cfg in CFG :
    fn = cfg['fn']
    sr3 = ogsim.IMEX(fn)
    sec = sr3.read_timeseries('SECTORS')
    df = sec.sel(origin='RES')[oil_str].to_dataframe()
    df['label'] = cfg['l']
    v0 = df.iloc[0][oil_str]
    df['RF'] = df[oil_str]/v0

    dfs.append(df)

df = pd.concat(dfs)
print(df)

fig, axs = plt.subplots(3, 1, sharex=True)
paperfig(fig)

ax=axs[0]
for l, grp in df.groupby("label") :
    ax.plot(grp.index, grp[oil_str], label=l)
ax.set_title(oil_str)
ax.legend(loc='lower right')

ax=axs[1]
for l, grp in df.groupby("label") :
    ax.plot(grp.index, grp["RF"], label=l)
ax.set_title("Recovery Factor")
ax.legend(loc='lower right')

fig.tight_layout()
fig.savefig("png/test.png", dpi=500)
