import sys
from time import time
from io import StringIO

class ScopeWatch :
    #
    #
    def __init__(self, ctx, hold_stdout=True) :
        self.ctx = ctx
        self.start = time()
        print('# {0:<50}'.format(ctx), 
             end='', 
             flush=True )

        # Capture stdout
        self.hold_stdout = hold_stdout
        if hold_stdout :
            self.old_stdout = sys.stdout
            sys.stdout = self.stdout = StringIO()


    #
    #
    def __del__(self) :
        if self.hold_stdout : sys.stdout = self.old_stdout

        dt = time() - self.start
        print(f"[Done] - {dt:.2f}s")

        if self.hold_stdout : print(self.stdout.getvalue(), end='')
    #
    #
    def __enter__(self) : pass
    def __exit__(self, exc_type, exc_value, exc_traceback): pass


#
# Usage
#
# from time import sleep
# with ScopeWatch("WRAPPER") :
#     sleep(2)
#
## Output:
## Running WRAPPER ...                               [Done] - 2.00 s

