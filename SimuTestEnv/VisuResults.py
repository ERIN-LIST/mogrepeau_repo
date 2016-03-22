# -*- coding: utf-8 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
"""
Created on Tue Jun 25 10:33:28 2013
"""

import pickle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
import matplotlib.dates as mdates


ControlMethod = 'GPC'
#ControlMethod = '2LvlsOnOff'

ResultFile = 'LISTshowroom_Scenario_Pattern'
#ResultFile = 'Scen0_Pattern_1D'
#ResultFile = 'Scen1_Winter_Pattern'
#ResultFile = 'Scen2_Summer_Pattern'
#ResultFile = 'Scen3_Fire_Pattern'


(VOL, IN, OUT, INsim, SP, ZArea, DTZ, DC, DTC, ResDayVol, Date_x, unitConv ) = pickle.load( open( "Results_" + ControlMethod + "_" + ResultFile + ".p", "rb" ) )

#[m3], [m3/cp]

plt.interactive = True

plt.ion()

#Behaelter = ["Langwiss","Froumbierg","Wuetelbierg","Puddel","Ahn","PreAhn","Machtum"]

TkName = ['Sauer', 'Alzette', 'Mousel']
VResMin = np.array([  79., 79., 202.])
VMax = np.array([   392., 392., 1005.])

t_x = [date2num(date.replace(tzinfo = None)) for date in Date_x]

idx_D = [idx for idx, val in enumerate(Date_x) if (val.hour==0 and val.minute==0 or idx==0 or idx==len(t_x)-1)]



#--- 4x FIG(3x1) : (IN, VOL, OUT) Simulation vs measurement--------------------
for i in range(len(TkName)):

    plt.figure()

    ax1 = plt.subplot(311)
    plt.title(TkName[i])
    hl11=plt.plot(t_x,INsim[:,i], label='IN simul')
    hl12=plt.plot(t_x,IN[:,i], label='IN command')
    plt.legend(prop={'size':6})
    plt.ylabel('$m^3/15min$')

    plt.subplot(312, sharex=ax1)
    hl21=plt.plot(t_x,VOL[:,i], label='VOL simul')
    hl22=plt.plot(t_x,SP[:,i], label='SetPoint')
    hl23=plt.plot(t_x,VResMin[i]*np.ones(len(SP[:,i])),'r--' )
    hl24=plt.plot(t_x,VMax[i]*np.ones(len(SP[:,i])),'r--' )
    plt.legend(prop={'size':6})
    plt.ylabel('$m^3$')

    plt.subplot(313, sharex=ax1)
    hl31=plt.plot(t_x,OUT[:,i], label='OUT simul')
    plt.legend(prop={'size':6})
    plt.ylabel('$m^3/15min$')

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gcf().autofmt_xdate()

plt.show()
#------------------------------------------------------------------------------



#--- FIG(2x2) : (VOL, SP) Simulation vs measurement (only for Volume)----------
plt.figure()
ax_id=0
for i in range(len(TkName)):
    ax_id+=1
    if ax_id!=1:
        plt.subplot(1,3,ax_id, sharex=ax1)
    else :
        ax1 = plt.subplot(1,3,ax_id)

    hl21=plt.plot(t_x,VOL[:,i])
    hl22=plt.plot(t_x,SP[:,i])
    hl23=plt.plot(t_x,VResMin[i]*np.ones(len(SP[:,i])),'r--' )
    hl24=plt.plot(t_x,VMax[i]*np.ones(len(SP[:,i])),'r--' )
    plt.title(TkName[i])

plt.show()

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
plt.gca().xaxis.set_major_locator(mdates.DayLocator())
plt.gcf().autofmt_xdate()
#------------------------------------------------------------------------------





#--- FIG(2x2) : (VOL, SP) Normalized [Vmin Vmax]-------------------------------
plt.figure()
ax_id=0
for i in range(len(TkName)):
    ax_id+=1
    if ax_id!=1:
        plt.subplot(1,3,ax_id, sharex=ax1)
    else :
        ax1 = plt.subplot(1,3,ax_id)

    hl21=plt.plot(t_x, (VOL[:,i]-VResMin[i])/(VMax[i]-VResMin[i])   )
    hl22=plt.plot(t_x, (SP[:,i]-VResMin[i])/(VMax[i]-VResMin[i])   )
    hl23=plt.plot(t_x,np.ones(len(SP[:,i])),'r--' )
    hl24=plt.plot(t_x,np.zeros(len(SP[:,i])),'r--' )
    plt.title(TkName[i])

plt.show()

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
plt.gca().xaxis.set_major_locator(mdates.DayLocator())
plt.gcf().autofmt_xdate()
#------------------------------------------------------------------------------



#--- FIG(1x1) : (VOL) Simulation vs measurement -------------------------------
plt.figure()
Show_Meas = 1
for i in range(len(TkName)):

    hl21=plt.plot(t_x, (VOL[:,i]-VResMin[i])/(VMax[i]-VResMin[i]), label=TkName[i]   )
#    hl22=plt.plot(t_x, (SP[:,i]-VResMin[i])/(VMax[i]-VResMin[i]),'--'   )
#    hl23=plt.plot(t_x,np.ones(len(SP[:,i])),'r--' )
#    hl24=plt.plot(t_x,np.zeros(len(SP[:,i])),'r--' )
    plt.legend()


    plt.show()

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gcf().autofmt_xdate()

#------------------------------------------------------------------------------





#--- FIG(2x1) : (Total Stocked Volume, Daily Volume form SIDERE) Simulation vs measurement--------
plt.figure()
Show_Meas = 1
ax1 = plt.subplot(211)
Vstock = np.nansum(VOL-VResMin, axis=1)

hl11=plt.plot(t_x,Vstock, label='Stocked Volume')

plt.title('Total available Volume in tanks')


plt.subplot(212, sharex=ax1)
hl31=plt.plot(t_x,DTC, label='Daily Consumption')
#hl31=plt.plot(t_x,DC)

hl32=plt.plot(t_x,ResDayVol)
plt.title('Daily water conveyance from SIDERE')
#------------------------------------------------------------------------------




#--- FIG(2x2) : (IN, OUT VOL, Daily IN_sidere) Simulation----------------------
plt.figure()
ax1 = plt.subplot(221)
#hl11=plt.plot(IN, label='IN command')
hl12=plt.plot(t_x,INsim, label='IN simul')
plt.legend(TkName)
plt.title('IN simul')

plt.subplot(222, sharex=ax1)
hl21=plt.plot(t_x,VOL, label='VOL simul')
hl22=plt.plot(t_x,SP, label='SetPoint')
#plt.legend()
plt.title('VOL simul, Setpoint')

plt.subplot(223, sharex=ax1)
hl31=plt.plot(t_x,OUT, label='OUT simul')
#plt.legend()
plt.title('OUT simul')

plt.subplot(224, sharex=ax1)
hl31=plt.plot(t_x,DTC, label='Daily Consumption')
hl31=plt.plot(t_x,DC)
hl32=plt.plot(t_x,ResDayVol)


plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
plt.gca().xaxis.set_major_locator(mdates.DayLocator())
plt.gcf().autofmt_xdate()

#plt.legend()
plt.title('Daily water conveyance')
plt.show()
#------------------------------------------------------------------------------




#--- FIG(4x2) : (IN, OUT VOL, Daily IN_sidere) Simulation----------------------

f, axarr = plt.subplots(4, 2, sharex=True)

for tk in range(len(TkName)):


    PltCol = tk
    PltRow = 0

    axarr[tk,0].plot(t_x, VOL[:,tk],'.-', label='volume')
    axarr[tk,0].plot(t_x, SP[:,tk],'-r', label='setpoint')
    axarr[tk,0].plot(t_x, VResMin[tk]*np.ones(len(t_x)),'m', label='Vmin')
    axarr[tk,0].plot(t_x, VMax[tk]*np.ones(len(t_x)),'m', label='Vmax')
    axarr[tk,0].grid(which='x')
    plt.ylabel('$m3$')

#    axarr[1].plot(t_x,Inflow_GPC, '-b', label='IN_GPC')
    axarr[tk,1].plot(t_x,INsim[:,tk]/unitConv['x/h'], '-c', label='IN')
    #    axarr[1].plot(t_x,Outflow_GPC, '-r', label='OUT_GPC')
    axarr[tk,1].plot(t_x,ZArea[:,tk]/unitConv['x/h'], '-m', label='ZArea')
    axarr[tk,1].set_title(TkName[tk])
    axarr[tk,1].grid(which='x')
    plt.ylabel('$m3/h$')

axarr[0,0].legend(loc='center left',bbox_to_anchor=(0.95,0.5))
axarr[0,1].legend(loc='center left',bbox_to_anchor=(0.95,0.5))



plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
plt.gca().xaxis.set_major_locator(mdates.DayLocator())
plt.gcf().autofmt_xdate()



Vstock = np.nansum(VOL-VResMin, axis=1)
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
#------------------------------------------------------------------------------





#--- FIG(2x2) : (VOL, SP) Simulation vs measurement (only for Volume)----------
f, axarr = plt.subplots(3, 3, sharex=True)

for i in range(len(TkName)):

    axarr[0,i].plot(t_x,VOL[:,i],label='Volume')
    if ControlMethod == 'GPC':
        axarr[0,i].plot(t_x,SP[:,i],'r',label='Setpoint')
    axarr[0,i].plot(t_x,VResMin[i]*np.ones(len(SP[:,i])),'g--',label='Vmin' )
    axarr[0,i].plot(t_x,VMax[i]*np.ones(len(SP[:,i])),'g--' , label='Vmax')
    axarr[0,i].set_ylim(-0.1*VMax[i],1.1*VMax[i])
    axarr[0,i].set_title(TkName[i])
    axarr[0,i].set_ylabel('$m3$')

#    axarr[1,i].plot(t_x,IN[:,i], '-b', label='IN command GPC')
    axarr[1,i].plot(t_x,INsim[:,i]/unitConv['x/h'], '-r', label='Inflow')
    #    axarr[1].plot(t_x,Outflow_GPC, '-r', label='OUT_GPC')
    axarr[1,i].plot(t_x,ZArea[:,i]/unitConv['x/h'], '-c', label='Flow to consumers ')
    axarr[1,i].set_title(TkName[i])
    axarr[1,i].grid(which='x')
    axarr[1,i].set_ylabel('$m3/h$')

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gcf().autofmt_xdate()

#ax = plt.subplot2grid( (3,3), (2,0), colspan=3)
axarr[2,0].plot(t_x,ResDayVol,':g')
axarr[2,0].step(np.array(t_x)[idx_D],np.array(DTC)[idx_D], '-r', label='Daily volume supplied')
axarr[2,0].step(np.array(t_x)[idx_D],np.array(DTZ)[idx_D], '-c', label='Daily consumption')
axarr[2,0].set_title('Daily water volume supplied from Provider')
axarr[2,0].set_ylabel('$m3$')

plt.gcf().delaxes(axarr[2,1])
plt.gcf().delaxes(axarr[2,2])
plt.draw()

axarr[0,0].legend(loc='lower left')
axarr[1,0].legend(loc='upper left')
axarr[2,0].legend(loc='upper left',bbox_to_anchor=(1.05,0.95))
#
#plt.show()
#
mngr = plt.get_current_fig_manager()
mngr.window.setGeometry(200,38,1333,1000)
plt.tight_layout()
#------------------------------------------------------------------------------
