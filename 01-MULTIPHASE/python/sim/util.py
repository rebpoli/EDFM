from ssh import SSH
import re

sh_cmd = ( 
           r'source /etc/profile; '
           r'sbatch -v --chdir "$chdir"  --job-name="$jobName"'
           r' --ntasks=$solverNodes --cpus-per-task=$solverCores'
           r' --account=$account '
           r' --comment="$jobComment_$solverName_$solverVersion" $slurm'
           r' $CMG_HOME/RunSim.sh $solverName $solverVersion "$modelURI" '
           r' -wd "$wd" -wait -parasol $solverCores $solverExtras | tee $logFile'
       )

#
def parse_cmd( params ) :
    ret = sh_cmd
    for k, v in params.items():
        ret = ret.replace( "$"+k, str(v))
    return ret
#
def job_id( ssh, stdout ) :
    m = re.search(r"job\s+(\d+)",stdout)
    if m : return int(m.groups()[0]) 
    return -1

#
def ln2win(fn) :
    # Converts a linux path to a windows path
    ret = re.sub(r"/dfs_geral_ep/", r"\\\\dfs.petrobras.biz/cientifico/", fn)
    #ret = re.sub(r"/", r"\\", ret)
    return ret

#
def launch(params, ssh=None) :
    if not ssh : ssh = SSH( "reslogin" )

    cmd = parse_cmd(params)
    stdout, stderr, status = ssh.cmd(cmd)
    jid = job_id(stdout)
    if jid < 0 : jid = ""

    return jid, ssh
