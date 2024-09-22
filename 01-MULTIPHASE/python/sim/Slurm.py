import re, os

class Slurm :

    #
    #
    #
    def __init__(self, ssh) :
        self.ssh = ssh

    #
    # 
    #
    def elapsed_s( self, myjobs = "" ) :
        ssh = self.ssh
        if not isinstance(myjobs, list):
            myjobs = [myjobs] 
        myjobs = [ str(i) for i in myjobs if i ] # Lets work with strings
        if not myjobs : return

        ret = []

        for jid in myjobs :
            cc = f"sacct -a -j {jid} --format=user%10,jobname%10,node%10,start%10,end%10,elapsed%10,MaxRS"
            stdout, stderr, status = ssh.cmd(cc)
            for l in stdout.splitlines() :
                m = re.search( r"(\d\d):(\d\d):(\d\d)", l ) 
                if m :
                    h_, min_, sec_ = m.groups()
                    sec_ = int(sec_)
                    sec_ += int(min_)*60 + int(h_)*60*60
                    ret.append(sec_)
                    break

        return ret

    #
    #
    #
    def running_jobs( self, myjobs = "" ) :
        ssh = self.ssh
        if not isinstance(myjobs, list):
            myjobs = [myjobs] 
        myjobs = [ str(i) for i in myjobs if i ] # Lets work with strings

        user = os.getlogin()

        jobs = []
        sq = (f"squeue -h -u {user} "+r' --format "%A;%M;%N;%P;%T;%V;%o;%a;%j"  --sort=-S')
        ssh.cmd( sq )
        for l in ssh.stdout.splitlines() :
            ll = l.split(';')
            jid = ll[0]
            if len(myjobs) :
                if not jid in myjobs : continue
            jobs.append( jid )

        return jobs
        

    #
    #
    #
    def squeue( self, myjobs = "" ) :
        ssh = self.ssh
        if not isinstance(myjobs, list):
            myjobs = [myjobs] 
        myjobs = [ str(i) for i in myjobs if i ] # Lets work with strings

        import os
        user = os.getlogin()

        jobs = []
        sq = (f"squeue -h -u {user} "+r' --format "%A;%M;%N;%P;%T;%V;%o;%a;%j"  --sort=-S')
        ssh.cmd( sq )
        for l in ssh.stdout.splitlines() :
            ll = l.split(';')
            if len(myjobs) :
                jid = ll[0]
                if not jid in myjobs : continue

            jobs.append( { 'id':           ll[0],
                            'age':         ll[1],
                            'nodes' :      ll[2],
                            'partition':   ll[3],
                            'state':       ll[4],
                            'startTime':   ll[5],
                            'command':     ll[6],
                            'account':     ll[7],
                            'name':        ll[8]
                            })
        return jobs
