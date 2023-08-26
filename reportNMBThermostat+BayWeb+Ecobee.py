#!/usr/bin/env python3
import datetime as dt
import sqlite3
from dateutil.tz import tz
from sys import path
path.append('/home/jim/tools/')
from shared import getTimeInterval
import pytz
import io

DBname = '/home/jim/tools/Honeywell/MBthermostat3.sql'
saneUsageMax = 33.3
#saneUsageMax = 10.0
global insaneUsage
insaneUsage = ''

def print_to_string(*args, **kwargs):
    output = io.StringIO()
    print(*args, file=output, **kwargs)
    contents = output.getvalue()
    output.close()
    return contents

def recodeOldThermostat(c, thermostat):
    select = 'select ' \
        ' id, dataTime, outputStatus, fan, desiredCool, desiredHeat, ' \
        ' temperature, src ' \
        'FROM ' + thermostat + ';'
    #print(select)
    c.execute(select)
    result = c.fetchall()
    updates = 0
    update = 'UPDATE ' + thermostat + \
        '  SET dataTime  = ?, ' \
        '      cool1     = ?, ' \
        '      heatPump1 = ?, ' \
        '      fan       = ?  ' \
        ' WHERE id = ?;'
    est = pytz.timezone('US/Eastern')
    fanTime = heatTime = coolTime = 0
    first = last = previous = None
    E = e400 = tz = \
        H = hCool = hHeat = hFan = hOff = hErr = \
            B = bCN = bCool = bHN = bHeat = bFan = bIdle = bErr = \
                oStatN = unxStat = 0 
    for record in result:
        dataTime     = record['dataTime']
        Rid          = record['id']
        outputStatus = record['outputStatus']
        fan          = record['fan']
        src          = record['src']
        desiredCool  = record['desiredCool']
        desiredHeat  = record['desiredHeat']
        temperature  = record['temperature']
        if src == 'E':   # EcoBee does not need recoding
            E += 1
            if desiredCool == 400:   # 400 is missing/invalid data
                updateCool = 'UPDATE ' + thermostat + \
                    '  SET  desiredCool = ? WHERE id = ?;'
                c.execute(updateCool, (None, Rid))
                e400 += 1
            continue
        if len(dataTime) == 19:
            updates += 1
            unaware  = dt.datetime.strptime(dataTime, '%Y-%m-%d %H:%M:%S')
            aware    = unaware.astimezone(est)
            dataTime = aware
            tz      += 1
            #print(Rid, unaware, aware)
            #c.execute(update,(aware, Rid))
        else:
            print('A', dataTime, type(dataTime))
        #print('B', dataTime, type(dataTime))
        fanTime = heatTime = coolTime = 0
        if first is None:
            first = dataTime
            previous = dataTime + dt.timedelta(minutes = 5)
        delta = (dataTime - previous).total_seconds()
        # account for missing data by assuming 5 minutes
        if delta > 900: delta = 300
        # HoneyWell thermostat
        if src == 'H':
            H += 1
            if   outputStatus == 'cool on':
                coolTime = delta
                fanTime  = delta
                hCool   += 1
            elif outputStatus == 'heat on':
                heatTime = delta
                fanTime  = delta
                hHeat   += 1
            elif fan == 1:
                fanTime  = delta
                hFan    += 1
            elif outputStatus == 'off':
                hOff    += 1
                pass
            else:
                print('Unexpected outputStatus:', outputStatus, Rid, dataTime, src)
                hErr += 1
        # BayWeb thermostat - assume running if temp outside setpoint
        elif src == 'B':
            B += 1
            if   outputStatus == 'cool':
                if temperature is None or desiredCool is None:
                    # missing data - ignore
                    bCN += 1
                    pass
                elif temperature > desiredCool:
                    coolTime = delta
                    fan      = delta
                    bCool   += 1
            elif outputStatus == 'heat':
                if temperature is None or desiredHeat is None:
                    # missing data - ignore
                    bHN += 1
                    pass
                elif temperature < desiredHeat:
                    heatTime = delta
                    fan      = delta
                    bHeat   += 1
            elif outputStatus == 'off':
                if fan == 1:
                    fan      = delta
                    bFan    += 1
                elif (fan == 0 or fan is None):
                    # no fan/heat/cool - just idle
                    bIdle   += 1
                    pass
            else:
                print('Unexpected outputStatus:', outputStatus, Rid, dataTime, src)
                bErr += 1
        elif outputStatus is None:
            oStatN += 1
            pass
        else:
            print('Unexpected: outputStatus:', outputStatus, '\tfan:',  fan)
            unxStat += 1
        previous = dataTime
        #print(dataTime, coolTime, heatTime, fanTime, id, outputStatus, delta)
        c.execute(update,(dataTime, coolTime, heatTime, fanTime, Rid))

    stats = print_to_string('recodeOldThermostat:', thermostat, '\n',
                            '\trecords updated:' , updates, '\n',
                            '\trecodes: \n'
                            '\t\tE:\t',       E,       '\n',
                            '\t\te400:\t',    e400,    '\n',
                            '\t\ttz:\t',      tz,      '\n',
                            '\t\tH:\t',       H,       '\n',
                            '\t\thCool:\t',   hCool,   '\n',
                            '\t\thHeat:\t',   hHeat,   '\n',
                            '\t\thFan:\t',    hFan,    '\n',
                            '\t\thOff:\t',    hOff,    '\n',
                            '\t\thErr:\t',    hErr,    '\n',
                            '\t\tB:\t',       B,       '\n',
                            '\t\tbCN:\t',     bCN,     '\n',
                            '\t\tbCool:\t',   bCool,   '\n',
                            '\t\tbHN:\t',     bHN,     '\n',
                            '\t\tbHeat:\t',   bHeat,   '\n',
                            '\t\tbFan:\t',    bFan,    '\n',
                            '\t\tbIdle:\t',   bIdle,   '\n',
                            '\t\tbErr:\t',    bErr,    '\n',
                            '\t\toStatN:\t',  oStatN,  '\n',
                            '\t\tunxStat:',   unxStat, '\n')
    return stats
    
def fmtTempsLine(tag, row):
    #print(tag, row['minT'],row['maxT'],row['avgT'],row['minC'],row['maxC'],row['avgC'],
    #      row['minH'],row['maxH'],row['avgH'])
    noData = '  None'
    noData = '     .'
    line = '{:>10s}'.format(tag) + ': (none)'
    if row['minT']:
        period =  '{:>10s}'.format(tag)
        minT   = ' {:>5.1f}'.format(row['minT'])       if row['minT'] is not None else noData
        maxT   = ' {:>5.1f}'.format(row['maxT'])       if row['maxT'] is not None else noData
        avgT   = ' {:>5.1f}'.format(row['avgT'])       if row['avgT'] is not None else noData
        minC   = ' {:>5.1f}'.format(int(row['minC']))  if row['minC'] is not None else noData
        maxC   = ' {:>5.1f}'.format(int(row['maxC']))  if row['maxC'] is not None else noData
        avgC   = ' {:>5.1f}'.format(row['avgC'])       if row['avgC'] is not None else noData
        minH   = ' {:>5.1f}'.format(int(row['minH']))  if row['minH'] is not None else noData
        maxH   = ' {:>5.1f}'.format(int(row['maxH']))  if row['maxH'] is not None else noData
        avgH   = ' {:>5.1f}'.format(row['avgH']) if row['avgH'] is not None else noData
        line = period + minT + maxT + avgT + minC + maxC + avgC + minH + maxH + avgH
    return line

def fmtRunTmLine(x):
    
    line = ''
    noData = '     .'
    if x['elapsed'] > 0:
        heatPct = '{:>6.1f}'.format(100.0 * x['heat']  / x['elapsed']) \
            if x['heat']  is not None and x['heat'] > 0 else noData
        coolPct = '{:>6.1f}'.format(100.0 * x['cool']  / x['elapsed']) \
            if x['cool']  is not None and x['cool'] > 0 else noData
        fanPct  = '{:>6.1f}'.format(100.0 * x['fan']   / x['elapsed']) \
            if x['fan']   is not None and x['fan']  > 0 else noData
        auxPct  = '{:>6.1f}'.format(100.0 * x['aux']   / x['elapsed']) \
            if x['aux']   is not None and x['aux']  > 0 else noData
        line = heatPct + coolPct + fanPct + auxPct
    return line

def printHeader():
    print('')
    #      2020/07/02 ttttt TTTTT aaaaa ccccc CCCCC aaaaa hhhhh HHHHH aaaaa
    #      hhhhhhccccccffffffaaaaaa
    print('                               Min   Max   Avg   Min   Max   Avg' \
          '  Heat  Cool   Fan   Aux')
    print('             Min   Max   Avg  Cool  Cool  Cool  Heat  Heat  Heat' \
          '   Run   Run   Run   Run')
    print('            Temp  Temp  Temp   Set   Set   Set   Set   Set   Set' \
          '     %     %     %     %')

def checkSanity(runStats, date, where):
    global insaneUsage
    for which in ['heat', 'cool', 'fan']:
        if runStats[which] is not None:
            runPct = 100.0 * runStats[which] / runStats['elapsed']
            if runPct > saneUsageMax:
                fmt = '\n{:>10s} - {:>10s} {:>4s} utilization of {:>5.1f}% exceeds the {:>5.1f}%' \
                    ' limit. Runtime = {:>8s}'
                runTime = str(dt.timedelta(seconds = runStats[which]))
                insaneUsage += fmt.format(date, where, which, runPct, saneUsageMax, runTime)
                return True
    return False
                                               
def runTimes(c, table, start, end):
    selectTime = 'SELECT min(dataTime) as first, max(dataTime) as last '\
        ' FROM ' + table +\
        ' WHERE dataTime >= ? AND dataTime <= ?'
    c.execute(selectTime, (start, end))
    result = c.fetchone()
    if result['first'] is None or result['last'] is None:
        return {'elapsed' : 0, 'heat' : 0, 'cool' : 0, 'aux' : 0, 'fan': 0}
    first = dt.datetime.strptime(result['first'], '%Y-%m-%d %H:%M:%S%z')
    last  = dt.datetime.strptime(result['last'], '%Y-%m-%d %H:%M:%S%z')
    selectRunTimes = 'SELECT ' \
        ' SUM(auxHeat1)  AS aux,    ' \
        ' SUM(heatPump1) AS heat,   ' \
        ' SUM(cool1)     AS cool,   ' \
        ' SUM(fan)       AS fan     ' \
        ' FROM ' + table + \
        ' WHERE dataTime >= ? AND dataTime <= ? ;'
    #print(selectRunTimes, start, end)
    c.execute(selectRunTimes, (start, end))
    result = c.fetchone()
    if result is None:
        heat = cool = aux = fan = 0
    else:
        heat = result['heat']
        cool = result['cool']
        aux  = result['aux']
        fan  = result['fan']
    elapsed = (last - first).total_seconds()
    return {'elapsed' : elapsed, 'heat' : heat, 'cool' : cool, 'aux' : aux, 'fan': fan}

def getYears(c, thermostat):
    select_min_max_yr = 'SELECT '\
        'min(dataTime) AS min,  '\
        'max(dataTime) AS max   '\
        'FROM ' + thermostat + ';'
    c.execute(select_min_max_yr)
    minmax = c.fetchone()
    first = dt.datetime.strptime(minmax['min'], '%Y-%m-%d %H:%M:%S%z')
    last  = dt.datetime.strptime(minmax['max'], '%Y-%m-%d %H:%M:%S%z')
    return first, last

def makeSection(c, thermostat, title, byDay = False, byMonth = False, year = None):
    start, end, name = getTimeInterval.getPeriod(title, year = year)
    selectFields =  'SELECT ' \
        'date(dataTime)    AS date,    '\
        'max(temperature)  AS maxT,    '\
        'min(temperature)  AS minT,    '\
        'avg(temperature)  AS avgT,    '\
        'max(desiredCool)  AS maxC,    '\
        'min(desiredCool)  AS minC,    '\
        'avg(desiredCool)  AS avgC,    '\
        'max(desiredHeat)  AS maxH,    '\
        'min(desiredHeat)  AS minH,    '\
        'avg(desiredHeat)  AS avgH     '\
        ' FROM ' + thermostat +\
        ' WHERE dataTime >= ? AND dataTime <= ? '
    select = selectFields + ' ;'
    # sqlite date(timestamp) returns the UTC date
    selectByDay   = selectFields + ' GROUP BY substr(dataTime,1,10) ORDER BY dataTime DESC;'
    selectByMonth = selectFields + ' GROUP BY substr(dataTime,1, 7) ORDER BY dataTime DESC;'
    if byDay:
        c.execute(selectByDay, (start, end))
    elif byMonth:
        c.execute(selectByMonth, (start, end))
    else:
        c.execute(select, (start, end))
    result = c.fetchall()
    for record in result:
        if byDay:
            lineTemps = fmtTempsLine(record['date'], record)
            BOD = dt.datetime.combine(dt.datetime.strptime(record['date'], '%Y-%m-%d').date(), \
                                      dt.time.min)
            EOD = dt.datetime.combine(dt.datetime.strptime(record['date'], '%Y-%m-%d').date(), \
                                      dt.time.max)
            dailyRunStats = runTimes(c, thermostat, BOD, EOD)
            lineRunTm = fmtRunTmLine(dailyRunStats)
            if checkSanity(dailyRunStats, record['date'], thermostat):
                lineRunTm += ' High Usage'
        elif byMonth:
            lineTemps = fmtTempsLine(record['date'][0:7], record)
            BOM = dt.datetime.combine(dt.datetime.strptime(record['date'], '%Y-%m-%d').date(), \
                                      dt.time.min)
            BOM = BOM.replace(day = 1)
            if BOM.month == 12:
                EOM = BOM.replace(year = BOM.year + 1, month = 1, day = 1) - \
                        dt.timedelta(microseconds = 1)
            else:
                EOM = BOM.replace(month = BOM.month + 1, day = 1) - \
                    dt.timedelta(microseconds = 1)
            #print('byMonth', record['date'], BOM, EOM)
            dailyRunStats = runTimes(c, thermostat, BOM, EOM)
            lineRunTm = fmtRunTmLine(dailyRunStats)
        else:
            lineTemps = fmtTempsLine(name, record)
            lineRunTm = fmtRunTmLine(runTimes(c, thermostat, start, end))
        print(lineTemps + lineRunTm)
        
def makeReport(c, thermostat):
    first, last = getYears(c, thermostat)
    print('---------------------------', thermostat, '----------------------------')
    printHeader()
    makeSection(c, thermostat, 'Today')
    makeSection(c, thermostat, 'Prev7days', byDay = True)
    printHeader()
    for period in ['This Week', 'Last Week', 'This Month', 'Last Month']:
        makeSection(c, thermostat,  period)
    for period in ['This Month', 'Last Month']:
        printHeader()
        for year in range(last.year, first.year - 1, -1):
            makeSection(c, thermostat, period, year = year)
    printHeader()
    makeSection(c, thermostat, 'YearByMonth', byMonth = True)
    makeSection(c, thermostat, 'LastYear')
    printHeader()
    for year in range(last.year, first.year - 1, -1):
        makeSection(c, thermostat, 'Year', year = year)
    print('')
    makeSection(c, thermostat,  'All')

    #printHeader()
    #makeSection(c, thermostat,  'All', byDay = True)
    
def main():
    HoneywellDB = '/home/jim/tools/Honeywell/MBthermostat3.sql'
    BayWebDB    = '/home/jim/tools/Honeywell/MBthermo.sql'
    EcobeeDB    = '/home/jim/tools/Ecobee/MBthermostat.sql'
    EcobeeDB    = '/home/jim/tools/Ecobee/Thermostats.sql'
    WorkingDB   = '/home/jim/tools/Honeywell/Working.sql'
    WorkingDB   = ':memory:'
    Create = 'CREATE TABLE IF NOT EXISTS ZZZZZZZZ (\n' +\
        ' id             INTEGER PRIMARY KEY,      \n' +\
        ' dataTime       TEXT,                     \n' +\
        ' temperature    INTEGER,                  \n' +\
        ' desiredCool    REAL DEFAULT NULL,        \n' +\
        ' desiredHeat    REAL DEFAULT NULL,        \n' +\
        ' outputStatus   TEXT,                     \n' +\
        ' fan            INTEGER,                  \n' +\
        ' heatPump1      INTEGER DEFAULT NULL,     \n' +\
        ' auxHeat1       INTEGER,                  \n' +\
        ' cool1          INTEGER,                  \n' +\
        ' hvacMode       TEXT,                     \n' +\
        ' src            TEXT                      \n' +\
        ' );'
    eCreate = 'CREATE TABLE IF NOT EXISTS ZZZZZZZZ ( \n' +\
        ' id             INTEGER PRIMARY KEY,        \n' +\
        ' dataTime       TEXT,                       \n' +\
        ' temperature    REAL,                       \n' +\
        ' desiredCool    REAL DEFAULT NULL,          \n' +\
        ' desiredHeat    REAL DEFAULT NULL,          \n' +\
        ' outputStatus   TEXT,                       \n' +\
        ' fan            INTEGER,                    \n' +\
        ' heatPump1      INTEGER,                    \n' +\
        ' auxHeat1       INTEGER,                    \n' +\
        ' cool1          INTEGER,                    \n' +\
        ' hvacMode       TEXT,                       \n' +\
        ' src            TEXT  DEFAULT "E"           \n' +\
        ' );'
    eInsert = 'INSERT INTO ZZZZZZZZ               \n' +\
        '   ( dataTime,                           \n' +\
        '     temperature,                        \n' +\
        '     desiredCool,                        \n' +\
        '     desiredHeat,                        \n' +\
        '     outputStatus,                       \n' +\
        '     fan,                                \n' +\
        '     heatPump1,                          \n' +\
        '     auxHeat1,                           \n' +\
        '     cool1,                              \n' +\
        '     hvacMode)                           \n' +\
        '  SELECT dataTime,                       \n' +\
        '         temperature,                    \n' +\
        '         desiredCool,                    \n' +\
        '         desiredHeat,                    \n' +\
        '         NULL     AS outputStatus,       \n' +\
        '         fan,                            \n' +\
        '         heatPump1,                      \n' +\
        '         auxHeat1,                       \n' +\
        '         cool1,                          \n' +\
        '         hvacMode                        \n' +\
        '    FROM Edb.YYYYYYYYX                   \n' +\
        '    WHERE SUBSTR(dataTime,1,4) > "2020"  \n' +\
        '    ;                                      '
    # EcoBee was new in NMB in March of 2021
    
    Insert = 'INSERT OR REPLACE INTO ZZZZZZZZ \n' +\
        '   ( dataTime,                       \n' +\
        '     temperature,                    \n' +\
        '     desiredCool,                    \n' +\
        '     desiredHeat,                    \n' +\
        '     outputStatus,                   \n' +\
        '     fan,                            \n' +\
        '     heatPump1,                      \n' +\
        '     auxHeat1,                       \n' +\
        '     cool1,                          \n' +\
        '     hvacMode,                       \n' +\
        '     src)                            \n' +\
        '  -- Use mode to set outputStatus    \n' +\
        '  -- for BayWeb:                     \n' +\
        '  -- {0,1,2} <--> {off, heat, cool}  \n' +\
        '  --                                 \n' +\
        '  SELECT datetime  AS dataTime,      \n' +\
        '         iat       AS temperature,   \n' +\
        '         sp        AS desiredCool,   \n' +\
        '         NULL      AS desiredHeat,   \n' +\
        '         "cool"    AS outputStatus,  \n' +\
        '         fan,                        \n' +\
        '         NULL     AS heatPump1,      \n' +\
        '         NULL     AS auxHeat1,       \n' +\
        '         NULL     AS cool1,          \n' +\
        '         NULL     AS hvacMode,       \n' +\
        '         "B"      AS src             \n' +\
        '    FROM Bdb.YYYYYYYY                \n' +\
        '    WHERE mode == 2                  \n' +\
        ' UNION ALL                           \n' +\
        '  SELECT datetime AS dataTime,       \n' +\
        '         iat      AS temperature,    \n' +\
        '         NULL     AS desiredCool,    \n' +\
        '         sp       AS desiredHeat,    \n' +\
        '         "heat"   AS outputStatus,   \n' +\
        '         fan,                        \n' +\
        '         NULL     AS heatPump1,      \n' +\
        '         NULL     AS auxHeat1,       \n' +\
        '         NULL     AS cool1,          \n' +\
        '         NULL     AS hvacMode,       \n' +\
        '         "B"      AS src             \n' +\
        '    FROM Bdb.YYYYYYYY                \n' +\
        '    WHERE mode == 1                  \n' +\
        ' UNION ALL                           \n' +\
        '  SELECT datetime AS dataTime,       \n' +\
        '         iat      AS temperature,    \n' +\
        '         NULL     AS desiredCool,    \n' +\
        '         NULL     AS desiredHeat,    \n' +\
        '         "off"    AS outputStatus,   \n' +\
        '         fan,                        \n' +\
        '         NULL     AS heatPump1,      \n' +\
        '         NULL     AS auxHeat1,       \n' +\
        '         NULL     AS cool1,          \n' +\
        '         NULL     AS hvacMode,       \n' +\
        '         "B"      AS src             \n' +\
        '    FROM Bdb.YYYYYYYY                \n' +\
        '    WHERE mode == 0                  \n' +\
        ' UNION ALL                           \n' +\
        '  SELECT                             \n' +\
        '     statusTime   AS dataTime,       \n' +\
        '     temp         AS temperature,    \n' +\
        '     coolSetPoint AS desiredCool,    \n' +\
        '     heatSetpoint AS desiredHeat,    \n' +\
        '     outputStatus,                   \n' +\
        '     fanOn        AS fan,            \n' +\
        '     NULL         AS heatPump1,      \n' +\
        '     NULL         AS auxHeat1,       \n' +\
        '     NULL         AS cool1,          \n' +\
        '     NULL         AS hvacMode,       \n' +\
        '     "H"          AS src             \n' +\
        '    FROM Hdb.YYYYYYYY                \n' +\
        ' UNION ALL                           \n' +\
        '  SELECT                             \n' +\
        '     dataTime,                       \n' +\
        '     temperature,                    \n' +\
        '     desiredCool,                    \n' +\
        '     desiredHeat,                    \n' +\
        '     outputStatus,                   \n' +\
        '     fan,                            \n' +\
        '     heatPump1,                      \n' +\
        '     auxHeat1,                       \n' +\
        '     cool1,                          \n' +\
        '     hvacMode,                       \n' +\
        '     "E"              AS src         \n' +\
        '    FROM eYYYYYYYY                   \n' +\
        ' ; '
    Index    = 'CREATE INDEX IF NOT EXISTS ZZZZZZZZindex ON YYYYYYYY (dataTime)'
    UpdateC  = 'UPDATE ZZZZZZZZ SET desiredCool = NULL WHERE desiredCool == "null";'
    UpdateH  = 'UPDATE ZZZZZZZZ SET desiredHeat = NULL WHERE desiredHeat == "null";'
    UpdateT  = 'UPDATE ZZZZZZZZ SET temperature = NULL WHERE temperature == "null";'
    db = sqlite3.connect(WorkingDB)
    db.row_factory = sqlite3.Row
    c = db.cursor()
    c.execute('ATTACH DATABASE "' + HoneywellDB + '" AS Hdb')
    c.execute('ATTACH DATABASE "' + BayWebDB    + '" AS Bdb')
    c.execute('ATTACH DATABASE "' + EcobeeDB    + '" AS Edb')
    #db.set_trace_callback(print)
    stats = ''
    for thermostat in ['Upstairs', 'Downstairs']:
        table = 'main.' + thermostat
        c.execute('DROP TABLE IF EXISTS ' + table)
        create = Create.replace('ZZZZZZZZ', table)
        #print(create)
        c.execute(create)
        
        index = Index.replace('ZZZZZZZZ', table)
        index = index.replace('YYYYYYYY', thermostat)
        #print(index)
        c.execute(index)
        
        # recode Ecobee coolStatus & heatStatus to outputStatus
        etable = 'main.e' + thermostat
        c.execute('DROP TABLE IF EXISTS ' + etable)
        ecreate = eCreate.replace('ZZZZZZZZ', etable)
        #print(ecreate)
        c.execute(ecreate)
        einsert = eInsert.replace('ZZZZZZZZ', etable)
        einsert = einsert.replace('YYYYYYYY', thermostat)
        #print(einsert)
        c.execute(einsert)
        db.commit()
        
        insert = Insert.replace('ZZZZZZZZ', table)
        insert = insert.replace('YYYYYYYY', thermostat)
        #print(insert)
        c.execute(insert)
        db.commit()
        update = UpdateC.replace('ZZZZZZZZ', table)
        c.execute(update)
        update = UpdateH.replace('ZZZZZZZZ', table)
        c.execute(update)
        update = UpdateT.replace('ZZZZZZZZ', table)
        c.execute(update)
        db.commit()
        #db.set_trace_callback(print)

        stats += recodeOldThermostat(c, thermostat)
        db.commit()
                
        makeReport(c, thermostat)

    print(insaneUsage)
    print('\n', stats)

if __name__ == '__main__':
  main()
