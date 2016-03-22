""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

from datetime import *
from dateutil import tz
import logging

try:
    from ReadNeededDataTest.ReadData_useOPC import AlgData_OPC
except:
    AlgData_OPC = None

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

h = NullHandler()
logging.getLogger("TriggerHandling").addHandler(h)


class ReadTrigger(object):
    TrigSizePct = 10
    gitter = 2

    def __init__(self, S0_tUpdate = 900, opcserver = 'OPC.SimaticHMI.CoRtHmiRTm.1', test = False):
        self._testmode = test
        self.logger = logging.getLogger("TriggerHandling.ReadTrigger")
        self.S0_tUpdate = S0_tUpdate
        self.lastT = None
        self.DT = max(1, self.S0_tUpdate * self.TrigSizePct/(2*100)) # should be multiple of second >= 1[sec]
        self.lastDT = self.DT
        self.job = None
        if AlgData_OPC and not self._testmode:
            Variables = {'OPC_Group':'RTrig'}
            Variables.update({'RTrig':[{'OPC':"DB102 GPC_EPA_DateTime",'GPC':"S98_DateTime"},]})
            self.TrigOPC = AlgData_OPC(variables=Variables)
            self.TrigOPC.logger = self.logger
        else:
            self.TrigOPC = None
            self.gitter = 0
    def setLogger(self,logger):
        self.logger = logger
        if self.TrigOPC:
            self.TrigOPC.logger = logger
    def isSync(self):
        if self.DT < 2:
            return True
        return False
    def isJobAlife(self):
        #implement a method to return the life state of the scheduled job.
        if self.job == None or self.job.next_run_time == None:
            return False
        else:
            return True
    def updateTrigParam(self,S0_tUpdate=None):
        if S0_tUpdate:
            self.S0_tUpdate = S0_tUpdate
        if not self._testmode:
            self.lastDT = self.DT
            self.DT = max(1,self.DT/2)
    def getMaxRuns(self):
        if self.lastT:
            return 2*self.lastDT/self.DT + 2*self.gitter/self.DT + 1
        else:
            return self.S0_tUpdate / self.DT + 1
    def getNextRT(self):
        if self.lastT:
            NextT = self.lastT + timedelta(seconds=self.S0_tUpdate-2*self.lastDT-self.gitter)
        else:
            NextT = datetime.now() + timedelta(seconds=1)
        return NextT
    def getRTrigJob(self):
        if self.TrigOPC:
            return self._getRTrigOPC()
        else:
            return self._getRTrigTest()
    def _getRTrigTest(self):
        self.jobRuns += 1
        self.logger.debug( "ReadTriggerJob Executed: %s at %s" % (self.jobRuns, datetime.now()) )
        if self.jobRuns < 1:
            return False
        else:
            self.lastT = datetime.now()
            return True
    def _getRTrigOPC(self):
        self.TrigOPC.readOPC()
        SysDateTimeObj = self.TrigOPC.opcVarsDict["S98_DateTime"]
        if SysDateTimeObj.quality == "Good":
            self.CTimeperiod
            SysDateTime = SysDateTimeObj.value
            S0_tUpdateTrigOld = S0TrigOPC.getCached("Latest")[1]
            # Only the positive slope is of importance.
            try:
                slop = S0_tUpdateTrig - S0_tUpdateTrigOld
            except:
                slop = 0

            if slop > 0:
                self.lastT = S0TrigOPC.dtLoc
                return True
            else:
                return False
        else:
            return False


class WriteTrigger(object):
    TrigSizePct = ReadTrigger.TrigSizePct
    maxRuns = 3
    def __init__(self, S0_tUpdate = 900, test = False):
        self.logger = logging.getLogger("TriggerHandling.WriteTrigger")
        self.S0_tUpdate = S0_tUpdate
        self.DT = max(1, self.S0_tUpdate * self.TrigSizePct/100) # should be multiple of second >= 1[sec]
        self.job = None
        self.run = 0
        self._state = ['Init',]
        self.TrigOPC = AlgData_OPC(variables={'WTrig':["S99_tUpdateTrig",]})
        self.TrigOPC.logger = self.logger
    def setLogger(self,logger):
        self.logger = logger
        self.TrigOPC.logger = logger
    def isJobAlife(self):
        #return the life state of the scheduled job.
        if self.job == None or self.job.next_run_time == None:
            return False
        else:
            return True
    def setTrigOPC(self):
        self.TrigOPC.readOPC()
        S99TrigOPC = self.TrigOPC.opcVarsDict["S99_tUpdateTrig"]
        if S99TrigOPC.value == 0 and self.state == 'Init':
            try:
                WStatus = self.TrigOPC.writeOPC((S99TrigOPC.name,1), toOPC=True)[0]
                if WStatus[1] != 'Success':
                    if self.run > self.maxRuns:
                        self.state = "SetError"
                    self.logger.warning( "%s OPC-Write ends with state %s" % ("GPC WriteTrigger:", WStatus) )
                else:
                    self.state = "Set"
                    self.run = 0
                    self.logger.info( "%s %s set (%s)" % \
                                      ("GPC WriteTrigger:", S99TrigOPC.name, (S99TrigOPC.value,S99TrigOPC.time)) )
            except StandardError as e:
                self.state = "Error"
                self.logger.error("StandardError: %s",e)
        else:
            self.logger.error("GPC WriteTrigger: %s was not reset correctly (state: %s)." % (S99TrigOPC.name,self._state))
        self.run +=1
    def resetTrigOPC(self):
        self.TrigOPC.readOPC()
        S99TrigOPC = self.TrigOPC.opcVarsDict["S99_tUpdateTrig"]
        if S99TrigOPC.value == 1 and self.state == 'Set':
            try:
                WStatus = self.TrigOPC.writeOPC((S99TrigOPC.name,0), toOPC=True)[0]
                if WStatus[1] != 'Success':
                    if self.run > self.maxRuns:
                        self.state = "ResetError"
                    self.logger.warning( "%s OPC-Write ends with state %s" % ("GPC WriteTrigger:", WStatus) )
                else:
                    self.state = "Reset"
                    self.run = 0
                    self.logger.info( "%s %s reseted (%s)" % \
                                      ("GPC WriteTrigger:", S99TrigOPC.name, (S99TrigOPC.value,S99TrigOPC.time)) )
            except StandardError as e:
                self.logger.error("StandardError: %s",e)
        else:
            self.logger.error("GPC WriteTrigger: %s was not set correctly." % (S99TrigOPC.name,))
        self.run +=1
    def isInProcess(self):
        if self.state in ['Init','Set']:
            return True
        return False
    @property
    def state(self):
        return self._state[0]
    @state.setter
    def state(self,value):
        return self._state.insert(0,value)
    def process(self):
        cSatate = self.state
        if cSatate == 'Init':
            self.setTrigOPC()
        elif cSatate == 'Set':
            self.resetTrigOPC()
        elif cSatate == 'Reset':
            pass
        else:
            self.logger.error("Write S99_tUpdateTrig is %s state!\n -> State history: %s", self._state[0], self._state)
