#!/usr/bin/env -S python3 

######### CHIMASPY HEADER
import sys, os
TOPDIR = "../"
for i in range(1,10) :
    if os.path.isfile(TOPDIR + ".chimas_top") :
        break 
    TOPDIR += "../" 
sys.path.append(TOPDIR+'share/script/python')

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--Output", help = "Output mesh file", default="msh/plain.msh")
parser.add_argument("-i", "--Input", help = "Input json config file", default="config.json")
args = parser.parse_args()

if args.Output:
    print("Displaying Output as: % s" % args.Output)
if args.Input:
    print("Reading JSON INPUT CONFIGURATION as: % s" % args.Input)

# ## Read json and feed variables into CFG
import json
print(f"Loading json '{args.Input}'")
with open(args.Input, 'r') as f:
    CFG = json.load(f)
###########

# Import libraries
import sys
import math
from math import pi, sin, cos, radians, sqrt
import numpy as np

# Import good functions to get things clean
import gmsh
from gmsh import model as Model
Clear = gmsh.clear
Plugin = gmsh.plugin
Option = gmsh.option
Initialize = gmsh.initialize
Finalize = gmsh.finalize
Run = gmsh.fltk.run
Mesh = Model.mesh
Generate = Mesh.generate
Occ = Model.occ
Synchronize = Model.occ.synchronize
AddModel = Model.add
AddBox = Occ.addBox
AddPoint = Occ.addPoint
AddLine = Occ.addLine
AddCurveLoop = Occ.addCurveLoop
AddCircle = Occ.addCircle
AddPlaneSurface = Occ.addPlaneSurface
Fragment = Occ.fragment
Intersect = Occ.intersect
Fuse = Occ.fuse
Remove = Occ.remove
Embed = Mesh.embed
###

#
# MAIN SCRIPT
#

Initialize( sys.argv )
Clear()
AddModel("SimpleMesh")

## Dimensions of the domain and the frame
DOMAIN_L = 100

FRAC_M = 6  # number of blocks for fracture reference
FRAC_N = CFG["mesh"]["frac_n"]  # number of fractures in the domain

print(f"Generating mesh with '{FRAC_N}' fractures ...");

##
#
#
def create_plane_from_strike_dip(strike, dip, origin=(0, 0, 0), size=10):
    print("Hello world")
    # Convert angles to radians
    strike_rad = radians(strike)
    dip_rad = radians(dip)

    # Calculate the normal vector of the plane
    # The strike direction is perpendicular to the normal's horizontal component
    # Strike is measured clockwise from North (Y-axis in this case)
    nx = sin(strike_rad - pi/2) * sin(dip_rad)
    ny = cos(strike_rad - pi/2) * sin(dip_rad)
    nz = cos(dip_rad)

    # Normalize the normal vector
    norm = sqrt(nx**2 + ny**2 + nz**2)
    nx, ny, nz = nx/norm, ny/norm, nz/norm

    # Calculate two vectors in the plane
    # First vector along the strike direction
    v1x = sin(strike_rad)
    v1y = cos(strike_rad)
    v1z = 0

    # Second vector (perpendicular to both normal and first vector)
    v2x = ny*v1z - nz*v1y
    v2y = nz*v1x - nx*v1z
    v2z = nx*v1y - ny*v1x

    # Create 4 corner points of the plane
    half_size = size / 2
    p1 = (origin[0] - v1x*half_size - v2x*half_size,
          origin[1] - v1y*half_size - v2y*half_size,
          origin[2] - v1z*half_size - v2z*half_size)

    p2 = (origin[0] + v1x*half_size - v2x*half_size,
          origin[1] + v1y*half_size - v2y*half_size,
          origin[2] + v1z*half_size - v2z*half_size)

    p3 = (origin[0] + v1x*half_size + v2x*half_size,
          origin[1] + v1y*half_size + v2y*half_size,
          origin[2] + v1z*half_size + v2z*half_size)

    p4 = (origin[0] - v1x*half_size + v2x*half_size,
          origin[1] - v1y*half_size + v2y*half_size,
          origin[2] - v1z*half_size + v2z*half_size)

    print(f"p1: {p1}")

    # Add points to Gmsh model
    p1_tag = AddPoint(p1[0], p1[1], p1[2])
    p2_tag = AddPoint(p2[0], p2[1], p2[2])
    p3_tag = AddPoint(p3[0], p3[1], p3[2])
    p4_tag = AddPoint(p4[0], p4[1], p4[2])

    # Create lines connecting the points
    l1 = AddLine(p1_tag, p2_tag)
    l2 = AddLine(p2_tag, p3_tag)
    l3 = AddLine(p3_tag, p4_tag)
    l4 = AddLine(p4_tag, p1_tag)

    # Create a curve loop
    curve_loop = AddCurveLoop([l1, l2, l3, l4])

    # Create a surface
    surface = AddPlaneSurface([curve_loop])

    print("Added surface %d" % surface)
    return surface


v1 = AddBox( 0,0,0, DOMAIN_L,DOMAIN_L,DOMAIN_L )
create_plane_from_strike_dip(60, 45, origin=(50, 50, 50), size=80)
create_plane_from_strike_dip(90, 90, origin=(50, 50, 50), size=80)
create_plane_from_strike_dip(0, 90, origin=(50, 50, 50), size=80)
Synchronize()

Mesh.field.add("Distance", 1)
Mesh.field.add("Threshold", 2)
Mesh.field.setNumber(2, "InField", 1)
Mesh.field.setNumber(2, "SizeMin", 100)
Mesh.field.setNumber(2, "SizeMax", 100)
Mesh.field.setNumber(2, "DistMin", 2)
Mesh.field.setNumber(2, "DistMax", 10)
Mesh.field.setAsBackgroundMesh(2)

Synchronize()
Generate(3)

# Model.addPhysicalGroup( 3, VOLT, -1, "TEST_FRAME" )
# Model.addPhysicalGroup( 3, VOLS, -1, "SIDEBURDEN" )

# # Write to output file
# Option.setNumber( "Mesh.SaveAll", 1 )
gmsh.write( "example.vtk" )

Run()
Finalize()
