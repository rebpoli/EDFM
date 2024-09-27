** 2024-05-21, 12:52:04, BFQ9
RESULTS SIMULATOR IMEX 2024.10.557b40a19d

INCLUDE '../../inc/io.inc'
INCLUDE '../../inc/mesh-2P2K4.inc'

DIFRAC CON $DIFRAC 
DJFRAC CON $DIFRAC
DKFRAC CON $DIFRAC 

PERMI MATRIX CON $PERMI_MATRIX
PERMJ MATRIX EQUALSI
PERMK MATRIX EQUALSI
MOD
BG 'frame' = 0

PERMI FRACTURE CON $PERMI_FRACTURE
PERMJ FRACTURE EQUALSI
PERMK FRACTURE EQUALSI

NULL CON 1
POR MATRIX CON 0.13903 ** porosity of the matrix has to be adjusted: \phi = 0.15 * 3.9^3 / 4^3 = 0.9268
POR FRACTURE CON 0.0025

VOLMOD FRACTURE CON 1
MOD
BG 'frame' * 1e6

*CPOR  MATRIX   2e-7  ** 1/KPa
*CPOR  FRACTURE   2e-7  ** 1/KPa

*PRPOR    40E3  ** KPa

**
**
**
INCLUDE '../../inc/model.inc'

**
**
**
ROCKFLUID
RTYPE MATRIX CON 1
RTYPE FRACTURE CON 2

*RPT 1
INCLUDE '../../inc/swt-ow.inc'

** *RPT 2
** *SWT
**     ** SW   KRW   KROW   
**      0     0.00   1.00
**      1.00  1.00   0.00                         

*RPT 2
INCLUDE '../../inc/swt-ow-frac.inc'

**
**
**
INITIAL
VERTICAL *BLOCK_CENTER *WATER_OIL

NREGIONS 2                 
ITYPE CON 1               
MOD BG 'frame' = 2

PB       *CON 20E3  ** KPa
REFDEPTH   5000.0 5000.0
REFPRES      40E3 40E3
DATUMDEPTH 5000.0
DGOC       1000.0 1000.0  
DWOC       6000.0 4000.0    ** Fractures saturated with water

NUMERICAL
INCLUDE '../../inc/numerical.inc'

RUN
DATE	2000	1	1.0000000	 ** 15 min interval

**WELL  'I1'
**INJECTOR MOBWEIGHT 'I1'
**INCOMP WATER
**OPERATE  MAX  BHP  45e3
**OPERATE  MAX  STW  5000
****GEOMETRY  K  0.0762  0.37  1.0  0.0  
**PERF      GEOA  'I1'
**1 1 1:179 1.0 OPEN


**WELL  'P1'
**PRODUCER 'P1'
**OPERATE  MIN  BHP 40e3
**OPERATE  MAX  STL 5000
****GEOMETRY  K  0.0762  0.37  1.0  0.0  
**PERF      GEOA  'P1'
**1 179 1:179 1.0 OPEN

**SHUTIN '*'

WSRF GRID TIME
WSRF SECTOR TIME

INCLUDE '../../inc/sch.inc'
STOP
