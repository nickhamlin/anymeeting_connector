anymeeting_connector
====================
Anymeeting is cheap/free, and, reporting-wise, you get what you pay for.  

This is an automated connector that will export all your webinar records and corresponding
views (both live and recorded) into a MySQL database (easily modified for csv export as well).

Data is separated into two tables (webinar and webinar_views).  Run get_webinars.py first to populate the webinar table,
then run get_webinar_views.py to populate the webinar_views table.  You'll need to run both of them periodically on a cron
to keep your records up to date.

Currently, this connects to MySQL via a homemade connector (database3).  In the future it's easy to modify this to be more
extensible, I just haven't gotten there yet.

Dependencies include:
-Mechanize
-BeautifulSoup
-Getpass (optional, if you don't want to hardcode passwords.  This is currently commented out)