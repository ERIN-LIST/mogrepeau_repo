""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
from glob import glob
import re
import numpy as np
from dateutil import parser, tz
import pandas as pds
from buildSysDataFromFiles import fileDataInTarget

def prepLogContent(fl=['GPC.log.2','GPC.log.1','GPC.log']):
    logQsoll_Conntinue = False
    lines = []
    for f in fl:
        print 'Parse file %s %s' % (f, '(continued)' if logQsoll_Conntinue else '')
        fh = open(f)
        for l in fh:
            if not ( l.startswith('MPC Results: ') \
                  or l.startswith('Log QSoll ') \
                  or l.startswith('#MPCActive ') \
                  or l.startswith('MPCAlgos (') ) :
                continue
            if l.startswith('MPC Results: '):
                if l.strip().endswith('[]'):
                    continue
                m = re.match(".*\[(?P<MRes>.*)\].*",l)
                mres = m.group('MRes').strip(')(').split('), (')
                for mi in mres:
                    m = re.match("'(?P<var>.*)', (?P<val>\d*)",mi)
                    lines.append(['MPC_Res', m.group('var'),m.group('val')])
            elif l.startswith('Log QSoll ') or logQsoll_Conntinue:
                if logQsoll_Conntinue:
                    logQsoll_Conntinue = False
                m = re.match("Log QSoll (?P<info>.*) trigger:", l)
                if m == None:
                    continue
                info = m.group('info')
                i = 0
                while i < 4:
                    try:
                        l = fh.next()
                    except StopIteration:
                        logQsoll_Conntinue = True
                        break
                    if re.match('^Job .* \(ID \d\):',l): continue
                    elif l.startswith('AlgData_OPC.readOPC()') : continue
                    elif l.startswith(' -> try again') : continue
                    i += 1
                    if l.startswith('ReadIn from OPC'):
                        m = re.match(".*\(\('(?P<var>.*)', (?P<val>\d*),.*'(?P<dt>[\d/: ]*)'.*",l)
                        if m != None:
                            lines.append([info, m.group('var'),m.group('val'),m.group('dt')])
                    else:
                        try:
                            pos = fh.tell()
                            fh.next()
                            fh.seek(pos)
                            break
                        except StopIteration:
                            logQsoll_Conntinue = True
            elif l.startswith('#MPCActive '):
                m = re.match(".*\((?P<dt>[-\d:\. ]*)\).*",l)
                lines.append(['MPCRun',m.group('dt')])
            elif l.startswith('MPCAlgos ('):
                if '): SP = ' in l:
                    tmp = l.split('):')[1].strip()
                    if not tmp.endswith(']'):
                        tmp = (l.split('):')[1].strip('\n') + fh.next()).strip()
                    r = re.match("(?P<Start>.*\[)(?P<data>.*)(?P<End>\])",tmp)
                    tmp = r.group('data').split()
                    lines.append(['SP',[float(ti) for ti in tmp]])

    return lines

fl = [fni for fni in glob("GPCLog_2013*.log") if not fileDataInTarget(fni, pds.datetools.parse('2013-08-29 11:45'))]

# #fh = open("GPCInc_SCADA_AlgSigError_20121204.log")
# fl = ['GPC.log.%s'%(i,) for i in xrange(1,11)]
# fl.insert(0, 'GPC.log')
# fl.reverse()
fh = prepLogContent(fl=fl)
d = []
tmp = {}
dtTmp = None
for l in fh:
    if l[0] == 'MPCRun':
        dtTmp = parser.parse(l[1]).replace(tzinfo=tz.gettz('CET')).astimezone(tz.tzutc()).replace(tzinfo=None,microsecond=0,)
        if tmp.has_key('DT') and tmp['DT'] != dtTmp:
            d.append(tmp)
            tmp = {'DT':dtTmp}
        elif not tmp.has_key('DT') and dtTmp:
            tmp['DT'] = dtTmp
    elif l[0] == 'MPC_Res' and dtTmp != None:
        tmp[':'.join((l[0],l[1].split('.')[1]))] = int(l[2])
    elif l[0] in ['before', 'after']:
        if not tmp.has_key('DT'):
            tmp['DT'] = parser.parse(l[3])
        tmp[':'.join((l[0],l[1].split('.')[1]))] = int(l[2])
    elif l[0] == 'SP':
        for i,sti in enumerate([6,1,5,2,3,4]):
            tmp['SP_S%s'%sti] = l[1][i]

df = pds.DataFrame(d)
if 'after' in df:
    df['DAfter'] = df['MPC_Res']-df['after']
    print df[df['DAfter'] != 0]
if 'before' in df:
    df['DBefore'] = df['MPC_Res']-df['before']
    print df[df['DBefore'] != 0]
if 'DT' in df:
    df = df.set_index('DT')
df.save('QSoll_201308.pkl')
