#!/usr/bin/env python

import datetime as dt
import time
import re
import csv
import sys
from HTMLParser import HTMLParser
from unicodedata import normalize

import mechanize
from bs4 import BeautifulSoup
from selenium import webdriver

def get_PIIDs(argv):
    browser=webdriver.Firefox()
    browser.get('https://www.anymeeting.com/AccountManager/AnyMeeting.aspx?')
    element=browser.find_element_by_id('aspnetForm')
    username=element.find_element_by_name("ctl00$cphPageContent$txtUserEmail")
    password=element.find_element_by_name("ctl00$cphPageContent$txtUserPassword")
    submit=browser.find_element_by_id('ctl00_cphPageContent_btnLogin_lbMain')
    username.send_keys(argv[0])
    password.send_keys(argv[1])
    submit.click()

    PIIDs=[]
    
    #give everything time to load
    time.sleep(60)

    for i in browser.find_elements_by_tag_name('a'):
        linktext=i.get_attribute('href')
        try:
            loc=linktext.find('PIID')
            if loc>0:
                PIIDs.append(linktext[loc+5:loc+19])
        except AttributeError:
            continue

    browser.quit()
    return(PIIDs)

#make this more robust
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

def format_name(name):
    parser=HTMLParser()
    unicode_name=parser.unescape(name)
    #this isn't foolproof yet, but it's getting there
    normalized_name=normalize('NFKD',name).encode('ASCII','ignore')
    normalized_name.replace(u'\xa0', u' ')
 #   output=unicode(str(unicode_name),'latin-1')
    return normalized_name

def csv_dict_writer(path, fieldnames, data):
    with open(path, "wb") as out_file:
        writer = csv.DictWriter(out_file, delimiter=',', fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            try:
                writer.writerow(row)
            except:
                print row
                continue

#only used for testing
def csv_dict_reader(path):
    results=[]
    f=open(path,'rb')
    readobject=csv.DictReader(f)
    for x in readobject:
        results.append(x)
    f.close()
    return results

def log_in_user(login):
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
    br.form['ctl00$cphPageContent$txtUserEmail']=login[0]
    br.form['ctl00$cphPageContent$txtUserPassword']=login[1]
    br.form['ctl00$cphPageContent$cbxRememberMe']=False
    br.submit()
    return(br)

def get_webinar_data(br,data):
    br.open('https://www.anymeeting.com/AccountManager/AnyMeeting.aspx?at=1')
    output=[]
    details_links=[]
    #Process each collected link to extract various IDs        
    for PIID in data:        
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
        print PIID+ ' entered'
    return(output)

def get_views(br,data,names_to_exclude=['Presenter','Anonymous'],domain_to_exclude='@globalgiving.org'):
    views=[]
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

                #try:
                name=format_name(name)
                #except UnicodeEncodeError :
#                    continue
                    
                email=col[1].string
                minutes_connected=col[2].string
                row_link=row.findAll('a')[0]['href']
                ip_a=row_link[row_link.index('ip_a=')+5:]
                record={'piid':i['piid'],'name':name,'email':email,'minutes_connected':minutes_connected,'ip_a':ip_a,'location':location}
                #ignore specified viewers
                if re.search(domain_to_exclude,email.lower()) or name in names_to_exclude:
                    continue
                else:
                    views.append(record)
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
                    record={'piid':i['piid'],'name':name,'email':email,'minutes_connected':minutes_connected,'view_date':view_date}
                    #ignore specified viewers
                    if re.search(domain_to_exclude,email.lower()) or name in names_to_exclude:
                        continue
                    else:
                        views.append(record)
                        print record['email']+' on '+record['view_date']+' processed'
    return views

if __name__=="__main__":
    credentials=sys.argv[1:]
    print 'starting up'
    PIID_list=get_PIIDs(credentials)
    browser=log_in_user(credentials)
    webinars=get_webinar_data(browser,PIID_list)
    webinar_views=get_views(browser,webinars)
    webinar_fieldnames=['title','start_date','piid','psrid','ip_presessid','ip_e']
    view_fieldnames=['piid','name','email','location','view_date','minutes_connected','ip_a']
    csv_dict_writer('webinars.csv',webinar_fieldnames, webinars)
    csv_dict_writer('views.csv',view_fieldnames, webinar_views)
    print 'success'

