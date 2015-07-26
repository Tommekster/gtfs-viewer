# ##########################################################################################################
# GTFS DATA EXTRACTOR
# Created by Jon Kostyniuk on 28MAY2015
# Last modified by Jon Kostyniuk on 28MAY2015
# Property of JK Enterprises
# v0.01a
# ##########################################################################################################
#
# Version History:
# ----------------
# 28MAY2015 v0.01a - JK
#   - Initial Version.
#
# Usage:
# ------
# Describe usage.
#
# Instructions:
# -------------
# None currently.
#

# ##########################################################################################################
# MODULES AND DEFINITIONS
# ##########################################################################################################

#!/usr/bin/python

# STANDARD MODULES
# ----------------

#import csv
import datetime as dt
import json
import os
import pandas as pd
import StringIO
import requests
import uuid
import zipfile

# CUSTOM MODULES
# --------------

# n/a

# GLOBAL CONSTANT VARIABLES
# -------------------------

# Initialize
global DATA_FOLDER		  # GTFS Server Side Data Folder

# Define
DATA_FOLDER = "./data/"

# DEFINITIONS
# -----------

# GTFS Feed Variables
gtfsFeeds = [           # GTFS Feed Sources, URLs, and API Keys
  {
    "name": "TransitFeeds",
    "url": "http://api.transitfeeds.com/v1/",
    "api-key": "0d8f7e0c-2f6d-4180-b824-242a44658b03"
  }
]


# SQLite Database Variables
#dbConn = None

testdata = {
  "success": "true",
  "uuid": "4f7698c38c734c249ecf9aa5a3c6e0ca",
  "data": [
    {
      "timestamp": 1434328453,
      "agency_name": "York Region Transit"
    }
  ]
}

# General Transit Feed Specification (GTFS) Variables
#gtfsSource = "http://gtfs.winnipegtransit.com/google_transit.zip"	# GTFS Source File
gtfsSource = "google_transit.zip"	# GTFS Source File

# External API Links
GTFS_API = "http://www.gtfs-data-exchange.com/api/agencies" # GTFS Exchange API Data


# ##########################################################################################################
# DEFINED CLASSES AND FUNCTIONS
# ##########################################################################################################

# MODULE CLASSES
# --------------

# n/a

# MODULE FUNCTIONS
# ----------------

# Function to Create Trip Map
def createTripMap(uuid, AgencyID, RouteID, datetime):
  # Define UUID and Preset Agency Folder Path
  datapath = DATA_FOLDER + str(uuid) + "/" + str(AgencyID) + "/"
  jsondata = {}
  jsondata["uuid"] = str(uuid)
  jsondata["agency_id"] = int(AgencyID)
  jsondata["route_id"] = RouteID

  # Split Date and Time Data
  trDate = datetime.split(", ")[0]
  trTime = datetime.split(", ")[1] + ":00"

  # Get Valid Service ID List for Date/Time
  try:
    lServiceID = getServiceID(datapath, trDate)
    jsondata["service_id"] = lServiceID # Audit Trail
    print lServiceID
    success = True
  except:
    jsondata["service_id"] = [] # Audit Trail
    print "ERROR: Service ID failed to resolve!!"
    success = False

  # Get Valid Trip ID List from Route and Service IDs
  try:
    lTripID = getTripID(datapath, RouteID, lServiceID)
    jsondata["trip_id"] = lTripID # Audit Trail
    print lTripID
    success = True
  except:
    jsondata["trip_id"] = [] # Audit Trail
    print "ERROR: Initial Trip ID failed to resolve!!"
    success = False

  # Get Trip ID Sequence Based on Arrival Time of First Stop, Return Sequence
  try:
    pdStopSeq = getStopSeq(datapath, lTripID, trTime)
    jsondata["trip_id"] = pdStopSeq["trip_id"][0] # Audit Trail
    print pdStopSeq["trip_id"][0]
    success = True
  except:
    jsondata["trip_id"] = -1 # Audit Trail
    print "ERROR: Final Trip ID failed to resolve!!"
    success = False

  # Get Shape ID from Trip ID
  try:
    ShpID = getShapeID(datapath, pdStopSeq["trip_id"][0])
    jsondata["shape_id"] = ShpID # Audit Trail
    print ShpID
    success = True
  except:
    jsondata["shape_id"] = -1 # Audit Trail
    print "ERROR: Polyline Shape ID failed to resolve!!"
    success = False

  # Get Route Polyline Sequence
  try:
    lShpSeq = getRtPolySeq(datapath, ShpID)
    jsondata["shape_sequence"] = lShpSeq
    print lShpSeq
    success = True
  except:
    jsondata["shape_sequence"] = [] # Audit Trail
    print "ERROR: Shape Sequence failed to resolve!!"
    success = False

  # Output Final Parsed Date and Time
  jsondata["datetime"] = trDate + ", " + trTime

  # Confirm whether calculations succeeded, as tried above
  if success:
    jsondata["success"] = "true"
  else:
    jsondata["success"] = "false"

  return json.dumps(jsondata)

# Function to Create Unique User ID
def createUUID():
  return str(uuid.uuid4().hex)

# Function to Get Preloaded Agencies
def getAgencies(uuid):
  # Define UUID Folder Path Variables
  uuidpath = DATA_FOLDER + str(uuid)
  jsondata = {}
  jsondata["uuid"] = str(uuid)
  jsondata["data"] = []  
  # Check if server-side UUID directory exists
  dataCount = 0
  if os.path.isdir(uuidpath):
    # Get preset folders for UUID
    listPreset = os.listdir(uuidpath)
    # Populate preset data list
    for listitem in listPreset:
      try: # Enables only timestamp directories to be fetched, others skipped
        itemdata = {}
        itemdata["timestamp"] = int(listitem)
        itemdata["agency_name"] = readAgencyName(uuidpath + "/" + listitem + "/")
        jsondata["data"].append(itemdata)
        dataCount += 1
      except:
        pass
  # Create directory for UUID
  else:
    os.makedirs(uuidpath)
  # Indicate JSON Data Success
  jsondata["data_count"] = dataCount
  jsondata["success"] = "true"
  
  return json.dumps(jsondata)

# Function to Get GTFS Exchange API Data
def getGTFS():
  return requests.get(GTFS_API).text

# Function to Get Routes List
def getRoutes(uuid, AgencyID):
  # Define UUID and Preset Agency Folder Path
  datapath = DATA_FOLDER + str(uuid) + "/" + str(AgencyID) + "/"
  jsondata = {}
  jsondata["uuid"] = str(uuid)
  jsondata["agency_id"] = int(AgencyID)
  # Get Full Agency Information to Display
  jsondata["agency_info"] = readAgency(datapath)
  # Get Start and End Calendar Dates
  jsondata["calendar_dates"] = readCalendarExt(datapath)
  # Get Required Route Fields to Display
  jsondata["data"] = readRoutes(datapath)
  # Indicate JSON Data Success
  jsondata["data_count"] = len(jsondata["data"])
  jsondata["success"] = "true"

  return json.dumps(jsondata)
  

# HELPER (MONKEY) FUNCTIONS
# -------------------------

# Function to Convert Date Format
def convDateFormat(longdate):
  return int(dt.datetime.strptime(longdate, "%a %b %d %Y").strftime("%Y%m%d"))

# Function to Convert Day of Week to Long
def convLongDoW(longdate): 
  return dt.datetime.strptime(longdate, "%a %b %d %Y").strftime("%A").lower()

# Function to Convert Time to Seconds
def convTimeSecs(hhmmss):
  # Split Hours/Minutes/Seconds
  hhmmss = hhmmss.strip().split(":")
  # Set and Cumulate Time Seconds
  timesecs = 0
  # Add Hour Seconds
  timesecs += int(hhmmss[0]) * 60 * 60
  # Add Minute Seconds
  timesecs += int(hhmmss[1]) * 60
  # Add Remaining Seconds
  timesecs += int(hhmmss[2])

  return timesecs

# Function to Get Route Polyline Sequence
def getRtPolySeq(filepath, shpid):
  pdShapes = pd.read_csv(filepath + "shapes.txt", encoding="utf-8-sig")
  pdShpSeq = pdShapes[(pdShapes["shape_id"] == shpid)].reset_index(drop=True)
  pdShpSeq = pdShpSeq.sort_index(by=["shape_pt_sequence"])
  pdShpSeq = pdShpSeq[["shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"]]
  dShpSeq = pdShpSeq.transpose().to_dict() # Transform to transposed dictionary object
  # Transfrom from dictionary to list object
  lShpSeq = []
  for seqk, seqv in dShpSeq.iteritems():
    lShpSeq.append(seqv) # Save sequence value, not key

  return lShpSeq

# Function to Get Shape ID
def getShapeID(filepath, tripid):
  pdTrips = pd.read_csv(filepath + "trips.txt", encoding="utf-8-sig")
  tripsel = pdTrips[(pdTrips["trip_id"] == tripid)].reset_index(drop=True)
  if len(tripsel) == 1:
    shpid = tripsel["shape_id"][0]
    return shpid
  else:
    return -1

# Function to Get Service IDs
def getServiceID(filepath, trdate):
  # Convert Format of Variables
  dow = convLongDoW(trdate) # Convert to Long Day of Week
  numdate = convDateFormat(trdate) # Convert to Numeric Date Value
  # Lookup Calendar Day of Week and Get Service ID 
  pdCalendar = pd.read_csv(filepath + "calendar.txt", encoding="utf-8-sig")
  calsel = pdCalendar[(pdCalendar[dow] == 1) & (pdCalendar["start_date"] <= numdate) & (pdCalendar["end_date"] >= numdate)].transpose().to_dict()
  # Lookup Calendar Dates Exceptions for Current Date
  pdCalDates = pd.read_csv(filepath + "calendar_dates.txt", encoding="utf-8-sig")  
  excsel = pdCalDates[(pdCalDates["date"] == numdate)].transpose().to_dict()
  # Create Valid Service ID List for Application
  lServiceID = [] # List to Hold Valid Service IDs
  for i in calsel.keys():
    lServiceID.append(calsel[i]["service_id"]) # Append Current Service ID Value
  # Add/Remove Exception Service IDs
  for i in excsel.keys():
    if excsel[i]["exception_type"] == 1: # Add Exception Service ID
      lServiceID.append(excsel[i]["service_id"]) # Append Current Service ID Value
    elif excsel[i]["exception_type"] == 2: # Remove Exception Service ID
      for j in range(len(lServiceID)):
        if excsel[i]["service_id"] == lServiceID[j]:
          lServiceID[j] = -1 # Set Exception Removal Flag
  # Drop Removal Flags
  lServiceID = filter(lambda a: a != -1, lServiceID)

  return lServiceID

# Function to Get Stop Sequence
def getStopSeq(filepath, trid, trtime):
  # Lookup Trip ID and Stop Times Sequence
  pdStopTimes = pd.read_csv(filepath + "stop_times.txt", encoding="utf-8-sig")
  # Lookup Valid Stop Sequence and Convert Arrival Time to Seconds
  selstseq = pdStopTimes[(pdStopTimes["trip_id"].isin(trid)) & (pdStopTimes["stop_sequence"] == 1)]
  dfTimeCol = selstseq["arrival_time"] # Temp Variable to Hold Time Data
  dfTimeCol = dfTimeCol.str.strip() # Strip Whitespace
  dfTimeCol = dfTimeCol.str.split(":") # Split Time Values between ':'  
  #### CAVEAT - POTENTIAL ISSUE, USE .loc, next line
  selstseq["arrival_time"] = (dfTimeCol.str[0].astype("int") * 3600) + (dfTimeCol.str[1].astype("int") * 60) +  dfTimeCol.str[2].astype("int") # Convert to Seconds
  selstseq = selstseq[(selstseq["arrival_time"] >= convTimeSecs(trtime))]
  try: # Attempt to find stop times for route at requested interval
    selstseq = selstseq.loc[selstseq["arrival_time"].idxmin(),:]
    pdStopSeq = pdStopTimes[(pdStopTimes["trip_id"] == selstseq["trip_id"])]
    return pdStopSeq.reset_index(drop=True)

  except: # Return empty data frame
    return pd.DataFrame() 

# Function to Get Trip IDs
def getTripID(filepath, rtid, srvid):
  # Lookup Calendar Day of Week and Get Service ID 
  pdTrips = pd.read_csv(filepath + "trips.txt", encoding="utf-8-sig")
  pdTrips["route_id"] = pdTrips["route_id"].astype(str) # Ensure Route ID Always String Type
  # Lookup Valid Trip IDs
  tripsel = pdTrips[(pdTrips["service_id"].isin(srvid)) & (pdTrips["route_id"] == rtid)]
  lTripID = tripsel["trip_id"].tolist()

  return lTripID

# Function to Read Agency Info
def readAgency(filepath):
  pdAgency = pd.read_csv(filepath + "agency.txt", encoding="utf-8-sig")
  pdAgency = pdAgency.fillna("")

  return {"name": pdAgency["agency_name"][0], "url": pdAgency["agency_url"][0], "timezone": pdAgency["agency_timezone"][0],}

# Function to Read Agency Name
def readAgencyName(filepath):
  pdAgency = pd.read_csv(filepath + "agency.txt", encoding="utf-8-sig")

  return pdAgency["agency_name"][0]

# Function to Read Calendar Extent Dates
def readCalendarExt(filepath):
  # Read Regular Calendar Data
  pdCalendar = pd.read_csv(filepath + "calendar.txt", encoding="utf-8-sig")
  sDate = pdCalendar.min()["start_date"]
  eDate = pdCalendar.max()["end_date"]
  
  return {"start": sDate, "end": eDate}

# Function to Read Routes File
def readRoutes(filepath):
  # Prepare Route Data
  pdRoutes = pd.read_csv(filepath + "routes.txt", encoding="utf-8-sig")
  pdRoutes = pdRoutes.fillna("")
  pdRoutes = pdRoutes.sort(columns=["route_short_name"])
  #pdRoutes = pdRoutes.sort_index(by = "route_short_name")
  numRt = len(pdRoutes)
  pdRoutes = pdRoutes.to_dict()
  # Load Route Data
  listRoutes = []
  for i in range(numRt):
    itemdata = {}
    itemdata["route_id"] = str(pdRoutes["route_id"][i])
    itemdata["route_short_name"] = pdRoutes["route_short_name"][i]
    if pdRoutes["route_long_name"][i] != "":
      itemdata["route_long_name"] = pdRoutes["route_long_name"][i]
    else:
      itemdata["route_long_name"] = "[ UNNAMED ROUTE ]"
    itemdata["route_type"] = pdRoutes["route_type"][i]
    listRoutes.append(itemdata)

  return listRoutes

# Function to Extract GTFS ZIP to Temporary Folder [UNFINISHED]
def unzipGTFS(fileloc):
  # Open ZIP Archive Location
  zf = zipfile.ZipFile(gtfsSource)

  # Loop through ZIP File Names
  #for filename in zf.namelist():


# ##########################################################################################################
# END OF SCRIPT
# ##########################################################################################################





"""
def main():
	# Open ZIP Archive Location
	zf = zipfile.ZipFile(gtfsSource)

	# Loop through ZIP File Names
	for filename in zf.namelist():
		# Find Transit Route Shape File
		if filename == "shapes.txt":
			# Read Data Model into Pandas
			shapes = pd.read_csv(zf.open(filename))



			# Test Outputs
			#print shapes.head()
			#print shapes[["shape_pt_sequence","shape_pt_lat","shape_pt_lon"]]

			# Grab by ID and sort by PT Sequence
			curShape = shapes[shapes['shape_id'] == 36099].sort_index(by = 'shape_pt_sequence')[["shape_pt_lat","shape_pt_lon"]]
"""

"""
try:
    data = zf.read(filename)
except KeyError:
    print "ERROR: Did not find %s in zip file" % filename
else:
    #print filename
"""


"""
TRY USING PANDAS HERE
http://bokeh.pydata.org/en/latest/
https://github.com/datalit/pythonworkshop

train[(train['Age'] == 34) & (train['Sex']== 'female')]
train[(train['Name'].str.contains('Lily'))]
train[(train['Name'].str.startswith('Futrelle'))]
sorting available... train.sort_index(by = 'Age')
train.sort_index(by = ['Age', 'Pclass'], ascending = [False, True]).head()
add fields to data frame... train['FareToAge'] = train['Fare'] / train['Age']
pivot tables... pd.pivot_table(train, values = 'Age', index = ['Sex'], columns = ['Pclass'], aggfunc = 'mean')
save... train.to_csv('./data/train-new.csv')
"""


"""
JSON--

{
  "shape_id": 36099,
  "shape_pt_number": 91,
  "shape_pt_sequence": [
    {
      "id": 1,
      "lat": 43.809785,
      "lon": -79.454099,
      "dist": 0.0
    },
    {
      "id": 2,
      "lat": 43.8098,
      "lon": -79.453994,
      "dist": 0.0082
    },
    {
      "id": 3,
      "lat": 43.809784,
      "lon": -79.45389,
      "dist": 0.0175
    }
  ]
}
"""