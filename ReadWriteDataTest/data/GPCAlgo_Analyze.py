""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
import pandas
from dateutil.parser import parse
import matplotlib.pyplot as plt

fh = open('GPCAlgo_20120808T1445.log')
df = pandas.DataFrame()
for l in fh:
    d,v = l.strip().split(': ')
    for vi in v.split(';'):
        exec(vi.strip())
    df2 = pandas.DataFrame(data = [[IN,OUT,VOL,INComm]],
                           columns=['In','Out','Vol','InComm'],
                           index=[parse(d[4:-1]).replace(tzinfo=None)])
    if df.shape == (0,0):
        df = df2
    else:
        df = pandas.concat([df,df2])
fh.close()
df['VolB'] = (df['In']-df['Out'])/1000. + df['Vol'].shift(1)

fig, axes = plt.subplots(nrows=2, ncols=1, sharex=True)
fh = df[['In','Out']].plot(ax=axes[0])
df.InComm.shift(1).plot(ax=axes[0], label='InComm')
fh.legend(loc='best')
fh = df[['Vol','VolB']].plot(ax=axes[1])
fh.legend(loc='best')

plt.show()
