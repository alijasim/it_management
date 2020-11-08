import frappe
import datetime
import sys
import json

## We'll try to use the local caldav library, not the system-installed
sys.path.insert(0, '..')

import caldav

def cleanName(name):
    name = name.replace("<","")
    name = name.replace(">","")

    return name

@frappe.whitelist()
def fetch_calendars(data):
    #Check if called from client side (not necessary)
    if(isinstance(data,str)):
        data = json.loads(data)

    account = frappe.get_doc("CalDav Account",data["caldavaccount"])

    client = caldav.DAVClient(url=data["url"], username=data["username"], password=data["password"])
    principal = client.principal()
    calendars = principal.calendars()

    for calendar in calendars:
        #Check if Calendar exists already

        #If not create
        doc = frappe.new_doc("CalDav Calendar")
        doc.title = cleanName(calendar.name)
        doc.caldav_account = data["caldavaccount"]
        doc.calendar_url = str(calendar)
        doc.parent = data["caldavaccount"]
        doc.parentfield = "calendars"
        doc.parenttype = "CalDav Account"
        doc.insert()

        doc.link = cleanName(calendar.name)
        doc.save()
    
    print("Done")
    
    return "response"


@frappe.whitelist()
def sync_calendar(data):
    #Check if called from client side (not necessary)
    if(isinstance(data,str)):
        data = json.loads(data)

    #Connect to CalDav Account
    client = caldav.DAVClient(url=data["url"], username=data["username"], password=data["password"])
    principal = client.principal()
    calendars = principal.calendars()

    #Look for the right calendar
    for calendar in calendars:
        if(str(calendar) == data["calendarurl"]):
            cal = calendar
    
    #Go through Events
    events = cal.events()

    nvalid = 0
    nsuccess = 0

    for event in events:
        nvalid = nvalid + 1
        vev = event.vobject_instance.vevent

        try:

            #Type conversions
            if(type(vev.dtstart.value) is datetime.date):
                vev.dtstart.value = datetime.datetime(year=vev.dtstart.value.year, month=vev.dtstart.value.month, day=vev.dtstart.value.day)
            if(type(vev.dtend.value) is datetime.date):
                vev.dtend.value = datetime.datetime(year=vev.dtend.value.year, month=vev.dtend.value.month, day=vev.dtend.value.day)

            print("Inserting " + vev.summary.value + " from " + str(vev.dtstart.value.date()))

            #Check if same day
            if(vev.dtstart.value.date() == vev.dtend.value.date()):
                doc = frappe.new_doc("Event")
                doc.subject = vev.summary.value
                doc.starts_on = vev.dtstart.value.strftime("%Y-%m-%d %H:%M:%S")
                if(hasattr(vev,"dtend")):
                    doc.ends_on = vev.dtend.value.strftime("%Y-%m-%d %H:%M:%S")
                    print(doc.ends_on)
                elif(hasattr(vev,"duration")):
                    doc.ends_on = (vev.dtstart.value + vev.duration.value).strftime("%Y-%m-%d %H:%M:%S")
                doc.event_type = "Public"
                doc.uid = vev.uid.value
                doc.caldav_calendar = data["caldavcalendar"]
                if(hasattr(vev,"last_modified")):
                    doc.last_modified = vev.last_modified.value.strftime("%Y-%m-%d %H:%M:%S")
                if(hasattr(vev,"created")):
                    doc.created_on = vev.created.value.strftime("%Y-%m-%d %H:%M:%S")
                
                doc.insert(
                    ignore_permissions=False, # ignore write permissions during insert
                    ignore_links=True, # ignore Link validation in the document
                    ignore_if_duplicate=True, # dont insert if DuplicateEntryError is thrown
                    ignore_mandatory=False # insert even if mandatory fields are not set
                )
                nsuccess = nsuccess + 1

            #Check if all day (starts midnight day 1 ends midnight day 2)

        except:
            vev.prettyPrint()
    
    print("Events total: " + str(nvalid) + " Synced: " + str(nsuccess))

    return "response"