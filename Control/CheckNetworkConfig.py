# -*- coding: utf-8 -*-
"""
Created on Fri Jun 14  2013

Check the network configuration

@author: fiorelli
"""

import os, sys
import numpy as np
from collections import Counter, defaultdict
import copy
import logging
from copy import deepcopy

sys.path.append(os.path.abspath(os.path.pardir))
from GPCVariablesConfig import GPC_Stations
from ReadWriteDataTest.handleConfig import readGPCConfig


#logging.basicConfig(filename='CheckConfigLOG.log',filemode='w', level = logging.DEBUG)


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def CheckNetworkConfig(B_cf,Area):
    """Run the different checks an reconfigure in case of bypass or off-line basins
    The returned value is True if everything is OK or a boolean defaultdict with levels of problems (warning == True, ...)"""
    #CheckCode can be used to fine-tune the overall check result 
    #and with this the resulting reaction
    CheckCode = defaultdict(bool) # The default (non existing) item is False.
    
    ConfigTanks = B_cf.keys()
    Providers = [si for si in B_cf if B_cf[si]['Status'] =='p']
    #-----------
    #---CHECK---
    #-----------
    logger.info("\n ----------------------------" +\
                "\n Check network config START" +\
                "\n ----------------------------" )
    
    #Update the basin sinks for all optional sinks that have the basin configured as source
    for bi in ConfigTanks:
        for osi in B_cf[bi].get('OptionSinkBehaelter',set()):
            if B_cf[osi]['Source'] !=None and  bi in B_cf[osi]['Source']:
                B_cf[bi]['Sink'].update(set([osi]))
    
    Vtest=[B_cf[x]['Vmax'] < B_cf[x]['Vmin'] for x in B_cf]
    if any(Vtest):
        err=[ConfigTanks[index] for index, val in enumerate(Vtest) if (val==True)]
        logger.warning('\n  Vmin is greater then Vmax for Tank(s) %s !!!' % err)
        CheckCode['warning'] |= True
    
    
    Sink=[B_cf[x]['Sink'] for x in B_cf]
    s=reduce(lambda x,y: x | y, Sink)
#    Sink_tk = list(Sink)
#    Sink_tk.pop(ConfigTanks.index('SIDERE'))
#    s_tk=reduce(lambda x,y: x | y, Sink_tk)
    
    #-----------
    if not(s>=Area):
        logger.warning('\n  One or several consumption areas are missed :  %s.' % list(Area-s))
    #    raise ValueError('One or several consumption areas are missed :  %s.' % list(Area-s))
        CheckCode['warning'] |= True
        
    #-----------    
    
    
    #-----------
    if not(s<=Area.union(set(ConfigTanks))) :
        logger.warning( '\n  For these operating modes, one or several destinations are undefined :  %s.' % list(s-Area.union(set(ConfigTanks)))) 
    #      raise ValueError('For these operating modes, one or several destinations are undefined :  %s.' % list(s-Area.union(set(ConfigTanks)))
        CheckCode['warning'] |= True
    #-----------
    
    #-----------
    
    
    cnt=reduce(lambda x,y: Counter(x)+Counter(y), Sink)
    for tk2s in ['Zweckekopp1000', 'Junglinster500', 'Biergebierg']:# Tanks supplied by 2 sources
        cnt[tk2s]-=1 
    #print cnt.values()
    if any(np.array(cnt.values())>1):
    #     print '\n  One or several destinations are repeated'
    #     print '\n  One or several destinations are repeated :  %s.' % cnt.keys()[find(np.array(cnt.values())>1)] #it works only if there is only one element
        RepeatedSink=[ci for ci in cnt if cnt[ci] > 1]
        logger.warning( '\n  One or several destinations are repeated :  %s.' % RepeatedSink )
    #    raise ValueError('One or several destinations are repeated :  %s.' % RepeatedSink)
        CheckCode['warning'] |= True
    #-----------
    
    
    #-----------
    TankSource = [(x,B_cf[x]['Source']) for x in B_cf if B_cf[x]['Source'] not in [None,'']]
    for t,s in TankSource:
#        if i=='SIDERE':
#            continue
        for ss in s:
            if not(t in B_cf[ss]['Sink']) and t not in Providers:
                logger.warning( '\n  Tank(s) %s are missed in the sinks of tank %s.' %(t,s) )
        #        raise ValueError('Tank(s) %s are missed in the sinks of tank #%s.' %(err,i))
                CheckCode['warning'] |= True
    #-----------

    
    
    #-----------    
    err = []
    for index, val in enumerate(Sink):
        TkInSk = set(ConfigTanks) & val
        if TkInSk :
            err = ['%s'%i for i in TkInSk if ConfigTanks[index]  not in B_cf[i]['Source'] ]
            
        if err:
            logger.warning( '\n  Tank(s) %s is assumed to be supplied by %s.' %(err,ConfigTanks[index]) )
    #       raise ValueError('Tank(s) %s is assumed to be supplied by %s.' %(err,ConfigTanks[index]))
            CheckCode['warning'] |= True
            err = []
    #-----------


    logger.info( "\n B_cf \n" )
    logger.info( B_cf )

    #-----------
    #---Reconfiguration---
    #---in the case where tanks are bypassed---
    #----------- 

    ByPassedTank= [x for x in B_cf if B_cf[x]['Status']=='b' and B_cf[x]['Source'] not in [None,'']]
    if ByPassedTank:
        B_cf_temp = dict()
        while B_cf_temp != B_cf:
            B_cf_temp = copy.deepcopy(B_cf) 
            
            for i in ByPassedTank:
                if B_cf[i]['Source'] not in [None]:
                    for ss in B_cf[i]['Source']:
                        if ss == None :
                            continue
                        B_cf[ss]['Sink'].difference_update(set([i]))
                        B_cf[ss]['Sink'].update(B_cf[i]['Sink']) 
                        
                        TkInSk = set(ConfigTanks) & B_cf[i]['Sink']
                        for ii in TkInSk:
                            B_cf[ii]['Source'].update(set([ss]))
                            B_cf[ii]['Source'].difference_update(set([i]))
                            
                    B_cf[i]['Source'] = None
                    B_cf[i]['Sink'] = set([])
        
        logger.info( "\n B_cf adapted due to bypassed tanks (%s) \n"  % ByPassedTank )
        logger.info( B_cf )



    #-----------
    #---Reconfiguration---
    #---in the case where tanks that supply anothers tanks are offline---
    #-----------

    # if tanks is supplied by another tank which is in "offline"
    # then if the sink tank was "controlled" it is now in "maintenance"     
    
#    Source = [B_cf[x]['Source'] for x in B_cf if B_cf[x]['Source'] not in [None,'']]
    tk =[x for x in B_cf if B_cf[x]['Source'] not in [None,'']]
    Source=set([])
    for x in tk:
        Source.update(B_cf[x]['Source'])
    BasinOff = [x for x in B_cf if B_cf[x]['Status'] == 'o'] 
#    SourceOff = list(set(BasinOff) & set(Source))
    SourceOff = list(set(BasinOff) & set(Source))
    for i in SourceOff :
        TkInSk = set(ConfigTanks) & B_cf[i]['Sink']
        for ii in TkInSk:
            B_cf[ii]['Status'] = 'a'
            #TO DO : set tank's status to "autonomous" mode
        
    if SourceOff:
        logger.info( "\n B_cf adapted due to source tanks in 'offline' mode (%s) \n"  % SourceOff  )
        logger.info( B_cf )

    #GSc-ToDo: here some checks would be needed to ensure that the resulting configuration (after adaptations) is usable. 

    logger.info( '\n ----------------------------' +\
                 '\nCheck network config END' +\
                 '\n ----------------------------' )

    if any([CheckCode[ci] for ci in ['warning','error']]):
        return CheckCode # This is used in GPC to switch to off-line
    return True


#def test_stdconfig():
#    Area=set(['A', 'D', 'E', 'K', 'L1', 'M1', 'M2', 'OW', 'W1', 'W2','Z1','Z2'])
#
#    B_cf = {'SIDERE':{'Source':'SIDERE', 'Sink':set(['Langwiss', 'Froumbierg', 'Wuetelbierg', 'Puddel']), 'Status':'p',
#                       'Vmin':np.NaN, 'Vmax':np.NaN},
#            'Langwiss':{'Source':'SIDERE', 'Sink':set(['K']), 'Status':'b',
#                        'Vmin':np.NaN, 'Vmax':np.NaN},
#            'Froumbierg':{'Source':'SIDERE', 'Sink':set(['Machtum']), 'Status':'c',
#                          'Vmin':100, 'Vmax':400}, 
#            'Wuetelbierg':{'Source':'SIDERE', 'Sink':set(['D', 'OW']), 'Status':'c',
#                           'Vmin':100, 'Vmax':460},          
#            'Puddel':{'Source':'SIDERE', 'Sink':set(['E', 'L1', 'W1', 'W2']), 'Status':'c',
#                      'Vmin':200, 'Vmax':1000},
#            'PreAhn':{'Source':'Machtum', 'Sink':set(['Ahn',]), 'Status':'b',
#                      'Vmin':np.NaN, 'Vmax':np.NaN},
#            'Ahn':{'Source':'PreAhn', 'Sink':set(['A']), 'Status':'c',
#                   'Vmin':50, 'Vmax':123},
#            'Machtum':{'Source':'Froumbierg', 'Sink':set(['PreAhn', 'M1', 'M2']), 'Status':'b',
#                       'Vmin':np.NaN, 'Vmax':np.NaN},
#            }                      
#    return B_cf, Area
#
#def test_errorconfig():
#    Area=set(['A', 'D', 'E', 'K', 'L1', 'M1', 'M2', 'OW', 'W1', 'W2','Z1','Z2'])
#
#    B_cf = {'SIDERE':{'Source':'SIDERE', 'Sink':set(['Froumbierg', 'Wuetelbierg', 'Puddel']), 'Status':'p',
#                      'Vmin':np.NaN, 'Vmax':np.NaN},
#            'Langwiss':{'Source':'SIDERE', 'Sink':set(['K','M1','A','Tank7','Y23']), 'Status':'b',
#                        'Vmin':500, 'Vmax':250},
#            'Froumbierg':{'Source':'SIDERE', 'Sink':set(['Machtum', 'M2']), 'Status':'o',
#                          'Vmin':100, 'Vmax':400}, 
#            'Wuetelbierg':{'Source':'Puddel', 'Sink':set(['D', 'OW']), 'Status':'c',
#                           'Vmin':100, 'Vmax':500},          
#            'Puddel':{'Source':'SIDERE', 'Sink':set(['E', 'L1', 'W1', 'W2', 'Ahn']), 'Status':'c',
#                      'Vmin':200, 'Vmax':1000},
#            'Ahn':{'Source':'SIDERE', 'Sink':set(['A']), 'Status':'c',
#                   'Vmin':50, 'Vmax':150},
#            'Machtum':{'Source':'Froumbierg', 'Sink':set(['Ahn', 'M1']), 'Status':'b',
#                       'Vmin':np.NaN, 'Vmax':np.NaN},
#            }
#    return B_cf, Area

def handleBypassedCascades(B_cf,bi_cf,resetToConfig):
    cascade = B_cf[bi_cf['Source']]
    if cascade['Status'] == 'b' and cascade['Source'] == None:
        resetToConfig.add(bi_cf['Source'])

def handleOptionalSinks(B_cf,bi_cf,UpStis,resetToConfig,affectedArea):
    for bi in bi_cf['OptionSinkBehaelter']:
        if GPC_Stations[bi] in UpStis:
            # do nothing as this is yet done or will be handled later in the loop. 
            continue 
        CSource = B_cf[bi]['Source']
        stid = int(GPC_Stations[bi].strip('S'))
        CBZbi = B_cf[bi]['CBZ']
        cbi,cvalbi = readGPCConfig(os.path.join('..','Control','Behaelter_%d.ini'%(stid,)))
        ConfSbi = cbi['Betriebszustaende'][CBZbi]['Source']
        if CSource != ConfSbi: #Need to reconfigure due to a previous bypass
            #Correct the considered optional sink basin and its current source.
            resetToConfig.add(bi)
            if CSource != None:
                B_cf[CSource]['Sink'] -= set([bi,])|affectedArea

def test_basinfileconfig(BZs=None, B_cf=None):

    StiMap = dict([reversed(i) for i in GPC_Stations.items()])
    Area=set(['Junglinster_ZI',
              'Junglinster_RuedeLuxembourg',
              'Gonderange',
              'Junglinster_Haut',
              'Godbrange-Schiltzberg-Koedange',
              'Altlinster_area',
              'PlaceDuVillage',
              'RueDeJunglinster',
              'RueDeCimetiere',
              'Gonderange_Haut',
              'Fromert',
              'Imbringen-Eisenborn',
              'Rodenbourg_area',
              'Eschweiler_area'])
    if B_cf == None:
        Update = False
        B_cf = {'SIDERE':{'Source':set(['SIDERE']), 'Sink':set([]), 'Status':'p', 'Vmin':np.NaN, 'Vmax':np.NaN},
                'Kriebseweiher':{'Source':set(['Kriebseweiher']), 'Sink':set([]), 'Status':'p', 'Vmin':np.NaN, 'Vmax':np.NaN},}
        Stis = StiMap.keys()
        affectedArea = Area
    else:
        Update = True
        Stis = BZs.keys()
        affectedArea = set()
    resetToConfig = set()
    for sti in Stis:
        if sti in ['S0', 'S99']: continue
        #Read the configuration file
        stid = int(sti.strip('S'))
        c,cval = readGPCConfig(os.path.join('..','Control','Behaelter_%d.ini'%(stid,)))
        if not c['Global']['BId'] == stid: # Additional checks could be added here.
            logger.debug("%s: Missmatch between Basin filename and internal BId\n -> config not used!" % (sti,))
            continue
        if BZs != None and sti in BZs: # BZ is specified for this basin
            vi = BZs[sti]
        else:
            vi = c['Global']['DefaultBZ'] # Here no real system variables are usable so take the default BZ

        #Check the usability of the configuration and current state
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

        if Update: #The network structure is updated (not newly created)
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
        spec['CBZ'] = vi
        spec['OptionSinkBehaelter'] = c['Global']['OptionSinkBehaelter']
        if Update:
            cascade = B_cf[spec['Source']]
            if cascade['Status'] == 'b' and cascade['Source'] == None: #Need to reconfigure this bypassed tank
                resetToConfig.add(spec['Source'])
        B_cf[StiMap[sti]] = spec

    while resetToConfig:
        bi = resetToConfig.pop()
        stid = int(GPC_Stations[bi].strip('S'))
        CBZbi = B_cf[bi]['CBZ']
        cbi,cvalbi = readGPCConfig(os.path.join('..','Control','Behaelter_%d.ini'%(stid,)))
        spec = deepcopy(cbi['Betriebszustaende'][CBZbi])
        spec['CBZ'] = CBZbi
        spec['OptionSinkBehaelter'] = cbi['Global']['OptionSinkBehaelter']
        B_cf[spec['Source']]['Sink'] -= spec['Sink']
        affectedArea |= spec['Sink']
        B_cf[bi] = spec
        cascade = B_cf[spec['Source']]
        if cascade['Status'] == 'b' and cascade['Source'] == set(): #Need to reconfigure this bypassed tank
            resetToConfig.add(spec['Source'])
        #GSc-ToDo this is the same code as in previous OptionSinkBehaelter handling. Should be put into a method.
        handleOptionalSinks(B_cf,spec,Stis,resetToConfig,affectedArea)
       
    ## Rebuild the Sinks of the providers after reading the complete network configuration.
    Providers = [si for si in B_cf if B_cf[si]['Status'] =='p']
    logger.debug("DebugInfo: Providers:%s;\n        AffectedAreas: %s" % (Providers, affectedArea))
    for t in B_cf:
        for ss in B_cf[t]['Source']:
            if ss not in Providers: continue
            if t in Providers:
                B_cf[t]['Sink'] -= affectedArea
                continue
            B_cf[ss]['Sink'].add(t)
    
    return B_cf, Area  

    
if __name__ == '__main__':
    sys.path.append(os.path.abspath(os.path.pardir))

    SH = logger.addHandler(logging.StreamHandler())
    SF = logger.addHandler(logging.FileHandler("xxx.log"))
    logger.setLevel(logging.DEBUG)

    # Build a configuration to check
#    B_cf, Area = test_stdconfig()
    logger.info("==\nBasic test with all default BZs\n===")
    B_cf, Area = test_basinfileconfig()
 
    # Test the network configuration check
    CheckNetworkConfig(B_cf, Area)
    CheckNetworkConfig(B_cf, Area) # Repeat to test if every adaptations where done in the first run
# 
#    logger.info("==\nTest: S51='BZ 2' rest default\n===")
#    B_cf, Area = test_basinfileconfig({'S51': 'BZ 2'})
#    CheckNetworkConfig(B_cf, Area)
# 
#    logger.info("==\nTest: S51= 'BZ 1' -> 'BZ 2' -> 'BZ 1' rest default\n===")
#    B_cf, Area = test_basinfileconfig()
#    CheckNetworkConfig(B_cf, Area)
#    B_cf1, Area = test_basinfileconfig(BZs={'S51': 'BZ 2'}, B_cf=B_cf)
#    CheckNetworkConfig(B_cf1, Area)
#    B_cf2, Area = test_basinfileconfig(BZs={'S51': 'BZ 1'}, B_cf=B_cf1)
#    CheckNetworkConfig(B_cf2, Area)
#
#    logger.info("==\nTest: S2='BZ 2a' -> S2='BZ 1' rest default\n===")
#    B_cf, Area = test_basinfileconfig({'S2': 'BZ 2a'})
#    CheckNetworkConfig(B_cf, Area)
#    B_cf1, Area = test_basinfileconfig(BZs={'S2': 'BZ 1'}, B_cf=B_cf)
#    CheckNetworkConfig(B_cf1, Area)
#  
#    logger.info("==\nTest: S2='BZ 3' S6='BZ 2' -> S2='BZ 1' S6='BZ 1' rest default\n===")
#    B_cf, Area = test_basinfileconfig({'S2': 'BZ 3', 'S6':'BZ 2'})
#    CheckNetworkConfig(B_cf, Area)
#    B_cf1, Area = test_basinfileconfig({'S2': 'BZ 1', 'S6':'BZ 1'}, B_cf=B_cf)
#    CheckNetworkConfig(B_cf1, Area)
#  
#    logger.info("==\nTest: S4='BZ 5' and S51='BZ 2' rest default\n===")
#    B_cf, Area = test_basinfileconfig({'S4': 'BZ 5', 'S51':'BZ 2'})
#    CheckNetworkConfig(B_cf, Area)
#
#    logger.info("==\nTest: S4='BZ 5', S51='BZ 2' and S3='BZ 0' rest default\n===")
#    B_cf, Area = test_basinfileconfig({'S3':'BZ 0', 'S4': 'BZ 5', 'S51':'BZ 2'}) #This should not be possible as there will be no source for all the areas Puddel Wuertelbierg Ahn
#    CheckNetworkConfig(B_cf, Area)
#    CheckNetworkConfig(B_cf, Area) #This second run should detect the missing consumption areas
#
#    logger.info("==\nTest: S4='BZ 9' and S51='BZ 2' rest default\n===")
#    B_cf, Area = test_basinfileconfig({'S4': 'BZ 9', 'S51':'BZ 2'})
#    CheckNetworkConfig(B_cf, Area)
#
#    logger.info("==\nTest: S1='BZ 2' rest default\n===")
#    B_cf, Area = test_basinfileconfig({'S1': 'BZ 2',})
#    CheckNetworkConfig(B_cf, Area)
#    logger.info("==\nTest: S1='BZ 2' -> S1='BZ 1' rest default\n===")
#    B_cf2, Area = test_basinfileconfig(BZs={'S1': 'BZ 1',}, B_cf=B_cf)
#    CheckNetworkConfig(B_cf2, Area)
#    
    
    
    logger.info("==\nTest: S4='BZ 3' rest default\n===")
    B_cf2, Area = test_basinfileconfig({'S4': 'BZ 3',}, B_cf=B_cf)
    CheckNetworkConfig(B_cf2, Area)

    logger.handlers = []
    logging.shutdown()