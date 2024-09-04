#!/usr/bin/env -S python3 

# PROPERTIES TO GENERATE THE MESH

idir = {
    'b0'       : "0.65 1.2 3*0.1",     # Boundary beginning
    'block'    : "1.2 1.3 1.2 3*0.1 ", # Block
    'b1'       : "1.2 0.65",           # Buondary end
    'n_blocks' : 12
}
jdir = {
    'b0'       : "0.65 1.2 3*0.1",     # Boundary beginning
    'block'    : "1.2 1.3 1.2 3*0.1 ", # Block
    'b1'       : "1.2 0.65",           # Buondary end
    'n_blocks' : 12
}
kdir = {
    'b0'       : "10 0.1",                # Boundary beginning (TOP)
    'block'    : "1.2 1.3 1.2 3*0.1 ", # Block
    'b1'       : "1.2 1.3 1.2 2*0.1 10",  # Buondary end (BOTTOM)
    'n_blocks' : 12
}
idir['n_cells'] = idir['n_blocks'] * 6 + 7
jdir['n_cells'] = jdir['n_blocks'] * 6 + 7
kdir['n_cells'] = kdir['n_blocks'] * 6 + 8

#
#  PROCEDURE : GENERATE GRID GEOMETRY
#


print(f"GRID VARI {idir['n_cells']} {jdir['n_cells']} {kdir['n_cells']}")
print("KDIR DOWN")

print("\nDI IVAR")
print(idir["b0"])
for i in range(idir['n_blocks']) :
    print(idir['block'], end="")
    if not (i+1)%5 : print("")
print()
print(idir["b1"])

print("\nDJ JVAR")
print(jdir["b0"])
for j in range(jdir['n_blocks']) :
    print(jdir['block'], end="")
    if not (j+1)%5 : print("")
print()
print(jdir["b1"])

print("\nDK KVAR")
print(kdir["b0"])
for i in range(kdir['n_blocks']) :
    print(kdir['block'], end="")
    if not (i+1)%5 : print("")
print()
print(kdir["b1"])

print("\nDTOP")
print(f" {idir['n_cells'] * jdir['n_cells']}*5000")


#
#  PROCEDURE : GENERATE BLOCKGROUPS
#

# The frame is the top and the bottom layers (only in K)
print("\nBLOCKGROUP 'frame' IJK")
print(f"1:{idir['n_cells']} 1:{jdir['n_cells']} 1:{kdir['n_cells']} 1")
print(f"1:{idir['n_cells']} 1:{jdir['n_cells']} 2:{kdir['n_cells']-1} 0")

cap_cont = True   # Control the KR of the fracture cells between matrix block

# Identify the fractures (K)
print("\nBLOCKGROUP 'fractures_k' ALL")
for k in range(kdir['n_cells']) :
    kfrac = not k%6 or k==kdir['n_cells']-1
    for j in range(jdir['n_cells']) :
        jfrac = not (j-3)%6
        for i in range(idir['n_cells']) :
            ifrac = not (i-3)%6
            frac = 0
            if jfrac or ifrac or kfrac : frac=1 

            print(f"{frac} ", end="")

            # Newlines
#             if not (i+1)%50 : print()
        print()
    print()

# Identify the fractures (KREL)
print("\nBLOCKGROUP 'fractures_krel' ALL")
for k in range(kdir['n_cells']) :
    kfrac = not k%6 or k==kdir['n_cells']-1
    for j in range(jdir['n_cells']) :
        jfrac = not (j-3)%6
        for i in range(idir['n_cells']) :
            ifrac = not (i-3)%6
            frac = 0
            if jfrac or ifrac or kfrac : frac=1 

            # Deal with capillary continuity
            if cap_cont :
                if kfrac and ( (i-3)%6 and (j-3)%6 ) :
                    frac = 0

            print(f"{frac} ", end="")

            # Newlines
#             if not (i+1)%50 : print()
        print()
    print()


# Blockgroup to block PERMK from frame to matrix
print("\nBLOCKGROUP 'matrix_frame' ALL")

# first and last layers
kgrp = [ 0 , kdir['n_cells']-1 ]
for k in range(kdir['n_cells']) :
    is_k = ( k in kgrp )

    for j in range(jdir['n_cells']) :
        is_j = ( j%6 ) != 3
        for i in range(idir['n_cells']) :
            is_i = ( i%6 ) != 3
            w = 0
            if is_i and is_j and is_k  : w = 1

            print(f"{w} ", end="")
#             if not (i+1)%50 : print()
        print()
    print()


#
#  PROCEDURE : RESERVOIR SECTOR ARRAY
#
print("\nSECTORARRAY 'RES' IJK")
print(f"1:{idir['n_cells']} 1:{jdir['n_cells']} 2:{kdir['n_cells']-1} 1")
