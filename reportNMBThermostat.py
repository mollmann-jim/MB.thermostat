#!/usr/bin/env python3
import datetime as dt
import sqlite3
from dateutil.tz import tz
from sys import path
path.append('/home/jim/tools/')
from shared import getTimeInterval

DBname = '/home/jim/tools/Honeywell/MBthermostat3.sql'

def fmtTempsLine(tag, row):
    line = tag + ': (none)'
    if row['minT']:
        period =  '{:>10s}'.format(tag)
        minT   = ' {:>5d}'.format(row['minT'])
        maxT   = ' {:>5d}'.format(row['maxT'])
        avgT   = ' {:>5.1f}'.format(row['avgT'])
        minC   = ' {:>-5d}'.format(row['minC'])
        maxC   = ' {:>5d}'.format(row['maxC'])
        avgC   = ' {:>5.1f}'.format(row['avgC'])
        minH   = ' {:>5d}'.format(row['minH'])
        maxH   = ' {:>5d}'.format(row['maxH'])
        avgH   = ' {:>5.1f}'.format(row['avgH'])
        line = period + minT + maxT + avgT + minC + maxC + avgC + minH + maxH + avgH
    return line

def fmtRunTmLine(x):
    
    line = 'Invalid "elapsed":' + str(x['elapsed'])
    if x['elapsed'] > 0:
        heatPct = '{:>6.1f}'.format(100.0 * x['heat']  / x['elapsed'])
        coolPct = '{:>6.1f}'.format(100.0 * x['cool']  / x['elapsed'])
        fanPct  = '{:>6.1f}'.format(100.0 * x['fanOn'] / x['elapsed'])
        line = heatPct + coolPct + fanPct
    return line

def printHeader():
    # period min/max/avg(temp) min/max/avg(dew) avg(wind) sum(precip)
    #      2020/07/02 mmmmm MMMMM aaaaa mmmmm MMMMM aaaaa wwwww rrrrr
    print('')
    print('                               Min   Max   Avg   Min   Max   Avg  Heat  Cool   Fan')
    print('             Min   Max   Avg  Cool  Cool  Cool  Heat  Heat  Heat   Run   Run   Run')
    print('            Temp  Temp  Temp   Set   Set   Set   Set   Set   Set     %     %     %')
    
def runTimes(c, table, start, end):
    select = 'SELECT statusTime, fanOn, outputStatus FROM ' + table +\
        ' WHERE statusTime >= ? AND statusTime <= ? ;'
    c.execute(select, (start, end))
    result = c.fetchall()
    fanTime = heatTime = coolTime = 0
    last = start
    for r in result:
        statTime = dt.datetime.strptime((r['statusTime']), '%Y-%m-%d %H:%M:%S')
        if r['outputStatus'] == 'cool on':
            coolTime += (statTime - last).total_seconds()
        elif r['outputStatus'] == 'heat on':
            heatTime += (statTime - last).total_seconds()
        elif r['fanOn'] == 1:
            fanTime += (statTime - last).total_seconds()
        elif r['fanOn'] == 0 and  r['outputStatus'] == 'off':
            # no fan/heat/cool - just idle
            pass
        elif r['fanOn'] is None and  r['outputStatus'] == 'off':
            # no fan/heat/cool - just idle
            pass
        else:
            print('Unexpected: outputStatus:', r['outputStatus'], '\tfanOn:',  r['fanOn'])
        last = statTime
    elapsed = (end - start).total_seconds()
        
    #print('Cooling:', coolTime, '\tHeating:', heatTime, '\tFan Only', fanTime, '\tElapsed:', elapsed)
    return {'elapsed' : elapsed, 'heat' : heatTime, 'cool' : coolTime, 'fanOn': fanTime}

def makeSection(c, thermostat, title, byDay = False, year = None):
    start, end = getTimeInterval.getPeriod(title, year = year)
    selectFields =  'SELECT ' \
        'max(temp)         AS maxT, '\
        'min(temp)         AS minT, '\
        'avg(temp)         AS avgT, '\
        'max(coolSetPoint) AS maxC, '\
        'min(coolSetPoint) AS minC, '\
        'avg(coolSetPoint) AS avgC, '\
        'max(heatSetPoint) AS maxH, '\
        'min(heatSetPoint) AS minH, '\
        'avg(heatSetPoint) AS avgH  '\
        ' FROM ' + thermostat +\
        ' WHERE statusTime >= ? AND statusTime <= ? '
    select = selectFields + ' ;'
    # sqlite date(timestamp) returns the UTC date
    selectByDay = selectFields + ' GROUP BY substr(statusTime,1,10) ORDER BY statusTime DESC;'
    if byDay:
        c.execute(selectByDay, (start, end))
    else:
        c.execute(select, (start, end))
    result = c.fetchall()
    if year: title += ' ' + year
    for record in result:
        if byDay:
            lineTemps = fmtTempsLine((record['date'], record))
        else:
            lineTemps = fmtTempsLine(title, record)
        lineRunTm = fmtRunTmLine(runTimes(c, thermostat, start, end))
        print(lineTemps + lineRunTm)
        
def makeReport(c, thermostat):
    print('---------------------------', thermostat, '----------------------------')
    printHeader()
    makeSection(c, thermostat, 'Today')
    
    printHeader()
    select_min_yr = 'SELECT min(statusTime) AS min FROM ' + thermostat + ';'
    c.execute(select_min_yr)
    min = c.fetchone()
    first = dt.datetime.strptime(min['min'], '%Y-%m-%d %H:%M:%S')
    select_max_yr = 'SELECT max(statusTime) AS max FROM ' + thermostat + ';'
    c.execute(select_max_yr)
    max = c.fetchone()
    last = dt.datetime.strptime(max['max'], '%Y-%m-%d %H:%M:%S')
    for year in range(last.year, first.year - 1, -1):
        makeSection(c, thermostat, 'Year', year = '{:4d}'.format(year))
    print('')
    
def main():
    db = sqlite3.connect(DBname)
    db.row_factory = sqlite3.Row
    c = db.cursor()
    #db.set_trace_callback(print)

    for int in ['Today', 'Yesterday', 'Prev7days', 'This Week', 'Last Week', 'This Month', \
                'Last Month']:
        start, end = getTimeInterval.getPeriod(int)
        #print(start, '\t', end, '\t', int)
    for yr in ['2017', '2018', '2019', '2020']:
        start, end = getTimeInterval.getPeriod('Year', year = yr)
        #print(start, '\t', end, '\t Year ', yr)

    for thermostat in ['Upstairs', 'Downstairs']:
        makeReport(c, thermostat)
    
        
    #makeReport(c, 'RDU')
    #makeReport(c, 'MYR')

if __name__ == '__main__':
  main()
