
mw16: .force
	./history_match_2p2k4.py -t 2P2K16-MW.tpl -s ../dat-LGR-long2/01-LGR-MW.sr3 2>&1 | tee MW16.stdout

mw: .force
	./history_match_2p2k4.py -t 2P2K4-MW.tpl -s ../dat-LGR/01-LGR-MW.sr3 2>&1 | tee MW.stdout
ow: .force
	./history_match_2p2k4.py -t 2P2K4-OW.tpl -s ../dat-LGR/01-LGR-OW.sr3 2>&1 | tee OW.stdout
ww: .force
	./history_match_2p2k4.py -t 2P2K4-WW.tpl -s ../dat-LGR/01-LGR-WW.sr3 2>&1 | tee WW.stdout

mw_1p: .force
	./history_match_1p.py -t 1P4-MW.tpl -s ../dat-LGR/01-LGR-MW.sr3 2>&1 | tee MW-1P.stdout

mw-refv: .force
	./history_match_2p2k4.py -t 2P2K4refv-MW.tpl -s ../dat-LGR/01-LGR-MW.sr3 2>&1 | tee MWrefv.stdout

all: mw ow ww mw16 mw_1p


clean: 
	rm -rf __2P2K* 
.force:
