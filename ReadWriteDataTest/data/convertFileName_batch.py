
from __future__ import with_statement
import os
from convertFileName import gpcLogFile
from zipfile import ZipFile, ZIP_DEFLATED 
 
if __name__ == '__main__':
    maxBytes=1000000 # may need adaptation to the used logfile size.
    if os.path.getsize('GPC.log') < maxBytes*9./10:
        # Handle the GPC.log files
        fl = ['GPC.log.%s'%(i,) for i in xrange(1,21)]
        fl.reverse()

        newFns = []
        for fn in fl:
            newfn = gpcLogFile(fn)
            if newfn:
                newFns.append(newfn)
        zf = ZipFile('GPC_log_Archive.zip','a',ZIP_DEFLATED)
        for fni in newFns:
            zf.write(fni)
        zf.close()
    else:
        print "wait until next Rotation of the log files"


