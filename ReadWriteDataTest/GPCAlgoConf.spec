[Global]
OPCServer = string()

[GPCLife]
minSampling = float(1.2, 600, default=5)
toBlank = boolean(default=False)
pctGPCSamp = integer(1, 100, default=1)

[MPC]
simu = boolean(default=True)
simuMode = option('OPCReadOnly', 'OPCWrite', 'NoOPCWrite', 'NoOPCWriteTrigger')
logFile = string()
mode = option('Dummy', 'ZigZag', 'Opti')

[MPC_ZigZag]
PredictionMode = option('Current', 'DMean', 'MeanPattern')

[MPC_Opti]
SolverVerbos = integer(0, 2, default=0)
ControlTimeperiod = integer(60, 14400)
DailyMeanHorizon = integer(1, 365, default=1) # ensure coherence with basin specific parameter
SPCalcType = integer(1, 2, default=1) # ensure coherence with basin specific parameter
ReservedCapacity = integer(100, 1000, default=1300)
MDC_Order = string_list(min=3,max=3)
MeanDailyConsumption = int_list(min=3,max=3)
Diameter = float_list(min=3,max=3)
MaxPickConsumption = int_list(min=3,max=3)
ConsProfile = float_list(min=24,max=24)

  [[CostFunctionWeights]]
  ReachSP = int_list(min=1,max=1)
  RelVolumeHomogenity = int_list(min=1,max=1)
  EmergancyReserve = int_list(min=1,max=1)
  VolRange = int_list(min=1,max=1)

[MPC_Dummy]
