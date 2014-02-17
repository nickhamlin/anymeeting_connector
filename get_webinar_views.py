import mechanize
#import getpass
from BeautifulSoup import BeautifulSoup
import database3 as db
import datetime as dt
import re
from HTMLParser import HTMLParser

###Enter Credentials - turn on if you don't want to hard code
#user_name=getpass.getpass(prompt='Username:')
#pwd=getpass.getpass(prompt='Password:')

user_name='<USER>'
pwd='<PASS>'

#create browser instance
cj=mechanize.CookieJar()
br=mechanize.Browser()
br.set_cookiejar(cj)
# Add headers to trick website into thinking this is a real browser
br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
# Browser options
br.set_handle_equiv(True)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)

# Follows refresh 0 but not hangs on refresh > 0
br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

# The site we will navigate into, handling its session
page=br.open('https://www.anymeeting.com/AccountManager/login.aspx')

print br.title()
cj.clear_session_cookies()
# Log in, then redirect to main page with Recording tab active
br.select_form("aspnetForm")
br.form['ctl00$cphPageContent$txtUserEmail']=user_name
br.form['ctl00$cphPageContent$txtUserPassword']=pwd
br.form['ctl00$cphPageContent$cbxRememberMe']=False
br.submit()

#download webinar records - set date according to how much you want to refresh
query="""select * from ggsandbox.webinar where year(start_date)=2014"""
data,msg=db.mysqldict(query,d='ggsandbox')

#Define data munging functions to put Anymeeting Data in convenient SQL format
def format_date(date):
    #pad month
    if date[1]=='/':
        date='0'+date
    #pad day
    if date[2]=='/' and date[4]=='/':
        date=date[:3]+'0'+date[3:]
    #pad minute
    if date[12]==':':
        date=date[:10]+' 0'+date[11:]
    return date

def format_name(name):
    parser=HTMLParser()
    unicode_name=parser.unescape(name)
    output=unicode(str(unicode_name),'latin-1')
    return output

#Define list of names to skip when importing    
names_to_exclude=['Presenter','Anonymous']

#Main Loop
for i in data:
    #start with live views
    url_for_live_views='https://www.anymeeting.com/AccountManager/Session/SessionAttendance.aspx?ip_e=%s&ip_presessid=%s'%(i['ip_e'],i['ip_presessid'])
    br.open(url_for_live_views)
    html=br.response().read()
    soup=BeautifulSoup(html)
    table=soup.find("table", {'id':'ctl00_cphPageContent_gvAttendees'})
    if table:
        #parse each live viewer record
        for row in table.findAll('tr')[1:]:
            col=row.findAll('td')
            name_location=col[0].string
            from_position=name_location.find('from')
            if from_position>0:
                name=name_location[:from_position].rstrip()
                location=name_location[from_position+5:].rstrip()
            else:
                name=name_location.rstrip()
                location=""
            name=format_name(name)
            email=col[1].string
            minutes_connected=col[2].string
            row_link=row.findAll('a')[0]['href']
            ip_a=row_link[row_link.index('ip_a=')+5:]
            record={'webinar_id':i['id'],'name':name,'email':email,'minutes_connected':minutes_connected,'ip_a':ip_a,'location':location} #leaving this in here in case we want to dump later
            #ignore GG viewers
            if re.search('@globalgiving.org',email.lower()) or name in names_to_exclude:
                continue
            else:
                uauser_query="""select if(count(a.uauserid)=0,"None",a.uauserid) as uauserid
                                from (select uauserid as uauserid
                                from ggonline.uauser where email='%s') a """ %email
                uauser_result,msg=db.mysqldict(uauser_query,d='ggonline')
                if uauser_result[0]['uauserid']!='None':
                    uauserid=uauser_result[0]['uauserid']
                else: 
                    uauserid='Null'
                insert_query=("""insert ignore into ggsandbox.webinar_views (webinar_id,name,email,uauserid,type,view_date,location,minutes_connected,ip_a)
                VALUES(%s,"%s","%s",%s,"live","%s","%s",%s,"%s")"""
                % (record['webinar_id'],record['name'],record['email'],uauserid,i['start_date'],record['location'],record['minutes_connected'],record['ip_a']))
                msg=db.mysqldict(insert_query,d='ggsandbox')
                print record['ip_a']+' processed'
    #Now get recording views
    if i['psrid']:
        url_for_recording_views='https://www.anymeeting.com/AccountManager/Recording/RecordingViewers.aspx?c_psrid=%s'%i['psrid']
        br.open(url_for_recording_views)
        html2=br.response().read()
        soup2=BeautifulSoup(html2)
        table2=soup2.find("table", {'id':'ctl00_cphPageContent_gvViewers'})
        if table2:
            for row in table2.findAll('tr')[1:]:
                col=row.findAll('td')
                name=col[0].string
                name=format_name(name)
                email=col[1].string
                view_date=format_date(col[2].string)
                view_date=dt.datetime.strptime(view_date,'%m/%d/%Y %I:%M:%S %p').strftime('%Y-%m-%d %H:%M:%S')
                minutes_connected=col[4].span.string
                record={'webinar_id':i['id'],'name':name,'email':email,'minutes_connected':minutes_connected,'view_date':view_date} #leaving this in here in case we want to dump later
                #ignore GG viewers - YMMV
                if re.search('@globalgiving.org',email.lower()) or name in names_to_exclude:
                    continue
                else:
                    uauser_query="""select if(count(a.uauserid)=0,"None",a.uauserid) as uauserid
                                    from (select uauserid as uauserid
                                    from ggonline.uauser where email='%s') a """ %email
                    uauser_result,msg=db.mysqldict(uauser_query,d='ggonline')
                    if uauser_result[0]['uauserid']!='None':
                        uauserid=uauser_result[0]['uauserid']
                    else: 
                        uauserid='Null'
                    insert_query=("""insert ignore into ggsandbox.webinar_views (webinar_id,name,email,uauserid,type,view_date,location,minutes_connected,ip_a)
                    VALUES(%s,"%s","%s",%s,"recording","%s","",%s,"")"""
                    % (record['webinar_id'],record['name'],record['email'],uauserid,record['view_date'],record['minutes_connected']))
                    msg=db.mysqldict(insert_query,d='ggsandbox')
                    print record['email']+' on '+record['view_date']+' processed'
    

#Viewer details URL, not really needed now, but saving the variable anyway
#https://www.anymeeting.com/AccountManager/Session/SessionAttendanceDetails.aspx?ip_e=EB50DE8685&ip_presessid=E954D884894F3A&ip_a=EE52DE82874838



