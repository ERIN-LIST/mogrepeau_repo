# -*- coding: utf-8 -*-
"""
Created on Wed Jul 11 09:52:35 2012


Example of data coming read from OPC server
structured as a dictionary of opcVar objects 

@author: fiorelli
"""
import sys
import numpy as np
import pandas
from dateutil import tz, parser

sys.path[0:0] = ['..',]

from utilities.opcVarHandling import opcVar


#a = opcVar('A',10,'Good',"2012-07-10 18:30:10")
#
#a.value
#a.quality
#
#a.setValue('A',12,'Good',"2012-07-10 18:30:15")
#a.cach[0].value
#a.cach[1].value
#
#x = {'A':a}
#x['A'].value
#x.keys()

def getDataFromDB(dbUrl):
    df =  pandas.read_csv(dbUrl, sep=",")
    
    df.index = [pandas.datetools.to_datetime(di, dayfirst = True) for di in df['Date']+' ' +df['Time']]

    
    return df
    

def Create_Dict_of_OPCVar(dbUrl='data\LISTshowroom_Scenario_Pattern.csv'):
    
#    OUT_DummyVariables = ["S2.S2_QSoll",
#                     "S3.S3_QSoll",
#                     "S4.S4_QSoll",
#                     "S5.S5_QSoll",
#                    ]
#
#    SYS_DummyVariables = ["S1.S1_zd",
#                     "S2.S2_zd",
#                     "S3.S3_zd",
#                     "S4.S4_zd",
#                     "S5.S5_zd",
#                    ]
#    STATE_DummyVariables = ["S0.S0_zLife",
#                     "S0.S0_tUpdate",
#                     "S0.S0_tUpdateTrig",
#                     "S0.S0_VdMax",
#                     "S2.S2_zLife",
#                     "S2.S2_Life",
#                     "S2.S2_K2_VMax",
#                     "S2.S2_VResMin",
#                     "S2.S2_QMax",
#                     "S2.S2_Param_OutDToVSollOben",
#                     "S2.S2_VdMax",
#                     "S3.S3_zLife",
#                     "S3.S3_Life",
#                     "S3.S3_K1_VMax",
#                     "S3.S3_K2_VMax",
#                     "S3.S3_K1_aktiv",
#                     "S3.S3_K2_aktiv",
#                     "S3.S3_VResMin",
#                     "S3.S3_QMax",
#                     "S3.S3_Param_OutDToVSollOben",
#                     "S3.S3_VdMax",
#                     "S4.S4_Param_OutDToVSollOben",
#                     "S4.S4_zLife",
#                     "S4.S4_Life",
#                     "S4.S4_BZ1_BZ3",
#                     "S4.S4_BZ3_BZ1",
#                     "S4.S4_QMax",
#                     "S4.S4_K1_VMax",
#                     "S4.S4_K2_VMax",
#                     "S4.S4_K1_aktiv",
#                     "S4.S4_K2_aktiv",
#                     "S4.S4_VResMin",
#                     "S4.S4_VdMax",
#                     "S5.S5_zLife",
#                     "S5.S5_Life",
#                     "S5.S5_K1_VMax",
#                     "S5.S5_K2_VMax",
#                     "S5.S5_K1_aktiv",
#                     "S5.S5_K2_aktiv",
#                     "S5.S5_VResMin",
#                     "S5.S5_QMax",
#                     "S5.S5_Param_OutDToVSollOben",
#                     "S5.S5_VdMax",
#                     "S99.S99_zLife",
#                     "S99.S99_tUpdateTrig",
#                    ]    

    OUT_DummyVariables = ["S01.S01_C01_T0",
                          "S01.S01_C02_T0",
                          "S01.S01_C03_T0",
                          "S02.S02_C01_T0",                     
                          "S02.S02_C02_T0",  
                          "S03.S03_C01_T0",                                              
                          "S03.S03_C02_T0",
                     ]

    SYS_DummyVariables = ["S01.S01_C01_T",
                     "S01.S01_C03_T",
                     "S01.S01_K1_LIst",
                     "S02.S02_C01_T",
                     "S02.S02_K1_LIst",
                     "S03.S03_C01_T",
                     "S03.S03_K1_LIst",
                    ]
                    
                    
    OUTcopytoSysVariables = ["S01.S01_C01_T0",
                          "S01.S01_C02_T0",
                          "S01.S01_C03_T0",
                          "S02.S02_C01_T0",                     
                          "S02.S02_C02_T0",  
                          "S03.S03_C01_T0",                                              
                          "S03.S03_C02_T0",
                     ]
                     
                     
#    sTmp = "S{0}.S{0}_zd"
#    for sti in ['01','02','03']:
#        SYS_DummyVariables.append(sTmp.format(sti))
        
        
    STATE_DummyVariables = [ "S0.S0_tUpdate",
                             "S0.S0_tUpdateTrig",
                             "S0.S0_VdMax",
                             "S99.S99_zLife",
                             "S99.S99_tUpdateTrig",
                             "S01.S01_Param_AutonomyFactor",
                             "S02.S02_Param_AutonomyFactor",
                             "S03.S03_Param_AutonomyFactor",                     
                             "S01.S01_C01_QMax",
                             "S02.S02_C01_QMax",
                             "S03.S03_C01_QMax",
                             "S01.S01_K1_LMax",
                             "S02.S02_K1_LMax",
                             "S03.S03_K1_LMax",
                             "S01.S01_K1_LResMin",
                             "S02.S02_K1_LResMin",
                             "S03.S03_K1_LResMin",
                             "S01.S01_C01_VdMax",
                             "S02.S02_C01_VdMax",
                             "S03.S03_C01_VdMax",
                     ]

            
    OUT_Variables = [ ]
                
    SYS_Variables = ["S01.S01_C02_T",
                     "S02.S02_C02_T",
                     "S03.S03_C02_T",  
                    ]
    STATE_Variables = [ ]           
#    STATE_Variables = ["S1.S1_BZ",
#                       "S2.S2_BZ",
#                       "S2.S2_Autonom_VSollOben",
#                       "S2.S2_Autonom_VHystereseOben",
#                       "S3.S3_BZ",
#                       "S3.S3_Autonom_VSollOben",
#                       "S3.S3_Autonom_VHystereseOben",
#                       "S4.S4_BZ",
#                       "S4.S4_Autonom_VSollOben",
#                       "S4.S4_Autonom_VHystereseOben",
#                       "S5.S5_BZ",
#                       "S51.S51_BZ",
#                       "S5.S5_Autonom_VSollOben",
#                       "S5.S5_Autonom_VHystereseOben",
#                       ]
    
    # Query the data from the Database and build a dataframe object.    
    df = getDataFromDB(dbUrl=dbUrl)
                
    OUT_opcVarsDict = dict()
    SYS_opcVarsDict = dict()
    STATE_opcVarsDict = dict()
     
    # Initializing the OPC Variable dictionary.
    for valeur in OUT_DummyVariables+OUT_Variables:
        OUT_opcVarsDict[valeur]=opcVar(valeur,None,'Good',"2000-01-01 00:00")
#        OUT_opcVarsDict[valeur]=opcVar(valeur,np.NAN,'Good',"2000-01-01 00:00")
    for valeur in SYS_DummyVariables+SYS_Variables:
#        SYS_opcVarsDict[valeur]=opcVar(valeur,None,'Bad',"2000-01-01 00:00")
        SYS_opcVarsDict[valeur]=opcVar(valeur,np.NAN,'Good',"2000-01-01 00:00")
    for valeur in STATE_DummyVariables+STATE_Variables:
#        STATE_opcVarsDict[valeur]=opcVar(valeur,None,'Bad',"2000-01-01 00:00")
        STATE_opcVarsDict[valeur]=opcVar(valeur,None,'Good',"2000-01-01 00:00")
    
    
#    LastBZ51 = "BZ 2"
    
    
    
    
    
    # Loop over the data samples to update the OPC variables
    for ind,ser in df.iterrows():
        tz = pandas.datetools.dateutil.tz
        if ind.tzinfo != None:
            opcDT = ind.to_pydatetime().astimezone(tz.tzutc()).replace(tzinfo=None).isoformat(' ')
        else:
            opcDT = ind.to_pydatetime().replace(tzinfo=tz.tzlocal()).astimezone(tz.tzutc()).replace(tzinfo=None).isoformat(' ')
        
        for valeur in OUT_DummyVariables+SYS_DummyVariables+STATE_DummyVariables:
            varValue = np.NAN
            # Some variables need a usable values for some of the algo implementations
            if valeur == "S0.S0_tUpdate": 
                varValue = 900 # Use the standard value (15min).
            if "_Param_AutonomyFactor" in valeur: 
                varValue = 1 #2 # Use the standard value (2 times the daily consumption).
            if "_QMax" in valeur: 
                DictQMax={"S01.S01_C01_QMax":50,
                     "S02.S02_C01_QMax":50,
                     "S03.S03_C01_QMax":50
                     }
                varValue = DictQMax[valeur] 
            if "_LIst" in valeur: 
                varValue = 4 # [m] see epanet inp file
            if "_C01_T" in valeur: 
                varValue = 0 
            if "_T0" in valeur: 
                varValue = 0 
            if "_VdMax" in valeur: 
                DictVdMax={"S0.S0_VdMax":1000,
                            "S01.S01_C01_VdMax":667,
                            "S02.S02_C01_VdMax":222,
                            "S03.S03_C01_VdMax":333
                            }#(m3/d).
                varValue = DictVdMax[valeur] 
            if "_LMax" in valeur: 
                DictLMax={ "S01.S01_K1_LMax":5,
                            "S02.S02_K1_LMax":5,
                            "S03.S03_K1_LMax":5
                            }#(m).
                varValue = DictLMax[valeur]
            if "_LResMin" in valeur: 
                DictLResMin={ "S01.S01_K1_LResMin":1,
                            "S02.S02_K1_LResMin":1,
                            "S03.S03_K1_LResMin":1
                            }#(m).
                varValue = DictLResMin[valeur]
            if "_BZ" in valeur: 
                varValue = "BZ 1" 
            if valeur == "S98.S98_DateTime": 
                varValue = parser.parse(opcDT).replace(tzinfo=tz.tzutc()) 
                from pytz import timezone
                varValue = varValue.astimezone(timezone('Europe/Luxembourg'))#

                
                
                
                
                
            if valeur in OUT_DummyVariables:
                OUT_opcVarsDict[valeur].setValue(valeur,varValue,'Good',opcDT)
            if valeur in SYS_DummyVariables:
                SYS_opcVarsDict[valeur].setValue(valeur,varValue,'Good',opcDT)
            if valeur in STATE_DummyVariables:
                STATE_opcVarsDict[valeur].setValue(valeur,varValue,'Good',opcDT)           
            
            
            
            
            
            
        for valeur in OUT_Variables+SYS_Variables+STATE_Variables:
            if valeur == "S51.S51_BZ" or not(np.isnan(ser[valeur[4:]])) :
                Qual='Good'
            else:
                Qual='Bad'
                ser[valeur[4:]]=0;Qual='Good'
             
            if valeur[-2:]== "_T" or valeur[-3:]== "_T0": 
                NK = 2
            else :
                NK = 0    
             
            if valeur in OUT_Variables:
                OUT_opcVarsDict[valeur].setValue(valeur,10**(-NK)*ser[valeur[4:]],Qual,opcDT) # Changed to avoid numpy array data in the opc value.
            elif valeur in SYS_Variables:
                SYS_opcVarsDict[valeur].setValue(valeur,10**(-NK)*ser[valeur[4:]],Qual,opcDT) # Changed to avoid numpy array data in the opc value.
#            elif valeur in STATE_Variables:
#                if "_BZ" in valeur: 
#                    
#                    if valeur == "S51.S51_BZ":
#                        if ser["S5_In5_z"] ==0 :
#                            varValue = LastBZ51
#                        elif ser["S6_InOut6_2_1_z"]:
#                            varValue = "BZ 1"
#                        else :
#                            varValue = "BZ 2"
#                        LastBZ51 = varValue
#                    else :
#                        varValue = "BZ "+str(int(ser[valeur[4:]]))    
#                    
#                    if varValue == 'BZ -1':
#                        varValue = (STATE_opcVarsDict[valeur].getCached()).Value
#                    STATE_opcVarsDict[valeur].setValue(valeur,varValue,Qual,opcDT) 
#                    
#                else:
#                    STATE_opcVarsDict[valeur].setValue(valeur,ser[valeur[4:]],Qual,opcDT) # Changed to avoid numpy array data in the opc value.     
#           

        for valeur in OUTcopytoSysVariables:
            SYS_opcVarsDict[valeur]= OUT_opcVarsDict[valeur]

        yield OUT_opcVarsDict, SYS_opcVarsDict, STATE_opcVarsDict

