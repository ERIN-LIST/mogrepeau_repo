""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

if __name__ == '__main__':
    import config

import sys
from collections import deque
from GPCAlgGlobFSM_sm import GPCAlgGlobProc_sm, GPCMap
from TriggerHandling import ReadTrigger, WriteTrigger
from apscheduler.scheduler import Scheduler
import logging
import logging.handlers
from datetime import *
from time import sleep, mktime, time
from ReadNeededDataTest.ReadData_useOPC import AlgData_OPC
from JobScheduler.JobManagement_GSc import jobManagement, jobSimple, jobNormal
from handleConfig import readConfigJob
from handleLifeCounter import MPCzLifeJob
from utilities.GPCStateUtilities import getSysGPCState, getSysGPCState_StMo, getSysBModeUpdate
import Control.MPCAlgos as MPCAlgos
from Control.GPCVariablesConfig import GPC_OutVars, GPC_StateVars


class sm_Logger(logging.Logger):
    def __init__(self,name):
        logging.Logger.__init__(self,name)
        self.setLevel(logging.DEBUG)
    def write(self,msg):
        self.debug(msg)

class GPCAlgGlobFSM():
    def __init__(self, debugFlag=False, configFile = None):
        #SM FSM specific initialization
        self._fsm = GPCAlgGlobProc_sm(self)
        self._fsm.setDebugFlag(debugFlag)
        self.MPCAlgo = {'Active':None}
        self.logger = logging.getLogger("GPCAlgGlobProc")
        tmpLogger = logging.getLoggerClass()
        logging.setLoggerClass(sm_Logger)
        self._fsm.setDebugStream(logging.getLogger("GPCAlgGlobProc.fsm"))
        logging.setLoggerClass(tmpLogger)
        self.eventDeque = deque()
        #APScheduler
        self.sched = Scheduler()
        self.configFile = configFile
    def __del__(self):
        self.sched.shutdown(wait=False)

    def start(self):
        self._fsm.enterStartState()
        self.sched.start()

    def initInit(self):
        self.doInitMemory = {"Count":0,
                             "S0_tUpdate":{'State':None},
                             "MPCData":{'State':None},
                             "Config":{'State':None}}

    def doInit(self):
        mem = self.doInitMemory
        mem["Count"] += 1

        # Get the GPC Config file
        if mem["Config"]['State'] != 'Done':
            conf = mem["Config"]
            try:
                if self.configJob.isConfigRead():
                    conf['State'] = 'Done'
            except AttributeError:
                conf['State'] = 'Running'

        # Get the main "S0_tUpdate" from the SCADA system.
        if mem["S0_tUpdate"]['State'] == None \
           and self.configJob.isConfigRead():

            AlgConfVars = AlgData_OPC(variables=["S0_tUpdate",],
                                      opcserver = self.config["Tree"]["Global"]["OPCServer"])
            AlgConfVars.logger = self.logger
            mem["S0_tUpdate"]["Data"] = AlgConfVars
            mem["S0_tUpdate"]['State'] = 'Running'
        if mem["S0_tUpdate"]['State'] in ['Running']:
            S0 = mem["S0_tUpdate"]
            for i in xrange(3):
                sleep(0.2)
                S0['Data'].readOPC()
                if S0['Data'].opcVarsDict["S0_tUpdate"].value not in [None, 0]:
                    self.S0_tUpdate = S0['Data'].opcVarsDict["S0_tUpdate"].value
                    S0['State'] = 'Done'
                    break
            else:
                # only if the for loop is not stopped with break (no usable value found)
                if S0['Data'].opcVarsDict["S0_tUpdate"].isProblem():
                    S0['Data'].opcVarsDict["S0_tUpdate"]._reset()
                S0['State'] = 'Running'

        # Initialize the MPC OPC data objects.
        if mem["MPCData"]['State'] == None \
           and self.configJob.isConfigRead():
            # Basic dynamic System variables needed for MPC as input variables
            self.MPCData = AlgData_OPC(opcserver = self.config["Tree"]["Global"]["OPCServer"])
            self.MPCData.logger = self.logger
            # All MPC related output variables
            Variables = {'OPC_Group':'MPCOutVariables' }
            Variables.update(GPC_OutVars)
            self.MPCOutData = AlgData_OPC(opcserver = self.config["Tree"]["Global"]["OPCServer"],
                                          variables = Variables)
            self.MPCOutData.logger = self.logger
            self.MPCOutData.readOPC() # Need to read this variable ones because otherwise it will not be usable for writing.
            # All GPC/MPC State related variables
            Variables = {'OPC_Group':'GPCStateVariables' }
            Variables.update(GPC_StateVars)
            self.MPCStateData = AlgData_OPC(opcserver = self.config["Tree"]["Global"]["OPCServer"],
                                            variables = Variables)
            self.MPCStateData.logger = self.logger
            mem["MPCData"]['State'] = 'Done'

    def doInitRTrigParam(self):
        self.RTrig = ReadTrigger( S0_tUpdate=self.S0_tUpdate,
                                  opcserver=self.config["Tree"]["Global"]["OPCServer"],
                                  test=True)
        self.RTrig.setLogger(self.logger)
        self.RTrig.CTimeperiod = self.config["Tree"]["MPC_Opti"]["ControlTimeperiod"]

    def doUpdateRTrigParam(self,dt):
        """Update trigger detection parameter to get a more precise
           identification of the positive slope instance."""
        self.RTrig.updateTrigParam()
        self.logger.debug( "Trigger: lastDT=%s,DT=%s" % (self.RTrig.lastDT,self.RTrig.DT) )

    def doUpdateConfig(self,conf):
        self.config = dict(zip(("Tree","Valid"),conf))
        MPCmode = self.config["Tree"]["MPC"]["mode"]
        if isinstance(self.MPCAlgo['Active'], MPCAlgos.__dict__[MPCmode]):
            self.MPCAlgo['Active'].updateConf(self.config['Tree']["MPC_"+MPCmode])

    def doRTrigInit(self):
        self.RTrig.jobRuns = 0
        DT = self.RTrig.DT
        NextRT = self.RTrig.getNextRT().replace(tzinfo=None)
        max_runs = self.RTrig.getMaxRuns()
        #Debug-GSc: test max_runs = 4
        self.RTrig.job = self.sched.add_interval_job(self.jobRTrig,
                                    seconds = DT,
                                    start_date = NextRT,
                                    max_runs = max_runs,
                                    name = "ReadTrigger-Job")
        self.doRTrigMemory = {"Count":0,
                              "TrigDone":False}

    def doRTrigStop(self):
        if self.RTrig.job.compute_next_run_time(datetime.now()):
            # only un-schedule if the job is still scheduled otherwise scheduler error
            self.sched.unschedule_job(self.RTrig.job)
        self.RTrig.job = None

    def doWTrigInit(self):
        #for debug reasons: OPC-values are sometimes lost.
        self.logger.debug( "Log QSoll before trigger:" )
        self.MPCOutData.readOPC()
        if self.isNoOPCWriteTrigger():
            self.logger.debug( "WriteTrigger is asked not to be set." )
        else:
            self.WTrig = WriteTrigger(S0_tUpdate=self.S0_tUpdate)
            self.WTrig.setLogger(self.logger)
            self.WTrig.job = self.sched.add_interval_job(self.jobWTrig,
                                        seconds = self.WTrig.DT,
                                        start_date = datetime.now() + timedelta(seconds=0.5),
                                        max_runs = 2,
                                        name = "WriteTrigger-Job")
            #GSc-ToDo: start a job that sets and resets the trigger
            # use self.WTrig.process()
            # Should be called a maximum of 2x self.WTrig.maxRuns
            # but only until self.WTrig.state is in ('Reset' or some "Error")
            # "sched" seems not to be best as Setting process can take several runs (DT 1s)
            # and reseting the same but in between 10%S0_tUpdate needs to be waited.
    def doReadOPC(self):
        #GSc-ToDo: rework this first level checking. Here only completely infeasible situations should lead to "VarsError"
        #Get first state related information and check it
        evStr = self.MPCStateData.readOPC()
        if evStr == None:
            evStr = self.checkMPCData(self.MPCStateData)
        #If OK Get the MPC "In" information and check it
        if evStr == "VarsOK":
            evStr = self.MPCData.readOPC()
        if evStr == None:
            evStr = self.checkMPCData(self.MPCData)

        if isinstance(evStr, (list,tuple)):
            evt = dict(zip(("Type","Data"),evStr))
        else:
            evt = {"Type":evStr}
        self.eventDeque.append(evt)

    def doUpdateParam(self):
        #Only update here is GPC is OPC triggered
        if not self.RTrig.TrigOPC:
            return

        #Do update only if changed
        S0_tUpdate = self.MPCStateData.opcVarsDict["S0.S0_tUpdate"]
        S0_tUpdateDiff = S0_tUpdate.getDiff()
        if S0_tUpdateDiff != None and S0_tUpdateDiff.Diff[0] != 0:
            self.S0_tUpdate = S0_tUpdate.value
            self.RTrig.updateTrigParam(S0_tUpdate=self.S0_tUpdate)

    def doWriteOPCInit(self):
        #GSc-ToDo: Init write process
        self.logger.debug( "Init writeOPCVars process" )
        self.doWriteOPCMemory = {"Count":0,}

    def doWriteOPC(self):
        opcResult = self.MPCOutData.writeOPC(allStored=True, toOPC=True)
        if opcResult in [True, None, []]:
            self.eventHandler({"Type":"OPCWriteError",
                               "Data":"writeOPC returns: %s" % (opcResult)})
            return
        nbrW = len(opcResult)
        tfSuccess = [ri[1] == "Success" for ri in opcResult]
        if not all(tfSuccess):
            nbrErr = nbrW - sum(tfSuccess)
            if self.doWriteOPCMemory["Count"] > 3:
                self.logger.debug( "doWriteOPC after (%s) tries still %s un-successful opc-writeouts\n -> give-up" % \
                                   (self.doWriteOPCMemory["Count"],nbrErr))
                self.eventHandler({"Type":"OPCWriteError",
                                   "Data":"writeOPC returns: %s" % (opcResult)})
            else:
                self.logger.debug( "doWriteOPC (%s): %s un-successful opc-writeouts" % \
                                   (self.doWriteOPCMemory["Count"],nbrErr))
                sleep(0.5)
        else:
            self.logger.debug( "doWriteOPC (%s): ends successful" % \
                               (self.doWriteOPCMemory["Count"],) )
        self.doWriteOPCMemory["Count"] += 1


    def doCheckSysStates(self):
        #ToDo-GSc: check the on/off states of the GPC
        MPCSimu = self.isMPCSimu()
        if MPCSimu and self.getMPCSimuMode() in ['OPCReadOnly',]:
            self.eventDeque.append({"Type":"MPCInactif","Data":"OPCReadOnly Mode specified"})
            return

        # Check the life states of all configured actors

#        SysGPCState = getSysGPCState(self.MPCStateData.opcVarsDict)# Old Life/Autonom based approach
        SysGPCState = getSysGPCState_StMo(self.MPCStateData.opcVarsDict)
        if getattr(self, "SysGPCState", None):
            UpdatedBState = dict([(si,Statei) for si, Statei in SysGPCState.iteritems() if Statei != self.SysGPCState[si]])
        else:
            UpdatedBState = {}
        self.SysGPCState = SysGPCState

        #check the life states of actor S0 (SCADA system)
        if self.SysGPCState['S0'] == 'offline':
            self.eventHandler({"Type":"MPCImpossible","Data":"S0 is %s" % (self.SysGPCState['S0'],)})
            return
        elif self.SysGPCState['S0'] == 'maintenance':
            self.eventDeque.append({"Type":"MPCInactif","Data":"S0 Station is in maintenance"})
            return

        if all([zi in ['offline','maintenance'] for si,zi in self.SysGPCState.iteritems() if si not in ['S0','S99']]):
            self.eventDeque.append({"Type":"MPCInactif","Data":"There is NO Station controllable"})
            return
        else:
            BModeUdate = getSysBModeUpdate(self.MPCStateData.opcVarsDict)
            UpdatedBMode = dict([(si,bmi['Mode']) for si, bmi in BModeUdate.iteritems() if bmi['Update']])
            if self.MPCAlgo['Active'] != None and (UpdatedBState !={} or UpdatedBMode != {}):
                updateStruct = False
                algo = self.MPCAlgo['Active']
                if UpdatedBMode != {}:
                    res = algo.readBConfig(toUpdate=UpdatedBMode) #ToDo: check the return value (True False) if network configuration is usable.
                    if res != True:
                        interItem = {"Type":"MPCImpossible",
                                     "Data":"Error in reading the current basin configuration: %s" % (res,)}
                        self.eventHandler(interItem)
                        return
                    updateStruct = True
                MPCmode = self.config["Tree"]["MPC"]["mode"]
                C_Switch = algo.updateBasinConf(self.SysGPCState,updateStruct=updateStruct)
                self.handleStateSwitch(C_Switch)
            else:
                try:
                    MPCmode = self.config["Tree"]["MPC"]["mode"]
                    try:
                        if not isinstance(self.MPCAlgo['Active'], MPCAlgos.__dict__[MPCmode]):
                            algo = MPCAlgos.__dict__[MPCmode](self.config['Tree']["MPC_"+MPCmode],
                                                              sysVars=self.MPCData.opcVarsDict,
                                                              stateVars=self.MPCStateData.opcVarsDict,
                                                              outVars=self.MPCOutData.opcVarsDict)
                            C_Switch = algo.updateBasinConf(self.SysGPCState)
                            self.handleStateSwitch(C_Switch)
                            self.MPCAlgo['Active'] = algo
                    except KeyError as e:
                        interItem = {"Type":"MPCImpossible",
                                     "Data":"MPC-mode related class is missing. %s" % (e,)}
                        self.eventHandler(interItem)
                        return
                    except BaseException as e:
                        interItem = {"Type":"MPCImpossible",
                                     "Data":"Error during instantiation of the algo class: %s" % (e,)}
                        self.eventHandler(interItem)
                        return
                except KeyError as e:
                    interItem = {"Type":"MPCImpossible",
                                 "Data":"Error getting MPC-Mode specification: %s" % e}
                    self.eventHandler(interItem)
                    return

                #ToDo: Handle possible other control approaches that will run only as off-line control
                self.MPCAlgo['Inactive'] = []
                try:
                    for im in self.config["Tree"]["MPC"]["inactiveModes"]:
                        pass
                except:
                    pass


        #ToDo-GSc: integrate the AlgInernalSysFSM (S4, ...)
        # - init it in doInit
        # - process it here using the self.MPCData.S4_BZ

        self.logger.debug( "doCheckSysStates(): SysStates: %s; SysModes: %s" % (self.SysGPCState,BModeUdate) )

        #Check the SysGPCState again here as it may have changed due to Switching.
        #If here a basin is in controllable this means it is not controlled by GPC in this cycle.
        if all([zi in ['offline','maintenance','controllable'] for si,zi in self.SysGPCState.iteritems() if si not in ['S0','S99']]):
            self.eventDeque.append({"Type":"MPCInactif","Data":"There is NO Station configured for GPC control"})
        else:
            self.eventDeque.append({"Type":"MPCActive"})


    def doRunMPC(self):
        #Initialize the specified MPC mode class object.
        algo = self.MPCAlgo['Active']
        #run MPC
        try:
            algo.run(self.MPCData.opcVarsDict,
                     stateVars=self.MPCStateData.opcVarsDict,
                     outVars=self.MPCOutData.opcVarsDict)
            self.eventDeque.append({"Type":"MPCDone",})
        except BaseException as e:
            interItem = {"Type":"MPCImpossible",
                         "Data":"General MPC-Error: %s" % e}
            self.eventHandler(interItem)
            return

    def doLogMPCResults(self):
        #get the results and build a log entry
        res = [vi.wvalue for ki,vi in self.MPCOutData.opcVarsDict.iteritems() if ki.endswith('QSoll') and vi.isWReady()]
        self.logger.debug("MPC Results: %s" % (res,))

    def doResetWriteVars(self):
        for ki,vi in self.MPCOutData.opcVarsDict.items() + self.MPCStateData.opcVarsDict.items():
            if vi.isWReady():
                vi._reset()

    def doWarning(self,msg):
        pass

    def doSetGPCOffline(self):
        self.logger.debug("""====== GPC is Offline ======
The GPC: is now in Offline mode.
Only a 'Reset'-Event or a complete GSP-restart are possible in this System state.
============================""")
        if self.isMPCSimu():
            try:
                DT = self.S0_tUpdate - 2*self.RTrig.gitter
                DT -= self.S0_tUpdate / self.RTrig.TrigSizePct # This is the sleep time in GPCOffline mode.
            except:
                DT = 900
            #Debug-GSc: test DT = 40
            self.sched.add_date_job( self.jobReset,
                                     date = datetime.now() + timedelta(seconds=DT),
                                     name = "Reset-Job" )
            self.logger.debug("""====!! GPC auto-Reset !!====
The GPC: will be automatically reset at %s
============================""" % (DT,))


    def isInitDone(self):
        #Check all doInitMemory entries for their "State" status
        state = [si['State'] == 'Done' for si in self.doInitMemory.itervalues() if isinstance(si, dict) and si.has_key('State')]
        return all(state)

    def isNotSync(self):
        return not self.RTrig.isSync()

    def isNoOPCWrite(self):
        if not self.isMPCSimu():
            return False
        elif self.getMPCSimuMode() in [None,'NoOPCWrite']:
            return True
        return False

    def isNoOPCWriteTrigger(self):
        if not self.isMPCSimu():
            return False
        elif self.getMPCSimuMode() in [None,'NoOPCWrite','NoOPCWriteTrigger']:
            return True
        return False

    def isMPCSimu(self):
        try:
            MPCSimu = self.config['Tree']['MPC']['simu']
        except:
            MPCSimu = True
        if MPCSimu:
            return True
        return False
    def isOPCWriteOK(self):
        if self.MPCOutData.isWAllIdle():
            self.logger.debug("isOPCWriteOK == True")
            return True
        self.logger.debug("isOPCWriteOK == False")
        return False
    def isOPCWriteError(self):
        if self.MPCOutData.isWAnyProblem():
            self.logger.debug("isOPCWriteError == True")
            return True
        self.logger.debug("isOPCWriteError == False")
        return False

    def logIgnored(self):
        self._fsm.getDebugStream().write("The latest asked transition was ignored by the StateMashine.")

    def jobRTrig(self):
        j = self.RTrig.job
        self.doRTrigMemory['Count'] += 1
        if self.RTrig.getRTrigJob():
            self.doRTrigMemory['TrigDone'] = True
            self.doRTrigMemory['Event'] = {"Type":"TrigOK", "Data":self.RTrig.lastT}
        else:
            if not j.compute_next_run_time(datetime.now()):
                self.doRTrigMemory['TrigDone'] = True
                self.doRTrigMemory['Event'] = {"Type":"TrigError",
                             "Data":"%s: no next fire time scheduled" % j.name}

    def jobWTrig(self):
        if self.WTrig.isInProcess():
            cSatate = self.WTrig.state
            while self.WTrig.state == cSatate:
                self.WTrig.process()
                if self.WTrig.state == cSatate:
                    sleep(1)
        #for debug reasons: OPC-values are sometimes lost.
        if not self.WTrig.isInProcess():
            self.logger.debug( "Log QSoll after trigger:" )
            self.MPCOutData.readOPC()

        if self.WTrig.isJobAlife() and not self.WTrig.isInProcess():
            self.sched.unschedule_job(self.WTrig.job)
            self.WTrig.job = None
            self.logger.debug("jobWTrigError: job unscheduled due to probable Error WTrig process")
            #GSC-ToDo: this is not a correct solution because it can leave the system in an incoherent state.

    def jobReset(self):
        interItem = {"Type":"Reset"}
        self.eventHandler(interItem)

    def checkInitSleep(self):
        if self.isInitDone():
            return False
        elif self.doInitMemory["Count"] == 0:
            return False
        elif self.doInitMemory["Count"] % 3 == 0:
            return True
        else:
            return False

    def checkMPCData(self,MPCData):
        #ToDo: Check if all variables of stations that are not "offline" are usable.
        for k,v in MPCData.opcVarsDict.iteritems():
            if not v.usable:
                return ("VarsError","%s: is not usable"%(k,))
        return "VarsOK"
    def getMPCSimuMode(self):
        try:
            MPCSimuMode = self.config['Tree']['MPC']['simuMode']
        except:
            return None
        return MPCSimuMode
    def getFSMState(self):
        if not self._fsm.isInTransition():
            cState = self._fsm.getState().getName()
            FSMState = "%s" % (cState,)
            ret = {'Trans':None,'State':cState,'Msg':FSMState}
        else:
            trans = self._fsm.getTransition()
            pState = self._fsm.getPreviousState().getName()
            FSMState = "In Transition: %s from %s" %(trans,pState)
            ret = {'Trans':trans,'State':pState,'Msg':FSMState}

        return ret

    def handleStateSwitch(self,C_Switch):
        """Handles the switch from Mode 1 (C-abl) -> 2 (C) or 2 (C) -> 1 (C-abl)
        """
        for sti in C_Switch.get('C-abl -> C',[]):
            vi = "%s.%s_SteuerModus" % (sti,sti)
            self.MPCStateData.opcVarsDict[vi].setWriteValue(6)
            self.SysGPCState[sti] = 'controlled'
        for sti in C_Switch.get('C -> C-abl',[]):
            vi = "%s.%s_SteuerModus" % (sti,sti)
            self.MPCStateData.opcVarsDict[vi].setWriteValue(5)
            self.SysGPCState[sti] = 'controllable'
        if not self.isNoOPCWrite() and len(C_Switch) > 0:
            opcResult = self.MPCStateData.writeOPC(allStored=True, toOPC=True)
            if opcResult in [True, None, []]:
                self.logger.debug( "Basin StateSwitch error: writeOPC returns: %s" % (opcResult))
            else:
                nbrW = len(opcResult)
                tfSuccess = [ri[1] == "Success" for ri in opcResult]
                if not all(tfSuccess):
                    nbrErr = nbrW - sum(tfSuccess)
                    self.logger.debug( "Basin StateSwitch error: writeOPC %s un-successful opc-writeouts" % \
                                       (nbrErr,))
                else:
                    self.logger.debug( "Basin StateSwitch: %s; writeOPC: %s" % (C_Switch, opcResult,))
        elif self.isNoOPCWrite() and len(C_Switch) > 0:
            self.logger.debug( "Basin StateSwitch: %s but NoOPCWrite is active" % (C_Switch,) )

    def eventHandler(self,evt):
        evtStr = evt["Type"]
        if evt.has_key("Data"):
            evtStr = ';'.join((evtStr,str(evt['Data'])))
        self._fsm.getDebugStream().write("#%s (%s)\n" % (evtStr,datetime.now()))

        if evt['Type'] == "DoInit":
            self._fsm.InitDone()
        elif evt['Type'] == "InitError":
            self._fsm.InitError(evt['Data'])
        elif evt['Type'] == "TrigOK":
            self._fsm.TrigOK(evt['Data'])
        elif evt['Type'] == "TrigError":
            self._fsm.TrigError(evt['Data'])
        elif evt['Type'] == "VarsOK":
            self._fsm.VarsOK()
        elif evt['Type'] == "VarsError":
            self._fsm.VarsError()
        elif evt['Type'] == "MPCActive":
            self._fsm.MPCActive()
        elif evt['Type'] == "MPCInactif":
            self._fsm.MPCInactif()
        elif evt['Type'] == "MPCImpossible":
            self._fsm.MPCImpossible(evt['Data'])
        elif evt['Type'] == "MPCDone":
            self._fsm.MPCDone()
        elif evt['Type'] == "OPCWrite":
            self._fsm.OPCWrite(evt.get('Data',None))
        elif evt['Type'] == "Reset":
            self._fsm.Reset()
        elif evt['Type'] == "Stop":
            sys.exit(0)
        else:
            raise ValueError("Unhandled Event type: %s" % evt)

class GPC_jobManagement(jobManagement):

    def __init__(self,cxt):
        jobManagement.__init__(self)
        self.cxt = cxt

    def getPending(self,fsm):
        """
        activity method to get the pending jobs from input or persistent storage.
        """

class scenarioJob(jobNormal):
    scenario = [
        {"Type":"DoInit","Done":False},
        {"Type":"Stop","Done":False},
    ]
    def __init__(self,jobId,cxt):
        jobNormal.__init__(self,jobId)
        self.cxt = cxt
        self.sleep = None
        self.logger = logging.getLogger("GPCAlgGlobProc.scenarioJob")
    def Error(self,fsm):
        self.logger.error( "%s: in Error", self.logHeader())
    def doPrep(self,fsm):
        self.logger.debug( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        self.sceIdx = 0
    def doRun(self,fsm):
        self.logger.debug( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        gpcState = self.cxt.getFSMState()['State']
        item = self.scenario[self.sceIdx]
        self.cxt.eventHandler(item)
        # If FSM change state, current scenario is done.
        if self.cxt.getFSMState()['State'] != gpcState:
            self.scenario[self.sceIdx]["Done"] = True
        elif gpcState == "GPCMap.INIT":
            if self.cxt.checkInitSleep():
                self.scenario[self.sceIdx]["Done"] = 'Sleep'
    def doPending(self,fsm):
        self.logger.debug( "%s in transit to %s" % (self.logHeader(), fsm.next_state) )
        self.sleep = 0.05
    def doResume(self,fsm):
        self.logger.debug( "%s in transit to %s" % (self.logHeader(), fsm.next_state) )
        self.sleep = 0.05
    def doCheckPending(self,fsm):
        self.logger.info( "%s runs in State %s (slept: %s)" % (self.logHeader(), fsm.current_state,self.sleep) )
        gpc = self.cxt
        gpcState = gpc.getFSMState()['State']
        sce = self.scenario[self.sceIdx]
        nextSce = True
        self.sleep = 0.01
        Data = None
        #GSc-ToDo: by inserting new scenarios this list is constantly growing and may lead to an out-of-memory error.
        # -> add some thing like garbage collection or use a queue with given length where old executed scenario entries are removed.
        if gpc.getFSMState()['Trans']:
            nextSce = False
            self.sleep = 0.1
        elif gpcState == "GPCMap.INIT":
            if not gpc.isInitDone():
                if sce['Type'] != "DoInit" or sce['Done'] == True:
                    # A system reset was initiated (not by the scenarioJob) A new Init scenario needs to be initiated.
                    self.scenario.insert(self.sceIdx+1, {"Type":"DoInit","Done":False})
                else:
                    if sce['Done'] == 'Sleep':
                        sce['Done'] = False
                        self.sleep = 45
                    else:
                        self.sleep = 5
                    nextSce = False

        elif gpcState == "GPCMap.GetRTrig":
            RTr = gpc.RTrig
            if gpc.doRTrigMemory["TrigDone"]:
                evt = gpc.doRTrigMemory['Event']
                evt['Done'] = False
                self.scenario.insert(self.sceIdx+1,evt)
            elif RTr.isJobAlife():
                self.sleep = max(mktime(RTr.getNextRT().timetuple()) - time(),
                                 RTr.DT)
                nextSce = False
            else:
                #If scheduled trigger job stopped due to an error raised in the job go to GPCisOffline
                msg = "Job %s (ID %s):" % (self.__class__.__name__,self.id)
                self.scenario.insert(self.sceIdx+1,
                                     {"Type":"TrigError",
                                      "Data":msg+" Trigger Job not alive any more.",
                                      "Done":False})
        elif gpcState == "GPCMap.WriteOPCVars":
            if sce['Type'] != "OPCWrite" or sce['Done'] == True:
                self.scenario.insert(self.sceIdx+1, {"Type":"OPCWrite","Done":False})
                self.sleep = None
            else:
                self.sleep = 0.5
                nextSce = False
        elif gpcState in \
            ["GPCMap.ReadOPCVars",
             "GPCMap.CheckSysStates",
             "GPCMap.RunMPC",]:
            try:
                evt = gpc.eventDeque.popleft()
                evt["Done"] = False
                self.scenario.insert(self.sceIdx+1, evt)
                self.sleep = None
            except IndexError:
                nextSce = False

        elif gpcState == "GPCMap.GPCisOffline":
            try:
                self.sleep = self.cxt.S0_tUpdate / self.cxt.RTrig.TrigSizePct
            except:
                self.sleep = 10
            nextSce = False
        else:
            self.logger.debug( "%s %s Unhandled GPC-State: %s" % (self.logHeader(), fsm.current_state, gpcState) )
            pass

        if nextSce:
            self.sceIdx += 1
            if Data : self.scenario[self.sceIdx]["Data"] = Data

    def isDone(self,fsm):
        if self.sceIdx == len(self.scenario)-1 \
           and self.scenario[self.sceIdx]["Done"] == True:
            return True
        return False
    def tobePending(self,fsm):
        if self.sceIdx < 0 or \
           (not self.isDone(fsm) \
            and self.scenario[self.sceIdx]["Done"] in [True,'Sleep']):
            return True
        return False
    def tobeResumed(self,fsm):
        if not self.sceIdx < 0 \
           and self.scenario[self.sceIdx]["Done"] == False:
            return True
        return False


def test_scenario(sm):
    print("\nSimple test scenario for GPCAlgGlobFSM SMC-State Machine")
    jM = GPC_jobManagement(sm)
    jmFSM = jM.fsm
    jmFSM.memory['Buffer'].append([(1,sm),scenarioJob])
    jmFSM.memory['Buffer'].append([(2,sm),readConfigJob])
    jmFSM.memory['Buffer'].append([(3,sm),MPCzLifeJob])
    while jmFSM.current_state != 'END':
        jmFSM.process(None)
        if jmFSM.current_state == 'Idle':
            sleep(0.05)


if __name__ == "__main__":

    # Setting up the logging handlers.
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    GPClogRF = logging.handlers.RotatingFileHandler(
                    filename='GPC.log', mode='a',
                    backupCount=10, maxBytes=1000000 )
    GPClogRF.setLevel(logging.DEBUG)
    GPCAlglogRF = logging.handlers.RotatingFileHandler(
                    filename='GPCAlgo.log', mode='a',
                    backupCount=10, maxBytes=1000000 )
    GPCAlglogRF.setLevel(logging.DEBUG)
    logging.getLogger("apscheduler").addHandler(ch)
    logging.getLogger("Control").addHandler(ch)
#    logging.getLogger("Control.MPCAlgos").addHandler(ch)
    logging.getLogger("Control.MPCAlgos").addHandler(GPClogRF)
    logging.getLogger("Control.MPCAlgos").setLevel(logging.DEBUG)
    logging.getLogger("Control").addHandler(GPCAlglogRF)
    logging.getLogger("Control").setLevel(logging.DEBUG)
    logging.getLogger("handleConfig").addHandler(ch)
    logging.getLogger("handleConfig").addHandler(GPClogRF)
    logging.getLogger("handleConfig").setLevel(logging.DEBUG)
    logging.getLogger("handleLifeCounter").addHandler(ch)
    logging.getLogger("handleLifeCounter").addHandler(GPClogRF)
    logging.getLogger("handleLifeCounter").setLevel(logging.INFO)
    logging.getLogger("GPCAlgGlobProc").addHandler(ch)
    logging.getLogger("GPCAlgGlobProc").addHandler(GPClogRF)
    logging.getLogger("GPCAlgGlobProc").setLevel(logging.DEBUG)

    # Initialize and start the GPC System
    sm = GPCAlgGlobFSM(debugFlag=True,configFile=config.GPCConfFile)
    sm.start()
    test_scenario(sm)
