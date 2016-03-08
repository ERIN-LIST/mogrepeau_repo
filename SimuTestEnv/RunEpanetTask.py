'''
Created on 7 aug. 2015

@author: schutz
'''

import logging
from time import sleep, time
from datetime import datetime, timedelta
from collections import deque
import sys
from os import path
from glob import glob, re

if __name__ == '__main__':
    sys.path[0:0] = ['..',]
    import ReadWriteDataTest.config as GPCConfig

from JobScheduler.JobManagement_GSc import jobManagement, jobNormal
from ReadNeededDataTest.ReadData_useOPC import AlgData_OPC
from Control.GPCVariablesConfig import EPA_Vars
from epanettools import epanet2 as et
import pandas as pds


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

h = NullHandler()
logging.getLogger("runepanettask").addHandler(h)

class EPAContainer(object):
    def __init__(self,cxt,SysVars=None):
        self.AreaCounterMap = {'C_Mittal':'S01_C02',
                               'C_Redange':'S02_C02',
                               'C_Esch':'S03_C02',}
        self.TankNames = {'Musel':'S01', 'Sauer':'S02', 'Alzette':'S03', }
        self.debugMode = getattr(cxt, 'debugMode').get('EPA',0)
        self._init_NoteData()
        self._init_LinkData()
        self._flatten_Patterns()
        self._init_Ruels()
        self._init_TankLevels(SysVars)
        self._init_TimeStep(cxt)
        #Initalize the hydraulics solver
        self._ENerr(et.ENopenH())
        self._ENerr(et.ENinitH(1))

    def _ENerr(self,e):
        if(e>0):
            print e, et.ENgeterror(e,25)
            ValueError(et.ENgeterror(e,25))

    def _init_NoteData(self):
        self.simuTimestamp=[]
        ret,nnodes=et.ENgetcount(et.EN_NODECOUNT)
        self.nodes=[]
        self.pres=[]
        self.actdemand = []
        self.sourcetracing=[]
        for index in xrange(1,nnodes+1):
            ret,t=et.ENgetnodeid(index)
            self.nodes.append(t)
            self.pres.append([])
            self.actdemand.append([])
            self.sourcetracing.append([])

    def _init_LinkData(self):
        ret,nlinks=et.ENgetcount(et.EN_LINKCOUNT)
        self.links=[]
        self.flow=[]
        self.speed=[]
        for index in range(1,nlinks+1):
            ret,t=et.ENgetlinkid(index)
            self.links.append(t)
            self.flow.append([])
            self.speed.append([])

    def _init_TimeStep(self,cxt):
        self.EPA_TimeStep = cxt.EPA_TimeStep
        self._ENerr(et.ENsettimeparam( et.EN_HYDSTEP, self.EPA_TimeStep ))
        self.simuTimerange = deque([[],[]],maxlen=2)
        self.simuSteps = deque([0,0],maxlen=2)
        self.TotSimuTime = 0

    def _flatten_Patterns(self):
        # In the integrated python simulation the scenarion consumptions are used
        # -> the pattern profile need to be set to ones
        ret,NbPat = et.ENgetcount(et.EN_PATCOUNT)
        self._ENerr(ret)
        for k in range(NbPat):
            ret,LenPat = et.ENgetpatternlen(k+1)
            self._ENerr(ret)
            for n in range(LenPat):
                ret = et.ENsetpatternvalue(k+1,n+1,1)
                self._ENerr(ret)
    def _init_Ruels(self):
        ret,NbControlRules = et.ENgetcount(et.EN_CONTROLCOUNT)
        self._ENerr(ret)
        for k in range(NbControlRules):
            ret = et.ENsetcontrol(k+1,0,0,0,0,0)
            self._ENerr(ret)

    def _init_TankLevels(self, InitLevels):
        pass #if needed implement this later

    def reset_TimeStep(self):
        self.simuTimerange.appendleft([])
        self.simuSteps.appendleft(0)

    def updateIN(self, SysOPC, QSollKeys, df, ScflowCols):
        # Update consumption zones
        for key,CId in self.AreaCounterMap.iteritems():
            et.ENsetnodevalue(et.ENgetnodeindex(key)[1], et.EN_BASEDEMAND, df.ix[0][CId+'_ival'])
        # Update tank inflow (control actions)
        for qi in QSollKeys:
            sti,vi = qi.split('.')
            et.ENsetlinkvalue(et.ENgetlinkindex(vi.rstrip('_QSoll'))[1], et.EN_SETTING, SysOPC[qi].value )
        # Update tank levels if debug mode
        if self.debugMode > 0:
            for ti in self.TankNames.values():
                et.ENsetnodevalue(et.ENgetnodeindex(ti)[1], et.EN_PRESSURE, SysOPC['{0}.{0}_K1_LIst'.format(ti)].value )

    def handleResults(self,simuTimestamp):
        self.simuTimestamp.append(simuTimestamp)
        for i in range(0,len(self.nodes)):
            ret,p=et.ENgetnodevalue(i+1, et.EN_PRESSURE)
            self.pres[i].append(p)
            ret,d=et.ENgetnodevalue(i+1, et.EN_DEMAND)
            self.actdemand[i].append(d)
            ret,q=et.ENgetnodevalue(i+1, et.EN_QUALITY)
            self.sourcetracing[i].append(q)
            
        for i in range(0,len(self.links)):
            ret,f=et.ENgetlinkvalue(i+1, et.EN_FLOW)
            self.flow[i].append(f)
            ret,s=et.ENgetlinkvalue(i+1, et.EN_SETTING)
            self.speed[i].append(s)

    def setOPCOut(self,OutOPC):
        #Write the flows, counter indicess and Basin levels to OPC
        for id in self.TankNames.values():
            idx = self.nodes.index(id)
            OutOPC['{0}.{0}_K1_LIst'.format(id)].setWriteValue(self.pres[idx][-1])

        for ki in filter(lambda x: x.endswith('_Flow'), OutOPC.keys()):
            sti,vi = ki.split('.')
            id = vi.rstrip('_Flow')
            idx = self.links.index(id)
            m = pds.np.array(self.flow[idx][-self.simuSteps[1]:])*self.simuTimerange[1]/3600. # unit [m3] with simuTimerange [s]
            f = m.sum()/sum(self.simuTimerange[1])*3600. # unit [m3/h] with simuTimerange [s]
            viBase = '{0}.{1}'.format(sti,id)
            OutOPC[viBase+'_Flow'].setWriteValue(f)
            OutOPC[viBase+'_Idx'].setWriteValue(OutOPC[viBase+'_Idx'].value + m.sum())

    def runTimeStep(self):
        while sum(self.simuTimerange[0]) < self.EPA_TimeStep:
            ret,tstep=et.ENnextH();
            self._ENerr(ret)
            ret,t=et.ENrunH()
            self._ENerr(ret)
            self.simuTimerange[0].append(tstep)
            self.TotSimuTime = t
            self.simuSteps[0] += 1
            self.handleResults(t)
        else:
            self.reset_TimeStep()

class EPASimuJob(jobNormal):
    '''
    This class builds the job that runns the Epanet based virtual reality.
    1. it reads on one side from a consuption scenario and on the 
	   other hand from OPC the current control actions.
	2. it simulates, using epanet, the network behaviour (levels and flows)
	3. writes the resulting values to OPC.
    '''
    zLifeEPA = "S98.S98_zLife"
    SysVars = {'OPC_Group':'EPASysVariables' }
    for sti in EPA_Vars:
        SysVars[sti] = filter(lambda x: x['OPC'] != "" and \
                                        x.has_key('Type') and \
                                        x['Type'] in ["CtrlAct","Conf","Life","Vol","Scenario"], EPA_Vars[sti])
    OutVars = {'OPC_Group':'EPAOutVariables' }
    for sti in EPA_Vars:
        OutVars[sti] = filter(lambda x: x['OPC'] != "" and \
                                        x.has_key('Access') and x['Access'] == "rw", EPA_Vars[sti])    
    _lenTSs = 5

    bitVarMap = {"SourcePipe":{"Vars": ["S01.S01_C01_Flow","S03.S03_C01_Flow"], "Range":10,"bit":11},
                 "SourceRural":{"Vars": ["S02.S02_C01_Flow",], "Range":10,"bit":12},
                 "SourceCity":{"Vars": ["S03.S03_C01_Flow",], "Range":10,"bit":13},
                 "TowerIndustry":{"Vars": ["S01.S01_C01_Flow",], "Range":0,"bit":8},
                 "TowerRural":{"Vars": ["S02.S02_C01_Flow",], "Range":0,"bit":9},
                 "TowerCity":{"Vars": ["S03.S03_C01_Flow",], "Range":0,"bit":10},
                 "Indurtry1":{"Vars": ["S01.S01_C02_Flow",], "Range":10,"bit":0},
                 "Indurtry2":{"Vars": ["S01.S01_C02_Flow",], "Range":15,"bit":1},
                 "Rural1":{"Vars": ["S02.S02_C02_Flow",], "Range":6,"bit":2},
                 "Rural2":{"Vars": ["S02.S02_C02_Flow",], "Range":10,"bit":3},
                 "City1":{"Vars": ["S03.S03_C02_Flow",], "Range":6,"bit":4},
                 "City2":{"Vars": ["S03.S03_C02_Flow",], "Range":10,"bit":5},
                 }
    
    def __init__(self,jobId,cxt):
        jobNormal.__init__(self,jobId)
        self.cxt = cxt
        self.sleep = None
        self.nextTS = None
        self._nextTSs = deque([],maxlen=self._lenTSs)
        self.runCnt = 0
        self.EPA_zLife = 0
        self.logger = logging.getLogger("runepanettask.epasimujob")
        self.logger.debug( "\n%s EPA Task starts at %s" % (self.logHeader(), datetime.now()) )
        
    def _init_OPC(self, opcclientName='OPCClient.Epanet'):
        opcserver = self.cxt.config["Tree"]["Global"]["OPCServer"]
        self.SysOPC = AlgData_OPC(variables = self.SysVars,
                                   opcclient_name = opcclientName+'Sys',
                                   opcserver = opcserver)
#        self.SysOPC.logger = self.logger
        self.SysOPC.readOPC()
        self.OutOPC = AlgData_OPC(variables = self.OutVars,
                                   opcclient_name = opcclientName+'Out',
                                   opcserver = opcserver)
#        self.OutOPC.logger = self.logger
        self.OutOPC.readOPC()
        self.QSollKeys = [ki for ki in self.SysOPC.gpcVars if ki.endswith('QSoll')]

    def _init_EPA(self,fnInp=None):
        if not fnInp:
            fnInp = self.cxt.EPA_fnInp
        fnParts = path.splitext(fnInp)
        dt = datetime.now().strftime("%Y%m%dT%H%M")
        fnRpt = fnParts[0]+'_'+dt+'.rpt'
        # Initalize epanettools. !!This is an global instance and not specific for the class-instance.
        ret=et.ENopen(fnInp,fnRpt," ")
        self._ENerr(ret)
        self.EPA = EPAContainer(self.cxt)
        #Run Epanet ones for initialization
        ret,t=et.ENrunH()
        self.EPA._ENerr(ret)

    def _init_nextTSs(self):
        ct = time()
        LCT = self._get_LifeCycle()
        self.logger.debug( "%s EPA cycle time (%s, %s)" % (self.logHeader(), LCT, self.EPA.EPA_TimeStep) )
        self._nextTSs.clear()
        for i in xrange(self._lenTSs):
            self._nextTSs.append(ct+(i+1)*LCT)
    
    def _ENerr(self,e):
        if(e>0):
            print e, et.ENgeterror(e,25)
            ValueError(et.ENgeterror(e,25))

    def _get_LifeCycle(self): #need to be linked to the OPC S0_tUpdate and perheaps "GPCLife" config
        try:
            LConf = self.cxt.config["Tree"]["GPCLife"]
            sr = self.cxt.S0_tUpdate*LConf['pctGPCSamp']/100.
            sleepD = max(sr,LConf['minSampling'])
        except AttributeError:
            sleepD = 10
        return sleepD
    def _check_Scenario(self):
        if not self.isScenarioChanged():
            return False
        ScId = self.SysOPC.opcVarsDict['S0.S0_Scenario'].value
        dbFile = None
        for fni in glob('data/*.csv'):
            if path.split(fni)[1].startswith("%s_"%ScId):
                dbFile = fni
                break
        else:
            self.logger.warning("=== Warning:\nThe Scenario ID in OPC (%s) has no corresponding ScenarioFile\n" % (ScId,) + \
                                "The old Scenario: %s will be continued\n===" % (self.cxt.dbFile,))
            return False
        if dbFile == self.cxt.dbFile:
            self.logger.info("The Scenario ID in OPC (%s) corresponds to the current running ScenarioFile (%s)\n" % (ScId,self.cxt.dbFile) + \
                             "The running ScenarioFile will be continued")
            return False
        else:
            self.logger.info("Change to Scenario %s" % (dbFile,))
            self.cxt._init_Scenario(dbFile=dbFile,dtime=self.df.index[0])
            return True
    def _get_ScenarioData(self):
        self.df = self.cxt.nextScenarioData()
        self.needNewScenarioData = False
    def _setNextTS(self):
        try:
            self.nextTS = self._nextTSs.popleft()
            self._nextTSs.append(self._nextTSs[-1]+self._get_LifeCycle())
        except IndexError:
            # Probably not life yet
            self.sleep = self._get_LifeCycle()
    def Error(self,fsm):
        self.logger.error( "%s: in Error", self.logHeader()) 
    def doPrep(self,fsm):
        self.logger.debug( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        if self.isEPALife():
            self._init_OPC()
            S0_tUpdate = self.SysOPC.opcVarsDict['S0.S0_tUpdate'].value
            if S0_tUpdate != None and S0_tUpdate > 0:
                self.cxt.S0_tUpdate = S0_tUpdate
            S0_Scenario = self.SysOPC.opcVarsDict['S0.S0_Scenario'].value
            if S0_Scenario != 0:
                ValueError("For the moment EpanetTask need to be initialized with the default scenario.")
                #GScToDo: get the scenario file and reinitalize the scenario.
            self._init_EPA()
        #Init Scenario data first reading.
        self._get_ScenarioData()
        self.ScflowCols = dict([(ci,ci.replace('_ival','_Flow'))for ci in filter(lambda x: not '_T' in x, self.df.columns)])
        self.ScIdxCols = dict([(ci,ci.replace('_T','_Idx'))for ci in filter(lambda x: '_T' in x, self.df.columns)])

        # Also Initialize the next runtime time steps
        self._init_nextTSs()
    def doRun(self,fsm):
        self.logger.debug( "%s runs in State %s: " % (self.logHeader(), fsm.current_state) )

        #Prepare and run epanet simulation for the next timestep
        self.EPA.updateIN(self.SysOPC.opcVarsDict, self.QSollKeys, self.df, self.ScflowCols)
        self.EPA.runTimeStep()
        self.EPA.setOPCOut(self.OutOPC.opcVarsDict)

        # Set the current simulation time
        sysTime = self.cxt.dfT0 + timedelta(seconds = self.EPA.TotSimuTime)
        self.OutOPC.opcVarsDict["S98.S98_DateTime"].setWriteValue(sysTime)

        #Write the LED bits to OPC depending on the In and Out flow.
        ioBitCode = 0
        for ki,vi in self.bitVarMap.iteritems():
            flow = sum([self.OutOPC.opcVarsDict[vari].value for vari in vi["Vars"]])
            if flow > vi["Range"]:
                ioBitCode |= 1 << vi["bit"]
        self.OutOPC.opcVarsDict['S0.S0_IOBit'].setWriteValue(ioBitCode)
        #Write the Scenario Bit-code to OPC
        self.OutOPC.opcVarsDict['S0.S0_ScenarioBit'].setWriteValue(int(self.df['Integer'][0]))

        #Increment zLifeEPA
        zL = self.SysOPC.opcVarsDict[self.zLifeEPA]
        if zL.value not in [None, 0]:
            self.EPA_zLife = zL.value
        self.EPA_zLife = (self.EPA_zLife+1) % (1<<16)
        self.OutOPC.opcVarsDict[self.zLifeEPA].setWriteValue(self.EPA_zLife)

        #Write results to OPC
        self.writeOPC()
        self.runCnt +=1 
    def doCheckPending(self,fsm):
        self._check_Scenario()
        if self.needNewScenarioData:
            #Get next Scenario data
            self._get_ScenarioData()
        self.logger.info( "%s runs in State %s: ScenarioDT=%s" % (self.logHeader(), fsm.current_state, self.df.index[0]) )
    def doPending(self,fsm):
        self.logger.debug( "%s in transit to %s: EpanetDT=%s" % (self.logHeader(), fsm.next_state, self.OutOPC.opcVarsDict["S98.S98_DateTime"].value) )
        self.runCnt = 0
        if self.nextTS == None and self.sleep == None:
            self._setNextTS()
        # Check if a next scenario data need to be read
        if timedelta(seconds=self.EPA.TotSimuTime) >= self.cxt.get_nextScenarioTime():
            self.needNewScenarioData = True
    def doResume(self,fsm):
        self.logger.debug( "%s in transit to %s" % (self.logHeader(), fsm.next_state) )
        try: #Check the initialization of the OPC variables
            self.SysOPC.readOPC()
        except AttributeError:
            if self.isEPALife():
                self._init_OPC()
        self.sleep = None
        self.nextTS = None
    def doPost(self,fsm):
        self.logger.debug( "%s in transit to %s" % (self.logHeader(), fsm.next_state) )
        et.ENcloseH()
        et.ENclose()
    def isScenarioChanged(self):
        ScDiff = self.SysOPC.opcVarsDict['S0.S0_Scenario'].getDiff()
        if ScDiff:
            if ScDiff.Diff[0] != 0:
                return True
            return False
        else:
            return False
    def isDone(self,fsm):
        if not isinstance(self.df, pds.DataFrame):
            return True
        return False
    def tobePending(self,fsm):
        if self.runCnt >= 1:
            return True
        elif getattr(self, "SysOPC", None) == None:
            self.logger.info( "%s EPA-Task is not aLife", self.logHeader())
            return True
        self.logger.info( "%s EPA-Task is aLife", self.logHeader())
        return False
    def tobeResumed(self,fsm):
        if not self.isEPALife():
            return False
        #Read current system state
        try: #Check the initialization of the OPC variables
            self.SysOPC.readOPC()
        except AttributeError:
            if self.isEPALife():
                self._init_OPC()
            return True
        if self.isScenarioChanged():
            return False
        elif self.needNewScenarioData:
            return False
        elif self.runCnt == 0:
            return True
        return False
    def isEPALife(self):
        if True: # Dummy for the moment. May be used to dynamically start/stop the EPA simulation.
            return True
        return False
    def writeOPC(self):
        try:
            SData = self.OutOPC
            opcVars = SData.getWritableVars()
            WStatus = SData.writeOPC(allStored=True, toOPC=True)
            if len(WStatus) != len(opcVars):
                self.logger.warning( "%s OPC Status size different from VarList size (%s, %s)" % (self.logHeader(), len(WStatus), len(opcVars)) )            
            tfSuccess = [ri[1] == "Success" if (isinstance(ri,tuple) and len(ri) >= 2) \
                         else False for ri in WStatus]
            if not all(tfSuccess):
                self.logger.warning( "%s some un-successful OPC-Writeouts %s" % (self.logHeader(), WStatus) )
            else:
                dt = SData.opcVarsDict[SData.gpcVars[0]].dt
                self.logger.info( "%s (%s) All Out variables written successful" % \
                                  (self.logHeader(), dt) )
        except StandardError as e:
            self.logger.error("StandardError: %s",e)
    def logHeader(self):
        try:
            return self.logHeaderStr.rstrip(':') + " %s:" % (datetime.now().time())
        except:
            super(EPASimuJob, self).logHeader()
            return self.logHeaderStr.rstrip(':') + " %s:" % (datetime.now().time())



from random import randint, choice
from utilities.opcVarHandling import opcVar
from ReadWriteDataTest.handleConfig import readConfigJob, readGPCConfig
if __name__ == '__main__': 
    import ReadWriteDataTest.config as GPCConfig


class Context():
    readConfigJob.confFileType
    def __init__(self,EPA_fnInp="ShowroomWN_V001.inp", dbFile='data/0_Pattern_1D.csv'):
        import ReadWriteDataTest.config as GPCConfig
        GPCConf = readGPCConfig(path.join('..','ReadWriteDataTest',GPCConfig.GPCConfFile))
        self.config = dict(zip(("Tree","Valid"),GPCConf))
        self.CTimeperiod = self.config["Tree"]["MPC_Opti"]["ControlTimeperiod"]
        pctGPCSamp = self.config["Tree"]["GPCLife"]["pctGPCSamp"]
        self.EPA_fnInp = EPA_fnInp
        self.EPA_TimeStep = self.CTimeperiod*pctGPCSamp/100 # in [s] --> This should be specified in some configuration
        self.TDeltaPrevious = timedelta(seconds=0)
        self.dbFile = dbFile
        self.debugMode = {'EPA':1,}
        self._init_Scenario()
    def _init_Scenario(self,dbFile=None,dtime=None):
        if dbFile:
            self.dbFile=dbFile
        self.df = pds.read_csv(self.dbFile,index_col='Datetime',parse_dates={'Datetime':['Date','Time']},dayfirst=True)
        samplIntervals = (pds.Series(self.df.index[1:])-pds.Series(self.df.index[:-1])).value_counts()
        if samplIntervals.size != 1:
            ValueError("Scenario file has not unique samplIntervals: %s" % (samplIntervals,) )
        self.dfFreq = samplIntervals.index[0]
        if not hasattr(self,'_ScIdx'): #in Context initialization phase.
            #Initialize the zero referenc time.
            self.dfT0 = self.df.index[0]
        if dtime:
            for i,dti in enumerate(self.df.index):
                if dtime.time() == dti.time():
                    self._ScIdx = i
                    break
            else:
                logging.getLogger("runepanettask").warning("StartIndex not found in the Scenario: start from 0")
                self._ScIdx = 0
        else:
            self._ScIdx = 0
    def get_nextScenarioTime(self):
        """returns the next scenarion time as timedelta from beginning"""
        ix = self._ScIdx%self.df.index.size
        try:
            tdel = self.TDeltaPrevious + self.df.index[ix]-self.df.index[0]
        except IndexError:
            tdel = self.TDeltaPrevious + self.df.index[ix-1]-self.df.index[0] + self.dfFreq
        return tdel
    def nextScenarioData(self):
        ix = self._ScIdx%self.df.index.size
        if self._ScIdx >= self.df.index.size \
           and ix == 0:
            TDelta = self.df.index[-1]-self.df.index[0] + self.dfFreq
            self.TDeltaPrevious += TDelta
            self.df.index = self.df.index.shift(TDelta.total_seconds(),freq='S')
        df = self.df.ix[ix:ix+1]
        self._ScIdx += 1
        return df

class GPC_jobManagement(jobManagement):
    def __init__(self,cxt):
        jobManagement.__init__(self)
        self.cxt = cxt
    def getPending(self,fsm):
        pass
    
if __name__ == '__main__':
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    EPAlogRF = logging.handlers.RotatingFileHandler( 
                    filename='EPA.log', mode='a', 
                    backupCount=10, maxBytes=1000000 )
    EPAlogRF.setLevel(logging.DEBUG)
    logging.getLogger("runepanettask").addHandler(ch)
    logging.getLogger("runepanettask").addHandler(EPAlogRF)
    logging.getLogger("runepanettask").setLevel(logging.DEBUG)

    sm = Context()
#    sm = Context(dbFile='data\LHC_7d.csv')
    jM = GPC_jobManagement(None)
    jM.fsm.memory['Buffer'].append([(1,sm),EPASimuJob])
    while jM.fsm.current_state != 'END':
        jM.fsm.process(None)
        if jM.fsm.current_state == 'Idle':
            sleep(0.05)
    