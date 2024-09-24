import re

#
def parse_cmd( cmd_sh, params ) :
    ret = cmd_sh
    for k, v in params.items():
        ret = ret.replace( "$"+k, str(v))
    return ret
#
def job_id( stdout ) :
    m = re.search(r"job\s+(\d+)", stdout)
    if m : return int(m.groups()[0]) 
    return -1

#
def ln2win(fn) :
    # Converts a linux path to a windows path
    ret = re.sub(r"/dfs_geral_ep/", r"\\\\dfs.petrobras.biz/cientifico/", fn)
    #ret = re.sub(r"/", r"\\", ret)
    return ret

#
# Parses a template into a final dat to run
def parse_dat( pars ) :
    round_id = pars["$ROUND_ID"]
    run_id = pars["$RUN_ID"]

    chdir = pars["$CHDIR"]
    tpl = pars["$TEMPLATE"]

    # PROCEDURE : Read template
    tplfh = open(tpl,"r")
    lines = tplfh.readlines()
    tplfh.close()

    # PROCEDURE : Replace
    ret = ""
    for line in lines :
        # Replace the template tags
        # Fix the includes
        line = re.sub(r"^(\s*\*?include\s*('|\"))", r"\1../", line, flags=re.IGNORECASE) 
        ret += line

    for k, v in pars.items():
        ret = ret.replace( k, str(v) )

    # PROCEDURE : Write .dat
    ofn = f"{chdir}/run_{run_id}.dat"
    ofh = open(ofn, "w")
    ofh.write(ret)
    ofh.close()
    
    return ofn

#
# Setup round dir
def setup_round_dir( template_fn, round_id ) :
    from .shared import DEBUG

    from os.path import basename, splitext, dirname
    template_bn, _ = splitext( basename( template_fn ) )
    DEBUG and print(f"# D: Template basename: {template_bn}")

    _chdir = dirname(template_fn)
    chdir    = f"{_chdir}/__{template_bn}/round_{round_id}"

    DEBUG and print(f"# D: chdir: {chdir}.")

    # Create dir
    from os import makedirs
    try: makedirs(chdir)
    except Exception as e:
        DEBUG and print(f"# D: makedirs: {e}.")
        pass

    return chdir

#
# 
def init() :
    import argparse, os
    import sim.shared
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--template', required=True, help="The file with the template for the history matching (*.tpl file).")
    parser.add_argument('-s', '--sr3_ref', required=True, help="The sr3 file of the reference model, typically a LGR fractured model.")
    parser.add_argument('-v', dest='verbose', action='store_true')
    parser.add_argument('-d', dest='debug', action='store_true')
    args = parser.parse_args()
    DEBUG = sim.shared.DEBUG = args.debug
    VERBOSE = sim.shared.VERBOSE = args.verbose

    # Validate inputs
    template_fn = args.template
    if not os.path.exists(template_fn) : 
        print(f"# F: Template file {template_fn} does not exist.")
        exit(-1)
    template_fn = os.path.abspath(template_fn)
    DEBUG and print(f"# D: Using template file: {template_fn}")

    sr3_ref_fn = args.sr3_ref
    if not os.path.exists(sr3_ref_fn) : 
        print(f"# F: Reference SR3 file {sr3_ref_fn} does not exist.")
        exit(-1)
    sr3_ref_fn = os.path.abspath(sr3_ref_fn)
    DEBUG and print(f"# D: Using SR3 reference file: {sr3_ref_fn}")

    return template_fn, sr3_ref_fn
