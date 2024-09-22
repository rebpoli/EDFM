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
