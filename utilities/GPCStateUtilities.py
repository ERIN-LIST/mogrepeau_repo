""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
"""
Created on 18 avr. 2013
"""

import re
from collections import defaultdict

from Control.GPCVariablesConfig import GPC_Stations


def getLifeVars(opcvar):
    """Returns the gpc internal variable names as a list
    - The parameter opcvar need to be a dictionary of opcVars."""
    reLifeFilter = re.compile("^S(?!99).*zLife$")
    gpcLifeVars = filter(reLifeFilter.match, opcvar.keys())
    return gpcLifeVars

def getBModeVars(opcvar):
    """Returns the gpc internal variable names as a list
    - The parameter opcvar need to be a dictionary of opcVars."""
    reLifeFilter = re.compile("^S.*BZ$")
    gpcLifeVars = filter(reLifeFilter.match, opcvar.keys())
    return gpcLifeVars

def buildLifeDiff(opcvar,varList=[]):
    d = defaultdict(int)
    if varList == []:
        varList = opcvar.keys()
    for ki in varList:
        vi = opcvar[ki]
        if ki == vi.name: #GSc: why this if, both paths are identical?
            # System is using the OPC variable names
            sti = ki.split('.')[0]
        else:
            #GPC internal variables are used.
            sti = ki.split('.')[0]
        if vi.getDiff() == None:
            diff = None
        else:
            diff = vi.getDiff().Diff[0]
            if diff < 0: diff += 1<<16
        try:
            d[sti] += diff
        except TypeError:
            d[sti] = None
    return d

def buildLifeCounter(opcvar,varList=[]):
    d = defaultdict(int)
    if varList == []:
        varList = opcvar.keys()
    for ki in varList:
        vi = opcvar[ki]
        if ki == vi.name: #GSc: why this if, both paths are identical?
            sti = ki.split('.')[0]
        else:
            sti = ki.split('.')[0]
        try:
            if vi.quality == 'Good':
                d[sti] += vi.value
            else: d[sti] = None
        except TypeError:
            d[sti] = None
    return d

def getSysGPCState(stateVars):
    """
    Returns the system GPC State of each configured station as a dictionary
      station: one of {'offline','maintenance','controlled'}
    - The parameter stateVars need to be a dictionary of opcVars with the system state variables.
    """
    gpcLifeVars = getLifeVars(stateVars)
    zLifeC = buildLifeCounter(stateVars,gpcLifeVars)
    zLife = buildLifeDiff(stateVars,gpcLifeVars)
    Sys_zLife = {}
    for sti in zLife:
        if zLifeC[sti] == None:
            Sys_zLife[sti] = False
        elif zLife[sti] > 0 or zLife[sti] == None:
            # zLife[sti] == None should only occure after GPC initialization or after a reset.
            Sys_zLife[sti] = True
        else:
            Sys_zLife[sti] = False
    SysGPCState = {}
    stiDefaults = {"Autonom":1,"Life":0} # Safe values if variables are not accessible
    for sti in GPC_Stations.values():
        if sti in ['S99']: continue
        elif sti in ['S0']:
            sTypes = [(0,"Autonom"),]  # Here only the binary levels 0 is defined.
            gpcStates = {-1:'offline',0:'controlled',1:'maintenance'}
        else:
            sTypes = [(0,"Autonom"),(1,"Life")] # Here the binary levels 0,1 are defined.
            gpcStates = {-1:'offline',0:'maintenance',1:'maintenance',3:'maintenance',2:'controlled'} # for binary mapping: Auto 2^0, Life 2^1
        viState = None
        if Sys_zLife.get(sti,None):
            viState = 0
            for i,vi in sTypes:
                varN = '.'.join((sti,"_".join((sti,vi))))
                varState = stateVars.get(varN,stiDefaults[vi]) # Default=1 means station is life but has no Autonom variable.
                if varState != stiDefaults[vi]:
                    varState = varState.value
                viState += varState<<i # binary shift operation
        SysGPCState[sti] = gpcStates.get(viState,gpcStates[-1]) # Default=-1 means station is not life.
    return SysGPCState

def getSysGPCState_StMo(stateVars):
    """
    Returns the system GPC State of each configured station as a dictionary
      station: one of {'offline','maintenance','controllable','controlled'}
    - The parameter stateVars need to be a dictionary of opcVars with the system state variables.
    """
    gpcLifeVars = getLifeVars(stateVars)
    zLifeC = buildLifeCounter(stateVars,gpcLifeVars)
    zLife = buildLifeDiff(stateVars,gpcLifeVars)
    Sys_zLife = {}
    for sti in zLife:
        if zLifeC[sti] == None:
            Sys_zLife[sti] = False
        elif zLife[sti] > 0 or zLife[sti] == None:
            # zLife[sti] == None should only occure after GPC initialization or after a reset.
            Sys_zLife[sti] = True
        else:
            Sys_zLife[sti] = False
    SysGPCState = {}
    stiDefaults = {"SteuerModus":0,"Autonom":1,"Life":0} # Safe values if variables are not accessible
    for sti in GPC_Stations.values():
        if sti in ['S99']: continue
        elif sti in ['S0']:
            sTypes = "Autonom"  # Here only the binary levels 0 is defined.
            gpcStates = {-1:'offline',0:'controlled',1:'maintenance'}
        else:
            sTypes = "SteuerModus" # Here the binary levels 0,1 are defined.
            gpcStates = {-1:'offline',0:'offline',
                         1:'maintenance',2:'maintenance',
                         5:'controllable',
                         6:'controlled:',7:'controlled:',8:'controlled:'} #Coding definition of SteuerModus
        viState = None
        if Sys_zLife.get(sti,None):
            vi = sTypes
            varN = '.'.join((sti,"_".join((sti,vi))))
            varState = stateVars.get(varN,stiDefaults[vi]) # Default=1 means station is life but has no SteuerModus/Autonom variable.
            if varState != stiDefaults[vi]:
                varState = varState.value
            viState = varState
            if sTypes == "SteuerModus":
                if viState >= 6:
                    viState = 6

        stiState = gpcStates.get(viState,gpcStates[-1]) # Default=-1 means station is not life.
        if viState == 6:
            stiState = stiState + str(varState) # add the SteuerModus value as extension
        SysGPCState[sti] = stiState
    return SysGPCState

def getSysBModeUpdate(stateVars):
    """
    Return the list of the basins for which the working-mode has changed since last cycle.
    """
    d = {}
    BModeVars = getBModeVars(stateVars)
    for ki in BModeVars:
        vi = stateVars[ki]
        sti = ki.split('.')[0]
        if vi.getDiff() == None:
            diff = None
        else:
            diff = vi.getDiff().Diff[0]
        d[sti] = {'Update':diff,'Mode':vi.value}
    return d
