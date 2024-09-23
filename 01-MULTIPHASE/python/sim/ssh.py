#!/usr/bin/env -S python3 

import os,time

class SSH :
    def __init__(self, server, quiet=1, debug=0) :
        self.ENDTAG = "THIS IS AN END TAG. THIS IS AN END TAG. THIS IS AN END TAG."
        self.SERVER = server

        # Controls verbosity
        self.quiet = quiet
        self.debug = debug

        # Lets go!
        self.connect()

    def exit( self ) :
        self.PROC.kill()
    #
    #
    #
    def connect( self ) :
        from subprocess import Popen, PIPE
        ssh_cmd = [ "ssh", "-T", self.SERVER ]
        proc = Popen(ssh_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE,  universal_newlines=True)
        os.set_blocking(proc.stdout.fileno(), False)
        os.set_blocking(proc.stderr.fileno(), False)
        self.PROC = proc

        import time
        s1, s2, status = self.flush()
        if status == "endtag" :
            print(f"#SSH# Connected to {self.SERVER}.")
            return 0
        else :
            print(f"#SSH# FAILED to connect to {self.SERVER}.")

    #
    #
    #
    def flush( self, timeout=5, end_tag = 1 ) :
        proc = self.PROC
        endtag = self.ENDTAG
        quiet = self.quiet
        deb = self.debug

        # Writes in the error pipe to avoid missing errors from the command.
        if ( end_tag ) :
            proc.stdin.write(f"echo {self.ENDTAG} 1>&2\n")
            proc.stdin.flush()

        self.stdout = ""
        self.stderr = ""

        #
        # PROCEDURE : Wait for the proces to start outputting
        #
        i=0
        while True :
            stderr_line = proc.stderr.readline()
            stdout_line = proc.stdout.readline()
            # Keep going if we have seen somethin in STDOUT or STDERR
            if stderr_line : break
            if stdout_line : break

            i+=1 
            if i > 100 : 
                print("#SSH# E: Process did not output as expected after 10 seconds.")
                return "", ""
            time.sleep(0.1)

        status = ""

        #
        # PROCEDURE : Collect all the output - break with ENDTAG or 1s idle
        #
        i=0
        while True :   # Still working
            # Collect stdout
            if stdout_line :
                if not quiet : print(stdout_line.strip())

                self.stdout += stdout_line
                i=0
                stdout_line = proc.stdout.readline()
                continue  ## STDOUT has the higher priority. Collect all those before checking for errors

            # Collect stderr
            if stderr_line :
                # The command is over and we have seen the endtag.
                if stderr_line.strip() == endtag :
                    if self.debug : print("#SSH#debug# Found end tag.")
                    status = "endtag"
                    break 
                if not quiet : print(stderr_line.strip())

                self.stderr += stderr_line
                stderr_line = proc.stderr.readline()
                i=0
                continue

            # Empty. Give one second
            i+=1 
            if i > timeout/0.1 : 
                print(f"#SSH# {timeout} second without output - ssh command TIMEOUT.")
                status = "timeout"
                break

            time.sleep(0.1)
            stdout_line = proc.stdout.readline()
            stderr_line = proc.stderr.readline()


        # DONE.
        return self.stdout, self.stderr, status

    #
    #
    def cmd( self, cmd, timeout=5 ) :
        proc = self.PROC
        quiet = self.quiet
        deb = self.debug
        #
        # PROCEDURE : Run command in remote host
        #
        if not quiet : 
            print(f"#SSH# Running command: $ \"{cmd}\" ...")

        proc.stdin.write(f"{cmd}\n")
        proc.stdin.flush()
        
        return self.flush( timeout )

    #
    # Return the number of processes running currently
    def n_jobs_running( deb = 0 ) :
        # Flush outputs
        n_tries = 0
        while n_tries < 10 :
            try :
                o,e = cmd( "squeue -u bfq9 -h -t pending,running -r | wc -l", deb=deb )
                print(f"#SSH# Currently running jobs for BFQ9: {int(o)}.")
                n = int(o)
                break
            except :
                print(f"#SSH# Failed to fetch the number of jobs running (n_tries={n_tries}). STDOUT='{o}'")
                time.sleep(0.5)
                n_tries += 1
        
        if n_tries >= 10 :
            print(f"#SSH# Failed to get the number of jobs running. Returning default value 1000 to keep things going...")
            n=1000

        return n


    ## EXAMPLE OF USAGE

    # # MAIN
    # p = chimas_ssh.connect()
    # msg,err = chimas_ssh.cmd( p, "ls", 1 )
    # print( msg )

    # msg,err = ssh_cmd( p, "cd temp ; ls",1 )
    # print( msg )
    # print( err )

    # msg,err = ssh_cmd( p, "echo AAAA 1>&2" )
    # print( err )

