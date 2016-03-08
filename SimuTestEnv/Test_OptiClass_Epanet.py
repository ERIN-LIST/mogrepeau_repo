# -*- coding: utf-8 -*-
"""
Created on August 2015
Program used to Test GPC for LIST Showroom based on the version programmed for Junglinster
@author: fiorelli


"""

def err(e):
    if(e>0):
        print e, et.ENgeterror(e,25)
    #        sys.exit(5)
        sys.exit("some error message")
        
        
if __name__ == "__main__":
    import sys
    import numpy as np
    #import pandas
    import logging
    import logging.handlers
    import datetime
    
    sys.path[0:0] = ['../ReadWriteDataTest',]
    sys.path[0:0] = ['..',]
    
    import Control.MPCAlgos as MPCAlgos
    from handleConfig import readGPCConfig
    from Create_Dict_of_OPCVar import Create_Dict_of_OPCVar
    from Control.GPCVariablesConfig import GPC_Stations
    from utilities.opcVarHandling import opcVar
    from pytz import timezone
    TZ = timezone('Europe/Luxembourg')
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logging.getLogger("Control.MPCAlgos").addHandler(ch)
    logging.getLogger("Control.MPCAlgos").setLevel(logging.DEBUG)
    GPCAlglogRF = logging.handlers.RotatingFileHandler( 
                    filename='GPCAlgo.log', mode='a', 
                    backupCount=10, maxBytes=1000000 )
    GPCAlglogRF.setLevel(logging.DEBUG)
    logging.getLogger("Control.MPCAlgos").addHandler(GPCAlglogRF)
    
    
    
    GPCConf = readGPCConfig('../ReadWriteDataTest/GPCAlgoConf.ini')
    config = dict(zip(("Tree","Valid"),GPCConf))


    ControlMethod = 'GPC'    
#    ControlMethod = '2LvlsOnOff'  

    
    dbFile = 'data\LISTshowroom_Scenario_Pattern.csv'
    dbFile = 'data\Scen0_Pattern_1D.csv'
    dbFile = 'data\Scen1_Winter_Pattern.csv'
    dbFile = 'data\Scen2_Summer_Pattern.csv'
    dbFile = 'data\Scen3_Fire_Pattern.csv'

    dbStep = 3600

    iterator = Create_Dict_of_OPCVar(dbUrl=dbFile)
    OutVarsDB,SysVarsDB,StateVarsDB = iterator.next()
    import copy
    #*VarsDB [ScenarioDB-->EPANET]  // *Vars [EPANET-->GPC]
    OutVars = copy.deepcopy(OutVarsDB)
    SysVars = copy.deepcopy(SysVarsDB)  
    StateVars = copy.deepcopy(StateVarsDB)  
    OutVarsDB,SysVarsDB,StateVarsDB = iterator.next()
    
    OPCDT = StateVarsDB.items()[0][1].dt
    StateVarsDB["S98.S98_DateTime"]=opcVar("S98.S98_DateTime",OPCDT.astimezone(TZ),'Good',OPCDT.isoformat())
    
    t_start = 3600*OPCDT.astimezone(TZ).hour+ 60*OPCDT.astimezone(TZ).minute+ OPCDT.astimezone(TZ).second    
#    t_start = 0
    
    #'controlled', 'maintenance', 'offline'
    SysGPCState= {'S0': 'controlled',
                  'S01': 'controlled',
                  'S02': 'controlled', 
                  'S03': 'controlled'}
           
    #SysModes: { 'S3': {'Update': False, 'Mode': u'BZ 1'}, 
    #            'S2': {'Update': False, 'Mode': u'BZ 1'}, 
    #            'S1': {'Update': False, 'Mode': u'BZ 1'}, 
    #            'S5': {'Update': False, 'Mode': u'BZ 1'}, 
    #            'S4': {'Update': False, 'Mode': u'BZ 1'},
    #            'S51': {'Update': False, 'Mode': u'BZ 1'}}       
    
    
    
    
    
    MPCmode = config["Tree"]["MPC"]["mode"]
    MPCmode = "Opti"
    algo = MPCAlgos.__dict__[MPCmode](config['Tree']["MPC_"+MPCmode],
                                        sysVars = SysVarsDB,
                                        stateVars = StateVarsDB,
                                        )
    
    
    
    algo.updateBasinConf(SysGPCState)
    
    
    Date_x=[]
    
 
    IN =[]
    INsim =[]
    OUT =[]
    IN_ot=[]
    VOL =[]
    SP = []
    PS_Vol = []
    
    
    sTmp = "S{0}.S{0}_C{1}_T"
    ActName=[] #should be coherent with VirtActOUT* in MPCAlgos
    ActName.append(sTmp.format("02","01"))#S
    ActName.append(sTmp.format("03","01"))#A
    ActName.append(sTmp.format("01","01"))#M

    
    ConsName = [] #should be coherent OUT* in MPCAlgos
    for C_id in ["02"]:
        ConsName.append(sTmp.format("02",C_id))#S
    for C_id in ["02"]:
        ConsName.append(sTmp.format("03",C_id))#A
    for C_id in ["02"]:
        ConsName.append(sTmp.format("01",C_id))#M


    ConsNameSIM = ['S02_C02',
                   'S03_C02',
                   'S01_C02',
                 ]
            
    RoundingErr = np.zeros(len(ConsName))       
            
    CurrentDailyCons=0
    CurrentDailyZCons=0
    ResDayVol =  []
    
    
    DC = [np.zeros(algo.NbTank)]
    DCons = np.zeros(algo.NbTank)
    DTC = [0,]  
    DTZ = [0,]
    
    
    VOLOPC = []
    ZArea=[]
    
    
    
    Nloop = 0
     
    
    
    
    
    
    
        
    from epanettools import epanet2 as et
    ret=et.ENopen("ShowroomWN_V001.inp","ShowroomWN_V001.rpt"," ")
    err(ret)
    
    
    ret,NbControlRules = et.ENgetcount(et.EN_CONTROLCOUNT)
    err(ret)
    print "hard coded + tanks order MUST be the same in inp and SysGPCState"
    if ControlMethod == 'GPC':
        for station,mode in SysGPCState.iteritems():
            if mode=='controlled' and station!='S0':
                cr = int(station[-1])-1
                ret = et.ENsetcontrol(2*cr+1,0,0,0,0,0)
                err(ret)
                ret = et.ENsetcontrol(2*cr+2,0,0,0,0,0)
                err(ret)
        
    
    ret,NbPat = et.ENgetcount(et.EN_PATCOUNT)
    err(ret)
    for k in range(NbPat):
        ret,LenPat = et.ENgetpatternlen(k+1)
        err(ret)
        for n in range(LenPat):
            ret = et.ENsetpatternvalue(k+1,n+1,1)
            err(ret)
            
#    ret = et.ENsettimeparam( et.EN_DURATION, long(150)*3600 ) #this scenario : 145 hours 
#    err(ret)    
    
#    algo.conf['ControlTimeperiod'] =  StateVarsDB["S0.S0_tUpdate"].value
    Tcp = algo.conf['ControlTimeperiod']/3600.0 #hour
    Epanet_step = min(algo.conf['ControlTimeperiod'],dbStep)
#    Epanet_step = 900
    # it still remains a gap betwenn Epanet and GPC of 1 hydstep : keep it smallest as possible
#    ret  = et.ENsettimeparam( et.EN_HYDSTEP, long(Epanet_step) ) 
#    err(ret)  
    ret  = et.ENsettimeparam( et.EN_REPORTSTEP, long(Epanet_step) ) 
    err(ret)  
    
    
    time=[]
    timeq=[]
              
                             
    ret,nnodes=et.ENgetcount(et.EN_NODECOUNT)
    nodes=[]
    pres=[]
    actdemand = []
    sourcetracing=[]
    for index in range(1,nnodes+1):
            ret,t=et.ENgetnodeid(index)
            nodes.append(t)
            pres.append([])
            actdemand.append([])
            sourcetracing.append([])

    print "\n Nodes : "
    print nodes
    
    
    ret,nlinks=et.ENgetcount(et.EN_LINKCOUNT)
    links=[]
    flow=[]
    speed=[]
    for index in range(1,nlinks+1):
            ret,t=et.ENgetlinkid(index)
            links.append(t)
            flow.append([])
            speed.append([])

    print "\n Links : "
    print links
    
    
    
  #===INITIALISATION
    et.ENsetnodevalue(et.ENgetnodeindex('S01')[1], et.EN_TANKLEVEL, SysVars['S01.S01_K1_LIst'].value),
    et.ENsetnodevalue(et.ENgetnodeindex('S02')[1], et.EN_TANKLEVEL, SysVars['S02.S02_K1_LIst'].value),
    et.ENsetnodevalue(et.ENgetnodeindex('S03')[1], et.EN_TANKLEVEL, SysVars['S03.S03_K1_LIst'].value),

    print "init actionneur also ?"
#================== 
        
        
    
    #Open the hydraulics solver 
    err(et.ENopenH())
    err(et.ENinitH(1))
    
    
    TDataYield = np.array([-1,-0.001]) + t_start/3600.
    TGPC_iter = 0 + t_start/3600.
    RunVar =True
    
    ChangeDay=False
        
#------ Start simulation loop--------------------------------------------------    
    while RunVar :
        
        

        Q15 = np.zeros(len(ConsNameSIM))
        PS_out15 = np.zeros(algo.N_decvar)
        Tstep15 = 0
        
    #-------- loop to step through a value generator---------------------------
        for OutVarsDB,SysVarsDB,StateVarsDB in Create_Dict_of_OPCVar(dbUrl=dbFile):
        
            Nloop += 1
            if Nloop <=2:
                OutVars = copy.deepcopy(OutVarsDB)
                SysVars = copy.deepcopy(SysVarsDB)  
                StateVars = copy.deepcopy(StateVarsDB)  
                continue
            
#            if Nloop >50:
#                Nloop -=1
#                RunVar = False
#                break
        




        #------ Retrieve current consumption-----------------------------------
            sTmp = "S{0}.S{0}_C{1}_T"
            AreaVal = lambda sti,ki: np.float(SysVarsDB[sTmp.format(sti,'%s'%ki if ki else '')].getDiff().Diff[0]) 
    
            AreaName = ['C_Mittal',            
                     'C_Redange',
                     'C_Esch',]
                     
            AreaCons = np.array([AreaVal("01","02"),
                                AreaVal("02","02"),
                                AreaVal("03","02"),])
        #--------------------------------------------------------------------
            for idx,val in enumerate(AreaName): 
                et.ENsetnodevalue(et.ENgetnodeindex(val)[1], et.EN_BASEDEMAND, AreaCons[idx] ) 
                                
            
            TDataYield += dbStep/3600.
#            while not time or time[-1] < TDataYield[1]-Tcp :
            while not time or ('tstep' in locals() and (time[-1]+tstep/3600.) <= TDataYield[1]) :
        
                ret,t=et.ENrunH()
#                print (float(t)/3600)
                time.append(float(t+t_start)/3600)
            #------ Retrieve hydraulic results for time t ---------------------
                for  i in range(0,len(nodes)):
                    ret,p=et.ENgetnodevalue(i+1, et.EN_PRESSURE )
                    pres[i].append(p)
                    ret,d=et.ENgetnodevalue(i+1, et.EN_DEMAND )
                    actdemand[i].append(d)
                    
                for  i in range(0,len(links)):
                    ret,f=et.ENgetlinkvalue(i+1, et.EN_FLOW)
                    flow[i].append(f)
                    ret,s=et.ENgetlinkvalue(i+1, et.EN_SETTING )
                    speed[i].append(s)
            #------------------------------------------------------------------
            
            
            #------- Incremental Variables ------------------------------------
                if 'tstep' in locals() or 'tstep' in globals():

#                #------ set time variable-------------------- -----------------    
#                    OPCDT = StateVars["S98.S98_DateTime"].dt+datetime.timedelta(0,tstep)                
#                    StateVars["S98.S98_DateTime"].setValue("S98.S98_DateTime",OPCDT.astimezone(TZ),'Good',OPCDT.isoformat())
#    
#
#                    S4_zLifeD = StateVars["S98.S98_DateTime"].getDiff()
#                    if S4_zLifeD.LocalDT.day - (S4_zLifeD.LocalDT - S4_zLifeD.TimeDiff[0]).day in [1,-27,-28,-29,-30]:
#                        ChangeDay = True
                    if np.floor_divide(time[-2],24) != np.floor_divide(time[-1],24):
                        ChangeDay = True
#
#                #--------------------------------------------------------------        


        
                    TempQ15 = tstep/3600.*np.array([ flow[et.ENgetlinkindex(val)[1]-1][-1] for val in ConsNameSIM])                 
                    Q15 += TempQ15
                                                                           
                    # dec var :   ['Sauer', 'Alzette', 'Mousel']
                    TempPS_out =  tstep/3600.*np.array([ flow[et.ENgetlinkindex('S02_C01')[1]-1][-1],
                                         flow[et.ENgetlinkindex('S03_C01')[1]-1][-1],
                                         flow[et.ENgetlinkindex('S01_C01')[1]-1][-1],])                   
                    PS_out15 += TempPS_out
                    Tstep15 += tstep    
                     
            #------------------------------------------------------------------
           
                
                
                
                
                
                if time[-1] >= TGPC_iter : #trigger GPC control loop
                
                    
            
                    
                    if 'tstep' in locals() or 'tstep' in globals():
                        
                    #------ set time variable----------------------------------    
                        OPCDT = StateVars["S98.S98_DateTime"].dt+datetime.timedelta(0,Tstep15)                
                        StateVars["S98.S98_DateTime"].setValue("S98.S98_DateTime",OPCDT.astimezone(TZ),'Good',OPCDT.isoformat())
        
    
#                        S4_zLifeD = StateVars["S98.S98_DateTime"].getDiff()
#                        if S4_zLifeD.LocalDT.day - (S4_zLifeD.LocalDT - S4_zLifeD.TimeDiff[0]).day in [1,-27,-28,-29,-30]:
#                            ChangeDay = True
    
                    #----------------------------------------------------------


                    #------ set OPC variables represented flows----------------
                        for idx,val in enumerate(ActName) :
                            if val is 'None'  :# or val =='S10.S10-C5-T_ival' : 
                                continue
                            SysVars[val].setValue(val,0.01*round(100*(SysVars[val].value+PS_out15[idx])),'Good',OPCDT.isoformat()) 
                        
                        SysVars['S01.S01_C03_T'].setValue('S01.S01_C03_T',SysVars['S02.S02_C01_T'].value,'Good',OPCDT.isoformat())                        
                        
                        for idx,val in enumerate(ConsName) :
                            if val not in ActName:
                                Val_real = 100*(SysVars[val].value+Q15[idx])
                                Val_int = 100*SysVars[val].value+round(100*Q15[idx]-RoundingErr[idx])
                                RoundingErr[idx] = RoundingErr[idx]+Val_int-Val_real
                                SysVars[val].setValue(val,0.01*Val_int,'Good',OPCDT.isoformat())
                    #----------------------------------------------------------    

                    #------ Update current daily consumption-------------------
                        DCons = DCons + PS_out15
                        CurrentDailyCons += np.sum(PS_out15[np.array([1,2])])
                        CurrentDailyZCons += np.sum(Q15)
                        
                        DC.append(DCons)
                        DTC.append(CurrentDailyCons)
                        DTZ.append(CurrentDailyZCons)
                        
                        if ChangeDay:                                   
                            DCons = np.zeros(algo.NbTank)
                            CurrentDailyCons=0
                            CurrentDailyZCons=0
                    #----------------------------------------------------------     
                        
                        
                    
                    else :
                    #------ init OPC variables representing date---------------                    
                        OPCDT = StateVars.items()[0][1].dt
                        StateVars["S98.S98_DateTime"]=opcVar("S98.S98_DateTime",OPCDT.astimezone(TZ),'Good',OPCDT.isoformat())
                    #----------------------------------------------------------

                    #------ init OPC variables representing flow for actuators--
                        for idx,val in enumerate(ActName) :
                            if val is 'None' : #or val =='S10.S10-C5-T_ival' : 
                                continue
#                            SysVars[val].setValue(val,0,'Good',OPCDT)
                            SysVars[val].setValue(val,SysVars[val].value,'Good',OPCDT.isoformat())   
                    #----------------------------------------------------------

                    print StateVars["S98.S98_DateTime"].dtLoc
                    Date_x.append(StateVars["S98.S98_DateTime"].dtLoc)
            
                    ResDayVol.append(StateVars["S0.S0_VdMax"].value)                   
                            
                   
                    
                #------- Reset Incremental Variables --------------------------
                    Q15 = 0
                    PS_out15 = np.zeros(algo.N_decvar)
                    Tstep15 = 0

                    TGPC_iter = Tcp*(1+np.floor_divide(time[-1],Tcp))
                #--------------------------------------------------------------
                    

                    
                #------ update OPC variables representing levels---------------
                    if VOL:
                        SysVars['S01.S01_K1_LIst'].setValue('S01.S01_K1_LIst',et.ENgetnodevalue(et.ENgetnodeindex('S01')[1], et.EN_PRESSURE)[1],'Good',OPCDT.isoformat())
                        SysVars['S02.S02_K1_LIst'].setValue('S02.S02_K1_LIst',et.ENgetnodevalue(et.ENgetnodeindex('S02')[1], et.EN_PRESSURE)[1],'Good',OPCDT.isoformat())
                        SysVars['S03.S03_K1_LIst'].setValue('S03.S03_K1_LIst',et.ENgetnodevalue(et.ENgetnodeindex('S03')[1], et.EN_PRESSURE)[1],'Good',OPCDT.isoformat())
                #--------------------------------------------------------------


                 #------ run MPCAlgos -----------------------------------------
                    try :
                        [INc , IN_opc, OUT_opc, VOL_opc, ZArea_iter] = algo.run(SysVars,StateVars,OutVars)
                        
                    except :
#                        [INc , IN_opc, OUT_opc, VOL_opc, ZArea_iter] = algo.run(SysVars,StateVars,OutVars)
                        print "Except"
                        
                    VOLOPC.append(VOL_opc)        
                    ZArea.append(ZArea_iter)   
                    

                #--------------------------------------------------------------
                    
                #------ store results------------------------------------------
                    OUT_opc = OUT_opc # [m3/cp]
                    IN.append(INc)      #[m3/cp]
                    INsim.append(IN_opc)
                    OUT.append(OUT_opc) #[m3/cp]
                    SP.append(algo.SP)
                    VOL.append(VOL_opc) #Volsim = VOL_opc
                #--------------------------------------------------------------

                    if ChangeDay:       
                        for val in SysVars:
                            if val[-2:]=='T0':
                                SysVars[val].setValue(val,SysVars[val[:-1]].value,'Good',OPCDT.isoformat())
                        ChangeDay = False        
                    
                #----------------SIMULATION------------------------------------      
                    #JUNCTIONS
#                    print "Step Scenario is synchronized with step GPC"
#                    for idx,val in enumerate(AreaName): 
#                        et.ENsetnodevalue(et.ENgetnodeindex(val)[1], et.EN_BASEDEMAND, AreaCons[idx] )            
    
                    if ControlMethod == 'GPC':             
                        # VALVES
                        OnOffAction = INc /algo.unitConv['x/h']
                        print "Hard Coded --> Must be changed"
                        VSupplyEst = (OnOffAction[1]+OnOffAction[2])*algo.unitConv['x/h']
                        if algo.VRemaining < VSupplyEst and algo.VRemaining>0:
                            OnOffAction[np.array([1,2])] = OnOffAction[np.array([1,2])]*algo.VRemaining/VSupplyEst
                        # dec var :   ['Sauer', 'Alzette', 'Mousel']
                        for idx,val in enumerate(algo.Actuator):
                            if algo.idx_VARcont[idx]:
                                tk = val.split(' ---> ')[1]
                                st = GPC_Stations[tk]
                                et.ENsetlinkvalue(et.ENgetlinkindex(st + '_C01')[1], et.EN_SETTING, OnOffAction[idx] )
#        for sti in gpcSysState:
#            Bi = StiMap[sti]
#            if self.B_cf.has_key(Bi):    
#                        if SysGPCState['S02']=='controlled':
#                            et.ENsetlinkvalue(et.ENgetlinkindex('S02_C01')[1], et.EN_SETTING, OnOffAction[0] )
#                        if SysGPCState['S03']=='controlled':
#                            et.ENsetlinkvalue(et.ENgetlinkindex('S03_C01')[1], et.EN_SETTING, OnOffAction[1] )
#                        if SysGPCState['S01']=='controlled':
#                            et.ENsetlinkvalue(et.ENgetlinkindex('S01_C01')[1], et.EN_SETTING, OnOffAction[2] )
                #--------------------------------------------------------------
            
            

            #------ determine next simulation step-----------------------------
                ret,tstep=et.ENnextH();
                err(ret)
                if (tstep<=0):
                    break
            #------------------------------------------------------------------
#            
            OutVars = copy.deepcopy(OutVarsDB)
#            SysVars = copy.deepcopy(SysVarsDB)
            StateVarsDB["S98.S98_DateTime"]=StateVars["S98.S98_DateTime"]
            StateVars = copy.deepcopy(StateVarsDB)   
  
    #------ End loop used by generator-----------------------------------------        

        
        RunVar = False 
        print "to do : the simulation could continue a little bit"
#------ End simulation loop----------------------------------------------------        
        
        
        
    IN=np.array(IN)          #[m3/cp]
    INsim = np.array(INsim)  #[m3/cp]
    OUT=np.array(OUT)        #[m3/cp]
    
    VOL=np.array(VOL)
    SP = np.array(SP)
    
    
    
    
    VOLOPC=np.array(VOLOPC)
    ZArea=np.array(ZArea)
    
    
    import pickle
    
    pickle.dump((VOL, IN, OUT, INsim, SP, ZArea, DTZ, DC, DTC, ResDayVol, Date_x, algo.unitConv), open( "Results_" + ControlMethod + "_" + dbFile[5:-4] + ".p", "wb" ) )  
        
    
    Datestr_x = [val.strftime("%d-%m-%Y %H:%M:%S") for val in Date_x]   
    
    DC=np.array(DC)
    DTC=np.array(DTC)
    DTC = DTC.reshape(len(DTC),1)

    DummyCol = 0*DTC
#    ToXL = np.hstack((VOLOPC,DummyCol,VirtualVOL,DummyCol,ZArea,DummyCol,VOL,DummyCol,INsim,DummyCol,DC,DummyCol,DTC,DummyCol,InGPC,DummyCol,VActVol,DummyCol,IN))
    ToXL = np.hstack((VOLOPC,DummyCol,ZArea,DummyCol,INsim,DummyCol,DC,DummyCol,DTC,DummyCol,IN))
    ToCalc = np.vstack((time,flow[-1],flow[2],pres[-2])).T
    ToXL_S2 = ToXL[:,np.array([0,4,8])]
    
    
    
    
    
    
    
    
    
    import matplotlib
#    matplotlib.use("QT4Agg")
    import matplotlib.pyplot as plt
    from matplotlib.dates import date2num
    import matplotlib.dates as mdates
    
    
    plt.ion()
    
    #['Sauer', 'Alzette', 'Mousel']
    LevelNames = ['S02','S03', 'S01']
    
    OUTNames = [['S02_C02'],
                ['S03_C02'],
                ['S01_C02'],]
    OUTNames_GPC = [[],
                [],
                ['S01_C03'],]            
    INNames = [ [],
                [],
                [],]            
    INNames_GPC = [['S02_C01'],
                ['S03_C01'],
                ['S01_C01'], ]  

    
    time = np.array(time)
    pres = np.array(pres)
    flow = np.array(flow)

    
   
# conversion error in ENgetnodevalue EN_TANKDIAM has to be fixed before to use this command  Diam = np.array([et.ENgetnodevalue(et.ENgetnodeindex(Tk)[1], et.EN_TANKDIAM )[1] for Tk in LevelNames])
    Diam = np.array([10,10,16])
    STank = np.pi*(Diam/2)**2    
    
    f, axarr = plt.subplots(2, 3, sharex=True)
    
    for tk in range(algo.NbTank):
        if LevelNames[tk] is 'None':
            continue

        PltCol = tk
        PltRow = 0

        
        i = nodes.index(LevelNames[tk])
        axarr[PltRow, PltCol].plot(time,pres[i]*STank[tk],'.-', label=nodes[i])
#        axarr[PltRow, PltCol].plot(time,VirtualVOL[:,tk],'-c', label="virtual")
#        axarr[PltRow, PltCol].plot(time,SP[:,tk],'-r', label=nodes[i])
        axarr[PltRow, PltCol].plot(time,algo.VResMin[tk]*np.ones(time.shape),'m', label=nodes[i])
        axarr[PltRow, PltCol].plot(time,algo.VMax[tk]*np.ones(time.shape),'m', label=nodes[i])
        axarr[PltRow, PltCol].grid()
    #    axarr[PltRow, PltCol].set_xticks([])
        if tk==2 :
            axarr[PltRow, PltCol].legend(('volume','min','max'),loc='center left',bbox_to_anchor=(0.95,0.5))
        
           
            
        if INNames[tk]:
            Inflow = sum([ flow[links.index(Name)] for Name in INNames[tk] ])
        else:
            Inflow = np.nan*time
        if INNames_GPC[tk]:
            Inflow_GPC = np.array([ flow[links.index(Name)] for Name in INNames_GPC[tk] ]).T
        else:
            Inflow_GPC = np.nan*time
        if OUTNames[tk] :
            Outflow = sum([ flow[links.index(Name)] for Name in OUTNames[tk] ])
        else:
            Outflow = np.nan*time
        if OUTNames_GPC[tk]:
            Outflow_GPC = np.array([ flow[links.index(Name)] for Name in OUTNames_GPC[tk] ]).T
        else:
            Outflow_GPC = np.nan*time
            
        axarr[PltRow+1, PltCol].plot(time,Inflow_GPC, '-b', label='INsim contGPC')
        axarr[PltRow+1, PltCol].plot(time,Inflow, '-c', label='INsim uncont')    
        axarr[PltRow+1, PltCol].plot(time,Outflow_GPC, '-r', label='OUTsim contGPC')
        axarr[PltRow+1, PltCol].plot(time,Outflow, '-m', label='OUTsim uncont')
        
        axarr[PltRow+1, PltCol].grid()
        if tk==2:
            axarr[PltRow+1, PltCol].legend(loc='center left',bbox_to_anchor=(0.95,0.5))
    
    #    axarr[PltRow, PltCol].get_xticklabels(), visible=False)
    #    plt.setp(axarr[PltRow, PltCol].get_xticklabels(), visible=False) 
        axarr[PltRow+1, PltCol].set_title(LevelNames[tk])
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    t_x = [date2num(date.replace(tzinfo = None)) for date in Date_x]
    
    
#    pickle.dump((ToXL,VOLOPC,DummyCol,VirtualVOL,DummyCol,ZArea,DummyCol,INsim,DummyCol,DC,DummyCol,DTC,DummyCol,InGPC,DummyCol,VActVol,DummyCol,IN),open("ResultsSIM_Jung1Y.p","wb"))    
#    D=matplotlib.dates.num2date(t_x)
#    label = [tx.strftime("%a, %d %b %Y %H:%M:%S") for tx in D]
#    import csv
#    with open("output.csv", "wb") as f:
#        writer = csv.writer(f)
#        writer.writerows(label)
        
    
    
    
    
    
    f, axarr = plt.subplots(2, 3, sharex=True)
    
    for tk in range(algo.NbTank):
        

        PltCol = tk
        PltRow = 0
    
        axarr[PltRow, PltCol].plot(t_x, VOLOPC[:,tk],'.-', label='volume')
        axarr[PltRow, PltCol].plot(t_x, SP[:,tk],'-r', label='setpoint')
        axarr[PltRow, PltCol].plot(t_x, algo.VResMin[tk]*np.ones(len(t_x)),'m', label='Vmin')
        axarr[PltRow, PltCol].plot(t_x, algo.VMax[tk]*np.ones(len(t_x)),'m', label='Vmax')
        axarr[PltRow, PltCol].grid()
    #    axarr[PltRow, PltCol].set_xticks([])
        if tk==2 :
            axarr[PltRow, PltCol].legend(loc='center left',bbox_to_anchor=(0.95,0.5))
        
           
            
    
            
    #    axarr[PltRow+1, PltCol].plot(t_x,Inflow_GPC, '-b', label='IN_GPC')
        axarr[PltRow+1, PltCol].plot(t_x,INsim[:,tk], '-c', label='IN')    
    #    axarr[PltRow+1, PltCol].plot(t_x,Outflow_GPC, '-r', label='OUT_GPC')
        axarr[PltRow+1, PltCol].plot(t_x,ZArea[:,tk], '-m', label='ZArea')
        
        axarr[PltRow+1, PltCol].grid()
        if tk==2:
    #        axarr[PltRow+1, PltCol].legend(('IN_GPC', 'INflow', 'OUT_GPC', 'OUTflow',),loc='center left',bbox_to_anchor=(0.95,0.5))
            axarr[PltRow+1, PltCol].legend(loc='center left',bbox_to_anchor=(0.95,0.5))
    
    
    #    axarr[PltRow, PltCol].get_xticklabels(), visible=False)
    #    plt.setp(axarr[PltRow, PltCol].get_xticklabels(), visible=False) 
        axarr[PltRow+1, PltCol].set_title(algo.ConfigTanks[tk])
        
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())
        plt.gcf().autofmt_xdate()
    
    
    
    #                       ['S','A','M']
    UpstreamTk =   np.array([ 2,  99,  99])
    DownstreamTk = np.array([ 0,  1,   2])
    
    
    for DecVar_id in range(algo.N_decvar):
        Tank_up_id = UpstreamTk[DecVar_id]
        Tank_down_id = DownstreamTk[DecVar_id]
        plt.figure()
        for tk in [Tank_up_id,Tank_down_id]: #range(NbTank):
            if tk == 99:
                ax1 = plt.subplot(231)
                continue
            if tk==Tank_up_id:
                ax1 = plt.subplot(231)
                ax1.set_title(algo.ConfigTanks[tk])
            elif tk==Tank_down_id:
                ax2 = plt.subplot(232,sharex=ax1)
                ax2.set_title(algo.ConfigTanks[tk])
                
    
            plt.plot(t_x, algo.VResMin[tk]*np.ones(len(t_x)),'m')
            plt.plot(t_x, algo.VMax[tk]*np.ones(len(t_x)),'m')
            plt.plot(t_x, VOLOPC[:,tk],'.-')   
            plt.plot(t_x, SP[:,tk],'-r')
        #    plt.legend(loc=1, bbox_to_anchor=(1,1))
          
            
            if tk==Tank_up_id:
                ax4 = plt.subplot(234,sharex=ax1)
            elif tk==Tank_down_id:
                ax5 = plt.subplot(235,sharex=ax1)    
            
            plt.plot(t_x, INsim[:,tk], '.-c', label='IN')
            plt.plot(t_x, ZArea[:,tk], '-m', label='ZArea')
        #    plt.legend(loc=1, bbox_to_anchor=(1,1))

            
            
        ax3 = plt.subplot(233,sharex=ax1)

        plt.plot(t_x,IN[:,DecVar_id], label='Command')
        #plt.legend(loc=1, bbox_to_anchor=(1,1))
        

        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
        ax3.xaxis.set_major_locator(mdates.DayLocator())
        plt.gcf().autofmt_xdate()
        



#--- FIG(2x1) : (Total Stocked Volume, Daily Volume form SIDERE) Simulation vs measurement--------
    plt.figure()
    ax1 = plt.subplot(211)
    Vstock = np.nansum(VOL-algo.VResMin, axis=1)
    
    hl11=plt.plot(t_x,Vstock, label='Stocked Volume')
    
    plt.title('Total available Volume in tanks')
    
    
    plt.subplot(212, sharex=ax1)
    hl31=plt.plot(t_x,DTC, label='Daily Consumption')
    #hl31=plt.plot(t_x,DC)
    
    hl32=plt.plot(t_x,ResDayVol)
    plt.title('Daily water conveyance from SIDERE')
    
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gcf().autofmt_xdate()
#------------------------------------------------------------------------------        












    f, axarr = plt.subplots(4, 2, sharex=True)
    
    for tk in range(algo.NbTank):
        

        PltCol = tk
        PltRow = 0
    
        axarr[tk,0].plot(t_x, VOLOPC[:,tk],'.-', label='volume')
        axarr[tk,0].plot(t_x, SP[:,tk],'-r', label='setpoint')
        axarr[tk,0].plot(t_x, algo.VResMin[tk]*np.ones(len(t_x)),'m', label='Vmin')
        axarr[tk,0].plot(t_x, algo.VMax[tk]*np.ones(len(t_x)),'m', label='Vmax')
        axarr[tk,0].grid(which='x')
        plt.ylabel('$m3$')
        
    #    axarr[1].plot(t_x,Inflow_GPC, '-b', label='IN_GPC')
        axarr[tk,1].plot(t_x,INsim[:,tk]/algo.unitConv['x/h'], '-c', label='IN')    
        #    axarr[1].plot(t_x,Outflow_GPC, '-r', label='OUT_GPC')
        axarr[tk,1].plot(t_x,ZArea[:,tk]/algo.unitConv['x/h'], '-m', label='ZArea')
        axarr[tk,1].set_title(algo.ConfigTanks[tk])
        axarr[tk,1].grid(which='x')
        plt.ylabel('$m3/h$')
        
    axarr[0,0].legend(loc='center left',bbox_to_anchor=(0.95,0.5))
    axarr[0,1].legend(loc='center left',bbox_to_anchor=(0.95,0.5))


    
    
    #    axarr[PltRow, PltCol].get_xticklabels(), visible=False)
    #    plt.setp(axarr[PltRow, PltCol].get_xticklabels(), visible=False) 
#    axarr[PltRow+1, PltCol].set_title(algo.ConfigTanks[tk])
        
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gcf().autofmt_xdate()
    
    
    
    

    Vstock = np.nansum(VOL-algo.VResMin, axis=1)
    axarr[3,0].plot(t_x,Vstock, label='Stocked Volume')
    plt.ylabel('$m3$')
    plt.title('Total available Volume in tanks')
    
    
    
    axarr[3,1].plot(t_x,ResDayVol,':r')
    axarr[3,1].plot(t_x,DTC, '-c', label='Daily IN volume')
    axarr[3,1].plot(t_x,DTZ, '-m', label='Daily OUT volume')
    plt.title('Daily water conveyance from SIDERE')
    plt.ylabel('$m3/h$')
    
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gcf().autofmt_xdate()
    
    
#    mngr = plt.get_current_fig_manager()
#    mngr.window.setGeometry(78,29,1842,1051)
#    plt.tight_layout()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
#    
#    f, axarr = plt.subplots(7, 1, sharex=True)
#    
#    for tk in range(algo.NbTank):
#        
#
#        PltCol = tk
#        PltRow = 0
#    
#        axarr[2*tk].plot(t_x, VOLOPC[:,tk],'.-', label='volume')
#        axarr[2*tk].plot(t_x, SP[:,tk],'-r', label='setpoint')
#        axarr[2*tk].plot(t_x, algo.VResMin[tk]*np.ones(len(t_x)),'m', label='Vmin')
#        axarr[2*tk].plot(t_x, algo.VMax[tk]*np.ones(len(t_x)),'m', label='Vmax')
#        axarr[2*tk].grid(which='x')
#        plt.ylabel('m3')
#        
#    #    axarr[1].plot(t_x,tk*10+Inflow_GPC, '-b', label='IN_GPC')
#        axarr[2*tk+1].plot(t_x,INsim[:,tk]/algo.unitConv['x/h'], '-c', label='IN')    
#        #    axarr[1].plot(t_x,tk*10+Outflow_GPC, '-r', label='OUT_GPC')
#        axarr[2*tk+1].plot(t_x,ZArea[:,tk]/algo.unitConv['x/h'], '-m', label='ZArea')
#        axarr[2*tk+1].set_title(algo.ConfigTanks[tk])
#        axarr[2*tk+1].grid(which='x')
#        plt.ylabel('m3/h')
#        
#    axarr[0].legend(loc='center left',bbox_to_anchor=(0.95,0.5))
#    axarr[1].legend(loc='center left',bbox_to_anchor=(0.95,0.5))
#
#
#    
#    
#    #    axarr[PltRow, PltCol].get_xticklabels(), visible=False)
#    #    plt.setp(axarr[PltRow, PltCol].get_xticklabels(), visible=False) 
##    axarr[PltRow+1, PltCol].set_title(algo.ConfigTanks[tk])
#        
#    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
#    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
#    plt.gcf().autofmt_xdate()
#    
#    
#    
#    
#    
#    
#    
#    
#    axarr[6].plot(t_x,ResDayVol,':r')
#    axarr[6].plot(t_x,DTC, '-c', label='Daily IN volume')
#    axarr[6].plot(t_x,DTZ, '-m', label='Daily OUT volume')
#    plt.title('Daily water conveyance from SIDERE')
#    plt.ylabel('m3/h')
#    
#    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
#    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
#    plt.gcf().autofmt_xdate()
#    
#    
#    mngr = plt.get_current_fig_manager()
#    mngr.window.setGeometry(300,38,550,1033)
#    plt.tight_layout()    