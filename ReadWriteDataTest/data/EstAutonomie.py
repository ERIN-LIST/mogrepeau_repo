import pandas as pds
import pprint
import pickle


xD = pds.read_pickle("DailyData.pkl")
ModelInfo = pickle.load(open("PredModels.pkl"))
BSequence = [5,2,3,4] #This is the basin sequence as it is used in the GPC loggs (to simplify the comparison)
V0Cs = ['S%d_V0'%ci for ci in BSequence]
OCs =  ['S%d_Out'%ci for ci in BSequence]


Vo = xD.ix[-1][V0Cs].values
VResMin = pds.np.array([29., 48., 48., 115.])

VRes = (Vo-VResMin).sum(axis=0)

C0 = xD[OCs+['S1_Out',]].ix[-4:-1].mean(axis=0).sum()

PredDayIncByBasin = pds.np.array([ ModelInfo[col].beta.x for col in ['S1_Out','S2_Out','S3_Out','S4_Out','S5_Out']]) #From the linear regression model
#PredDayInc = pds.np.array([5,0,6,11]).sum() # Out of an manual linear regr estimation of last x days
#PredDayInc = pds.np.array([2,0,2,8]).sum() # Out of an manual linear regr estimation of last x days
PredDayInc = PredDayIncByBasin.sum() # Out of an automatic linear regr estimation of last x days
Horizon = 10
pred = C0 + pds.np.arange(1,Horizon+1)*PredDayInc

Scenario = {}
for CR in xrange(550,700,10):
    VResPred = VRes - (pred-CR).cumsum()
    CRReached = VResPred < 0
    VIn = pds.np.ones(Horizon)
    VIn[-CRReached]=CR
    CRReachDay = pds.np.hstack([False, pds.np.diff(CRReached)])
    VIn[CRReachDay] = CR - VResPred[CRReachDay]
    VIn[-CRReachDay & CRReached] = pred[-CRReachDay & CRReached]
    VResPred[VResPred<0] = 0
    Scenario[CR] = {'VIn':VIn.copy(), 'VResPred':VResPred.copy()}

print "== Report %s ==" % (pds.datetime.now().date(),)
print "Base Consumption: C0 = %.2f [m3/d]" % (C0,)
print "Current Reserve: VRes0 = %d [m3]" % (VRes,)
print "Predicted daily consumption incr.: PredDayInc = %.2f +[m3/d]" % (PredDayInc,)
pprint.pprint( pred, width=200 )
print "\n-- Network Reserve evolution according to the reserved capacity (CR) --"
pprint.pprint( Scenario, width=200 )