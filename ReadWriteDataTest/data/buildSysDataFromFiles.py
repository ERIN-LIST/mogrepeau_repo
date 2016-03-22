""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
import pandas as pds
import pylab
from glob import glob, re, os
import sys
from getopt import getopt, GetoptError
import pytz

def fileDatetime(fn):
    fnDT = pds.datetime.strptime(re.match("GPCLog_([T\d]+)(_noTrigOK){0,1}\.log",
                                          fn).groups()[0],
                                 "%Y%m%dT%H%M")
    return fnDT

def fileDataInTarget(fn, refDate):
    ret = False
    fnDT = fileDatetime(fn)
    tz_Lux = pds.datetools.dateutil.tz.gettz('Europe/Luxembourg')
    TZOffset = tz_Lux.utcoffset(fnDT)
    acceptedOffset = 1 # [hours]
    try:
        if refDate == None:
            #This means no file was specified and no date to start from.
            # -> take every thing by default, file is not in target.
            ret = False
        elif (fnDT -TZOffset + pds.DateOffset(hours=acceptedOffset) - refDate).total_seconds() < -60:
            ret = True
    except AttributeError:
        def total_seconds(td):
            return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
        if total_seconds(fnDT + pds.DateOffset(hours=acceptedOffset) - refDate) < -60:
            ret = True
    return ret

def prepFileSysData(fn,preD=[]):
    ret = preD[:]
    started = False
    if len(ret) > 0:
        started = True
    reStart = re.compile("^ENTER STATE\s*: GPCMap.ReadOPCVars")
    reEnd = re.compile("^LEAVING STATE")
    reData = re.compile("^ReadIn from OPC - \((?P<data>.*)\)")
    reTrigg = re.compile("(?!.*(GPC_Mode_Bef_.*|M_F\d{2}_GPC_(Bef|Ist|Soll)))")
    for l in open(fn):
        if started and reEnd.match(l):
            started = False
        elif not started and reStart.match(l):
            started = True
        if not started:
            continue
        rem = reData.match(l)
        if rem:
            d = eval(rem.group('data'))
            if reTrigg.match(d[0]):
                ret.append(d)
    return ret, started

def prepFileGPCOut(fn,preD=[]):
    ret = preD[:]
    started = False
    if len(ret) > 0:
        started = True
    reStart = re.compile("^ENTER TRANSITION\s*: GPCMap.WriteOPCVars.OPCWrite")
    reEnd = re.compile("^EXIT TRANSITION")
    reData = re.compile("^ReadIn from OPC - \((?P<data>.*)\)")
    reTrigg = re.compile("(?!.*(GPC_Mode_Bef_.*|M_F\d{2}_GPC_(Bef|Ist)))")
    for l in open(fn):
        if started and reEnd.match(l):
            started = False
        elif not started and reStart.match(l):
            started = True
        if not started:
            continue
        rem = reData.match(l)
        if rem:
            d = eval(rem.group('data'))
            if reTrigg.match(d[0]):
                ret.append(d)
    return ret, started

def fuseData(xa,d):
    x = pds.DataFrame(d,columns=['Name', 'Value','Quality','Date'])
    # GSC-ToDo: only use data where 'Quality' == 'Good'
    xg = x[x['Quality'] == 'Good']
    xp = pds.pivot_table(xg,values='Value',index=['Date'],columns=['Name'],aggfunc='first')
    # Build the timeseries by converting the index to a datetime object
    # In OPC the time variable is by convention in UTC
    xp.index = [pds.datetools.to_datetime(di) for di in xp.index]
    samp = pds.np.diff(xp.index.to_pydatetime())
    samptf = (samp >= pds.datetools.timedelta(seconds=1))&(samp <= pds.datetools.timedelta(seconds=3))
    sampfilt = samp[samptf]
    ix_1s = xp.ix[:-1][samptf].index
    ix2drop=[]
    for i,ixi in enumerate(reversed(ix_1s)):
        sdiff = sampfilt[-(i+1)].seconds
        dr = pds.date_range(start=ixi,periods=sdiff+1,freq='1S')
        xptmp = xp.ix[dr]
        for tmpxi in xptmp.index[1:]:
            xp.loc[dr[0],xptmp.loc[tmpxi].notnull()] = xptmp.loc[tmpxi,xptmp.loc[tmpxi].notnull()]
            ix2drop.append(tmpxi)
    for ixi in ix2drop: #This needs to be done in a separate loop to avoid problems with direct follows sequences.
        if ixi in xp.index:
            xp = xp.drop(ixi,axis=0)
    try:
        ixaM = xa.index[-1]
    except:
        ixaM = None
    xa = xa.combine_first(xp)
    if ixaM:
        xt = xa.xs(ixaM)
        xa.ix[ixaM] = xt
    return xa

def getCLParam(argv):
    param = {'DType':'System'}
    try:
        opts, args = getopt( argv, "hd:l:t:p:",
                                    ["help", "data=", "ldt=", "dtype=", "fpattern="] )
    except GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ['-h','--help']:
            usage()
            sys.exit()
        if opt in ['-d','--data']:
            arg = arg.strip()
            param['data'] = arg
        if opt in ['-l','--ldt']:
            param['latestDT'] = pds.datetools.parse(arg)
        if opt in ['-t','--dtype']:
            if arg in ['System','GPCOut']:
                param['DType'] = arg
        if opt in ['-p','--fpattern']:
            if "'" in arg:
                arg = arg.strip("'")
            elif '"' in arg:
                arg = arg.strip('"')
            param['FPattern'] = arg
    return param

def usage():
    print """Syntax: python buildSysDataFromFiles.py [parameters]
    The supported parameters are:
    -d datafile      : Specify the datafile to use
    -l datetime      : --ldt=datetime (use a parsable datetime format)
                       Specify the datetime from which on the log files should be parsed
    -p pattern       : --fpattern=pattern (use a file pattern usable within python)
    -t type          : --dtype=type (default = System)
                       Possibilities are {System, GPCOut}
    -h               : --help
                       Print this help message
    """


if __name__=='__main__':

    param = getCLParam(sys.argv[1:])
    pklFile = param.get('data',"opcVars_V3.pkl")
    logFPattern = param.get('FPattern',"GPCLog_2015*.log")

    if os.path.exists(pklFile):
        xa = pds.read_pickle(pklFile)
    else:
        xa = pds.DataFrame()

    if param['DType'] == 'System':
        preFileFct = prepFileSysData
    elif param['DType'] == 'GPCOut':
        preFileFct = prepFileGPCOut
    else:
        raise ValueError('Unhandled DataType specified')

    if param.has_key('latestDT'):
        latesedDT = param['latestDT']
    elif xa.index.tolist() != []:
        latesedDT = xa.index[-1]
    else:
        latesedDT = None
#    latesedDT = datetime(2013,05,20)
    toBeContinued = False
    for fni in glob(logFPattern):
        if fileDataInTarget(fni, latesedDT):
            continue
        if toBeContinued:
            detail = "(conntinued)"
        else:
            detail = ""
        print "File read: %s %s" % (fni,detail)
        if toBeContinued:
            data, toBeContinued = preFileFct(fni, data)
        else:
            data, toBeContinued = preFileFct(fni)
        if toBeContinued or len(data) == 0:
            continue
        xa = fuseData(xa,data)
    else:
        if len(data) > 0:
            xa = fuseData(xa,data)
    xa.to_pickle(pklFile)
