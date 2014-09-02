anymeeting_connector
====================
Anymeeting is cheap/free, and, reporting-wise, you get what you pay for.  

This is an automated connector that will export all your webinar records and corresponding
views (both live and recorded) into convenient, easy-to-use CSV files.

SEPT. 2014 UPDATE:
Anymeeting has changed how their pages are rendered in JavaScript, which makes the old version of this obsolete.
This new version is a single file which uses both Selenium and Mechanize to scrape the AnyMeeting site.
Outputs remain the same: one file containing data about webinars and another with data about views.
Views are linked to webinars via the PIID, which can be used as a foreign key should you want to put your results in a database.

HOW TO:
-Make sure you've got the modules listed below installed
-Clone this repo somewhere
-Make sure get_webinars.py is executable (chmod +x get_webinars.py)
-Run get_webinars.py from the command line, with your anymeeting username and password as arguments. It should look like: (get_webinars.py example@email.com password).


Dependencies include:
-Mechanize
-BeautifulSoup 4
-Selenium

All of these can be installed via SetupTools (for example: easy_install mechanize)

Why Selenium AND Mechanize?  We need a browser that can render JS properly (mechanize can't).  However, it would by really slow to scrape everything out of Selenium, so instead we switch to something headless as faster for most of the heavy duty work.

Happy Scraping!