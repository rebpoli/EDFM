import sys, os

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

