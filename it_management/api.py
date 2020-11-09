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

def color_variant(hex_color, brightness_offset=50):
    """ takes a color like #87c95f and produces a lighter or darker variant """
    if len(hex_color) != 7:
        raise Exception("Passed %s into color_variant(), needs to be in #87c95f format." % hex_color)
    rgb_hex = [hex_color[x:x+2] for x in [1, 3, 5]]
    new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
    new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int] # make sure new values are between 0 and 255
    # hex() produces "0x88", we want just "88"
    return "#" + "".join([hex(i)[2:] for i in new_rgb_int])

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
    account = frappe.get_doc("CalDav Account", data["caldavaccount"])
    client = caldav.DAVClient(url=account.url, username=account.username, password=account.password)
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
            if(hasattr(vev,"dtend")):
                if(type(vev.dtend.value) is datetime.date):
                    vev.dtend.value = datetime.datetime(year=vev.dtend.value.year, month=vev.dtend.value.month, day=vev.dtend.value.day)

            #Insert log statement
            print("Inserting " + vev.summary.value + " from " + str(vev.dtstart.value.date()))
            
            #Berechne Dinge
            if(hasattr(vev,"dtstart") and hasattr(vev,"dtend")):
                timedelta = vev.dtend.value - vev.dtstart.value
                days = (vev.dtend.value.date() - vev.dtstart.value.date()).days
            elif(hasattr(vev,"dtstart") and hasattr(vev,"duration")):
                timedelta = vev.duration.value
                days = ((vev.dtstart.value + vev.duration.value).date() - vev.dtstart.value.date()).days

            #Default
            insertable = False
            doc = frappe.new_doc("Event")
            doc.subject = vev.summary.value
            doc.starts_on = vev.dtstart.value.strftime("%Y-%m-%d %H:%M:%S")
            doc.event_type = "Public"
            doc.uid = vev.uid.value
            doc.caldav_calendar = data["caldavcalendar"]
            if(hasattr(vev,"description")):
                doc.description = vev.description.value

            #Meta
            if(hasattr(vev,"transp")):
                if(vev.transp.value == "TRANSPARENT"):
                    doc.color = color_variant(data["color"])
                elif(vev.transp.value == "OPAQUE"):
                    doc.color = data["color"]
                else:
                    doc.color = data["color"]
            
            if(hasattr(vev,"status")):
                #print("Status: " + vev.status.value)
                pass

            if(hasattr(vev,"organizer")):
                #print("Organizer: " + vev.organizer.value)
                pass

            if(hasattr(vev,"attendee")):
                #vev.prettyPrint()
                pass

            if(hasattr(vev, "sequence")):
                #print("Sequence: " + vev.sequence.value)
                pass

            if(hasattr(vev,"location")):
                #print("Location: " + vev.location.value)
                pass

            if(hasattr(vev, "class")):
                pass

            #Case: has dtend, within a day
            if((hasattr(vev,"dtend") and days == 1)):
                doc.ends_on = vev.dtend.value.strftime("%Y-%m-%d %H:%M:%S")
                insertable = True
            #Case: has duration, within a day
            elif(hasattr(vev,"duration") and days == 1 ):
                doc.ends_on = (vev.dtstart.value + vev.duration.value).strftime("%Y-%m-%d %H:%M:%S")
                insertable = True
            #Case: Allday, one day
            elif((timedelta.seconds / 3600) == 1.0 and vev.dtstart.value.hour == 0 and vev.dtstart.value.minute == 0):
                doc.ends_on = ""
                doc.all_day = 1
                insertable = True
            #Case: Allday, more than one day
            #elif((timedelta.seconds / 3600) == int(timedelta.seconds / 3600)):
                #doc.
            #Case: has dtend, not within a day
            #elif((hasattr(vev,"dtend") and days > 1)):
                #doc.ends_on = vev.dtstart.value.date().strftime("%Y-%m-%d %H:%M:%S")
                #for i in days - 2:
                #    insert_a_whole_day(vev)
                #insert_from_midnight_to_hour(vev)
            #Case: Not within a day, has duration
            #elif((hasattr(vev,"duration") and days > 1)):
                #doc.ends_on = vev.dtstart.value.date().strftime("%Y-%m-%d %H:%M:%S")
                #for i in days - 2:
                #    insert_a_whole_day(vev)
                #insert_from_midnight_to_hour(vev)

            if(hasattr(vev,"rrule")):
                dates = list(vev.getrruleset()) #this is potentially infinite
                for date in dates:
            
            #!--------- EXPERIMENTAL RULEMAPPING ------------------
            #Repeating Events
            #if(hasattr(vev,"rrule")):
                #insertable = False
                #print(type(vev.rrule))
                #print(type(vev.rrule.value))
                #print(dir(vev.rrule.value))
                #print(vev.rrule.value)

            #if(hasattr(vev,"exdate")):
                #insertable = False
                #print(type(vev.exdate))
                #print(type(vev.exdate.value))

            #Note: Wann kann ich mappen? https://www.kanzaki.com/docs/ical/recur.html
            #Ausschlusskriterium:
            # EXDATE
            # COUNT mod 7 != 0
            # INTERVAL
            # ...
            #Positivkriterien:
            #FREQ (WEEKLY) and (COUNT mod 7 == 0 or UNTIL) and optionally BYDAY
            #FREQ (DAILY) ...
            #!------------------------------------------------------

            #If insertable insert
            if(insertable):
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
            else:
                vev.prettyPrint()


        except Exception as ex:
            print(str(ex))
            vev.prettyPrint()

            #frappe.sendmail...
    
    print("Events total: " + str(nvalid) + " Synced: " + str(nsuccess))

    return "response"