#!/usr/bin/env python3
import datetime as dt
import sqlite3
from dateutil.tz import tz
from sys import path
path.append('/home/jim/tools/')
from shared import getTimeInterval

DBname = '/home/jim/tools/Honeywell/MBthermostat3.sql'

def fmtLine(tag, row):
    line = tag + ': (none)'
    if row['minT']:
        period =  '{:>10s}'.format(tag)
        minT   = ' {:>5d}'.format(row['minT'])
        maxT   = ' {:>5d}'.format(row['maxT'])
        avgT   = ' {:>5.1f}'.format(row['avgT'])
        minC   = ' {:>-7d}'.format(row['minC'])
        maxC   = ' {:>7d}'.format(row['maxC'])
        avgC   = ' {:>7.1f}'.format(row['avgC'])
        minH   = ' {:>7d}'.format(row['minH'])
        maxH   = ' {:>7d}'.format(row['maxH'])
        avgH   = ' {:>7.1f}'.format(row['avgH'])
        line = period + minT + maxT + avgT + minC + maxC + avgC + minH + maxH + avgH
    return line
                                

def printHeader():
    # period min/max/avg(temp) min/max/avg(dew) avg(wind) sum(precip)
    #      2020/07/02 mmmmm MMMMM aaaaa mmmmm MMMMM aaaaa wwwww rrrrr
    print('')
    print('             Min   Max   Avg     Min     Max    Avg      Min     Max     Avg ')
    print('            Temp  Temp  Temp CoolSet CoolSet CoolSet HeatSet HeatSet HeatSet')
def makeSection(c, site, title, byDay = False, year = None):
    start, end = getPeriod(title, year = year)
    selectFields = 'SELECT date(timestamp) as date, ' +\
        'MIN(temperature) AS minT, MAX(temperature) AS maxT, AVG(temperature) AS avgT, ' +\
        'MIN(dewpoint) AS minD, MAX(dewpoint) AS maxD, AVG(dewpoint) AS avgD, ' +\
        'AVG(wind) AS avgW, TOTAL(precipitation1hr) AS rain ' +\
        'FROM ' + site + ' WHERE timestamp >= ? AND timestamp <= ?'
    select = selectFields + ' ;'
    # sqlite date(timestamp) returns the UTC date
    #selectByDay = selectFields + ' GROUP BY date(timestamp) ORDER BY date(timestamp) DESC;'
    selectByDay = selectFields + ' GROUP BY substr(timestamp,1,10) ORDER BY timestamp DESC;'
    #print(title, start, end)
    if byDay:
        c.execute(selectByDay, (start, end))
    else:
        c.execute(select, (start, end))
    result = c.fetchall()
    #printHeader()
    if year: title += ' ' + year
    for record in result:
        if byDay:
            print(fmtLine(record['date'], record))
        else:
            print(fmtLine(title, record))

def makeReport(c, site):
    print('---------------------------', site, '----------------------------')
    printHeader()
    makeSection(c, site, 'Today')
    makeSection(c, site, 'Prev7days', byDay = True)

    printHeader()
    for period in ['This Week', 'Last Week', 'This Month', 'Last Month']:
        makeSection(c, site,  period)
        
    printHeader()
    select_min_yr = 'SELECT min(timestamp) AS min FROM ' + site + ';'
    c.execute(select_min_yr)
    min = c.fetchone()
    first = dt.datetime.strptime(min['min'], '%Y-%m-%d %H:%M:%S%z')
    select_max_yr = 'SELECT max(timestamp) AS max FROM ' + site + ';'
    c.execute(select_max_yr)
    max = c.fetchone()
    last = dt.datetime.strptime(max['max'], '%Y-%m-%d %H:%M:%S%z')
    for year in range(last.year, first.year - 1, -1):
        makeSection(c, site, 'Year', year = '{:4d}'.format(year))
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

    table = 'Upstairs'
    select = 'SELECT ' \
        'max(temp)         AS maxT, '\
        'min(temp)         AS minT, '\
        'avg(temp)         AS avgT, '\
        'max(coolSetPoint) AS maxC, '\
        'min(coolSetPoint) AS minC, '\
        'avg(coolSetPoint) AS avgC, '\
        'max(heatSetPoint) AS maxH, '\
        'min(heatSetPoint) AS minH, '\
        'avg(heatSetPoint) AS avgH  '\
        ' FROM ' + table +\
        ' WHERE statusTime >= ? AND statusTime <= ? ;'
    print(select)
    start, end = getTimeInterval.getPeriod('Yesterday')
    start = dt.datetime(2019, 8, 3)
    end   = dt.datetime(2019, 8, 4) - dt.timedelta(microseconds = 1)
    print(start,end)
    c.execute(select, (start, end))
    result = c.fetchall()
    printHeader()
    for record in result:
        line = fmtLine('Yesterday', record)
        print(line)

    select = 'SELECT statusTime, fanOn, outputStatus FROM ' + table +\
        ' WHERE statusTime >= ? AND statusTime <= ? ;'
    c.execute(select, (start, end))
    result = c.fetchall()
    fanTime = heatTime = coolTime = 0
    fanLast = heatLast = coolLast = start
    for r in result:
        statTime = dt.datetime.strptime((r['statusTime']), '%Y-%m-%d %H:%M:%S')
        #print(statTime, r['fanOn'], r['outputStatus'])
        if r['outputStatus'] == 'cool on':
            coolTime += (statTime - coolLast).total_seconds()
            print('Cooling', coolTime, coolLast, statTime, (statTime - coolLast).total_seconds())
        elif r['outputStatus'] == 'heat on':
            heatTime += (statTime - heatLast).total_seconds()
            print('Heating', heatTime, heatLast, statTime, (statTime - heatLast).total_seconds())
        elif r['fanOn'] == 1:
            fanTime += (statTime - heatLast).total_seconds()
            print('Fan Only', fanTime, fanLast, statTime, (statTime - fanLast).total_seconds())
        elif r['fanOn'] == 0 and  r['outputStatus'] == 'off':
            # no fan/heat/cool - just idle
            pass
        else:
            print('Unexpected: outputStatus:', r['outputStatus'], '\tfanOn:',  r['fanOn'])
        fanLast = heatLast = coolLast = statTime
        
    print('Cooling:', coolTime, '\tHeating:', heatTime, '\tFan Only', fanTime)

        
    #makeReport(c, 'RDU')
    #makeReport(c, 'MYR')

if __name__ == '__main__':
  main()
