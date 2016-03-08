from dateutil.parser import parse
from datetime import timedelta
import re
import numpy as np
import pylab
import argparse


class gpcEvent(object):
    def __init__(self,name,dt):
        self.name = name
        self.dt = dt
class subEvent(gpcEvent):
    def __init__(self,name,dt,ref):
        super(subEvent, self).__init__(name,dt)
        self.delta = dt-ref
    def repDelta(self):
        return "%s (%s)" % (self.name, self.delta)
class cycle(object):
    def __init__(self,tOkdT):
        self.tOK = gpcEvent("TrigOK", tOkdT)
        self.refDT = tOkdT
        self.theoDT = self.getBaseDT(tOkdT)
        self.delta = self.refDT - self.theoDT
        self.evtList = []
        self.evtDict = {}
    def addEvent(self,evt,dt):
        if evt in self.evtDict:
            # second occurency of an event
            NewEvt = "%s:%s" % (evt,0)
            self.evtDict[NewEvt] = self.evtDict.pop(evt)
            self.evtList[self.evtDict[NewEvt]].name = NewEvt
        if [ki for ki in self.evtDict.iterkeys() if ki.startswith(evt)]:
            i = max([int(ki.split(":")[1]) for ki in self.evtDict.iterkeys() if ki.startswith(evt)])
            evt = "%s:%s" % (evt,i+1)
        self.evtList.append(subEvent(evt, dt, self.refDT))
            
        self.evtDict[evt] = len(self.evtList)-1
    def printDeltas(self):
        s = "TOK-%s: " % self.refDT
        evts = []
        evts = ', '.join([ei.repDelta() for ei in self.evtList])
        return s + evts
    def getBaseDT(self,ti,up_to_nearest=15):
        """Rounds to the nearest specified minute frequency"""
        ti += timedelta(minutes=up_to_nearest)/2
        ti -= timedelta(minutes=ti.minute % up_to_nearest,
                        seconds=ti.second,
                        microseconds=ti.microsecond)
        return ti

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process gpc-logFile for timing analysis.')
    parser.add_argument('logfile', nargs='?', type=str, default="GPC.log", 
                        help='the log filename')
    args = parser.parse_args()

    fh = open(args.logfile)

    C = []
    for l in fh:
        e = re.match("(?P<Evt>#\w+).*\((?P<dt>[0-9:\-\. ]+)\)",l.strip())
        if e:
            evt = e.group('Evt')
            dt = parse( e.group('dt') )
            if evt == '#TrigOK':
                refdt = dt
                C.append(cycle(dt))
            elif evt in ['#VarsOK','#MPCActive','#MPCDone','#OPCWrite']:
                C[-1].addEvent(evt,dt)
            else:
                print "Unhandled Event:\n  -> %s" % (l.strip(),)

    fh.close()
    
    # for ci in C:
        # print "tOK (%s), Nbr-subEvents=%s" % (ci.refDT, len(ci.evtList))

    TOKGitter = np.array([ci.delta.total_seconds() for ci in C])
    VOK = np.array([ci.evtList[ci.evtDict["#VarsOK"]].delta.total_seconds() for ci in C])
    MPCA = np.array([ci.evtList[ci.evtDict["#MPCActive"]].delta.total_seconds() for ci in C])
    MPCD = np.array([ci.evtList[ci.evtDict["#MPCDone"]].delta.total_seconds() for ci in C])
    OW0 = np.array([ci.evtList[ci.evtDict["#OPCWrite:0"]].delta.total_seconds() for ci in C])
    OW1 = np.array([ci.evtList[ci.evtDict["#OPCWrite:1"]].delta.total_seconds() for ci in C])
    d = np.array([TOKGitter, VOK, MPCA-VOK, MPCD-MPCA, OW0-MPCD, OW1-OW0]).T
    
    for i in xrange(6):
        print "%s: min=%s; max=%s" % (i,d[:,i].min(), d[:,i].max())
    
    bh = pylab.boxplot(d)
    pylab.xticks([1,2,3,4,5,6],['TRef->TOK','TOK->VOK','VOK->MPCA','MPCA->MPCD','MPCD->OW1','OW1->OW2'])
    pylab.xlabel("Different GPC process steps")
    pylab.title("GPC process timing analysis (%s - %s)" % tuple([C[i].refDT.strftime("%Y-%m-%d") for i in [0,-1]]))
    pylab.show()
