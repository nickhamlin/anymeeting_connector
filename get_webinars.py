import mechanize
#import getpass
from BeautifulSoup import BeautifulSoup
import database3 as db
import datetime as dt
import re

###Enter Credentials
#company_login=getpass.getpass(prompt='Company Login:')
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
#br.set_handle_gzip(True)
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
br.open('https://www.anymeeting.com/AccountManager/AnyMeeting.aspx?at=1')
#br.open('https://www.anymeeting.com/AccountManager/AnyMeeting.aspx?at=2')

#initialize lists for results
output=[] #Will return list of dicts for csv export if you don't want to use MySQL
details_links=[]

# Collect links from page 1
def get_links():
    for i in br.links():
        if i.text=='View Meeting Detail':
            details_links.append(i)

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

#Collect links from different pages (enter page numbers in list)
pages=[2,1]
for i in pages:
    br.select_form("aspnetForm")
    br.set_all_readonly(False)
    br.form["__EVENTTARGET"]='ctl00$cphPageContent$tabsMain$tpnlPast$gvPastInvitations'
    br.form["__EVENTARGUMENT"]='Page$%s'%i
    br.find_control('ctl00$cphPageContent$btnOpenStartMeetingModal').disabled=True
    br.find_control('ctl00$cphPageContent$btnScheduleMeeting').disabled=True
    br.submit()
    get_links()
    print 'gathered links from page '+str(i)

#Process each collected link to extract various IDs        
for link in details_links:        
    PIID=link.url[link.url.index('PIID=')+5:link.url.index('&at')]
    corrected_url='https://www.anymeeting.com/AccountManager/RegistrationDetails.aspx?PIID=%s&at=6'%PIID
    br.open(corrected_url)
    try:
        psrid_link=[i for i in br.links(url_regex='http://www.anymeeting.com/globalgivingUS/')][0]
        psrid=psrid_link.url[psrid_link.url.index('US')+3:]
    except:
        psrid=""
    attend_link=[i for i in br.links(text_regex='View Attendance Report')][0]
    ip_e=attend_link.url[attend_link.url.index('?ip_e=')+6:attend_link.url.index('&')]
    ip_presessid=attend_link.url[attend_link.url.index('presessid=')+10:]
    corrected_url2='https://www.anymeeting.com/AccountManager/RegistrationDetails.aspx?PIID=%s&at=0'%PIID
    br.open(corrected_url2)
    html=br.response().read()
    soup=BeautifulSoup(html)
    title_text=soup.find('span',{'id':'ctl00_cphPageTitle_lblMeetingTitleTopPage'}).text
    title=title_text[title_text.index('"')+1:len(title_text)-1]
    if re.search(r'\btest',title.lower()):
        print 'skipping '+title+' '+PIID
        continue
    date=soup.find('span',{'id':'ctl00_cphPageContent_tcMain_tpMeetingOptions_dvInvitation_Label2'}).text
    #pad dates
    format_date(date)
    #convert to sql format
    converted_date=dt.datetime.strptime(date,'%m/%d/%Y %I:%M %p').strftime('%Y-%m-%d %H:%M:00')
    record={'piid':PIID,'psrid':psrid,'ip_e':ip_e,'ip_presessid':ip_presessid,'title':title,'start_date':converted_date}
    output.append(record)
    #insert into MySQL database
    insert_query=("""insert ignore into ggsandbox.webinar (title,start_date,piid,psrid,ip_presessid,ip_e)
            VALUES("%s","%s","%s","%s","%s","%s")"""
            % (record['title'],record['start_date'],record['piid'],record['psrid'],record['ip_presessid'],record['ip_e']))
    msg=db.mysqldict(insert_query,d='ggsandbox')
    print PIID+ ' entered'

print 'success'


