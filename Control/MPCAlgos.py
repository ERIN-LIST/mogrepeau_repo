""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

from os import path

import logging
#from datetime import now # DF ImportError: cannot import name now
from datetime import datetime
from dateutil import parser
from collections import defaultdict, deque
from utilities.GPCStateUtilities import getBModeVars
from ReadWriteDataTest.handleConfig import readGPCConfig
from GPCVariablesConfig import GPC_Stations, GPC_OutVars
from utilities.opcVarHandling import opcVar
import pickle

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

logging.getLogger(__name__).addHandler(NullHandler())
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Dummy(object):
    def __init__(self,*args,**kwds):
        pass
    def updateBasinConf(self,*args,**kwds):
        C_Switch = defaultdict(list)
        return C_Switch
    def run(self,*args,**kwds):
        pass


import numpy as np
import numpy.ma as ma
import math
import cvxpy
from CheckNetworkConfig import CheckNetworkConfig, handleOptionalSinks, handleBypassedCascades
from copy import deepcopy



class Opti(object):
    """
    Algo class to control tanks with the proposed global predictive control approach.
    This network structure is still hard coded
    """

    # Network config HARD CODED
    #Source, Sink, Status, Vmin (m3), Vmax (m3)
    _B_cf = { 'Provider':{'Source':set(['Provider']), 'Sink':set([]), 'Status':'p', 'Vmin':np.NaN, 'Vmax':np.NaN},
              'Mousel':{'Source': set([]), 'Sink':set([]), 'Status':None, 'Vmin':None, 'Vmax':None},
              'Sauer':{'Source':set([]), 'Sink':set([]), 'Status':None, 'Vmin':None, 'Vmax':None},
              'Alzette':{'Source': set([]),'Sink':set([]), 'Status':None, 'Vmin':None, 'Vmax':None},
              }
    CStateMap = {'offline':'a','maintenance':'a','controllable':'cabl','controlled':'c'}

    #Consumption Areas
    Area=set(['Mittal',
              'Redange',
              'Esch'])
#    Check the coherence of the network configuration


    # Filename used for pickeling persistent data in case of a crash or stop of GPC.
    persistentFileName = 'MPCAlgos.Opti_persistent.pkl'




    def __init__(self,conf,sysVars=None,stateVars=None,outVars=None):
        self.conf = conf
        self.verbose_solver = False #The default config for solver verbosity
        if self.conf.get('SolverVerbos',0) > 0:
            self.verbose_solver = True

        self._getPersistentData()
        self._update_CFWeight(self.conf['CostFunctionWeights'])
        self.readBConfig(stateVars) #Check return value (True or error level details)
        if self.BcfChecks != True:
            raise RuntimeWarning('There is an inconsistency in the water network configuration')

        # Pay Attention : ControlledTanks must be in the same order that they are in ConfigTanks
        self.ConfigTanks = [x for x in self.B_cf if self.B_cf[x]['Status'] in ['c','a','b','o']]
        self.ControlledTank = [x for x in self.ConfigTanks if self.B_cf[x]['Status'] in ['c'] ]
        self.Actuator = []
        for tk in self.ConfigTanks:
            Src = self.B_cf[tk]['Source']
            if Src is None:
                self.Actuator.append('...' + ' ---> ' + tk)
            else :
                for src in Src:
                    self.Actuator.append(src + ' ---> ' + tk)
#                    self.idx_VARcont = np.hstack((self.idx_VARcont,(tk in self.ControlledTank)*np.ones(len(Src),dtype='bool')))




        self.NbTank=len(self.ConfigTanks)
        self.NbContTank=len(self.ControlledTank)
        self.idx_TKcont = np.array([k in self.ControlledTank  for k in  self.ConfigTanks])

        self.idx_VARcont = np.array(self.Actuator,dtype='bool')
        for idx,val in enumerate(self.Actuator):
            if val.split(' ---> ')[1] not in self.ControlledTank:
                self.idx_VARcont[idx] = 0


        # get some parameter defaults for config files
        # GSc-ToDo: this parameters should be handled using a common approach (using a specific class)
        self.DailyMeanHorizon = [self.BConf[GPC_Stations[x]]['Tree']['Global']['DailyMeanHorizon'] \
                                 for x in self.ConfigTanks]

        self.SPCalcType = [self.BConf[GPC_Stations[x]]['Tree']['Global']['SPCalcType'] \
                           for x in self.ConfigTanks]

# only use for simulation if we do not want to change the ini files
#        self.DailyMeanHorizon = [2,2,2]
#        self.SPCalcType = [1,1,1]

        # perform other initialisations
        self.zInit()
        self.set_AlgState(stateVars)

        ### Update self.OUT and self.zS[0]
        self.updateAlgHistory(sysVars)

        self.N_decvar = len(self.Actuator)
        self.setVolumes(sysVars,stateVars)

        self.reservedCapacity = self.conf['ReservedCapacity']
        self.initDay(dayChange=False)
        self.setOPCVarSetpoint(outVars)
        if self.persistentData != None:
            self.LastIN = self.persistentData['LastIN']
        else:
            self.LastIN = np.zeros((self.N_decvar,1)) #only for Test, should be removed afterwards

        #All persistent data is used for the init and should not be used later in any cycle.
        self.persistentData = None

        #-----------------------------------------------------------------------------#
        #-------------------------Problem Formulation---------------------------------#
        #-----------------------------------------------------------------------------#
        #--- Fixed Matrices                                ---------------------------#
        #--- as long as the network structure does not change ------------------------#


        #--- Decision Variables-----------------------#
        # NbTanks first variables represents the min-max normalized tank's inflow (i.e. 0-->valve closed [0 m3] ;  1-->valve fully opened [Qmax m3])
        # followed by 2 groups of slack variables (emergency volume end, Vmin/Vmax_violation)
        self.x = cvxpy.Variable(self.N_decvar+2*self.NbTank,1,name='x')



        # Hard constraints: 0<inflow<1

        self.constr_cf = ma.hstack([self.x[kk]>=0 for kk in range(self.N_decvar)])
        for kk in range(self.N_decvar) :
            self.constr_cf = ma.hstack((self.constr_cf, self.x[kk]<=1))



    def _getPersistentData(self):
        self.persistentData = None
        if path.exists(self.persistentFileName):
            age = datetime.now() - datetime.fromtimestamp(path.getmtime(self.persistentFileName))
            if age.total_seconds() > 30*60: # persistent file older than 30min (2 normal cycles)
                logger.info("Info: persistent datafile too old (not loaded): %s" % (age,))
            else:
                try:
                    fh = open(self.persistentFileName,'rb')
                    data = pickle.load(fh)
                    fh.close()
                except:
                    logger.error("Error in loading persistent datafile")
                    return
                finally:
                    if isinstance(fh,file) and not fh.closed:
                        fh.close()

                if set(data.keys()) ^ set(['zS','Vo','LastIN','zS_Zarea']) != set():
                    logger.error("Error: content of pesistent datafile is not conform:\n %s" % (data,))
                else:
                    logger.info("Info: persistent datafile loaded:\n %s" % (data,))
                    self.persistentData = data

    def _setDailyCons(self):
        """Calculate the basin specific daily consumption based on the specified horizon"""
        DailyMeanHorizon = [int(di) for di in self.DailyMeanHorizon] # in case the variable from opc is float.
        #GSc-ToDo: if DailyMeanHorizon parameter is float what to do in case of 1.5 for example

        t = np.ma.array(list(self.zS)[1:max(DailyMeanHorizon)+1]) #zS[0] is the current day
        m = np.isnan(t.data) #as zS is initalized with nan this needs to be masked
        #build the daily horizon mask
        ix = np.arange(1, t.shape[0]+1)
        dmh = np.repeat(np.c_[DailyMeanHorizon].T, max(ix), axis=0)
        t.mask = (np.repeat(np.c_[ix], self.NbTank, axis=1) > dmh) | m
        #GSc-ToDo: here another customizable aggregation method could be used.
        #calculate the mean of masked array
        self.DCons = t.mean(axis=0).tolist()

        t = np.ma.array(list(self.zS_Zarea)[1:max(DailyMeanHorizon)+1]) #zS[0] is the current day
        m = np.isnan(t.data) #as zS is initalized with nan this needs to be masked
        #build the daily horizon mask
        ix = np.arange(1, t.shape[0]+1)
        dmh = np.repeat(np.c_[DailyMeanHorizon].T, max(ix), axis=0)
        t.mask = (np.repeat(np.c_[ix], self.NbTank, axis=1) > dmh) | m
        #GSc-ToDo: here another customizable aggregation method could be used.
        #calculate the mean of masked array
        self.DCons_Zarea = t.mean(axis=0).tolist()

    def readBConfig(self,stateVars=None,toUpdate=None):
        if stateVars == None and toUpdate == None:
            return
        elif stateVars != None and toUpdate != None:
            logger.error("readBConfig is called with bad parameters: both stateVars and toUpdate are specified.")
            return
        elif stateVars != None: #During init process of Opti
            logger.debug("readBConfig (%s): stateVars provided", datetime.now())
            BModeVars = getBModeVars(stateVars)
            B_cf = deepcopy(self._B_cf)
        elif toUpdate != None: #During gpc running if state/config change.
            logger.debug("readBConfig (%s): update provided - %s", datetime.now(), toUpdate)
            BModeVars = ["%s.%s_BZ" % (sti,sti) for sti in toUpdate.iterkeys()]
            B_cf = deepcopy(self.B_cf)
        else:
            logger.error("readBConfig is called with impossible parameters")
            return

        StiMap = dict([reversed(i) for i in GPC_Stations.items()])
        Stis = StiMap.keys()
        affectedArea = self.Area
        if toUpdate != None:
            Stis = toUpdate.keys()
            affectedArea = set()
        resetToConfig = set()
        for sti in Stis:
            if sti in ['S0', 'S98', 'S99']: continue
            vsti = "%s.%s_BZ" % (sti,sti)
            stid = int(sti.strip('S'))
            ## First read and store the config.
            try:
                bcf = self.BConf
            except AttributeError:
                self.BConf = {sti:None}
                bcf = self.BConf
            #Update the affected Areas using the previous working mode if available
            if sti in bcf and bcf[sti] != None: #do this only during runtime not in the init state.
                vi = self.B_cf[StiMap[sti]]['CBZ']
                affectedArea |= bcf[sti]['Tree']['Betriebszustaende'][vi]['Sink']
            c,cval = readGPCConfig(path.join('..','Control','Behaelter_%d.ini'%(stid,)))
            if c['Global']['BId'] == stid: # Additional checks could be added here.
                bcf[sti] = dict(zip(("Tree","Valid"),(c,cval)))
            else:
                logger.debug("%s: Missmatch between Basin filename and internal BId\n -> config not used!" % (sti,))
                continue
            ## Check the basin default parameters that may need to be overwritten by global values
            for param in ['DailyMeanHorizon', 'SPCalcType']:
                if param in bcf[sti]['Tree']['Global'].defaults\
                   and bcf[sti]['Tree']['Global'][param] != self.conf[param]:
                    bcf[sti]['Tree']['Global'][param] = self.conf[param]
            ## Now use the basin mode state to configure the current network.
            if vsti in BModeVars:
                if stateVars != None:
                    vi = stateVars[vsti].value
                else:
                    vi = toUpdate[sti]
            else:
                vi = None
            if vi == None:
                vi = c['Global']['DefaultBZ']

            #Check the usability of the configuration and current state
            if cval !=True :
                if cval['Betriebszustaende'] == False:
                    logger.debug("Error in Basin '%s' ini-File in part %s.\n -> config not used!" % (sti,"Betriebszustaende") )
                    continue
                elif cval['Betriebszustaende'].get(vi,False) != True:
                    if vi not in cval['Betriebszustaende']:
                        logger.debug("Error in Basin '%s' ini-File - part '%s' not existing.\n -> config not used!" % (sti,vi) )
                        continue
                    cvali = cval['Betriebszustaende'][vi]
                    if not all([cvali[ki] for ki in ['Source', 'Sink', 'Status']]):
                        logger.debug("Error in Basin '%s' ini-File in part %s.\n -> config not used!" % (sti,vi) )
                        continue

            if toUpdate != None: #The network structure is updated (not newly created)
                #Store the (previous) configured BZ and update the affected areas
                bzOld = B_cf[StiMap[sti]]['CBZ']
                affectedArea |= c['Betriebszustaende'][bzOld]['Sink']
                bcfSOld = B_cf[StiMap[sti]]['Source']
                ConfSOld = c['Betriebszustaende'][bzOld]['Source']
                if ConfSOld not in ["",None]:
                    # Put the current basin into the list of the to be reconfigured structures
                    resetToConfig.add(StiMap[sti])
                    # Remove the affected areas from the old configured Source
                    B_cf[ConfSOld]['Sink'] -= affectedArea
                if bcfSOld not in ["",None]:
                    #Remove the basin from the previous Source's Sinks
                    B_cf[bcfSOld]['Sink'] -= set([StiMap[sti],])
                handleOptionalSinks(B_cf,B_cf[StiMap[sti]],Stis,resetToConfig,affectedArea)

            #Specify the the new network specification of this basin
            spec = deepcopy(c['Betriebszustaende'][vi])
            #Update spec with additional and the runtime keys
            spec['CBZ'] = vi
            spec['OptionSinkBehaelter'] = c['Global']['OptionSinkBehaelter']
            if 'CState' in B_cf[StiMap[sti]]:
                spec['CState'] =  B_cf[StiMap[sti]]['CState']
            #Check for bypassed cascades
            if toUpdate != None and spec['Status'] != 'o': #ToDo the chef of offline is because the source is '' this case -> key error
                handleBypassedCascades(B_cf,spec,resetToConfig)
            #Store new specification
            B_cf[StiMap[sti]] = spec

        while resetToConfig:
            bi = resetToConfig.pop()
            sti = GPC_Stations[bi]
            stid = int(sti.strip('S'))
            CBZbi = B_cf[bi]['CBZ']
            cbi = bcf[sti]['Tree']
            spec = deepcopy(cbi['Betriebszustaende'][CBZbi])
            #Update spec with additional and the runtime keys
            spec['CBZ'] = CBZbi
            spec['OptionSinkBehaelter'] = cbi['Global']['OptionSinkBehaelter']
            if 'CState' in B_cf[bi]:
                spec['CState'] =  B_cf[bi]['CState']
            B_cf[spec['Source']]['Sink'] -= spec['Sink']
            affectedArea |= spec['Sink']
            B_cf[bi] = spec
            handleBypassedCascades(B_cf,spec,resetToConfig)
            handleOptionalSinks(B_cf,spec,Stis,resetToConfig,affectedArea)

        ## Rebuild the Sinks of the providers after reading the complete network configuration.
        self.Providers = [si for si in B_cf if B_cf[si]['Status'] =='p']
        logger.debug("DebugInfo: Providers:%s;\n       AffectedAreas: %s" % (self.Providers, affectedArea))
        for t in B_cf:
            for ss in B_cf[t]['Source']:
                if ss not in self.Providers: continue
                if t in self.Providers:
                    B_cf[t]['Sink'] -= affectedArea
                    continue
                B_cf[ss]['Sink'].add(t)

        self.BcfChecks = CheckNetworkConfig(B_cf, self.Area)
        self.B_cf = B_cf
        return self.BcfChecks



    def updateMatrixA(self):



        # Obj 1. Homogenous self-sufficiency
        AB_mask = np.ma.copy(self.asp)
        AB_mask.mask = False
        AB_mask.mask[np.ix_(~self.idx_TKcont,~self.idx_VARcont)]=True
        AB_mask = ma.mask_rowcols(AB_mask)


#        # DF 'SIDERE' or self.Providers ?? case when there are many providers ???
        idxp = [idx for idx,val in enumerate(self.Actuator) if val.split(' ---> ')[0] == 'Provider']
        AB_mask[:,idxp] -= np.c_[self.AutoRepart]
        Vect = ~AB_mask.any(axis=1).mask # same that self.idx_TKcont ???
        AB_mask = AB_mask.compress(Vect.flatten(),axis=0)

        self.Ahom = np.dot( AB_mask, np.diag(self.QMax) )

        ahom_tmp = np.hstack([self.Ahom.filled(0),
                              np.zeros((self.NbContTank,2*self.NbTank))])
        AX_hom = self.ScHom*ahom_tmp*self.x
        del ahom_tmp


        # Obj 2. Reach setpoint
        Asp = np.dot( self.asp, np.diag(self.QMax) )
        Asp = Asp.compress(Vect.flatten(),axis=0)


        asp_tmp = np.hstack([Asp.filled(0),
                             np.zeros((self.NbContTank,2*self.NbTank))])
        self.WeightSP = cvxpy.Parameter(1,name='Wsp',sign="positive")
        AX_sp = self.WeightSP*asp_tmp*self.x
        del asp_tmp

        # Obj 3.1 Respect minimal volume [end of the prediction horizon] (slack variables)
        avolmin = np.hstack([    np.zeros((self.NbContTank,self.N_decvar)),
                                 self.Aemergres,
                                 np.zeros((self.NbContTank,1*self.NbTank))])
        AX_volmin = self.ScEmerg*avolmin*self.x
        del avolmin


        # Obj 3.2 Respect minimal/maximal volume [nest step] (slack variables)
        avolrge = np.hstack([    np.zeros((2*self.NbContTank,self.N_decvar)),
                                 np.zeros((2*self.NbContTank,1*self.NbTank)),
                                 np.tile(self.VolRange,(2,1))])
        AX_volrge = self.ScVolRge*avolrge*self.x
        del avolrge



        self.AX = cvxpy.vstack(AX_hom, AX_sp, AX_volmin, AX_volrge)





    def zInit(self):
        """
        Method where the historical consumptions are initalized
        """
        if self.persistentData != None:
            self.zS = self.persistentData['zS']
            self.zS_Zarea = self.persistentData['zS_Zarea']
            self._setDailyCons()
            return
        ## MeanDailyConsumption: is ordered according to the attributed basin number B1 == Laangwiss == S1 in GPC_Stations
        #ToDo: get history of daily consumptions from the Victory Archive files (CSV-Format).
        _MeanDC = self.conf['MeanDailyConsumption']
        _MDC_Ord = self.conf['MDC_Order']
        MeanDC = [np.nan,]*self.NbTank
        for bi in self.ConfigTanks:
            _idx = _MDC_Ord.index(GPC_Stations[bi])
            idx = self.ConfigTanks.index(bi)
            MeanDC[idx] = _MeanDC[_idx]
        if 'ConsProfile' in self.conf:
            profile = np.array(self.conf['ConsProfile'])/24.
        else:
            profile = np.ones(24)/24. #Solution with no profile in the config file
        zSInit = np.array(MeanDC) * sum(profile[:datetime.now().hour]) #
        zS_ZareaInit = np.array(MeanDC) * sum(profile[:datetime.now().hour]) #

        # The daily consumption is gathered up to the max (see config spec files) of DailyMeanHorizon
        maxDays = 365 #Attention 365 is hard coded here so if spec is modified this need to be modified.
        zS = deque(maxDays*[[np.nan,]*self.NbTank,],maxDays)
        zS_Zarea = deque(maxDays*[[np.nan,]*self.NbTank,],maxDays)
        # The current Day (idx 0) is initialized with the configured profile up to the current moment.
        # and only one historic day (idx 1) is initialized with configured mean values in order not to bias the system to much (difference from config and real consumptions)
        zS[0] = zSInit.tolist()
        zS[1] = MeanDC
        self.zS = zS
        zS_Zarea[0] = zS_ZareaInit.tolist()
        zS_Zarea[1] = MeanDC
        self.zS_Zarea = zS_Zarea
        self._setDailyCons()



    def initDay(self, dayChange=True, zLifeD=None):
        """
        Method used to initialize / update all attributes at the moment of day-change
        - Setpoint, V(0) at beginning of day ...
        This method is also used at MPCAlgo initialization
        """
        potentialDeltaDays = [1,-27,-28,-29,-30]
        if isinstance(zLifeD, tuple):
            #Handle the case of zLife OPC timestamp based day-change
            if zLifeD.LocalDT.day - (zLifeD.LocalDT - zLifeD.TimeDiff[0]).day in potentialDeltaDays:
                dayChange = True
            else:
                return False
        elif isinstance(zLifeD, opcVar):
            #Handle the case of an explicit OPC datetime variable based approach
            TMinus1 = zLifeD.getCached('Latest').Value
            if TMinus1 and \
               zLifeD.value.day - TMinus1.day in potentialDeltaDays:
                dayChange = True
            else:
                return False
        elif zLifeD == None and dayChange == True:
            return False
        elif zLifeD != None:
            return False

        if self.persistentData != None:
            self.Vo = self.persistentData['Vo']
        else:
            self.Vo = self.VOL.copy()

        if dayChange:
            # Shift and reset the cumulated consumption value since the beginning of the day

            self.zS.appendleft([0,]*self.NbTank)
            self.zS_Zarea.appendleft([0,]*self.NbTank)
            self._setDailyCons()

#        self.OUTpred = np.array(self.DCons)*self.unitConv['x/d']
        print "keep both ? OUTpred and DCons_Zarea ?"#OUTpred is similar to DCons_Zarea with different unit"
        self.OUTpred = np.array(self.DCons_Zarea)*self.unitConv['x/d']

        self.updateSP(doUpdMA=dayChange)

        return dayChange


    def updateSP(self,doUpdMA=False):
        """
        This method is used to calculate the new setpoint
        - doUpdMA is used to also run an update of the A matrix of the optimization problem.
        """
        #GSc-ToDo: Implement here a flexible way to calculate the SP
        SP = list()
        SPCalcType = self.SPCalcType
        if not isinstance(SPCalcType, list): # only one setting for all basins
            SPCalcType = [self.SPCalcType,]*self.NbTank
        # For all the Calculation types the SP is build and append to in ascend order
        for SPCTi in set(SPCalcType):
            if SPCTi == 1: #Autonomy based
                SP.append(self.NbrAutoDays*self.DCons+self.VResMin)
            elif SPCTi == 2: #Retention time based
#                 _MDC_Ord = self.conf['MDC_Order']
#                 VInMax = self.QMax/self.unitConv['x/h']*2
#                 VConsMax = self.conf['MaxPickConsumption']
#                 #Bring VConsMax into the self.ConfigTanks order
#                 VConsMax = [VConsMax[_MDC_Ord.index(GPC_Stations[bi])] for bi in self.ConfigTanks]
#                 VRes = self.VResMin-VInMax+VConsMax
#                SP.append(self.NbrAutoDays*self.DCons+VRes) #to be defined
                SP.append(self.NbrAutoDays*self.DCons) # Absolute retention time
            else:
                ValueError("Parameter 'Setpoint calculation type' == %s has an not handled value" % (SPCTi,))
        #Select for each basin the specified SP according to the calculation type.
#DF : doesn't work if SPCalcType contains only 2
        self.SP = np.choose(np.array(SPCalcType)-1,SP)
#        self.SPbkup=np.copy(self.SP)
#        print "SP Saturation --> To do put in log"
#        self.SP=np.where(self.SP > 0.9*self.VMax, 0.9*self.VMax, self.SP)
        logger.debug("MPCAlgos (%s): SP = %s", self.DZ, self.SP)

        self.AutonomVol = self.NbrAutoDays*self.DCons
        self.AutoRepart = self.AutonomVol/np.sum(self.AutonomVol[self.idx_TKcont])

        if doUpdMA:
            self.updateMatrixA()


    def _update_CFWeight(self,cfW):
        self.ScSP = cfW['ReachSP'][0]
        self.ScHom = cfW['RelVolumeHomogenity'][0]
        self.ScEmerg = cfW['EmergancyReserve'][0]
        self.ScVolRge = cfW['VolRange'][0]


    def updateConf(self,conf):
        if 'ControlTimeperiod' in conf and self.tUpdate != conf['ControlTimeperiod']:
            logger.warning('Changing "ControlTimeperiod" is currently not supported')

        self.conf = conf

        # weighting coefficients
        self._update_CFWeight(conf['CostFunctionWeights'])
        self.updateMatrixA()

        if conf.get('SolverVerbos',0) > 0:
            self.verbose_solver = True
        else:
            self.verbose_solver = False


    def updateBasinConf(self, gpcSysState, updateStruct=False):
        #ToDo-GSc: parameters conf and sysVars are only needed until MPCAlgo can correctly handle reconfigurations without a complete initialization.
        C_Switch = defaultdict(list)
        StiMap = dict([reversed(i) for i in GPC_Stations.items()])
        for sti in gpcSysState:
            Bi = StiMap[sti]
            if self.B_cf.has_key(Bi):
                Bi_cf = self.B_cf[Bi]
                if 'CState' not in Bi_cf: # only after init of algo
                    Bi_cf['CState'] = self.CStateMap[gpcSysState[sti].split(':')[0]]
                    updateStruct = True
                if gpcSysState[sti] in ['offline','maintenance'] and Bi_cf['CState'] == 'c':
                    # Nothing to do on System level as this is of higher order
                    Bi_cf['CState'] = self.CStateMap[gpcSysState[sti]]
                    updateStruct |= True
                elif gpcSysState[sti] in ['controllable',] and Bi_cf['Status'] == 'c':
                    if Bi_cf['CState'] in ['a','cabl']:
                        C_Switch['C-abl -> C'].append(sti)
                        Bi_cf['CState'] = 'c'
                        updateStruct |= True
                    elif Bi_cf['CState'] == 'c':
                        logger.warning("MPCAlgo-warning: B_cf[%s]['CState'] is 'c' but SysGPCState is %s" % (sti,gpcSysState[sti]))
                        C_Switch['C-abl -> C'].append(sti)
                        # On GPC level no updateStruct needed as Bi_cf is already set to 'c'.
                elif gpcSysState[sti] in ['controllable',] and Bi_cf['Status'] == 'a':
                    logger.warning("MPCAlgo-warning: Missmatch ob System and config level B_cf[%s]['Status'] is 'a' but SysGPCState is %s" % (sti,gpcSysState[sti]))
                    # Nothing to do on System level as this is of higher order
                    if Bi_cf['CState'] in ['c','cabl']:
                        Bi_cf['CState'] = 'a'
                        updateStruct |= True
                elif gpcSysState[sti].split(':')[0] == 'controlled' and Bi_cf['Status'] == 'a':
                    if Bi_cf['CState'] in ['cabl','c']:
                        # Basin Mode change can produce this state.
                        logger.warning("MPCAlgo-warning: Uncoherent Basin config and system behavior - B_cf[%s]['Status'] is 'a' but SysGPCState is %s" % (sti,gpcSysState[sti]))
                        C_Switch['C -> C-abl'].append(sti)
                        Bi_cf['CState'] = 'a'
                        updateStruct |= True
                    elif Bi_cf['CState'] == 'a':
                        #This should newer happon! But is possible in some strange restart situations.
                        logger.error("MPCAlgo-error: B_cf[%s]['CState'] is 'a' but SysGPCState is %s" % (sti,gpcSysState[sti]))
                        C_Switch['C -> C-abl'].append(sti)
                elif gpcSysState[sti].split(':')[0] == 'controlled' and Bi_cf['Status'] == 'c':
                    if Bi_cf['CState'] in ['a','cabl']:
                        # Systate OPC variable was set by external to controlled (should not happon)
                        logger.warning("MPCAlgo-warning: external process wrote controlled to OPC variabl - B_cf[%s]['CState'] is '%s' but SysGPCState is %s" % (sti,Bi_cf['CState'],gpcSysState[sti]))
                        Bi_cf['CState'] = 'c'
                        updateStruct |= True

        if updateStruct:
            #--- Update Matrix -----------------------#
            self.ControlledTank = [x for x in self.ConfigTanks if self.B_cf[x]['CState'] in ['c'] ]
            self.NbContTank=len(self.ControlledTank)
            self.idx_TKcont = np.array([k in self.ControlledTank  for k in  self.ConfigTanks])

            self.idx_VARcont = np.array(self.Actuator,dtype='bool')
            for idx,val in enumerate(self.Actuator):
                if val.split(' ---> ')[1] not in self.ControlledTank:
                    self.idx_VARcont[idx] = 0

            if self.NbContTank > 0:
                self.updateStructOptPB()

        return C_Switch



    def updateStructOptPB(self): # only use if status has changed between "a" and "c"
        logger.debug( "Controlled Tanks: %s" % (self.ControlledTank,) )

        a_cf = np.zeros((self.NbTank, len(self.Actuator)))

        for idx,val in enumerate(self.Actuator):
            Tkact = val.split(' ---> ')
            if Tkact[0] not in self.Providers and Tkact[0] != '...':
                a_cf[self.ConfigTanks.index(Tkact[0]),idx] = -1
            if Tkact[1] in self.ControlledTank: # iterate on ConfigTanks ?
                a_cf[self.ConfigTanks.index(Tkact[1]),idx] = 1

        # Goal : homogeneous self-sufficiency
        self.AutoRepart = self.AutonomVol / np.sum(self.AutonomVol[self.idx_TKcont])

        # Goal : reach the setpoint at the end of the day
        # ONLY IF EACH TANK HAS ONLY ONE SOURCE
        Uncont_TF = np.array([x not in self.ControlledTank for x in self.ConfigTanks])
        # IF ONE OR SEVERAL TANK HAS MORE THAN ONE SOURCE
#        print "hard coded --> must be changed"
#        Uncont_TF = np.zeros(self.N_decvar,dtype=bool)
#        Uncont_TF[np.array([2,8])]=1

        # Goal : reach the setpoint at the end of the day
#        N_Hp = cvxpy.Parameter(1,name='N_Hp',sign="positive")
#        asp = np.hstack([    a,       np.zeros((self.NbTank,self.NbTank)) ])
#        AX_sp = N_Hp*asp*x
#        del asp
        self.asp = ma.array(a_cf)

#        Source = set([self.B_cf[x]['Source'] for x in self.B_cf] )
#        self.TankAsSource = set(self.ConfigTanks) & Source
#        if self.TankAsSource:
#            for i in self.TankAsSource:
#                if self.B_cf[i]['Status'] != 'c' :
#                    continue
#                DestTk = self.B_cf[i]['Sink'] & set(self.ControlledTank)
#                for j in DestTk :
#                    s = self.ConfigTanks.index(i)
#                    d = self.ConfigTanks.index(j)
#                    self.asp[s,d] =-1

        self.asp.mask = False
        self.asp.mask[0,:]= Uncont_TF
        self.asp = ma.mask_cols(self.asp)
        Asp = np.dot( self.asp, np.diag(self.QMax) )
        Asp = Asp.compress(self.idx_TKcont,axis=0)

#        self.AspX = cvxpy.matrix(Asp.filled(0))*self.x[0:self.NbTank,0]
        self.AspX = Asp.filled(0)*self.x[0:self.N_decvar]

#        # Goal (soft constraints) : Vo-eps < V < SP+eps
#        self.Arge = np.identity(2*self.NbTank)
#        self.Arge = self.Arge.compress(np.hstack([self.idx_TKcont,self.idx_TKcont]),0)

        # Goal : (soft constraints) : Vmin < V +eps
        self.Aemergres = np.identity(self.NbTank)
        self.Aemergres = self.Aemergres.compress(self.idx_TKcont,0)

        # Goal : (soft constraints) : Vmin < V +eps; Vmax>V-eps
        self.VolRange = np.identity(1*self.NbTank)
        self.VolRange =  self.VolRange.compress(self.idx_TKcont,0)



        self.updateMatrixA()


        # update the mask affected the constraints
        self.constr = self.constr_cf # need deep copy ?
        self.constr.mask = np.tile(Uncont_TF,(1,2))
        self.constr = list(self.constr.compressed())




        # hard constraint: sum(flow_fromSIDERE)<VresSIDERE
        #ts_p represents a mask for the Tanks supplied by the Provider
        ts_p = np.zeros((self.NbTank,1))
        for idx, val in enumerate(self.ControlledTank):
            if 'Provider' in self.B_cf[val]['Source']:
                ts_p[self.ConfigTanks.index(val)] = self.QMax[self.idx_VARcont][idx]
        self.ts_pX = ts_p.T*self.x[0:self.N_decvar,0]


        #slack variables only applied on controlled tanks
        Svmat = np.diag(self.idx_TKcont.astype(int)).compress(self.idx_TKcont,axis=0)
#        self.ts_s1 = Svmat*self.x[self.NbTank:2*self.NbTank,0]
        self.ts_s1 = Svmat*self.x[self.N_decvar:(self.N_decvar+self.NbTank),0]
        self.ts_sV = Svmat*self.x[(self.N_decvar+self.NbTank):(self.N_decvar+2*self.NbTank),0]
        self.ts_sRV = Svmat*self.x[(self.N_decvar+1*self.NbTank):,0]



        #Update some boolean selection arrays
        UnControlledTank = list(set(self.ConfigTanks) - set(self.ControlledTank))
        self.idx_uncontSrcP = np.array([k in UnControlledTank and self.B_cf[k]['Source'] is not None and 'Provider' in self.B_cf[k]['Source'] for k in  self.ConfigTanks])

#        if any(idx_uncont): # is needed because nansum([]) gives nan while sum([]) gives 0
#            self.Vres_uncontrolledTank = np.nansum( self.VdMax[idx_uncont])
#        else:
#            self.Vres_uncontrolledTank = 0.0



    def updateAlgHistory(self,sysVars):
        ### extension to multi-tanks : Temporaly Hard coded
        #['Sauer', 'Alzette', 'Mousel']
        sTmp = "S0{0}.S0{0}_C0{1}_T"
        CountDiff = lambda sti,ki: sysVars[sTmp.format(sti,'%d'%ki if ki else '')].getDiff()
        CountVal = lambda x: x.Diff[0] if getattr(x,'Diff',False) else np.nan


        OUTS = CountVal(CountDiff(2,2))
        OUTA = CountVal(CountDiff(3,2))
        OUTM = CountVal(CountDiff(1,2)) + CountVal(CountDiff(1,3))
        self.OUT = np.hstack((OUTS, OUTA, OUTM))

        ZAreaS = CountVal(CountDiff(2,2))
        ZAreaA = CountVal(CountDiff(3,2))
        ZAreaM = CountVal(CountDiff(1,2))
        self.ZArea = np.hstack((ZAreaS, ZAreaA, ZAreaM))

        sTmp0 = "S0{0}.S0{0}_C0{1}_T0"
        DayVol = lambda sti,ki: (sysVars[sTmp.format(sti,'%d'%ki if ki else '')].value - sysVars[sTmp0.format(sti,'%d'%ki if ki else '')].value)

        OUTS = DayVol(2,2)
        OUTA = DayVol(3,2)
        OUTM = (DayVol(1,2) + DayVol(1,3))
        DOUT = np.hstack((OUTS, OUTA, OUTM))

        ZAreaS = DayVol(2,2)
        ZAreaA = DayVol(3,2)
        ZAreaM = DayVol(1,2)
        DZArea = np.hstack((ZAreaS, ZAreaA, ZAreaM))

        self.zS[0] = DOUT;#ToDo: needs to be adapted if S0_tUpdate is not synchronized with the Day Change.
        self.zS_Zarea[0]  = DZArea


        #Init/Update self.zd
        #['Sauer', 'Alzette', 'Mousel']
        ZDS = DayVol(2,1)
        ZDA = DayVol(3,1)
        ZDM = DayVol(1,1)
        self.zd = np.hstack((ZDS, ZDA, ZDM))





    def set_AlgState(self,stateVars):
        """Initalize Sys-State specifc Algo Data"""
        self.DZ = stateVars["S98.S98_DateTime"].value
        if 'ControlTimeperiod' in self.conf:
            self.tUpdate = self.conf['ControlTimeperiod']
        else:
            self.tUpdate = stateVars["S0.S0_tUpdate"].value
        self.unitConv = {'l/s':float(self.tUpdate)/1000} # "*" [l/s] -> [m3/control-period]; "/" [m3/control-period] -> [l/s]
        self.unitConv['l'] = 1./1000  # "*" [l] -> [m3]; "/" [m3] -> [l]
        self.unitConv['x/d'] =self.tUpdate/float(86400)  # "*" [x/d] -> [x/control-period]; "/" [x/control-period] -> [x/d]
        self.unitConv['x/h'] =self.tUpdate/float(3600)  # "*" [x/h] -> [x/control-period]; "/" [x/control-period] -> [x/h]

        #Init/Update self.QMax
        #ToDo : "do automatic mapping between counter and actuator (use GPCVariablesConfig ?)"
        QmaxS = stateVars["S02.S02_C01_QMax"].value
        QmaxA = stateVars["S03.S03_C01_QMax"].value
        QmaxM = stateVars["S01.S01_C01_QMax"].value

#        ['Sauer', 'Alzette', 'Mousel']
        self.QMax = self.unitConv['x/h']*np.hstack((QmaxS, QmaxA, QmaxM))


        _Area = np.pi*np.square(self.conf['Diameter'])/4
        _MDC_Ord = self.conf['MDC_Order']

        #Init/Update self.VMax
        sTmp = "{0}.{0}_K{1}_LMax"
        VMax = []
        for bi in self.ConfigTanks :
            sti = GPC_Stations[bi]
            LMax = stateVars[sTmp.format(sti,1)].value
            _idx = _MDC_Ord.index(sti)
            VMax.append(_Area[_idx]*LMax)
        self.VMax = np.hstack(VMax)

        #Init/Update self.VResMin
        sTmp = "{0}.{0}_K{1}_LResMin"
        VResMin = []
        for bi in self.ConfigTanks :
            sti = GPC_Stations[bi]
            LResMin = stateVars[sTmp.format(sti,1)].value
            _idx = _MDC_Ord.index(sti)
            VResMin.append(_Area[_idx]*LResMin)
        self.VResMin = np.hstack(VResMin)

        #Init/Update self.VdMax
        #ToDo: pay attention in case of tanks that are bypassed or with tanks in cascade
        VdMaxS = stateVars["S02.S02_C01_VdMax"].value
        VdMaxA = stateVars["S03.S03_C01_VdMax"].value
        VdMaxM = stateVars["S01.S01_C01_VdMax"].value
#        ['Sauer', 'Alzette', 'Mousel']
        self.VdMax = np.hstack((VdMaxS, VdMaxA, VdMaxM))
        #ToDo: remove this once this variables are correclty handled.
        if stateVars["S0.S0_VdMax"].value != 0: #ToDo: To remove if the S0_VdMax is correctly handled by the system.
            self.reservedCapacity = stateVars["S0.S0_VdMax"].value

        #Handle the available online parameters (opc variables)
        #GSc-ToDo try to exchange this more fixed coded approach by a specific parameter object with linked (dependant) actions
        # -> see class MPCParamVar (not ready yet)
        doUpdSP = False
        self.NbrAutoDays = np.ones(self.NbTank)*np.nan
        paramVars = set([vi.split('_Param_')[-1] for vi in stateVars if '_Param_' in vi])
        for ti in self.ConfigTanks:
            sti = GPC_Stations[ti]
            i = self.ConfigTanks.index(ti)
            for pi in paramVars:
                vi = "{0}.{0}_Param_{1}".format(sti, pi)
                if vi in stateVars:
                    stateVari = stateVars[vi]
                    if stateVari.getDiff() != None and \
                       stateVari.getDiff().Diff[0] != 0:
                        # Param was modified since last reading.
                        if pi in ['AutonomyFactor', 'VdHistTage', \
                                  'SP_RechenModus']:
                            doUpdSP |= True
                    if pi == 'AutonomyFactor':
                        selfVar = self.NbrAutoDays
                        valDefault = 2 #GSc-ToDo: the default should come from config
                        valRange = [0.1,10] # Hard coded need to be coherent wirh conf and opc specification
                    elif pi == 'VdHistTage':
                        selfVar = self.DailyMeanHorizon
                        valDefault = 1 #GSc-ToDo: the default should come from config
                        valRange = [1,365] # Hard coded need to be coherent wirh conf and opc specification
                    elif pi == 'SP_RechenModus':
                        selfVar = self.SPCalcType
                        valDefault = 1 #GSc-ToDo: the default should come from config
                        valRange = [1,2]
                    else:
                        continue
                    vali = stateVari.value
                    if vali > 0 and valRange[0] <= vali <= valRange[1]:
                        selfVar[i] = vali
                        #GSc-ToDo: find a way to - In DailyMeanHorizon case the DailyMeanHorizonConf should be set to "opc"
                    else:
                        if valRange[0] <= vali <= valRange[1]:
                            logger.error("Parameter out of range error (default used):"+\
                                         " {0}={1} ({2}) {0} <- {3}".format(vi,vali,valRange,valDefault))
                        selfVar[i] = valDefault # Default value could come from config.

        if doUpdSP:
            #Param NbrAutoDays has changed -> update the Setpoint and all related elements.
            self.updateSP(doUpdMA=True)


    def setVolumes(self,sysVars,stateVars):
        """Init/Update self.VOL"""

        _Area = np.pi*np.square(self.conf['Diameter'])/4
        _MDC_Ord = self.conf['MDC_Order']

        sTmp = "{0}.{0}_K{1}_LIst"
        VOL = []
        for bi in self.ConfigTanks :
            sti = GPC_Stations[bi]
            LIst = sysVars[sTmp.format(sti,1)].value
            _idx = _MDC_Ord.index(sti)
            VOL.append(_Area[_idx]*LIst)
        self.VOL = np.hstack(VOL)



    def setOPCVarT0(self,outVars,sysVars):
        TFilter = lambda x: x.endswith('_T')
        for vTi in filter(TFilter,sysVars):
            vT0i = vTi.rstrip('_T')+'_T0'
            outVars[vT0i].setWriteValue(sysVars[vTi].value)

    def setOPCVarAutonomie(self,outVars):
        AutoFilt = lambda x: isinstance(x,dict) and '_Autonomie' in x['GPC']
        value = (self.VOL -self.VResMin)/self.DCons * 24 #in hours
        self._setOPCVars(outVars,AutoFilt,value)

    def setOPCVarSetpoint(self,outVars):
        SPFilt = lambda x: isinstance(x,dict) and 'GPCSetpoint' in x['GPC']
        self._setOPCVars(outVars,SPFilt,self.SP)

        #Calculate LMax/LMin GPC
        _Area = np.pi*np.square(self.conf['Diameter'])/4
        _MDC_Ord = self.conf['MDC_Order']
        _idx = [_MDC_Ord.index(GPC_Stations[ci]) for ci in self.ConfigTanks]
        _Area = _Area[_idx]
        _SP = np.min([self.SP,self.VMax],axis=0)
        LMax = _SP / _Area
        LMin = (_SP - self.VMax*0.1) / _Area
        LMaxFilt = lambda x: isinstance(x,dict) and 'LMax_GPC' in x['GPC']
        self._setOPCVars(outVars,LMaxFilt,LMax)
        LMinFilt = lambda x: isinstance(x,dict) and 'LMin_GPC' in x['GPC']
        self._setOPCVars(outVars,LMinFilt,LMin)

    def _setOPCVars(self,outVars,Filt,values):
        for ci in self.ConfigTanks:
            sti = GPC_Stations[ci]
            gpcVars = filter(Filt, GPC_OutVars.get(sti,[None,]))
            if len(gpcVars) == 0:
                continue
            gpcVi = '.'.join((sti,gpcVars[0]['GPC']))
            if outVars != None and gpcVi in outVars:
                val = values[self.ConfigTanks.index(ci)]
                wvalue = outVars[gpcVi].setWriteValue(val)
                if wvalue == None:
                    #GSc-ToDo: How to react in this case?
                    logger.debug("Set the Setpoint value for '%s' did not work" % (gpcVi))


    def run(self,sysVars,stateVars=None,outVars=None,RUB_IN_Real=None):
        try:
            ### Update State specifc Algo data.
            self.set_AlgState(stateVars)

            ### Update self.OUT and self.zS[0]
            self.updateAlgHistory(sysVars)
            ### Update self.VOL
            self.setVolumes(sysVars,stateVars)



            BStr = "MPCAlgos (%s): " % (self.DZ,)

            #['Sauer', 'Alzette', 'Mousel']
            sTmp = "S0{0}.S0{0}_C0{1}_T"
            CountDiff = lambda sti,ki: sysVars[sTmp.format(sti,'%d'%ki if ki else '')].getDiff()
            CountVal = lambda x: x.Diff[0] if getattr(x,'Diff',False) else np.nan
            # ['Sauer', 'Alzette', 'Mousel']
            INS = CountVal(CountDiff(2,1))
            INA = CountVal(CountDiff(3,1))
            INM = CountVal(CountDiff(1,1))
            IN= np.hstack((INS, INA, INM))

            # ['Sauer', 'Alzette', 'Mousel']
            INactS = CountVal(CountDiff(2,1))
            INactA = CountVal(CountDiff(3,1))
            INactM = CountVal(CountDiff(1,1))
            self.INact= np.hstack((INactS, INactA, INactM))



            ### extension to multi-tanks : TotalCons calculation has to be modified
            # ToDo: This needs to be the sum of all IN from SIDERE use a variable config element.
            # TO DO  : create an internal variable for TotalCons and update it based on the current BZs
            # DF : Error when "sx.sx_zd" is nan for example !
            print "Hard Coded --> tank List should come from configured Providers"
            zdProviders = [self.zd[self.ConfigTanks.index(ki)] for ki in ['Alzette', 'Mousel']]
            TotalCons = np.nansum(zdProviders)

            S0_zLifeD = stateVars["S98.S98_DateTime"]
            if self.initDay(zLifeD=S0_zLifeD):
                TotalCons = 0
                self.setOPCVarT0(outVars,sysVars)
                self.setOPCVarSetpoint(outVars)

#            for idx,val in enumerate(self.ConfigTanks):
#                self.B_cf[val]['Vmin'] = self.VResMin[idx]
#                self.B_cf[val]['Vmax'] = self.VMax[idx]

#DF can be removed (see GSc comment below)
#            try: # GSc this is now obsolet as algo.updateBasinConf() is called after inint in doCheckSysStates()
#                self.AX
#            except AttributeError:
#                self.updateStructOptPB()


            # VDistribKey represents the consumption distribution on the different tanks if they are NOT interconnected
            # For the moment, to define this distribution, we use the variables S*_VdMax and assume that VdMax['Puddel'] integrates VdMax['Ahn']
            # Should depend on the network configuration (eventually use Zarea)
            VDistrib = self.VdMax
#            VDistrib[self.ConfigTanks.index('Schoenert')] -= VDistrib[self.ConfigTanks.index('Imbringen')]
#            VDistrib[self.ConfigTanks.index('Zweckekopp1000')] -= VDistrib[self.ConfigTanks.index('Godbrange')]
#            VDistrib[self.ConfigTanks.index('Puddel')] -= VDistrib[self.ConfigTanks.index('Ahn')]
#            VDistrib[self.ConfigTanks.index('Puddel')] -= VDistrib[self.ConfigTanks.index('Ahn')]
#            VDistrib[self.ConfigTanks.index('Puddel')] -= VDistrib[self.ConfigTanks.index('Ahn')]
#            VDistrib[self.ConfigTanks.index('Puddel')] -= VDistrib[self.ConfigTanks.index('Ahn')]
#            VDistrib[self.ConfigTanks.index('Puddel')] -= VDistrib[self.ConfigTanks.index('Ahn')]
            # TO THINK ABOUT : VDistrib -= (self.zd-self.zd'),  and therefore put this section into run()
            self.VDistribKeys = VDistrib/float(np.nansum(VDistrib))



        except StandardError as e:
            logger.debug( "StandardError in Opti.run() in preparation part: %s", e )


        try:
            INcommand = self.OptPB(TotalCons) #m3/cp
            self.LastIN = INcommand


            print "do differently, maybe elsewhere and not hard coded"
            if self.VRemaining-self.Vres_uncontrolledTank <=0 :
#                OnOffAction[np.array([1,6,8,10])] = False
                idxp = [idx for idx,val in enumerate(self.Actuator) if val.split(' ---> ')[0] == 'Provider']
                INcommand[np.array(idxp)] = 0



        except StandardError as e:
            logger.debug( "StandardError in Opti.run() in solving part: %s", e )


        try:
            #update and write basin Autonomie
            self.setOPCVarAutonomie(outVars)
            #write the control actions
            Ctanks = [(self.ConfigTanks.index(x),x) for x in self.ControlledTank]
            QSollFilt = lambda x: isinstance(x,dict) and 'QSoll' in x['GPC']
            for i,ti in Ctanks:
                sti = GPC_Stations[ti]
                gpcOutVari = filter(QSollFilt, GPC_OutVars.get(sti,[None,]))
                if len(gpcOutVari) == 1: # ToDo: This may not always be correct (if several QSoll exist for one basin)
                    gpcOutVari = '.'.join((sti,gpcOutVari[0]['GPC']))
                if outVars != None and gpcOutVari != None:
                    # Unit of OPC "QoutSpN" needs to be [m3/h]
                    wvalue = outVars[gpcOutVari].setWriteValue(INcommand[i]/self.unitConv['x/h'])
                    if wvalue == None:
                        #GSc-ToDo: How to react in this case?
                        logger.debug("Set the result value for '%s' did not work" % (gpcOutVari))

            #Build the VTodayMax
            VTDMFilt = lambda x: isinstance(x,dict) and 'VTodayMax' in x['GPC']
            for ci in self.ConfigTanks:
                sti = GPC_Stations[ci]
                gpcVTodayMaxi = filter(VTDMFilt, GPC_OutVars.get(sti,[None,]))
                if len(gpcVTodayMaxi) == 0:
                    continue
                gpcVTodayMaxi = '.'.join((sti,gpcVTodayMaxi[0]['GPC']))
                if outVars != None and gpcVTodayMaxi in outVars:
                    val = self.VdTodayMax[self.ConfigTanks.index(ci)]
                    wvalue = outVars[gpcVTodayMaxi].setWriteValue(val)
                    if wvalue == None:
                        #GSc-ToDo: How to react in this case?
                        logger.debug("Set the VTodayMax value for '%s' did not work" % (gpcVTodayMaxi))

            ### keep persistent the needed data to restart MPCAlgo with given Historical data.
            try:
                fh = open(self.persistentFileName,'wb')
                pickle.dump({'zS':self.zS,'Vo':self.Vo,'LastIN':self.LastIN,'zS_Zarea':self.zS_Zarea}, fh)
                fh.close()
            except:
                logger.error( "MPCAlgos.Opti_persistent.pkl could not be written")
            finally:
                if isinstance(fh,file) and not fh.closed:
                    fh.close()
#EndDF unused in my simulation Evironment

        except StandardError as e:
            logger.debug( "StandardError in Opti.run() in post-processing part: %s", e )

        logger.debug(BStr+"IN = %(In)s; OUT = %(Out)s; VOL = %(Vol)s;  SP = %(SP)s;  INComm = %(InComm)s;   TotalDailyIN = %(TotalDailyIN)s",
                     {'In':IN, 'Out':self.OUT, 'Vol':self.VOL, 'InComm':INcommand, 'TotalDailyIN':TotalCons, 'SP':self.SP})


#            return INcommand, IN, self.OUT, self.VOL
        return INcommand, IN, self.OUT, self.VOL, self.ZArea




    def updateVTodayMax(self, T, TotalCons, Zarea_Sidere):
        """
        """
#        self.zd[self.ConfigTanks.index('Langwiss')] = T*self.VdMax[self.ConfigTanks.index('Langwiss')]*self.unitConv['x/d']

        self.VRemaining = self.reservedCapacity - TotalCons - Zarea_Sidere*T
        if self.VRemaining <=0 :
            return
        VdTodayMax_ind = self.VDistribKeys*self.VRemaining

        TK_Sidere = set(['Mousel', 'Alzette', ])#hard coded :  Flowmeter directly connected to SIDERE supply pipe
        for idx, tk in enumerate(self.ConfigTanks):
            if tk in TK_Sidere:
                VdTodayMax_ind[idx] += self.zd[idx]

        self.VdTodayMax = deepcopy(VdTodayMax_ind)
        for idx, tk in enumerate(self.ConfigTanks):
            dwtk = tk
            sti = GPC_Stations[dwtk]
            uptk = self.BConf[sti]['Tree']['Betriebszustaende'][self.B_cf[dwtk]['CBZ']]['Source']
            #GScToDo: This is not working as Sources is a set of Sources and there can be several
            #GScToDo: here this is ok as the showroom network simple and not more than one source is specified
            uptk = list(uptk)[0]
            while uptk not in self.Providers and uptk != '': #DF : bugfix (need to be checked) there was error when Froumbierg's state 'o' BZ3
                if not np.isnan(self.VdTodayMax[idx]):
                    self.VdTodayMax[self.ConfigTanks.index(uptk)] += VdTodayMax_ind[idx]
                dwtk = uptk
                sti = GPC_Stations[dwtk]
                uptk = self.BConf[sti]['Tree']['Betriebszustaende'][self.B_cf[dwtk]['CBZ']]['Source']
                #GScToDo: This is not working as Sources is a set of Sources and there can be several
                #GScToDo: here this is ok as the showroom network simple and not more than one source is specified
                uptk = list(uptk)[0]

        for idx, tk in enumerate(self.ConfigTanks):
            if tk not in TK_Sidere:
                self.VdTodayMax[idx] += self.zd[idx]

        logger.debug("MPCAlgos (%s): VTodayMax = %s" % (self.DZ, self.VdTodayMax) )



    def OptPB(self,TotalCons):
        """
        In this method the optimization problem is formulated and solved depending on:
        - the specified configuration (self.B_cf)
        - the current system data (B_opc)
        The method returns a array with the inflows to be commanded.
        the size of this array depends also on the configuration.
        """
        # To do : use the value defined in the config
#        print self.conf['CostFunctionWeights']


#        logger.debug("==== OptPB: Config ====\n%s\n==== Data ====\n%s", self.B_cf, B_opc)


        m = 60*(60*self.DZ.hour+self.DZ.minute)+self.DZ.second
        T = math.ceil((86400.-m)/self.tUpdate)




##        profile = np.array([[0.1, 0.1, 0.1, 0.1, 0.1, 17.5, 15.9, 12.6, 13.4, 11.2, 11.5, 10.9, 11.2, 10.3, 10.1, 6.7, 10.1, 11.2, 13.0, 12.6, 9.6, 6.5, 5.3, 0.1],
##                           [4.7, 3.5, 3.7, 3.6, 5.4, 12.1, 15.9, 16.7, 20.4, 19.3, 18.8, 17.7, 18.0, 16.1, 15.2, 14.4, 15.1, 15.7, 15.2, 13.6, 12.1, 10.3, 7.2, 5.0],
##                           [8.9, 6.7, 5.8, 6.7, 7.4, 16.2, 20.6, 22.1, 25.5, 25.6, 24.5, 22.9, 23.3, 21.5, 20.0, 19.4, 19.4, 18.8, 18.4, 16.2, 15.1, 13.6, 12.0, 9.6]])
##
##        OUTPastEst = np.array([sum(profile[k][:self.DZ.hour]) for k in range(3)])
##        self.OUTpred = (np.array(self.DCons_Zarea)- OUTPastEst)/T
#
#        self.ScSP = 1
#        self.ScHom = 0
#
#
#        self.OUTpred = (np.array(self.DCons_Zarea)- self.zS_Zarea[0])/T
#
##        if 'ConsProfile' in self.conf:
##            profile = np.array(self.conf['ConsProfile'])/24.
##        else:
##            profile = np.ones(24)/24. #Solution with no profile in the config file
##        zSInit = np.array(MeanDC) * sum(profile[:datetime.now().hour]) #
##        zS_ZareaInit = np.array(MeanDC) * sum(profile[:datetime.now().hour]) #
#        if T<8:
##            print ""
##            self.ScSP = 0.1
##            self.OUTpred = self.ZArea
#            Tvirt=8
#
#            self.SP=self.SPbkup+(self.SPbkup-self.VOL)/T*(Tvirt-T)
#            T = Tvirt
##        else :
##            self.ScSP = self.conf['CostFunctionWeights']['ReachSP'][0]






        self.WeightSP.value = self.ScSP*T

        VmSPimOUT_tmp = list()
        SPCalcType = self.SPCalcType
        if not isinstance(SPCalcType, list): # only one setting for all basins
            SPCalcType = [self.SPCalcType,]*self.NbTank
        VmSPimOUT_tmp.append( np.r_[self.VOL-self.VResMin-self.OUTpred   ]  )
        VmSPimOUT_tmp.append( np.r_[self.VOL-self.OUTpred   ]  )
        VmSPimOUT = np.c_[  np.choose(np.array(SPCalcType)-1,VmSPimOUT_tmp)[self.idx_TKcont]  ]
        del VmSPimOUT_tmp

#        VmSPimOUTxT = np.c_[self.VOL[self.idx_TKcont]-self.Vo[self.idx_TKcont]-self.OUTpred[self.idx_TKcont]*T ]
        SPmVpOUTxT = np.c_[self.SP[self.idx_TKcont]-self.VOL[self.idx_TKcont]+self.OUTpred[self.idx_TKcont]*T  ]/T




        VmOUTxT = self.VOL[self.idx_TKcont]-self.OUTpred[self.idx_TKcont]*T
        VmOUT = self.VOL[self.idx_TKcont]-self.OUTpred[self.idx_TKcont]









        b = np.c_[self.AutoRepart[self.idx_TKcont]*np.sum(VmSPimOUT)]-VmSPimOUT
#        b=np.c_[AutonomVol*np.roll(VmSPimOUT,-1)-VmSPimOUT*np.roll(AutonomVol,-1)]
#        b = b/(self.Epsqre.reshape(4,1))
#        n=0;# n=1; A=delete(A,0,0); b=delete(b,0)
        B=np.vstack((self.ScHom*b, self.WeightSP.value*SPmVpOUTxT)) #Use coefficients from config here
        del b

        B=np.vstack([ B,
                      np.zeros((3*self.NbContTank,1))])  #Use coefficients from config here also only zeros are used.


        Vmin_cont = self.VResMin[self.idx_TKcont]
        Vmax_cont = self.VMax[self.idx_TKcont]

        Constr = self.constr[:]

        print "hard coded"
        Zarea_Sidere = 0 #To Do this value should be the predicted consumption of an area supplied directly by SIDERE

        self.updateVTodayMax(T, TotalCons, Zarea_Sidere)

        if any(self.idx_uncontSrcP): # is needed because nansum([]) gives nan while sum([]) gives 0
            self.Vres_uncontrolledTank = np.nansum( (self.VdTodayMax - self.zd)[self.idx_uncontSrcP]  )
        else:
            self.Vres_uncontrolledTank = 0.0

        # The inflow at the others tanks (the uncontrolled ones) is assumed to be constant over the day !!!
        # Problem in the case when an uncontrolled tank is really filling up at the end of the day
        Constr.append(T*self.ts_pX <= (self.VRemaining-self.Vres_uncontrolledTank))


#        if TotalCons > self.reservedCapacity:
#            print "Daily Limit reached"


#DF to do later
#        # hard constraints: sum(flow_fromTankinMaintenance)<VresTankinMaintenance
#        VdTodayMaxRest = self.VdTodayMax-self.zd
#        for i in self.TankAsSource:
#            if self.B_cf[i]['CState'] == 'a' :
#                ts = np.zeros((self.NbTank,1))
##                for idx, val in enumerate(self.ControlledTank):
##                    if self.B_cf[val]['Source'] == i:
##                        ts[self.ConfigTanks.index(val)] = self.QMax[self.idx_TKcont][idx]
#                Vresuncont = 0
#                for idx, val in enumerate(self.ConfigTanks):
#                    if self.B_cf[val]['Source'] == i:
#                        if val in self.ControlledTank:
#                            ts[idx] = self.QMax[idx]
#                        else:
#                            Vresuncont = np.nansum([Vresuncont,VdTodayMaxRest[idx]])
##                Constr.append(cvxpy.leq(T*ts.T*self.x[0:self.NbTank,0],self.VdMax[self.ConfigTanks.index(i)]-self.zd[self.ConfigTanks.index(i)] )) #TO DO : and substract the expected out to the area  -Vres_uncontrolledTank*self.unitConv['x/d']*T
##                Constr.append(cvxpy.leq(T*ts.T*self.x[0:self.NbTank,0],self.VdMax[self.ConfigTanks.index(i)]-self.zS[0][self.ConfigTanks.index(i)]  )) #TO DO : and substract the expected out to the area  -Vres_uncontrolledTank*self.unitConv['x/d']*T
#                Constr.append( (T*ts.T*self.x[0:self.NbTank,0]) <= np.max(( VdTodayMaxRest[self.ConfigTanks.index(i)] - Vresuncont,0)  )) #TO DO : and substract the expected out to a consumption area Zi




        # Soft constraints: Volume>minimal Volume
        Constr.append((VmOUTxT+self.AspX*T+self.ts_s1) >= Vmin_cont.T)


        # Hard constraints: Volume<maximal Volume
        Constr.append((VmOUT+self.AspX-self.ts_sV)<= Vmax_cont.T)
        # Hard constraints: Volume>minimal Volume
        Constr.append((VmOUT+self.AspX+self.ts_sV)>= Vmin_cont.T)



#        if T>2:
#            MaxChangeOfCommand = 0.20
#        else :
#            MaxChangeOfCommand = 0.001
#        for kk in range(self.N_decvar):
#            if self.idx_VARcont[kk]:
#                Constr.append(self.x[kk]<= self.INact[kk]/self.QMax[kk] + MaxChangeOfCommand)
#                Constr.append(self.x[kk]>= self.INact[kk]/self.QMax[kk] - MaxChangeOfCommand)
#
        Obj = cvxpy.Minimize(cvxpy.norm2(self.AX-B))
        p = cvxpy.Problem(Obj,Constr)

        #p.options = {'reltol': 1e-06, 'maxiters': 100, 'abstol': 1e-07, 'feastol': 1e-06} #Default configuration
        #p.options['abstol'] = 1e-3                             # Change solver configuration
        #p.options['reltol'] = 1e-2
        #p.options['feastol'] = 1e-3
        #p.options['maxiters'] = 200
        e = 0

        #reset the optimisation variables
        self.x.value=np.nan*np.ones(self.x.size)

#        p.solve()
#        res = p.solve(quiet=True) #To suppress the output
        try :
            res = p.solve()
        except :
            try :
#                res= p.solve(verbose=True)
#                res = p.solve(verbose=True, solver = 'ECOS')
#                res = p.solve(verbose=True, solver = 'SCS')
                res = p.solve(verbose=True, solver = 'CVXOPT')
            except StandardError as err: #e.g. "domain error" when problem is poorly scaled
                logger.debug( "StandardError: %s", err )
                res = np.nan

        # Build p.show() as string for logging
        # Build p.show() as string for logging
#        if self.verbose_solver:
#            if p.action == cvxpy.defs.MINIMIZE:
#                pshowStr = '\nminimize '
#            else:
#                pshowStr = '\nmaximize '
#            pshowStr += str(p.objective)+'\n'
#            pshowStr += 'subject to\n'
#            pshowStr += str(p.constraints)
#
#            logger.debug("==== Opt-Problem ====\n%s\n==== Solution-%s ====\n%s", pshowStr, e, self.x.value)

        #print x.value
        #print p.constraints
        #print p.variables

#        p.show()
        #print x.value



        #TO DO Change self.NbTank by self.idx_TKcont
        if not np.isfinite(res):
            if self.VRemaining-self.Vres_uncontrolledTank <=0 :
                print "add logging"
                print "manage differently this situation e.g. solve the problem without this hard constraint"
                In = np.zeros(self.N_decvar)
                return In.flatten()
            try:
#               p.options['abstol'] = 1e-10                              # Change solver configuration
#               p.options['reltol'] = 1e-9
#               p.options['feastol'] = 1e-9
#               p.options['maxiters'] = 200
                e+=1
                logger.debug("Change Solver Config")
                p.options['feastol'] = 1e-12
                res = p.solve(quiet=True) #To suppress the output
                if self.verbose_solver:
                    logger.debug("==== Solution-%s ====\n%s", e, self.x.value)
            except:
                e+=1
                while e<10:
                    try:
                        logger.debug("another try: %s",e)
                        res = p.solve(quiet=True)
                        if self.verbose_solver:
                            logger.debug("==== Solution-%s ====\n%s", e, self.x.value)
                        e=10
                    except:
                        e+=1

        logger.debug("\n===Understanding the optimal solution===")
        if self.verbose_solver & np.isfinite(res):
            Vprct_tmp = list()
            Vprct_tmp.append( (1*(self.VOL-self.VResMin)/self.AutonomVol)  )
            Vprct_tmp.append( (1*self.VOL/self.AutonomVol)  )
            Vprct = np.choose(np.array(SPCalcType)-1,Vprct_tmp)[self.idx_TKcont]
            del Vprct_tmp

            if self.NbContTank==1:
                Vend = (VmOUTxT.T+self.AspX.T*T).value
            else :
                Vend = (VmOUTxT.T+np.array((self.AspX.T*T).value)[0])

            Vendprct_tmp = list()
            Vendprct_tmp.append( 1*(Vend-self.VResMin[self.idx_TKcont])/self.AutonomVol[self.idx_TKcont]  )
            Vendprct_tmp.append( 1*(Vend)/self.AutonomVol[self.idx_TKcont]  )
            Vendprct = np.choose(np.array(SPCalcType)[self.idx_TKcont]-1,Vendprct_tmp)
            del Vendprct_tmp


            C1 = np.abs(self.AX.value-B)[:self.NbContTank]
            C2 = (self.AX.value-B)[self.NbContTank:2*self.NbContTank]
            C3 = np.abs((self.AX.value-B)[2*self.NbContTank:3*self.NbContTank])
            C4 = np.abs((self.AX.value-B)[3*self.NbContTank:4*self.NbContTank])


            DCest = self.reservedCapacity-((self.VRemaining-self.Vres_uncontrolledTank)-T*self.ts_pX.value)
            logger.debug( "Controlled Tanks: %s" % (self.ControlledTank,) )
            logger.debug( "Vo :     %s" % (self.Vo[self.idx_TKcont],) )
            logger.debug( "SP* :    %s" % ((self.SP)[self.idx_TKcont],) )
            logger.debug( "Vol   :    %s" % (self.VOL[self.idx_TKcont],) )
            logger.debug( "V_aut :    %s" % (Vprct,) )
            logger.debug( "Vend :   %s" % (Vend,) )
            logger.debug( "Vend_aut : %s" % (Vendprct,) )
            logger.debug( "Estimated inflow volume for today : %s" % (DCest,) )
            logger.debug("---Cost function [Weights]---")
            logger.debug("   RelVolumeHomogenity : [%sx]\n %s" % (self.ScHom, np.array(C1).T[0],) )
            logger.debug("   ReachSP (  <0 --> belowSP,    >0 --> aboveSP): [%sx]\n %s" % (self.WeightSP.value/T, np.array(C2).T[0],) )
            logger.debug("   EmergancyReserve  : [%sx]\n %s" % (self.ScEmerg, np.array(C3).T[0],) )
            logger.debug("   Vminmax_Violation  : [%sx]\n %s" % (self.ScVolRge, np.array(C4).T[0],) )
            logger.debug("-----------------------------")





        #TO DO Change self.NbTank by self.idx_TKcont
        In = np.array(self.x.value[:self.N_decvar])*np.c_[self.QMax]
        if np.any(In < 0):
            logger.debug("Warning: Negative 'In' values are set to zero!")
            In[In < 0]=0

        if np.any(In > 10*np.c_[self.QMax]):
            logger.debug("Warning: some 'In' values calculated are untrustworthy; set to NaN!")
            In = np.where(In > 10*np.array(np.c_[self.QMax]), np.nan, In)


        if np.any(In > np.c_[self.QMax]):
            logger.debug("Warning: some 'In' values are larger than QMax; set to QMax!")
#            In = np.where(In > Qmax.T, Qmax, In) #is equal to: In[In > Qmax]=Qmax[In > Qmax]
            In[In > np.c_[self.QMax]] = np.array(np.c_[self.QMax][In > np.c_[self.QMax]])[0]


#        # if the current daily consumption is already greater than [Global reserved capacity - SUM(reserved capacity for the autonomous tanks)]
#        # the Optimisation problem is infeasable and x.value=NaN is returned
#
        if  np.isnan(In[self.idx_VARcont]).any():
            logger.debug("==== Infeasable Problem (after %s) ====", e)

            indnan=np.where(np.isnan(In[self.idx_VARcont]))[0]
#            indnan=np.where(np.isnan(In))[0]
            if self.reservedCapacity-self.Vres_uncontrolledTank -TotalCons<0:
                for indn in indnan :
#                    if self.VOL[self.idx_TKcont][indn]<1.1*Vmin_cont[indn]:
#                        logger.debug("'In' values are set equal to OUT!")
#                        #In=np.where(np.isnan(In),self.OUTpred[self.idx_TKcont],In)
##                        In[self.idx_TKcont][indn] = self.OUTpred[self.idx_TKcont][indn]
#                        In[np.where(self.idx_TKcont)[0][indn]] = self.OUTpred[self.idx_TKcont][indn]
#                    else :
                    logger.debug("'In' values are set to zero!")
                    #In=np.where(np.isnan(In),0,In)
                    In[np.where(self.idx_VARcont)[0][indn]] = 0
            else:
                logger.debug("Last computed 'In' values are reused")
                #In=np.where(np.isnan(In),self.LastIN,In)
                for indn in indnan :
                    #DF if tank was offline the last Incommand is nan
                    #bugfix only for simulation
                    if np.isnan(self.LastIN[self.idx_VARcont][indn]) :

#                        self.LastIN[self.idx_VARcont][indn] = 0 # DF I don't understand why that doesn't work
                        Tmp = self.LastIN[self.idx_VARcont]
                        Tmp[indn]=0
                        self.LastIN[self.idx_VARcont] = Tmp
                    In[np.where(self.idx_VARcont)[0][indn]] = self.LastIN[self.idx_VARcont][indn]



        if self.verbose_solver:
            logger.debug("==== OptPB: End ====")

#        if (V[1]-T*OUT[1]+Volume_reserve-Vres_uncontrolledTank-TotalCons)< Vmin_cont:
#            In=(Vmin_cont-V[1])/T+OUT[1]
#            print 'Cte Inflow'



#        In_extend = np.nan * self.SP
#        In_extend[self.idx_VARcont] = In
#        return np.array(In_extend).flatten()
        return In.flatten()


class MPCParamVar(object):
    """This class is used to handle MPCAlgo specific parameter-variables.
    This are parameters specified in one or more config files in a potential hierarchical way
    and can have an opc variable for user interaction via SCADA."""
    def __init__(self,paramName,opcName=None,size=None,dtype=None,default=None):
        self.Name = paramName
        if opcName != None:
            self.opcName = opcName

