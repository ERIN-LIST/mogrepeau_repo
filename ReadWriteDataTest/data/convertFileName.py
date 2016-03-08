
from __future__ import with_statement
import os, re
import datetime as dt
from dateutil.parser import parse

def fTail(fname,nbrL=500):
    with open(fname, "r") as f:
        f.seek(0, 2)           # Seek @ EOF
        fsize = f.tell()        # Get Size
        lines = []
        b = 0
        fstart = False
        while len(lines) < nbrL and fstart == False:
            b += 1
            f.seek(max(fsize-b*1024, 0), 0) # Set pos @ last n chars
            if f.tell() == 0:
                fstart = True
            lines = f.readlines()       # Read to end
    lines = lines[-nbrL:]
    return lines, fstart
    
def gpcLogFile(fn):
    if os.path.exists(fn):
        e = None
        nbrL = 500
        stop = False
        while not e and not stop:
            lines, stop = fTail(fn,nbrL)
            
            # searching for the re
            lines.reverse() #revers the lines as we search from back.
            for l in lines:
                if l.startswith("#TrigOK;"):
                    break
            e = re.match("(?P<Evt>#\w+).*\((?P<dt>[0-9:\-\. ]+)\)",l.strip())
            if not e:
                nbrL *= 2
        if e:
            f_dt = parse( e.group('dt') )
            fnpattern = 'GPCLog_%s.log'
        else:
            print "No #TrigOK found in file: %s; Use file modification time" % (fn,)
            f_dt = dt.datetime.fromtimestamp(os.path.getmtime(fn))
            fnpattern = 'GPCLog_%s_noTrigOK.log'
        newfn = fnpattern % f_dt.strftime("%Y%m%dT%H%M")
        os.rename(fn, newfn)
        return newfn
    else:
        print "filename '%s' does not exist" % (fn,)

def gpcAlgoLogFile(fn):
    if os.path.exists(fn):
        f_dt = dt.datetime.fromtimestamp(os.path.getmtime(fn))
        os.rename(fn, 
                  'GPCAlgoLog_%s.log' % f_dt.strftime("%Y%m%dT%H%M"))
    else:
        print "filename '%s' does not exist" % (fn,)

if __name__ == '__main__':
    # Handle the GPC.log files
    fl = ['GPC.log.%s'%(i,) for i in xrange(1,21)]
    fl.insert(0, 'GPC.log')
    fl.reverse()

    for fn in fl:
        gpcLogFile(fn)

    # Handle the GPCAlgo.log files
    fl = ['GPCAlgo.log.%s'%(i,) for i in xrange(1,21)]
    fl.insert(0, 'GPCAlgo.log')
    fl.reverse()
    for fn in fl:
        gpcAlgoLogFile(fn)

