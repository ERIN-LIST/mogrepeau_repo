
GPC_OutVars = { 'S01': #GSc: should be ready
               [
                 { 'OPC':"DB102 GPC_S01_C01_QSoll", 'GPC':"S01_C01_QSoll", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S01_C01_VTodayMax", 'GPC':"S01_C01_VTodayMax", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S01_VTodayAim", 'GPC':"S01_GPCSetpoint", 'Access':'rw', },
                 { 'OPC':"GPC_S01_Autonomie", 'GPC':"S01_Autonomie", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S01_C01_Autonom_LMax_GPC", 'GPC':"S01_C01_LMax_GPC", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S01_C01_Autonom_LMin_GPC", 'GPC':"S01_C01_LMin_GPC", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S01_C01_T0", 'GPC':"S01_C01_T0", 'Type':'In', 'NK':2, 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S01_C02_T0", 'GPC':"S01_C02_T0", 'Type':'Out', 'NK':2, 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S01_C03_T0", 'GPC':"S01_C03_T0", 'Type':'Out', 'NK':2, 'Access':'rw', },
                ],
               'S02':
               [ 
                 { 'OPC':"DB102 GPC_S02_C01_QSoll", 'GPC':"S02_C01_QSoll", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S02_C01_VTodayMax", 'GPC':"S02_C01_VTodayMax", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S02_VTodayAim", 'GPC':"S02_GPCSetpoint", 'Access':'rw', },
                 { 'OPC':"GPC_S02_Autonomie", 'GPC':"S02_Autonomie", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S02_C01_Autonom_LMax_GPC", 'GPC':"S02_C01_LMax_GPC", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S02_C01_Autonom_LMin_GPC", 'GPC':"S02_C01_LMin_GPC", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S02_C01_T0", 'GPC':"S02_C01_T0", 'Type':'In', 'NK':2, 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S02_C02_T0", 'GPC':"S02_C02_T0", 'Type':'Out', 'NK':2, 'Access':'rw', },
                ],
               'S03':
               [
                 { 'OPC':"DB102 GPC_S03_C01_QSoll", 'GPC':"S03_C01_QSoll", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S03_C01_VTodayMax", 'GPC':"S03_C01_VTodayMax", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S03_VTodayAim", 'GPC':"S03_GPCSetpoint", 'Access':'rw', },
                 { 'OPC':"GPC_S03_Autonomie", 'GPC':"S03_Autonomie", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S03_C01_Autonom_LMax_GPC", 'GPC':"S03_C01_LMax_GPC", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S03_C01_Autonom_LMin_GPC", 'GPC':"S03_C01_LMin_GPC", 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S03_C01_T0", 'GPC':"S03_C01_T0", 'Type':'In', 'NK':2, 'Access':'rw', },
                 { 'OPC':"DB102 GPC_S03_C02_T0", 'GPC':"S03_C02_T0", 'Type':'Out', 'NK':2, 'Access':'rw', },
                ],
              }

GPC_SysVars = { 'S01': #GSc: GPC should be ready, OPC to be compleated
              [ 
                { 'OPC':"DB102 GPC_S01_C01_T0", 'GPC':"S01_C01_T0", 'Type':'In', 'NK':2, },
                { 'OPC':"DB102 GPC_S01_C01_T", 'GPC':"S01_C01_T", 'Type':'In', 'NK':2, },
                { 'OPC':"DB102 GPC_S01_C02_T0", 'GPC':"S01_C02_T0", 'Type':'Out', 'NK':2, },
                { 'OPC':"DB102 GPC_S01_C02_T", 'GPC':"S01_C02_T", 'Type':'Out', 'NK':2, },
                { 'OPC':"DB102 GPC_S01_C03_T0", 'GPC':"S01_C03_T0", 'Type':'Out', 'NK':2, },
                { 'OPC':"DB102 GPC_S01_C03_T", 'GPC':"S01_C03_T", 'Type':'Out', 'NK':2, },
                { 'OPC':"DB102 GPC_S01_K1_List", 'GPC':"S01_K1_LIst", 'Type':'Vol', }, #GScToDo -feedback M. Beyers List-> LIst
               ],
              'S02':
              [ 
                { 'OPC':"DB102 GPC_S02_C01_T0", 'GPC':"S02_C01_T0", 'Type':'In', 'NK':2, },
                { 'OPC':"DB102 GPC_S02_C01_T", 'GPC':"S02_C01_T", 'Type':'In', 'NK':2, },
                { 'OPC':"DB102 GPC_S02_C02_T0", 'GPC':"S02_C02_T0", 'Type':'Out', 'NK':2, },
                { 'OPC':"DB102 GPC_S02_C02_T", 'GPC':"S02_C02_T", 'Type':'Out', 'NK':2, },
                { 'OPC':"DB102 GPC_S02_K1_List", 'GPC':"S02_K1_LIst", 'Type':'Vol', }, #GScToDo -feedback M. Beyers List-> LIst
               ],
              'S03':
              [ 
                { 'OPC':"DB102 GPC_S03_C01_T0", 'GPC':"S03_C01_T0", 'Type':'In', 'NK':2, },
                { 'OPC':"DB102 GPC_S03_C01_T", 'GPC':"S03_C01_T", 'Type':'In', 'NK':2, },
                { 'OPC':"DB102 GPC_S03_C02_T0", 'GPC':"S03_C02_T0", 'Type':'Out', 'NK':2, },
                { 'OPC':"DB102 GPC_S03_C02_T", 'GPC':"S03_C02_T", 'Type':'Out', 'NK':2, },
                { 'OPC':"DB102 GPC_S03_K1_List", 'GPC':"S03_K1_LIst", 'Type':'Vol', }, #GScToDo -feedback M. Beyers List-> LIst
               ],
             }

GPC_StateVars = { 'S0': #GSc: still some parts to be done
                 [
                   { 'OPC':"S0_zLife", 'GPC':"S0_zLife", 'Type':'Life', },
                   { 'OPC':"S0_Autonom", 'GPC':"S0_Autonom", 'Type':'Life', },
                   { 'OPC':"S0_tUpdate", 'GPC':"S0_tUpdate", },
                   { 'OPC':"S0_VdMax", 'GPC':"S0_VdMax", },
                  ],
                 'S01':
                 [
                   { 'OPC':"DB102 GPC_S01_zlife", 'GPC':"S01_zLife", 'Type':'Life', }, #GScToDo -feedback M. Beyers zlife-> zLife
#                   { 'OPC':"S01_Life", 'GPC':"S01_Life", 'Type':'Life', },
#In outvars?        { 'OPC':"S01_Autonom", 'GPC':"S01_Autonom", 'Type':'Life', },
                   { 'OPC':"DB102 GPC_S01_Steuermodus", 'GPC':"S01_SteuerModus", 'Access':'rw', 'Type':'Life' }, #GScToDo -feedback M. Beyers Steuermodus-> SteuerModus
#                   { 'OPC':"S01_BZ", 'GPC':"S01_BZ", },
                   { 'OPC':"DB102 GPC_S01_C01_VdMax", 'GPC':"S01_C01_VdMax", },
                   { 'OPC':"DB102 GPC_S01_C01_QMax", 'GPC':"S01_C01_QMax", 'NK':2, },
                   { 'OPC':"DB102 GPC_S01_Param_AutonomyFactor", 'GPC':"S01_Param_AutonomyFactor", 'NK':0 }, #GScToDo only compleat days are possible
                   { 'OPC':"DB102 GPC_S01_K1_LMax", 'GPC':"S01_K1_LMax", 'Type':'Vol', },
                   { 'OPC':"DB102 GPC_S01_K1_LResMin", 'GPC':"S01_K1_LResMin", 'Type':'Vol', },
                   { 'OPC':"DB102 GPC_S01_Param_VdHistTage", 'GPC':"S01_Param_VdHistTage", },
#                   { 'OPC':"S01_Param_SP_RechenModus", 'GPC':"S01_Param_SP_RechenModus", },
                  ],
                 'S02':
                 [
                   { 'OPC':"DB102 GPC_S02_zlife", 'GPC':"S02_zLife", 'Type':'Life', }, #GScToDo -feedback M. Beyers zlife-> zLife
#                   { 'OPC':"S02_Life", 'GPC':"S02_Life", 'Type':'Life', },
#In outvars?        { 'OPC':"S02_Autonom", 'GPC':"S02_Autonom", 'Type':'Life', },
                   { 'OPC':"DB102 GPC_S02_Steuermodus", 'GPC':"S02_SteuerModus", 'Access':'rw', 'Type':'Life' }, #GScToDo -feedback M. Beyers Steuermodus-> SteuerModus
#                   { 'OPC':"S02_BZ", 'GPC':"S02_BZ", },
                   { 'OPC':"DB102 GPC_S02_C01_VdMax", 'GPC':"S02_C01_VdMax", },
                   { 'OPC':"DB102 GPC_S02_C01_QMax", 'GPC':"S02_C01_QMax", 'NK':2, },
                   { 'OPC':"DB102 GPC_S02_Param_AutonomyFactor", 'GPC':"S02_Param_AutonomyFactor", 'NK':0 }, #GScToDo only compleat days are possible
                   { 'OPC':"DB102 GPC_S02_K1_LMax", 'GPC':"S02_K1_LMax", },
                   { 'OPC':"DB102 GPC_S02_K1_LResMin", 'GPC':"S02_K1_LResMin", },
                   { 'OPC':"DB102 GPC_S02_Param_VdHistTage", 'GPC':"S02_Param_VdHistTage", },
#                   { 'OPC':"S02_Param_SP_RechenModus", 'GPC':"S02_Param_SP_RechenModus", },
                  ],
                 'S03':
                 [
                   { 'OPC':"DB102 GPC_S03_zlife", 'GPC':"S03_zLife", 'Type':'Life', }, #GScToDo -feedback M. Beyers zlife-> zLife
#                   { 'OPC':"S03_Life", 'GPC':"S03_Life", 'Type':'Life', },
#In outvars?        { 'OPC':"S03_Autonom", 'GPC':"S03_Autonom", 'Type':'Life', },
                   { 'OPC':"DB102 GPC_S03_Steuermodus", 'GPC':"S03_SteuerModus", 'Access':'rw', 'Type':'Life' }, #GScToDo -feedback M. Beyers Steuermodus-> SteuerModus
#                   { 'OPC':"S03_BZ", 'GPC':"S03_BZ", },
                   { 'OPC':"DB102 GPC_S03_C01_VdMax", 'GPC':"S03_C01_VdMax", },
                   { 'OPC':"DB102 GPC_S03_C01_QMax", 'GPC':"S03_C01_QMax", 'NK':2, },
                   { 'OPC':"DB102 GPC_S03_Param_AutonomyFactor", 'GPC':"S03_Param_AutonomyFactor", 'NK':0 }, #GScToDo only compleat days are possible
                   { 'OPC':"DB102 GPC_S03_K1_LMax", 'GPC':"S03_K1_LMax", },
                   { 'OPC':"DB102 GPC_S03_K1_LResMin", 'GPC':"S03_K1_LResMin", },
                   { 'OPC':"DB102 GPC_S03_Param_VdHistTage", 'GPC':"S03_Param_VdHistTage", },
#                   { 'OPC':"S03_Param_SP_RechenModus", 'GPC':"S03_Param_SP_RechenModus", },
                  ],
                 'S98':
                 [
                   { 'OPC':"DB102 GPC_EPA_DateTime", 'GPC':"S98_DateTime", 'Type':'DateTime' },
                   #{ 'OPC':"", 'GPC':"S98_zLife", 'Type':'Life', 'Access':'rw', },
                  ],
                 'S99':
                 [
                   { 'OPC':"S99_zlife", 'GPC':"S99_zLife", 'Access':'rw', 'Type':'Life' }, #GScToDo -feedback M. Beyers zlife-> zLife
                   { 'OPC':"S99_tUpdateTrig", 'GPC':"S99_tUpdateTrig", 'Access':'rw', },
                  ],
               }
EPA_Vars = { 'S0': #GSc: should be ready
             [
               { 'OPC':"S0_tUpdate", 'GPC':"S0_tUpdate", 'Type':'Conf', },
               { 'OPC':"S0_zLife", 'GPC':"S0_zLife", 'Type':'Life', },
               { 'OPC':"S0_Scenario", 'GPC':"S0_Scenario", 'Type':'Scenario', },
               { 'OPC':"S0_ScenarioBit", 'GPC':"S0_ScenarioBit", 'Type':'Scenario', 'Access':'rw', },
               { 'OPC':"DB102 GPC_S0_S0_IO", 'GPC':"S0_IOBit", 'Type':'Scenario', 'Access':'rw', },
              ],
             'S01':
             [
               { 'OPC':"DB102 GPC_S01_C01_QSoll", 'GPC':"S01_C01_QSoll", 'Type':'CtrlAct', },
               { 'OPC':"DB102 GPC_EPA_S01_C01_Flow", 'GPC':"S01_C01_Flow", 'Type':'In', 'Access':'rw', },
               { 'OPC':"DB102 GPC_EPA_S01_C01_Index", 'GPC':"S01_C01_Idx", 'Type':'In', 'Access':'rw', 'NK':2, },
               { 'OPC':"DB102 GPC_EPA_S01_C02_Flow", 'GPC':"S01_C02_Flow", 'Type':'Out', 'Access':'rw', },
               { 'OPC':"DB102 GPC_EPA_S01_C02_Index", 'GPC':"S01_C02_Idx", 'Type':'Out', 'Access':'rw', 'NK':2, },
               { 'OPC':"DB102 GPC_EPA_S01_C03_Flow", 'GPC':"S01_C03_Flow", 'Type':'Out', 'Access':'rw', },
               { 'OPC':"DB102 GPC_EPA_S01_C03_Index", 'GPC':"S01_C03_Idx", 'Type':'Out', 'Access':'rw', 'NK':2, },
               { 'OPC':"DB102 GPC_EPA_S01_H01", 'GPC':"S01_K1_LIst", 'Type':'Vol', 'Access':'rw', },
              ],
             'S02':
             [ 
               { 'OPC':"DB102 GPC_S02_C01_QSoll", 'GPC':"S02_C01_QSoll", 'Type':'CtrlAct', },
               { 'OPC':"DB102 GPC_EPA_S02_C01_Flow", 'GPC':"S02_C01_Flow", 'Type':'In', 'Access':'rw', },
               { 'OPC':"DB102 GPC_EPA_S02_C01_Index", 'GPC':"S02_C01_Idx", 'Type':'In', 'Access':'rw', 'NK':2, },
               { 'OPC':"DB102 GPC_EPA_S02_C02_Flow", 'GPC':"S02_C02_Flow", 'Type':'Out', 'Access':'rw', },
               { 'OPC':"DB102 GPC_EPA_S02_C02_Index", 'GPC':"S02_C02_Idx", 'Type':'Out', 'Access':'rw', 'NK':2, },
               { 'OPC':"DB102 GPC_EPA_S02_H01", 'GPC':"S02_K1_LIst", 'Type':'Vol', 'Access':'rw', },
              ],
             'S03':
             [
               { 'OPC':"DB102 GPC_S03_C01_QSoll", 'GPC':"S03_C01_QSoll", 'Type':'CtrlAct', },
               { 'OPC':"DB102 GPC_EPA_S03_C01_Flow", 'GPC':"S03_C01_Flow", 'Type':'In', 'Access':'rw', },
               { 'OPC':"DB102 GPC_EPA_S03_C01_Index", 'GPC':"S03_C01_Idx", 'Type':'In', 'Access':'rw', 'NK':2, },
               { 'OPC':"DB102 GPC_EPA_S03_C02_Flow", 'GPC':"S03_C02_Flow", 'Type':'Out', 'Access':'rw', },
               { 'OPC':"DB102 GPC_EPA_S03_C02_Index", 'GPC':"S03_C02_Idx", 'Type':'Out', 'Access':'rw', 'NK':2, },
               { 'OPC':"DB102 GPC_EPA_S03_H01", 'GPC':"S03_K1_LIst", 'Type':'Vol', 'Access':'rw', },
              ],
             'S98':
             [
               { 'OPC':"DB102 GPC_EPA_DateTime", 'GPC':"S98_DateTime", 'Type':'DateTime', 'Access':'rw', },
               { 'OPC':"EPA_zLive", 'GPC':"S98_zLife", 'Type':'Life', 'Access':'rw', },
              ],
            }

GPC_Stations = {'SCADA':'S0',
                'Mousel':'S01',
                'Sauer':'S02',
                'Alzette':'S03',
                'EPA':'S98',
                'GPC':'S99',
                }


OPCVarSpecif = {}
for si,varsi in GPC_SysVars.items() + GPC_StateVars.items() + GPC_OutVars.items() + EPA_Vars.items():
    for vi in varsi:
        if vi.get('Access','') == 'rw' or vi.get('NK',None) != None:
            OPCVarSpecif[vi['OPC']] = vi
