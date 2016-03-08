
import sys
from os import path

if __name__ == '__main__':
    sys.path[0:0] = ['..',]

from Control.GPCVariablesConfig import EPA_Vars, GPC_SysVars, GPC_StateVars
from ReadWriteDataTest.handleConfig import readConfigJob, readGPCConfig
import ReadWriteDataTest.config as GPCConfig
import OpenOPC

GPCConf = readGPCConfig(path.join('..','ReadWriteDataTest',GPCConfig.GPCConfFile))
OPCServer = GPCConf[0]["Global"]["OPCServer"]
opc = OpenOPC.client()
opc.connect(OPCServer)

#Set the Valves into automatic mode.
# This need sto be done first otherwise some other settings will be ignored.
variables = [('HMI_VanneVM1enAuto_S01',1),
             ('HMI_VanneVM1enAuto_S02',1),
             ('HMI_VanneVM1enAuto_S03',1),]
opc.write(variables)

#Set all the other variables that need to have a specific value at startup.
variables = []
for sti in EPA_Vars:
    variables.extend([(vi['OPC'],0) for vi in EPA_Vars[sti] if vi['OPC'].endswith('_Index')])

for sti in GPC_SysVars:
    variables.extend([(vi['OPC'],0) for vi in GPC_SysVars[sti] if vi['OPC'].endswith('_T0')])

variables.extend([('S0_VdMax',1000),
                  #-- S01 --
                  ("DB102 GPC_S01_Param_AutonomyFactor",1),
                  ("DB102 GPC_S01_Param_VdHistTage",1),
                  ("DB102 GPC_S01_Steuermodus",5),
                  ('DB102 GPC_S01_C01_QMax',50),
                  ('DB102 GPC_S01_C01_VdMax',667),
                  ('DB101 SW_S01_AlmNivMax',5.0),
                  ('DB102 GPC_S01_K1_LMax',4.98),
                  ('DB101 SW_S01_Contr\xf4leLocalMax',4.99),
                  ('DB101 SW_S01_Contr\xf4leLocalMin',4.5),
                  ('DB102 GPC_S01_K1_LResMin',1.02),
                  ('DB101 SW_S01_AlmNivMin',1.0),
                  #-- S02 --
                  ("DB102 GPC_S02_Param_AutonomyFactor",1),
                  ("DB102 GPC_S02_Param_VdHistTage",1),
                  ("DB102 GPC_S02_Steuermodus",5),
                  ('DB102 GPC_S02_C01_QMax',50),
                  ('DB102 GPC_S02_C01_VdMax',222),
                  ('DB101 SW_S02_AlmNivMax',5.0),
                  ('DB102 GPC_S02_K1_LMax',4.98),
                  ('DB101 SW_S02_Contr\xf4leLocalMax',4.99),
                  ('DB101 SW_S02_Contr\xf4leLocalMin',4.5),
                  ('DB102 GPC_S02_K1_LResMin',1.02),
                  ('DB101 SW_S02_AlmNivMin',1.0),
                  #-- S03 --
                  ("DB102 GPC_S03_Param_AutonomyFactor",1),
                  ("DB102 GPC_S03_Param_VdHistTage",1),
                  ("DB102 GPC_S03_Steuermodus",5),
                  ('DB102 GPC_S03_C01_QMax',50),
                  ('DB102 GPC_S03_C01_VdMax',333),
                  ('DB101 SW_S03_AlmNivMax',5.0),
                  ('DB102 GPC_S03_K1_LMax',4.98),
                  ('DB101 SW_S03_Contr\xf4leLocalMax',4.99),
                  ('DB101 SW_S03_Contr\xf4leLocalMin',4.5),
                  ('DB102 GPC_S03_K1_LResMin',1.02),
                  ('DB101 SW_S03_AlmNivMin',1.0),

#                  (,),
#                  (,),
                  ])

opc.write(variables)

opc.close()
