""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

from apscheduler.scheduler import Scheduler
from time import sleep
from datetime import *
import logging
import logging.handlers
from random import randint

import OpenOPC


opcserver = 'OPCManager.DA.XML-DA.Server.DA'
RTags = [ "VictoryClient.S0_zLife",
#          "VictoryClient.S0_tUpdate",
#          "VictoryClient.S0_tUpdateTrig",
#          "VictoryClient.S4_Autonom_VSollOben",
#          "VictoryClient.S4_Autonom_VHystereseOben",
          "VictoryClient.S4_zLife",
#          "VictoryClient.S4_Life",
           ]
WTags = [ "VictoryClient.S4_QSoll",
          "VictoryClient.S99_tUpdateTrig" ]
LCTag = [ "VictoryClient.S99_zLife", ]

#opcserver = 'Graybox.Simulator.1'
#RTags = [ "numeric.saw.int32", ]
#LCTag = [ "options.sawfreq", ]


def jobReadOPC(Tags,opcserver='OPCManager.DA.XML-DA.Server.DA',client_name=None):
    opc = OpenOPC.client(client_name=client_name)
    opc.connect(opcserver)
    sleep(0.7)
    opcIn = []
    for i in xrange(2):
        try:
            opcIn = opc.read(Tags,timeout=1000)
            break
        except OpenOPC.TimeoutError:
            print "%s: TimeoutError" % (client_name,)
            opc.close()
            sleep(1)
            opc.connect(opcserver)
            sleep(0.7)
    opc.close()
    return opcIn

def jobWriteOPC(TVpairs,opcserver='OPCManager.DA.XML-DA.Server.DA',client_name=None):
    opc = OpenOPC.client(client_name=client_name)
    opc.connect(opcserver)
    sleep(0.7)
    status = opc.write(TVpairs)
    sleep(0.7)
    opc.close()
    return status

def jobLifeC():
    client_name='LifeC.Client'
    res = jobReadOPC(LCTag, opcserver=opcserver, client_name=client_name)
    if len(res) != 1:
        print "jobReadOPC() results in an empty set"
        return
    (name, value, quality, time) = res[0]
    if opcserver == 'OPCManager.DA.XML-DA.Server.DA':
        inc = 1
    elif opcserver == 'Graybox.Simulator.1':
        inc = 0.01
    TVP = zip(LCTag,[value+inc,])
    print "To be written: %s" % [TVP,]
    status = jobWriteOPC(TVP,client_name=client_name)
    if any([si[1] != 'Success' for si in status]):
        print "Status: %s" % status

def jobAlgoR():
    client_name='AlgoRead.Client'
    Tags = RTags
    outStr = []
    opcVars = jobReadOPC(Tags, opcserver=opcserver, client_name=client_name)
    for oi in opcVars:
        outStr.append("%s: %s" % (oi[0], oi[1],))
    print "\n".join(outStr)

def jobAlgoW():
    client_name='AlgoWrite.Client'
    if opcserver == 'OPCManager.DA.XML-DA.Server.DA':
        TVP = zip(WTags,(randint(0,20)*100,1)) # QSoll is in l/s but with 2NK
    elif opcserver == 'Graybox.Simulator.1':
        return
    print "To be written: %s" % [TVP,]
    status = jobWriteOPC(TVP,client_name=client_name)
    if any([si[1] != 'Success' for si in status]):
        print "Status: %s" % status
    sleep(10)
    TVP = zip(WTags[-1:],(0,))
    print "To be written: %s" % [TVP,]
    status = jobWriteOPC(TVP,client_name=client_name)
    if any([si[1] != 'Success' for si in status]):
        print "Status: %s" % status

if __name__ == '__main__':
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logging.getLogger("apscheduler").addHandler(ch)

    sched = Scheduler()
    sched.start()

    LifeCJ=True
    AlgoRJ=True
    AlgoWJ=True

    if LifeCJ:
        LifeC = {'job':None, 'schedParam': {'name':"LifeCounter-Job",'seconds':15},
                }
        LifeC['job'] = sched.add_interval_job( jobLifeC,
                                               start_date = datetime.now() + timedelta(seconds=1),
                                               **LifeC['schedParam'] )
    if AlgoRJ:
        AlgoR = {'job':None, 'schedParam': {'name':"AlgoRead-Job",'seconds':45},
                }
        AlgoR['job'] = sched.add_interval_job( jobAlgoR,
                                               start_date = datetime.now() + timedelta(seconds=2),
                                               **AlgoR['schedParam'] )

    if AlgoWJ:
        AlgoW = {'job':None, 'schedParam': {'name':"AlgoWrite-Job",'seconds':45},
                }
        AlgoW['job'] = sched.add_interval_job( jobAlgoW,
                                               start_date = datetime.now() + timedelta(seconds=3.5),
                                               **AlgoW['schedParam'] )

    i = 0
    while i <= 50:
        print "%s: Running" % i
        sleep(10)
        i += 1
    sched.shutdown()

