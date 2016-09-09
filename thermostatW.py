#!/usr/bin/env python3

# Jim Mollmann
# original:
# By Brad Goodman
# http://www.bradgoodman.com/
# brad@bradgoodman.com

# To Do:
# error recovery on network calls
# weather?
# fail-safe "off" calls
# status data to DB
import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import json
import datetime
import re
import time
import math
import base64
import time
import http.client
import socket
import sys
import getopt
import os
import stat
import subprocess
import string
import sched
import random
import sqlite3
import math
import traceback

try:
    import therm_auth
    USERNAME = therm_auth.USERNAME
    PASSWORD = therm_auth.PASSWORD
    DEVICE_ID_UP = therm_auth.DEVICE_ID_UP
    DEVICE_ID_DOWN = therm_auth.DEVICE_ID_DOWN
    WEATHER_KEY = therm_auth.OPEN_WEATHER_MAP_key
except:
    pass

DBname = '/home/jim/tools/Honeywell/MBthermostat3.sql'

class Thermo:
    
    def __init__(self, DEVICE_ID, name):
        self.DEVICE_ID = DEVICE_ID
        self.name = name
        self.cookie = ""
        self.temperature = None
        self.coolSet = None
        self.heatSet = None
        self.holdUntil = None
        self.coolStatus = None
        self.heatStatus = None
        self.fanStatus = None
        self.fanOn = None
        self.outputStatus = None
        self.switchPosition = None
        self.whenStatus = None
        self.statusValidSeconds = 30
        self.statusLineNum = 0
        self.statusLinesPerPage = 20
        self.strSwitchPosition = [ 'aux ' , 'heat', 'off ', 'cool', 'autoHeat', 'autoCool', 'SouthernAway', '7WTF' ]
        self.strStatus = [ 'schedule', 'hold until', 'hold perm', 'vacation', '4WTF' ]
        self.strFan = [ 'auto', 'on', 'circulate', 'schedule', '4WTF' ]
        self.strOutputStatus = ['off', 'heat on', 'cool on', 'undefined' ]
        self.cookiere = re.compile('\s*([^=]+)\s*=\s*([^;]*)\s*')
        self.table = 'savedStatus'
        self.cursor = None
        self.sqlite = self.initSavedStatus()

    def initSavedStatus(self):
        sqlite = sqlite3.connect(DBname)
        create = "CREATE TABLE IF NOT EXISTS " + self.table + "(" +\
                 " thermostat     TEXT PRIMARY KEY, " +\
                 " timestamp      INTEGER DEFAULT CURRENT_TIMESTAMP, " +\
                 " coolNextPeriod INTEGER, " +\
                 " coolSetPoint   INTEGER, " +\
                 " heatNextPeriod INTEGER, " +\
                 " heatSetPoint   INTEGER, " +\
                 " coolStatus     INTEGER, " +\
                 " heatStatus     INTEGER, " +\
                 " fanStatus      INTEGER, " +\
                 " switchPosition INTEGER  " +\
                 " )"
        #print(create)
        sqlite.execute(create)
        sqlite.row_factory = sqlite3.Row
        self.cursor = sqlite.cursor()
        # make an initial record
        insert = "INSERT OR IGNORE INTO " +\
                 self.table + "(thermostat) " +\
                 " VALUES('" + self.name +"')"
        #print(insert)
        self.cursor.execute(insert)
        sqlite.commit()
        return sqlite

    def saveStatus(self):
        update = "UPDATE " + self.table + " SET " +\
                 " timestamp      = ?, " +\
                 " coolNextPeriod = ?, " +\
                 " coolSetPoint   = ?, " +\
                 " heatNextPeriod = ?, " +\
                 " heatSetPoint   = ?, " +\
                 " coolStatus     = ?, " +\
                 " heatStatus     = ?, " +\
                 " fanStatus      = ?, " +\
                 " switchPosition = ?  " +\
                 " WHERE thermostat = ?"
        #print(update)
        values = (self.whenStatus, \
                  self.coolNextPeriod, \
                  self.coolSet, \
                  self.heatNextPeriod, \
                  self.heatSet, \
                  self.coolStatus, \
                  self.heatStatus, \
                  self.fanStatus, \
                  self.switchPosition, \
                  self.name \
                  )
        #print(values)
        self.cursor.execute(update, values)
        self.sqlite.commit()

    def getSavedStatus(self):
        select = "SELECT * from " + self.table + " WHERE thermostat=?"
        #print(select)
        self.cursor.execute(select, (self.name,))
        row = self.cursor.fetchone()
        return row

    def showStatusLong(self):
        self.getStatus()
        print(self.name, ':')
        print(" Indoor Temperature:", self.temperature)
        print(" Cool Setpoint:", self.coolSet)
        print(" Heat Setpoint:", self.heatSet)
        print(" Hold Until :", self.holdUntil)
        print(" Status Cool:", self.strStatus[self.coolStatus])
        print(" Status Heat:", self.strStatus[self.heatStatus])
        print(" Status Fan:", self.strFan[self.fanStatus])
        print(" Fan Running", self.fanOn)
        print(" Output Status", self.strOutputStatus[self.outputStatus])
        print(" System Switch", self.strSwitchPosition[self.switchPosition])

    def showStatusShort(self):
        self.getStatus()
        print(self.name, \
            self.whenStatus, \
            "Temp:", self.temperature, \
            "Cool Set:", self.coolSet, \
            "Heat Set:", self.heatSet, \
            "Hold:", self.holdUntil, \
            "Cool:", self.strStatus[self.coolStatus], \
            "Heat:", self.strStatus[self.heatStatus], \
            "Fan:", self.strFan[self.fanStatus], \
            "Fan On", self.fanOn, \
            "Output:", self.strOutputStatus[self.outputStatus], \
            "Mode:", self.strSwitchPosition[self.switchPosition])

    def showStatusLine(self):
        self.getStatus()
        if self.statusLineNum % self.statusLinesPerPage == 0:
            print('{11:10s} {0:^20s} {1:4s} {2:4s} {3:4s} {4:5s} {5:^10s} {6:^10s} {7:^6s} {8:^7s} {9:6s} {10:8s}'.\
                format('         ', '    ', 'Cool', 'Heat', ' Hold', ' Cool ', ' Heat ', 'Fan', 'Fan', 'Output',\
                       '    ', ' '))
            print('{11:10s} {0:^20s} {1:4s} {2:4s} {3:4s} {4:5s} {5:^10s} {6:^10s} {7:^6s} {8:^7s} {9:6s} {10:^8s}'.\
                format('Date Time', 'Temp', ' Set', ' Set', 'Until', 'Status', 'Status', 'Status', 'On', 'Status',\
                       'Mode', ' '))
        print('{11:10s} {0:^20s} {1:4d} {2:4d} {3:4d} {4:5s} {5:^10s} {6:^10s} {7:^6s} {8:^7s} {9:^6s} {10:^8s}'.\
            format(str(self.whenStatus), self.getTemp(), self.getCoolSetpoint(), self.getHeatSetpoint(),\
                   self.getHoldUntil(),  self.getCoolStatus(), self.getHeatStatus(), self.getFanStatus(),\
                   str(self.fanOn), self.getOutputStatus(), self.getSwitchPosition(), self.name))
        self.statusLineNum += 1
        
    def staleStatus(self):
        if self.whenStatus != None:
            last = (time.mktime(self.whenStatus.timetuple()))
            t = datetime.datetime.now()
            now = (time.mktime(t.timetuple()))
            delta = now - last
            return delta > self.statusValidSeconds
        else:
            return True

    def scheduleOn(self):
        return self.coolStatus == 0 and self.heatStatus == 0

    def getCoolSetpoint(self):
        self.getStatus()
        return int(self.coolSet)

    def getHeatSetpoint(self):
        self.getStatus()
        return int(self.heatSet)

    def getTemp(self):
        self.getStatus()
        return int(self.temperature)

    def getStatusWhen(self):
        self.getStatus()
        return self.whenStatus

    def getHoldUntil(self):
        self.getStatus()
        untilHH = int(self.holdUntil / 60)
        untilMM = self.holdUntil % 60
        until = "{0:02d}:{1:02d}".format(untilHH, untilMM)
        if self.holdUntil == 0:
            until = '     '
        return until

    def getCoolStatus(self):
        self.getStatus()
        return self.strStatus[self.coolStatus]
    
    def getHeatStatus(self):
        self.getStatus()
        return self.strStatus[self.heatStatus]

    def getFanStatus(self):
        self.getStatus()
        return self.strFan[self.fanStatus] if self.fanStatus is not None else None
        #print(x)
        #return self.strFan[self.fanStatus]

    def getOutputStatus(self):
        self.getStatus()
        return self.strOutputStatus[self.outputStatus]

    def getSwitchPosition(self):
        self.getStatus()
        return self.strSwitchPosition[self.switchPosition]
    
    def client_cookies(self, cookiestr, container):
        if not container: container={}
        #print "cookiestr - ",cookiestr
        toks=re.split(';|,',cookiestr)
        for t in toks:
            k=None
            v=None
            m=self.cookiere.search(t)
            if m:
                k=m.group(1)
                v=m.group(2)
                if (k in ['path','Path','HttpOnly']):
                    k=None
                    v=None
            if k: 
                #print k,v
                container[k]=v
        return container

    def export_cookiejar(self, jar):
        s=""
        for x in jar:
            s+='%s=%s;' % (x,jar[x])
        return s

    def myHTTPrequest(self, host, method, url, body, headers, reauthorize = False):
        retries = 5
        delay = 8
        for attempt in range(retries):
            #print attempt, ':', method, url
            try:
                conn = http.client.HTTPSConnection(host)
                conn.request(method, url, body, headers)
            except (http.client.HTTPException, socket.error, ConnectionResetError) as detail:
                print(attempt, ':', method, url)
                print(("myHTTPrequest socket.error:{0}".format(detail)))
                #print attempt
                time.sleep(delay)
                delay += delay
                if (attempt == (retries-1)):
                    print("fifth try failed too")
                    raise
            else:
                response = conn.getresponse()
                status = response.status
                #print "status:", status
                if (status == 200):
                    pass
                elif (status == 302):
                    pass
                else:
                    print(("Error Didn't get 200 status on {2} {3} status={0} {1}".\
                          format(response.status,response.reason, method, url)))
                    print(attempt, ':', method, url)
                    if ((status == 401) or (status == 500)) and (reauthorize):
                        print("Retrying get_login() try:", attempt)
                        time.sleep(delay)
                        delay += delay
                        self.get_login()
                        print("old Headers:", headers)
                        headers['Cookie'] = self.cookie
                        print("new Headers:", headers)
                        print("After get_login() retry", attempt)
                        continue
                #print "returning response"
                return response
        print("All 3 attempts are done. Return None")
        return None

    def get_login(self):
        #print "get_login"
        cookiejar=None
        #print
        #print
        #print "Run at ",datetime.datetime.now()
        headers={"Content-Type":"application/x-www-form-urlencoded",
                 "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                 "Accept-Encoding":"sdch",
                 "Host":"mytotalconnectcomfort.com",
                 "DNT":"1",
                 "Origin":"https://mytotalconnectcomfort.com/portal",
                 "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36"
        }
        #conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
        #conn.request("GET", "/portal/",None,headers)
        #r0 = conn.getresponse()
        r0 = self.myHTTPrequest("mytotalconnectcomfort.com", "GET", "/portal/", None, headers)
        #print r0.status, r0.reason
  
        for x in r0.getheaders():
            (n,v) = x
            #print "R0 HEADER",n,v
            if (n.lower() == "set-cookie"): 
                cookiejar=self.client_cookies(v,cookiejar)
        #cookiejar = r0.getheader("Set-Cookie")
        location = r0.getheader("Location")

        retries=5
        params=urllib.parse.urlencode({"timeOffset":"240",
                                 "UserName":USERNAME,
                                 "Password":PASSWORD,
                                 "RememberMe":"false"})
        #print params
        newcookie=self.export_cookiejar(cookiejar)
        #print "Cookiejar now",newcookie
        headers={"Content-Type":"application/x-www-form-urlencoded",
                 "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                 "Accept-Encoding":"sdch",
                 "Host":"mytotalconnectcomfort.com",
                 "DNT":"1",
                 "Origin":"https://mytotalconnectcomfort.com/portal/",
                 "Cookie":newcookie,
                 "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36"
        }
        #conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
        #conn.request("POST", "/portal/",params,headers)
        #r1 = conn.getresponse()
        r1 = self.myHTTPrequest("mytotalconnectcomfort.com", "POST", "/portal/", params, headers)
        #print r1.status, r1.reason
    
        for x in r1.getheaders():
            (n,v) = x
            #print "GOT2 HEADER",n,v
            if (n.lower() == "set-cookie"): 
                cookiejar=self.client_cookies(v,cookiejar)
                self.cookie=self.export_cookiejar(cookiejar)
        #print "Cookiejar now",self.cookie
        location = r1.getheader("Location")
        
        if ((location == None) or (r1.status != 302)):
            #raise BaseException("Login fail" )
            print(("ErrorNever got redirect on initial login  status={0} {1}".format(r1.status,r1.reason)))
            return

    def getStatus(self, now = False):
        #print "getStatus"
        if not now and not self.staleStatus():
            return
        if self.cookie == "":
            self.get_login()
        code=str(self.DEVICE_ID)
        t = datetime.datetime.now()
        utc_seconds = (time.mktime(t.timetuple()))
        utc_seconds = int(utc_seconds*1000)
        #print "Code ",code

        location="/portal/Device/CheckDataSession/"+code+"?_="+str(utc_seconds)
        #print "THIRD"
        headers={
            "Accept":"*/*",
            "DNT":"1",
            #"Accept-Encoding":"gzip,deflate,sdch",
            "Accept-Encoding":"plain",
            "Cache-Control":"max-age=0",
            "Accept-Language":"en-US,en,q=0.8",
            "Connection":"keep-alive",
            "Host":"mytotalconnectcomfort.com",
            "Referer":"https://mytotalconnectcomfort.com/portal/",
            "X-Requested-With":"XMLHttpRequest",
            "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36",
            "Cookie":self.cookie
        }
        #conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
        #conn.set_debuglevel(999);
        #print "LOCATION R3 is",location
        #conn.request("GET", location,None,headers)
        #r3 = conn.getresponse()
        #if (r3.status != 200):
        #    print("Error Didn't get 200 status on R3 status={0} {1}".format(r3.status,r3.reason))
        #    return
        r3 = self.myHTTPrequest("mytotalconnectcomfort.com", "GET", location, None, headers, reauthorize = True)
        # Print thermostat information returned
    
        #print r3.status, r3.reason
        rawdata=r3.read().decode('utf-8')
        try:
            j = json.loads(rawdata)
        except (ValueError):
            print("json ValueError:", rawdata)
            return False
        except:
            print("error rawdata:", rawdata)
            raise
        #print "R3 Dump"
        #print json.dumps(j,indent=2)
        #print json.dumps(j,sort_keys=True,indent=4, separators=(',', ': '))
        #print "Success:",j['success']
        #print "Live",j['deviceLive']
        self.temperature = j['latestData']['uiData']["DispTemperature"]
        self.coolSet = j['latestData']['uiData']["CoolSetpoint"]
        self.heatSet = j['latestData']['uiData']["HeatSetpoint"]
        self.holdUntil = int(j['latestData']['uiData']["TemporaryHoldUntilTime"])
        self.coolStatus = j['latestData']['uiData']["StatusCool"]
        self.heatStatus = j['latestData']['uiData']["StatusHeat"]
        self.fanStatus = j['latestData']['fanData']["fanMode"]
        self.fanOn = j['latestData']['fanData']['fanIsRunning']
        self.outputStatus = j['latestData']['uiData']['EquipmentOutputStatus']
        self.switchPosition = j['latestData']['uiData']['SystemSwitchPosition']
        self.coolNextPeriod = j['latestData']['uiData']['CoolNextPeriod']
        self.heatNextPeriod = j['latestData']['uiData']['HeatNextPeriod']
        self.whenStatus = t.replace(microsecond = 0) # close enough
        return True

    def getStatusRetry(self, now = True, retries = 5):
        delay = 8
        for attempt in range(retries):
            if (self.getStatus(now)):
                return
            print("getStatus try ", attempt)
            time.sleep(delay)
            delay += delay
        print("Failed to getStatus for ", self.name, " in ", retries, " tries")
        
    def setThermostat(self, heat=None, cool=None, fan=None, coolNext=None, heatNext=None,\
                      statusCool=None, statusHeat=None, switch=None):
        headers={
            "Accept":'application/json; q=0.01',
            "DNT":"1",
            "Accept-Encoding":"gzip,deflate,sdch",
            'Content-Type':'application/json; charset=UTF-8',
            "Cache-Control":"max-age=0",
            "Accept-Language":"en-US,en,q=0.8",
            "Connection":"keep-alive",
            "Host":"mytotalconnectcomfort.com",
            "Referer":"https://mytotalconnectcomfort.com/portal/",
            "X-Requested-With":"XMLHttpRequest",
            "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36",
            'Referer':"/TotalConnectComfort/Device/CheckDataSession/"+str(self.DEVICE_ID),
            "Cookie":self.cookie
        }
         # Data structure with data we will send back
        payload = {
            "CoolNextPeriod": self.coolNextPeriod,
            "CoolSetpoint": self.coolSet,
            "DeviceID": self.DEVICE_ID,
            "FanMode": self.fanStatus,
            "HeatNextPeriod": self.heatNextPeriod,
            "HeatSetpoint": self.heatSet,
            "StatusCool": self.coolStatus,
            "StatusHeat": self.heatStatus,
            "SystemSwitch": self.switchPosition
        }
        # Calculate the hold time for cooling/heating
        #t = datetime.datetime.now();

        #stop_time = ((t.hour+hold_time)%24) * 60 + t.minute
        #stop_time = stop_time/15

        # Modify payload based on user input
        if heat:
            payload['HeatSetpoint'] = heat
        if cool:
            payload['CoolSetpoint'] = cool
        if fan != None:
            payload['FanMode'] = fan
        if coolNext:
            payload['CoolNextPeriod'] = coolNext
        if heatNext:
            payload['HeatNextPeriod'] = heatNext
        if statusCool:
            payload['StatusCool'] = statusCool
        if statusHeat:
            payload['StatusHeat'] = statusHeat
        if switch:
            payload['SystemSwitch'] = switch 
        # Prep and send payload
            
        location="/portal/Device/SubmitControlScreenChanges"

        rawj=json.dumps(payload)
  
        #conn = httplib.HTTPSConnection("mytotalconnectcomfort.com");
        #conn.set_debuglevel(999);
        #print "R4 will send"
        #print rawj
        #conn.request("POST", location,rawj,headers)
        #r4 = conn.getresponse()
        #if (r4.status != 200): 
        #    print("Error Didn't get 200 status on R4 status={0} {1}".format(r4.status,r4.reason))
        #    return
        #else:
            #print "Success in configuring thermostat!"
            #  print "R4 got 200"
        #    pass
        r4 = self.myHTTPrequest("mytotalconnectcomfort.com", "POST", location, rawj, headers, reauthorize = True)

class Circulate:

    def __init__(self, thermostat, scheduler):
        self.thermostat = thermostat
        self.scheduler = scheduler
        self.runtime = 5*60
        self.frequency = 60*60
        self.startMinute = 0
        self.starttime = None
        self.endtime = None
        #print "init Circulate for", self.thermostat.name

    def Schedule(self, startMinute = None, runtime = None, frequency = None):
        if startMinute:
            self.startMinute = startMinute
        if runtime:
            self.runtime = runtime
        if frequency:
            self.frequency = frequency
        now = datetime.datetime.now()
        firstTime = now.replace(hour = 0, minute = self.startMinute, second = 0, microsecond = 0) -\
                    datetime.timedelta(days=7)
        firstEnd = firstTime + datetime.timedelta(seconds = self.runtime)
        while firstTime < now:
            firstTime += datetime.timedelta(seconds = self.frequency)
        self.starttime = firstTime
        while firstEnd < now:
            firstEnd += datetime.timedelta(seconds = self.frequency)
        self.endtime = firstEnd
        #print "Fan Start time:", self.starttime, self.thermostat.name
        #print "Fan   End time:", self.endtime, self.thermostat.name
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.FanStart, [True])
        self.scheduler.enterabs(time.mktime(self.endtime.timetuple()), 1, self.FanStart, [False])

    def FanStart(self, on):
        self.thermostat.getStatusRetry()
        if on:
            if self.thermostat.scheduleOn():
                self.thermostat.saveStatus()
                #print "Fan On", datetime.datetime.now(), self.thermostat.name
                self.thermostat.setThermostat(fan = True)
            self.starttime = self.starttime + datetime.timedelta(seconds = self.frequency)
            #print "Next fan on", self.starttime
            self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.FanStart, [True])
        else:
            if self.thermostat.scheduleOn():
                saved = self.thermostat.getSavedStatus()
                #print "Fan Off", datetime.datetime.now(), self.thermostat.name
                # if the fan is already off, let it be
                if self.thermostat.fanStatus != 0:
                    self.thermostat.setThermostat(fan = saved['fanStatus'])
            self.endtime = self.endtime + datetime.timedelta(seconds = self.frequency)
            #print "Next fan off", self.starttime
            self.scheduler.enterabs(time.mktime(self.endtime.timetuple()), 1, self.FanStart, [False])

class HumidityControl:

    def __init__(self, thermostat, scheduler):
        self.thermostat = thermostat
        self.scheduler = scheduler
        self.runtime = 30*60
        self.frequency = 24*60*60
        self.startHour = 6
        self.startMinute = 30
        self.coolSet = 62
        self.heatSet = 72
        self.coolLimit = 65
        self.heatLimit = 68
        self.myCool = None
        self.myHeat = None
        self.starttime = None
        self.endtime = None
        #print "init HumidityControl for", self.thermostat.name

    def Schedule(self, startHour = None, startMinute = None, runtime = None, frequency = None, cool = None, heat = None):
        if startHour:
            self.startHour = startHour
        if startMinute:
            self.startMinute = startMinute
        if runtime:
            self.runtime = runtime
        if frequency:
            self.frequency = frequency
        if cool:
            self.coolSet = cool
        if heat:
            self.heatSet = heat
        now = datetime.datetime.now()
        firstTime = now.replace(hour = self.startHour, minute = self.startMinute, second = 0, microsecond = 0) -\
                    datetime.timedelta(days=7)
        firstEnd = firstTime + datetime.timedelta(seconds = self.runtime)
        while firstTime < now:
            firstTime += datetime.timedelta(seconds = self.frequency)
        self.starttime = firstTime
        while firstEnd < now:
            firstEnd += datetime.timedelta(seconds = self.frequency)
        self.endtime = firstEnd
        print("Humidity Start time:", self.starttime, self.thermostat.name)
        print("Humidity  End time:", self.endtime, self.thermostat.name)
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.runSystem, [True])
        self.scheduler.enterabs(time.mktime(self.endtime.timetuple()), 1, self.runSystem, [False])

    def runSystem(self, on):
        self.thermostat.getStatusRetry()
        temperature = self.thermostat.getTemp()
        if temperature > self.coolLimit:
            cool = self.coolSet
            heat = cool - 10
        elif temperature < self.heatLimit:
            heat = self.heatSet
            cool = heat + 10
        else:
            cool = None
            heat = None
        self.myCool = cool
        self.myHeat = heat
        #when to cool, when to heat???
        if on:
            #print "Humidity Control On", datetime.datetime.now(), self.thermostat.name, "cool:", cool, "Heat:", heat
            if not self.thermostat.scheduleOn():
                self.thermostat.saveStatus()
                self.thermostat.setThermostat(cool = cool, heat = heat)
            self.starttime = self.starttime + datetime.timedelta(seconds = self.frequency)
            #print "Next fan on", self.starttime
            self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.runSystem, [True])
        else:
            if not self.thermostat.scheduleOn():
                saved = self.thermostat.getSavedStatus()
                if self.myCool == self.thermostat.getCoolSetpoint():
                    cool = saved['coolSetPoint']
                else:
                    cool = self.thermostat.getCoolSetpoint()
                if self.myHeat == self.thermostat.getHeatSetpoint():
                    heat = saved['heatSetPoint']
                else:
                    heat = self.thermostat.getHeatSetpoint()
                self.thermostat.setThermostat(cool = cool, heat = heat)
            self.endtime = self.endtime + datetime.timedelta(seconds = self.frequency)
            #print "Next fan off", self.starttime
            self.scheduler.enterabs(time.mktime(self.endtime.timetuple()), 1, self.runSystem, [False])

                
class showStatus:
    def __init__(self, thermostat, scheduler):
        self.thermostat = thermostat
        self.scheduler = scheduler
        self.frequency = 5*60
        self.offsetSeconds = 0
        self.starttime = None
        #self.endtime = None
        #print "init showStatus for", self.thermostat.name

    def Schedule(self, offsetSeconds = None, frequency = None):
        if offsetSeconds:
            self.offsetSeconds = offsetSeconds
        if frequency:
            self.frequency = frequency
        now = datetime.datetime.now()
        firstTime = now.replace(hour = 0, minute = 0, second = self.offsetSeconds, microsecond = 0) -\
                    datetime.timedelta(days = 7)
        while firstTime < now:
            firstTime += datetime.timedelta(seconds = self.frequency)
        self.starttime = firstTime
        #print "showStatus Start time:", self.starttime, self.thermostat.name
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.showStatus, ())

    def showStatus(self):
        self.thermostat.showStatusLine()
        self.starttime = self.starttime + datetime.timedelta(seconds = self.frequency)
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.showStatus, ())
        
class logStatus:
    def __init__(self, thermostat, scheduler):
        self.thermostat = thermostat
        self.scheduler = scheduler
        self.frequency = 5*60
        self.offsetSeconds = 0
        self.starttime = None
        self.table = self.thermostat.name
        self.sqlite = sqlite3.connect(DBname)
        create = "CREATE TABLE IF NOT EXISTS " + self.table + "(" +\
                 " id             INTEGER PRIMARY KEY, " +\
                 " timestamp      INTEGER DEFAULT CURRENT_TIMESTAMP, " +\
                 " statusTime     INTEGER, " +\
                 " temp           INTEGER, " +\
                 " coolSetPoint   INTEGER, " +\
                 " heatSetPoint   INTEGER, " +\
                 " holdUntil      TEXT,    " +\
                 " coolStatus     TEXT,    " +\
                 " heatStatus     TEXT,    " +\
                 " fanStatus      TEXT,    " +\
                 " fanOn          INTEGER, " +\
                 " outputStatus   TEXT,    " +\
                 " switchPosition TEXT     " +\
                 " )"
        #print create
        self.sqlite.execute(create)                 

    def Schedule(self, offsetSeconds = None, frequency = None):
        if offsetSeconds:
            self.offsetSeconds = offsetSeconds
        if frequency:
            self.frequency = frequency
        now = datetime.datetime.now()
        firstTime = now.replace(hour = 0, minute = 0, second = self.offsetSeconds, microsecond = 0) -\
                    datetime.timedelta(days = 7)
        while firstTime < now:
            firstTime += datetime.timedelta(seconds = self.frequency)
        self.starttime = firstTime
        #print "showStatus Start time:", self.starttime, self.thermostat.name
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.logStatus, ())

    def logStatus(self):
        row = "INSERT INTO " + self.table + "(statusTime, temp, coolSetPoint, heatSetPoint, holdUntil, " +\
              "coolStatus, heatStatus, fanStatus, fanOn, outputStatus, switchPosition) VALUES(" +\
              "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        #print row
        values = (self.thermostat.getStatusWhen(), \
                  self.thermostat.getTemp(), \
                  self.thermostat.getCoolSetpoint(), \
                  self.thermostat.getHeatSetpoint(), \
                  self.thermostat.getHoldUntil(), \
                  self.thermostat.getCoolStatus(), \
                  self.thermostat.getHeatStatus(), \
                  self.thermostat.getFanStatus(), \
                  self.thermostat.fanOn, \
                  self.thermostat.getOutputStatus(), \
                  self.thermostat.getSwitchPosition() \
        )
        #print values
        self.sqlite.execute(row, values)
        self.sqlite.commit()
        self.starttime = self.starttime + datetime.timedelta(seconds = self.frequency)
        self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.logStatus, ())

class Weather:
    def __init__(self, location = 4598678):
        self.temp = None
        self.name = None
        self.pressure = None
        self.humidity = None
        self.wind = None
        self.direction = None
        self.weather = None
        self.description = None
        self.dewpoint = None
        self.when = None
        self.weatherValidSeconds = 300
        self.locationID = location
        self.where = 'id=' + str(location) + '&APPID=' + WEATHER_KEY
        self.degCtoK=273.15        # Temperature offset between K and C (deg C)
        self.table = 'weather'
        self.sqlite = sqlite3.connect(DBname)
        drop = "DROP TABLE IF EXISTS " + self.table
        self.sqlite.execute(drop)
        self.sqlite.commit()
        create = "CREATE TABLE IF NOT EXISTS " + self.table + "(" +\
                 " id             INTEGER PRIMARY KEY, " +\
                 " timestamp      INTEGER DEFAULT CURRENT_TIMESTAMP, " +\
                 " obsTime        INTEGER, " +\
                 " temp           INTEGER, " +\
                 " pressure       REAL,    " +\
                 " humidity       INTEGER, " +\
                 " dewpoint       INTEGER, " +\
                 " wind           INTEGER, " +\
                 " direction      INTEGER, " +\
                 " locationID     INTEGER, " +\
                 " weather        TEXT,    " +\
                 " description    TEXT,    " +\
                 " name           TEXT     " +\
                 " )"
        #print create
        self.sqlite.execute(create)   
        self.sqlite.commit()

    def CtoF(self, T):
        return (T * 1.8) + 32

    def FtoC(self, T):
        return (T -32) / 1.8

    def CtoK(self, T):
        return T + self.degCtoK

    def KtoC(self, T):
        return T - self.degCtoK

    def getConstants(self, T):
        if ((T > -40.) and (T <= 0.)):
            return [6.1121, 17.368, 238.88, 234.5]
        elif ((T > 0.) and (T <= 50.)):
            return [6.1121, 17.996, 247.15, 234.5]
        else:
            return [6.1121, 18.678, 257.14, 234.5]

    def dewPoint(self, T_K, RH):
        T = self.KtoC(T_K)
        a, b, c, d = self.getConstants(T)
        exponent = (b - (T/d)) * (T/(c + T))
        gamma = math.log((RH/100.) * math.exp(exponent))
        T_d = (c * gamma) / (b - gamma)
        return T_d

    def staleWeather(self):
        if self.when != None:
            last = (time.mktime(self.when.timetuple()))
            t = datetime.datetime.now()
            now = (time.mktime(t.timetuple()))
            delta = now - last
            return delta > self.weatherValidSeconds
        else:
            return True

    def getWeather(self, now = False):
        if not now and not self.staleWeather():
            return
        """ call openweathermap api"""
        try:
            response = urllib.request.urlopen('http://api.openweathermap.org/data/2.5/weather?' + self.where)
            openWeather = response.read().decode('utf-8')
            w = json.loads(openWeather)
            #print (json.dumps(w, indent=2))
            T_K = self.pressure = self.humidity = self.dewpoint = self.wind = self.direction = self.when = 0
            self.name = w.get('name')
            main = w.get('main')
            if main is not None:
                T_K = float(main.get('temp', 0))
                self.temp = int(self.CtoF(self.KtoC(T_K)) + 0.5)
                self.pressure =  0.02953 * main.get('pressure', 0)
                self.humidity = int(main.get('humidity', 0) + 0.5)
                self.dewpoint = int(self.CtoF(int(self.dewPoint(T_K, self.humidity) + 0.5)))
                Xpressure = main.get('pressure', 0)
                Xhumidity = main.get('humidity', 0)
            else:
                print ("main:", json.dumps(w, indent=2))
            wind = w.get('wind')
            if wind is not None:
                self.wind = int(2.23694 * wind.get('speed') + 0.5)
                self.direction = int(wind.get('deg', 999))
                Xwind = wind.get('speed')
            else:
                print ("wind:", json.dumps(w, indent=2))
            weather = w.get('weather')
            if weather is not None:
                w0 = weather[0]
                self.weather = w0.get('main')
                self.description = w0.get('description')
                if len(weather) > 1:
                    print("weather len > 1:", weather)
            else:
                print (json.dumps(w, indent=2))
            when = w.get('dt')
            if when is not None:
                self.when = datetime.datetime.fromtimestamp(when)
            else:
                print ("when:", json.dumps(w, indent=2))
            Xdt = w.get('dt')
            if (T_K * self.pressure * self.humidity * self.dewpoint * self.wind * self.direction) == 0:
                print ("00000:", json.dumps(w, indent=2))
        except:
            for var in dir():
                myvalue = eval(var)
                print(var, type(var), myvalue)
            print ("except:", json.dumps(w, indent=2))
            traceback.print_exc()

    def printWeather(self):
        self.getWeather()
        t = datetime.datetime.now().replace(microsecond = 0)
        #            date     name   temp   humid   dew      press      wind      dir
        Wformat = '{0:^20s} {1:15s} {2:3d} {3:3d}% {4:3d}  {5:5.2f}"Hg {6:3d}mph {7:3d} {8:10s} {9:20s} {10:8.0f} {11:20s}'
        try:
            print(Wformat.format(str(t), self.name, self.temp, self.humidity, self.dewpoint, self.pressure, \
                                 self.wind, self.direction, self.weather, self.description, \
                                 self.locationID, str(self.when)))
        except:
            print("Exception in printWeather:")
            for var in dir():
                myvalue = eval(var)
                print(var, type(var), myvalue)
            traceback.print_exc()

    def Schedule(self, offsetSeconds = None, frequency = None):
        if offsetSeconds:
            self.offsetSeconds = offsetSeconds
        if frequency:
            self.frequency = frequency
        now = datetime.datetime.now()
        firstTime = now.replace(hour = 0, minute = 0, second = self.offsetSeconds, microsecond = 0) -\
                    datetime.timedelta(days = 7)
        while firstTime < now:
            firstTime += datetime.timedelta(seconds = self.frequency)
        self.starttime = firstTime
        #print "showStatus Start time:", self.starttime, self.thermostat.name
        ###self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.logStatus, ())

    def logWeather(self):
        self.getWeather()
        row = 'INSERT INTO ' + self.table + '(obsTime, temp, pressure, humidity, dewpoint, wind, ' +\
              'direction, locationID, weather, description, name)' +\
              'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        #print(row)
        values = (self.when,        \
                  self.temp,        \
                  self.pressure,    \
                  self.humidity,    \
                  self.dewpoint,    \
                  self.wind,        \
                  self.direction,   \
                  self.locationID,  \
                  self.weather,     \
                  self.description, \
                  self.name         \
                  )
        #print(values)
        self.sqlite.execute(row, values)
        self.sqlite.commit()
        #self.starttime = self.starttime + datetime.timedelta(seconds = self.frequency)
        #self.scheduler.enterabs(time.mktime(self.starttime.timetuple()), 1, self.logStatus, ())

        
def main():

    up = Thermo(DEVICE_ID_UP, 'Upstairs')
    down = Thermo(DEVICE_ID_DOWN, 'Downstairs')
    
    # Build a scheduler object that will look at absolute times
    scheduler = sched.scheduler(time.time, time.sleep)

    if False:
        upCirculate = Circulate(up, scheduler)
        downCirculate = Circulate(down, scheduler)
        upCirculate.Schedule(startMinute = 0)
        downCirculate.Schedule(startMinute = 1)

        upStatus = showStatus(up, scheduler)
        downStatus = showStatus(down, scheduler)
        upStatus.Schedule(offsetSeconds = 2)
        downStatus.Schedule(offsetSeconds = 4)

        upHumidity = HumidityControl(up, scheduler)
        downHumidity = HumidityControl(down, scheduler)
        upHumidity.Schedule(startHour = 6, startMinute = 30)
        downHumidity.Schedule(startHour = 6, startMinute = 32)

        upLog = logStatus(up, scheduler)
        downLog = logStatus(down, scheduler)
        upLog.Schedule(offsetSeconds = 1)
        downLog.Schedule(offsetSeconds = 3)

    weather = Weather()
    for i in range(1000):
        weather.printWeather()
        weather.logWeather()
        time.sleep(900)
    
    up.showStatusLong()
    #down.showStatusLong()
    #up.showStatusShort()
    #down.showStatusShort()

    if False:
        scheduler.run()
        
if __name__ == '__main__':
  main()
    
