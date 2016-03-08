'''
Created on 28 juil. 2011

@author: schutz
'''

from apscheduler.scheduler import Scheduler
from datetime import datetime, timedelta
from time import sleep
from JobManagement_GSc import jobManagement

class My_jobManagement(jobManagement):
    
#    def __init__(self):
#        jobManagement.__init__(self)

    def getPending(self,fsm):
        """
        activity method to get the pending jobs from input or persistent storage.
        """
        inputstr = '1:s,2:n,3:n'
        for stri in inputstr.split(','):
            stri = stri.split(':')
            if len(stri) == 1:
                stri.append('s') #Default job-type is "simple"
            if len(stri) == 2:
                jid,jtype = stri
            else:
                self.Error()
            if jid.isalnum() and jtype in ['s','n']:
                fsm.memory['Buffer'].append([int(jid),self.jobDict[jtype]])
            else:
                self.Error()
        fsm.memory['Buffer'].append('End')
    

def jobM():
    print "JobManagement started: %s" % (datetime.now())
    jM = My_jobManagement()
    jmFSM = jM.fsm

    while jmFSM.current_state != 'END':
        jmFSM.process(None)


if __name__ == '__main__':
    # Instantiate scheduler
    sched = Scheduler()
    d = datetime.now() + timedelta( seconds = 2 )
    job = sched.add_interval_job(jobM,
                                 start_date=d, 
                                 seconds=15,
                                 max_runs=3,
                                 #args=[sched,'Test IntervalJob']
                                 )

    # Start the scheduler
    sched.start()

    while sched.get_jobs() != []:
        sleep(2)
    else:
        sched.shutdown()
