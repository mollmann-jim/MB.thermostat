#!/usr/bin/env python

# By Brad Goodman
# http://www.bradgoodman.com/
# brad@bradgoodman.com

import urllib2
import urllib
import json
import datetime
import re
import time
import math
import base64
import time
import httplib
import sys
import getopt
import os
import stat
import subprocess
import string
import sched

try:
    import therm_auth
    USERNAME = therm_auth.USERNAME
    PASSWORD = therm_auth.PASSWORD
    DEVICE_ID_UP = therm_auth.DEVICE_ID_UP
    DEVICE_ID_DOWN = therm_auth.DEVICE_ID_DOWN
except:
    pass

class Thermo:
    AUTH="https://mytotalconnectcomfort.com/portal"
    cookiere=re.compile('\s*([^=]+)\s*=\s*([^;]*)\s*')
    
    def __init__(self, DEVICE_ID):
        self.DEVICE_ID = DEVICE_ID
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
        self.whenStatus = None
        self.statusValidSeconds = 30
        print "__init__ DEVICE_ID", DEVICE_ID

    def sample(self):
        print "sample DEVICE_ID", self.DEVICE_ID
        print "AUTH", self.AUTH
        print "USERNAME", USERNAME

    def showStatusLong(self):
        if self.staleStatus():
            print "status is stale"
            self.getStatus()
        print "Indoor Temperature:",self.temperature
        print "Cool Setpoint:",self.coolSet
        print "Heat Setpoint:",self.heatSet
        print "Hold Until :",self.holdUntil
        print "Status Cool:",self.coolStatus
        print "Status Heat:",self.heatStatus
        print "Status Fan:",self.fanStatus
        print "Fan Running",self.fanOn
        print "Output Status",self.outputStatus

    def showStatusShort(self):
        if self.staleStatus():
            self.getStatus()
        print self.whenStatus, \
            "Temp:", self.temperature, \
            "Cool Set:", self.coolSet, \
            "Heat Set:", self.heatSet, \
            "Hold:", self.holdUntil, \
            "Cool:", self.coolStatus, \
            "Heat:", self.heatStatus, \
            "Fan:", self.fanStatus, \
            "Fan On", self.fanOn, \
            "Output:", self.outputStatus
        
    def staleStatus(self):
        if self.whenStatus != None:
            last = (time.mktime(self.whenStatus.timetuple()))
            t = datetime.datetime.now()
            now = (time.mktime(t.timetuple()))
            delta = now - last
            return delta > self.statusValidSeconds
        else:
            return True
    
    def client_cookies(self, cookiestr, container):
        if not container: container={}
        print "cookiestr - ",cookiestr
        toks=re.split(';|,',cookiestr)
        for t in toks:
            k=None
            v=None
            m=cookiere.search(t)
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
        conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
        conn.request("GET", "/portal/",None,headers)
        r0 = conn.getresponse()
        #print r0.status, r0.reason
  
        for x in r0.getheaders():
            (n,v) = x
            #print "R0 HEADER",n,v
            if (n.lower() == "set-cookie"): 
                cookiejar=self.client_cookies(v,cookiejar)
        #cookiejar = r0.getheader("Set-Cookie")
        location = r0.getheader("Location")

        retries=5
        params=urllib.urlencode({"timeOffset":"240",
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
        conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
        conn.request("POST", "/portal/",params,headers)
        r1 = conn.getresponse()
        #print r1.status, r1.reason
    
        for x in r1.getheaders():
            (n,v) = x
            #print "GOT2 HEADER",n,v
            if (n.lower() == "set-cookie"): 
                cookiejar=self.client_cookies(v,cookiejar)
                self.cookie=self.export_cookiejar(cookiejar)
        print "Cookiejar now",self.cookie
        location = r1.getheader("Location")
        
        if ((location == None) or (r1.status != 302)):
            #raise BaseException("Login fail" )
            print("ErrorNever got redirect on initial login  status={0} {1}".format(r1.status,r1.reason))
            return

    def getStatus(self):
        #print "getStatus"
        if self.cookie == "":
            self.get_login()
        code=str(self.DEVICE_ID)
        t = datetime.datetime.now()
        self.whenStatus = t
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
        conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
        #conn.set_debuglevel(999);
        #print "LOCATION R3 is",location
        conn.request("GET", location,None,headers)
        r3 = conn.getresponse()
        if (r3.status != 200):
            print("Error Didn't get 200 status on R3 status={0} {1}".format(r3.status,r3.reason))
            return

        # Print thermostat information returned
    
        #print r3.status, r3.reason
        rawdata=r3.read()
        j = json.loads(rawdata)
        #print "R3 Dump"
        #print json.dumps(j,indent=2)
        #print json.dumps(j,sort_keys=True,indent=4, separators=(',', ': '))
        #print "Success:",j['success']
        #print "Live",j['deviceLive']
        self.temperature = j['latestData']['uiData']["DispTemperature"]
        self.coolSet = j['latestData']['uiData']["CoolSetpoint"]
        self.heatSet = j['latestData']['uiData']["HeatSetpoint"]
        self.holdUntil = j['latestData']['uiData']["TemporaryHoldUntilTime"]
        self.coolStatus = j['latestData']['uiData']["StatusCool"]
        self.heatStatus = j['latestData']['uiData']["StatusHeat"]
        self.fanStatus = j['latestData']['fanData']["fanMode"]
        self.fanOn = j['latestData']['fanData']['fanIsRunning']
        self.outputStatus = j['latestData']['uiData']['EquipmentOutputStatus']
        self.whenStatus = t
    
#===============================================================================

AUTH="https://mytotalconnectcomfort.com/portal"

cookiere=re.compile('\s*([^=]+)\s*=\s*([^;]*)\s*')

def client_cookies(cookiestr,container):
  if not container: container={}
  toks=re.split(';|,',cookiestr)
  for t in toks:
    k=None
    v=None
    m=cookiere.search(t)
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

def export_cookiejar(jar):
  s=""
  for x in jar:
    s+='%s=%s;' % (x,jar[x])
  return s



def get_login(action, value=None, hold_time=1, DEVICE_ID=DEVICE_ID_DOWN):

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
  conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
  conn.request("GET", "/portal/",None,headers)
  r0 = conn.getresponse()
  #print r0.status, r0.reason
  
  for x in r0.getheaders():
    (n,v) = x
    #print "R0 HEADER",n,v
    if (n.lower() == "set-cookie"): 
      cookiejar=client_cookies(v,cookiejar)
  #cookiejar = r0.getheader("Set-Cookie")
  location = r0.getheader("Location")

  retries=5
  params=urllib.urlencode({"timeOffset":"240",
    "UserName":USERNAME,
    "Password":PASSWORD,
    "RememberMe":"false"})
  #print params
  newcookie=export_cookiejar(cookiejar)
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
  conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
  conn.request("POST", "/portal/",params,headers)
  r1 = conn.getresponse()
  #print r1.status, r1.reason
    
  for x in r1.getheaders():
    (n,v) = x
    #print "GOT2 HEADER",n,v
    if (n.lower() == "set-cookie"): 
      cookiejar=client_cookies(v,cookiejar)
  cookie=export_cookiejar(cookiejar)
  #print "Cookiejar now",cookie
  location = r1.getheader("Location")

  if ((location == None) or (r1.status != 302)):
    #raise BaseException("Login fail" )
    print("ErrorNever got redirect on initial login  status={0} {1}".format(r1.status,r1.reason))
    return


  # Skip second query - just go directly to our device_id, rather than letting it
  # redirect us to it. 

  code=str(DEVICE_ID)
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
          "Cookie":cookie
      }
  conn = httplib.HTTPSConnection("mytotalconnectcomfort.com")
  #conn.set_debuglevel(999);
  #print "LOCATION R3 is",location
  conn.request("GET", location,None,headers)
  r3 = conn.getresponse()
  if (r3.status != 200):
    print("Error Didn't get 200 status on R3 status={0} {1}".format(r3.status,r3.reason))
    return


  # Print thermostat information returned

  if (action == "status"):
    
    #print r3.status, r3.reason
    rawdata=r3.read()
    j = json.loads(rawdata)
    #print "R3 Dump"
    #print json.dumps(j,indent=2)
    #print json.dumps(j,sort_keys=True,indent=4, separators=(',', ': '))
    #print "Success:",j['success']
    #print "Live",j['deviceLive']
    print "Indoor Temperature:",j['latestData']['uiData']["DispTemperature"]
    #print "Indoor Humidity:",j['latestData']['uiData']["IndoorHumidity"]
    print "Cool Setpoint:",j['latestData']['uiData']["CoolSetpoint"]
    print "Heat Setpoint:",j['latestData']['uiData']["HeatSetpoint"]
    print "Hold Until :",j['latestData']['uiData']["TemporaryHoldUntilTime"]
    print "Status Cool:",j['latestData']['uiData']["StatusCool"]
    print "Status Heat:",j['latestData']['uiData']["StatusHeat"]
    print "Status Fan:",j['latestData']['fanData']["fanMode"]
    print "Fan Running",j['latestData']['fanData']['fanIsRunning']
    print "Output Status",j['latestData']['uiData']['EquipmentOutputStatus']
    return
    
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
          'Referer':"/TotalConnectComfort/Device/CheckDataSession/"+code,
          "Cookie":cookie
      }


  # Data structure with data we will send back

  payload = {
      "CoolNextPeriod": None,
      "CoolSetpoint": None,
      "DeviceID": DEVICE_ID,
      "FanMode": None,
      "HeatNextPeriod": None,
      "HeatSetpoint": None,
      "StatusCool": 0,
      "StatusHeat": 0,
      "SystemSwitch": None
  }


  # Calculate the hold time for cooling/heating
  t = datetime.datetime.now();

  stop_time = ((t.hour+hold_time)%24) * 60 + t.minute
  stop_time = stop_time/15

  # Modify payload based on user input

  if (action == "cool"):
    payload["CoolSetpoint"] = value
    payload["StatusCool"] = 1
    payload["StatusHeat"] = 1
    payload["CoolNextPeriod"] = stop_time
    
  if (action == "heat"):
    payload["HeatSetpoint"] = value
    payload["StatusCool"] = 1
    payload["StatusHeat"] = 1
    payload["HeatNextPeriod"] = stop_time

  if (action == "cancel"):
    payload["StatusCool"] = 0
    payload["StatusHeat"] = 0

  if (action == "fan"):
    payload["FanMode"] = value


  # Prep and send payload

  location="/portal/Device/SubmitControlScreenChanges"

  rawj=json.dumps(payload)
  
  conn = httplib.HTTPSConnection("mytotalconnectcomfort.com");
  #conn.set_debuglevel(999);
  #print "R4 will send"
  #print rawj
  conn.request("POST", location,rawj,headers)
  r4 = conn.getresponse()
  if (r4.status != 200): 
    print("Error Didn't get 200 status on R4 status={0} {1}".format(r4.status,r4.reason))
    return
  else:
    print "Success in configuring thermostat!"
   #  print "R4 got 200"


def printUsage():
  print
  print "Cooling: -c temperature -t hold_time"
  print "Heating: -h temperature -t hold_time"
  print "Status: -s"
  print "Cancel: -x"
  print "Fan: -f [0=auto|1=on]"
  print
  print "Example: Set temperature to cool to 80f for 1 hour: \n\t therm.py -c 80 -t 1"
  print
  print "If no -t hold_time is provided, it will default to one hour from command time."
  print
    
    
def main():

    up = Thermo(DEVICE_ID_UP)
    down = Thermo(DEVICE_ID_DOWN)

    up.showStatusLong()
    for i in range(1000):
        up.showStatusShort()
        time.sleep(300)
        
    up.sample()

    if sys.argv[1] == "-s":
        get_login("status")
        sys.exit()

    if sys.argv[1] == "-x":
        get_login("cancel")
        sys.exit()        
        
    if (len(sys.argv) < 3) or (sys.argv[1] == "-help"):
        printUsage()
        sys.exit()
        
    if sys.argv[1] == "-c":
        get_login("cool", sys.argv[2])
        sys.exit()

    if sys.argv[1] == "-h":
        get_login("heat", sys.argv[2])
        sys.exit()

    if sys.argv[1] == "-f":
        get_login("fan", sys.argv[2])
        sys.exit()        
        
if __name__ == '__main__':
  main()
    
