# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 10:33:28 2013

@author: fiorelli
"""

import pickle
import csv
import sys
import numpy as np


ControlMethod = 'GPC'    
ControlMethod = '2LvlsOnOff' 
    
ResultFile = 'Pattern_high_flow'    
#ResultFile = 'LLC_20d'
#ResultFile = 'LHC_20d'
#ResultFile = 'GHC_20d'
#ResultFile = 'LISTshowroom_Scenario_All'

(VOL, IN, OUT, INsim, SP, ZArea, DTZ, DC, DTC, ResDayVol, Date_x, unitConv ) = pickle.load( open( "Results_" + ControlMethod + "_" + ResultFile + ".p", "rb" ) ) 
 
#[m3], [m3/cp]  

Datestr_x = [val.strftime("%d-%m-%Y %H:%M:%S") for val in Date_x] 
DC=np.array(DC)
DTC=np.array(DTC)
DTC = DTC.reshape(len(DTC),1)
DummyCol = 0*DTC

#ToXL = np.hstack((SP,DummyCol, VOL,DummyCol, OUT,DummyCol, ZArea,DummyCol, IN,DummyCol, INsim,DummyCol, DC,DummyCol, DTC))
ToXL = np.hstack((SP,  VOL,  OUT,  ZArea,  IN,  INsim,  DC,  DTC))
#ToXL.tofile('foo.csv',sep=',',format='%8.3f')


#rows=zip(Datestr_x,ToXL)



csvfile = open("Results_" + ControlMethod + "_" + ResultFile + ".csv",'wb')

f = csv.writer(csvfile,delimiter=',')

Var = ['SP_','VOL_',  'OUT_',  'ZArea_',  'INcommand_',  'IN_',  'DailyIN_', ]
Tk = ['Sauer', 'Alzette', 'Mousel']

Header = ['Datestr_x']
for v in Var:
    for t in Tk:
        Header.append(v+t)
Header.append('DailyVolFromProvider_')

f.writerow(Header)
#f.writerow(rows)

for kk in range(ToXL.shape[0]):
#    f.writerow([ToXL[kk]])
#    f.writerow([SP[kk], VOL[kk], OUT[kk], ZArea[kk], IN[kk], INsim[kk], DC[kk], DTC[kk]])
    f.writerow([Datestr_x[kk], 
                SP[kk][0],SP[kk][1],SP[kk][2],
                VOL[kk][0],VOL[kk][1],VOL[kk][2],
                OUT[kk][0],OUT[kk][1],OUT[kk][2], 
                ZArea[kk][0],ZArea[kk][1],ZArea[kk][2],  
                IN[kk][0],IN[kk][1],IN[kk][2], 
                INsim[kk][0],INsim[kk][1],INsim[kk][2], 
                DC[kk][0],DC[kk][1],DC[kk][2], 
                DTC[kk][0]])


csvfile.close()
