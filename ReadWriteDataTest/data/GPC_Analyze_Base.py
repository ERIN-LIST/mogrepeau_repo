import pandas as pds
import matplotlib.pyplot as plt
import pickle
from collections import defaultdict
import re

#xa = pds.load('opcVars_V3.pkl')
xa = pds.read_pickle('opcVars_GPC2.2_V1.pkl')

C_Out = filter(re.compile(".*\.S\d{1}_Out").match,xa.columns)
OutCs = defaultdict(list)
for ci in C_Out:
    tre = re.match(".*\.S(?P<id>\d{1})_Out",ci)
    outid = "S%s_Out" % tre.group('id')
    OutCs[outid].append(ci)

C_VIst = filter(re.compile(".*\.S\d{1}_K\d{1}_VIst").match,xa.columns)
VIstCs = defaultdict(list)
for ci in C_VIst:
    tre = re.match(".*\.S(?P<id>\d{1})_K\d{1}_VIst",ci)
    outid = "S%s_VIst" % tre.group('id')
    VIstCs[outid].append(ci)

xo = pds.DataFrame(index = xa.index)
for ci in OutCs:
    xo[ci] = xa[OutCs[ci]].sum(axis=1)
    if ci == 'S4_Out':
        xo[ci] -= xa[['VictoryClient.S5_In5_z','VictoryClient.S4_Out4_3_z']].sum(axis=1)
    if ci == 'S3_Out':
        xo[ci] -= xa[['VictoryClient.S4_In4_1_z','VictoryClient.S4_In4_1a_z']].sum(axis=1)
        xo[ci] += xa[['VictoryClient.S4_Out4_3_z',]].sum(axis=1)

for ci in VIstCs:
    xo[ci] = xa[VIstCs[ci]].sum(axis=1)

#Daily out
xoD = xo[OutCs.keys()].shift(2*4).resample('1d',sum)/1000.
V0Cs = [ki.replace('Ist','0') for ki in VIstCs.keys()]
xoD[V0Cs] = xo[VIstCs.keys()].shift(2*4).resample('1d','first')
xoD.to_pickle("DailyData.pkl")

MeasSamplesD = xo[OutCs.keys()].shift(2*4).resample('1d','count').mean(level=0)
MSDidx = (MeasSamplesD > 96*0.9).astype(int).diff()
if (MSDidx == 1).any():
    sD = MeasSamplesD.index[MSDidx == 1][0]
else:
    sD = MeasSamplesD.index[0]
if (MSDidx == -1).any():
    eD = MeasSamplesD.index[(MSDidx == -1).shift(-1).fillna(False)][-1]
else:
    eD = MeasSamplesD.index[-1]
tmp = xoD[sD:eD][OutCs.keys()]
tmp['OutTot'] = tmp.sum(axis=1)
tmp['idx'] = range(len(tmp.index))
ModelInfo = {}
for col in ['S1_Out','S2_Out','S3_Out','S4_Out','S5_Out','OutTot']:
    model = pds.stats.ols.OLS(y=tmp[col],x=tmp['idx'])
    ModelInfo[col] = model
    print "%s: %s" % (col,model.beta)
    tmp[col.split('_')[0]+'_fit'] = model.y_fitted
pickle.dump(ModelInfo,open('PredModels.pkl','wb'))

ahO = tmp[['OutTot','OutTot_fit']].plot()
ahO.figure.show()

V0Cs.sort()
ahV = xoD[V0Cs].plot()
ahV.figure.show()

ResCapacity = 550
DaysToGo = (ResCapacity-ModelInfo['OutTot'].y_fitted[eD])/ModelInfo['OutTot'].beta.x
print "DaysBefor reaching Daily consumption (%s[m3]): %s" % (ResCapacity,DaysToGo,)
