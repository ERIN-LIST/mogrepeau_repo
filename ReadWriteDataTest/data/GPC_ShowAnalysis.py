import pandas as pds
import matplotlib.pyplot as plt
from collections import defaultdict

xa = pds.load('opcVars_V3.pkl')
df = pds.load('QSoll_201308.pkl')

InSIDERE_Cs = ['VictoryClient.S3_In3_z', 'VictoryClient.S2_In2_1_z','VictoryClient.S4_In4_z']
SPCols = [ci for ci in df.columns if ci.startswith('SP')]
FireRes = 200+100+96+50

InCs = defaultdict(list)
for ci in [ci for ci in xa.columns if '_In' in ci and not '_InOut' in ci]:
    sti,var = ci.split('.')[1].split('_',1)
    InCs[sti].append(ci)
VolCs = defaultdict(list)
for ci in [ci for ci in xa.columns if '_VIst' in ci]:
    sti,var = ci.split('.')[1].split('_',1)
    VolCs[sti].append(ci)
resC = dict([(ci.split(':')[1].split('_',1)[0],ci) for ci in df.columns if 'MPC_Res' in ci])
cols = {}
for sti in resC:
    cols[sti] = {'MPCRes':resC[sti],'In':InCs[sti],'Vol':VolCs[sti]}

plt.rcParams.update({'legend.fontsize': 9,'legend.linewidth': 1})

for sti in cols:
    dfci = cols[sti]['MPCRes']
    xacIi = cols[sti]['In']
    xacVi = cols[sti]['Vol']
    if len(xacIi) > 1:
        xai = xa[xacIi].sum(axis=1)/(15.*60)
        xLabel = "%s_InAll" % (sti,)
    else:
        xai = xa[xacIi]/(15.*60)
        xLabel = [xacIi[0].split('.')[1],]
    xaVi = xa[xacVi].sum(axis=1)
    xVLabel = "%s_Vol" % (sti,)
    
    if isinstance(xai,pds.Series): plt.figure();
    ah = xai.plot(label=xLabel)
    (df[dfci]/100.).plot(ax=ah,label=dfci)
    xaVi.plot(ax=ah,label=xVLabel,secondary_y=True)
    ah.legend()
    ah.figure.canvas.set_window_title(sti)
    ah.figure.show()

InSIDERE = xa[InSIDERE_Cs].sum(axis=1).shift(2*4).resample('1d',sum)/1000.

Vol = pds.DataFrame(index=xa.index)
for sti in VolCs:
        Vol[sti] = xa[VolCs[sti]].sum(axis=1)
VolEndDay = Vol.shift(2*4-1).resample('1d','last')
StoredVol = VolEndDay.sum(axis=1)-FireRes

SP = df[SPCols[1:-1]].shift(2*4).resample('1d','last')
SP.columns = [ci.split('_')[1] for ci in SP.columns]

ah = (VolEndDay - SP).plot(kind='bar', stacked=True)
ah.set_title('VolumeED - Setpoint')
ah.figure.canvas.set_window_title('VED-SP')
ah.figure.show()
