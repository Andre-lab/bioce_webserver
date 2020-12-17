
# Depoyment on bioce (vm on mozzarella)

1. Apache should be installed from webmin, one still needs to install mod_wsgi module:
```
sudo apt-get install apache2
sudo apt-get install python3-pip
sudo apt-get install libapache2-mod-wsgi-py3
sudo apt-get install supervisor
sudo apt-get install libgsl-dev
sudo apt-get install swig 
```

2. Now __clone the BioCE webserver repo__ and register the app with apache and make a few folders:
```
git clone github.com/Andre-lab/bioce_webserver.git
mkdir logs
mkdir failedAnalyses
mkdir userData
```

3. __Install all Python packages__ to native python (Need to change it to requirements file):
```
pip install flask flask-mail flask-sqlalchemy flask-login flask-security flask-admin flask-migrate requests email_validator seaborn pystan pandas freesas
```

4. __Compile vbi module__
```
swig -python -c++ -o vbw_sc_wrap.cpp vbw_sc.i
g++ -c VBW_sc.cpp vbw_sc_wrap.cpp -shared -fpic -I/usr/include/python3.8 -fopenmp -O3 -lgsl -lgslcblas -lm -std=c++11
g++ -shared VBW_sc.o vbw_sc_wrap.o -o _vbwSC.so -fopenmp -lgsl -lgslcblas -lm -std=c++11
```

5. We want to serve our users through a __secure HTTPS connection__. This can be done from Webmin interface

6. __Edit config file for Apache__:
 
 ```
 vi /etc/apache2/sites-enabled/0000-default.conf 
 ```
 
Remove what is in the file and copy and paste the following:
 
 ```
<VirtualHost *:80>
  
ServerAdmin admin@bioce.plantbio.lu.se
ServerName bioce.plantbio.lu.se
DocumentRoot /var/www/html/

#Redirect permanent / http://130.235.135.6

WSGIDaemonProcess frontend user=wojtek group=wojtek processes=1 threads=1
WSGIScriptAlias / /var/www/html/bioce_webserver/frontend/frontend.wsgi process-group=frontend application-group=%{GLOBAL}

<Directory /var/www/html/bioce_webserver/frontend>
WSGIProcessGroup frontend
WSGIApplicationGroup %{GLOBAL}
Require all granted
</Directory>

<Directory /var/www/html/bioce_webserver>
WSGIProcessGroup frontend
WSGIApplicationGroup %{GLOBAL}
Require all granted
</Directory>

#Static Directories
Alias /static /var/www/html/bioce_webserver/frontend/static/
<Location "/static">
SetHandler None
</Location>

</VirtualHost>
 ```
It seems that since our access point is running ssl certificate and the server is behind firewall it doesn't require additional SSL setup on `bioce`

7. __Customize `frontend/config_example.py`__ and rename it to `frontend/config.py`
    1. Generate a secret key for your app like [this](https://pythonadventures.wordpress.com/2015/01/01/flask-generate-a-secret-key/)
    2. Setup the username, email, password for the admin. You can then log in with
     these credentials and go to the Admin profile from the Profile page. Then you
     can edit all the tables of the database from online.
    3. Setup mail sending. You can use [AWS's SES service](http://docs.aws.amazon.com/ses/latest/DeveloperGuide/quick-start.html) if you have a domain name,
     (that's what I did for CorrMapper and for this demo). Alternatively you can use [Gmail](http://stackoverflow.com/questions/37058567/configure-flask-mail-to-use-gmail) also.
     You'll need to [allow](https://support.google.com/accounts/answer/6010255?hl=en) 
     less secure apps to use your account for this to work which might not be a great idea. You can also
     [create an app-key](http://www.wpbeginner.com/plugins/how-to-send-email-in-wordpress-using-the-gmail-smtp-server/).
      
8. If you'd like to use Alembic to migrate your database if you update it's schema, 
then read [this blog post](https://blog.miguelgrinberg.com/post/flask-migrate-alembic-database-migration-wrapper-for-flask) 
and the docs [here](https://blog.miguelgrinberg.com/post/flask-migrate-alembic-database-migration-wrapper-for-flask) and do:

```
./manage.py db init
./manage.py db migrate
./manage.py db upgrade
```

9. We are getting close. Let's __install SQLite__ and create the database for the app.
```
sudo apt-get install sqlite
sudo apt-get install python-tk
python db_create.py
```

10. __Install RabbitMQ__ and setup a user with it, add it to config.py
 
 ```
sudo apt-get install rabbitmq-server
sudo rabbitmqctl add_user bioce *********
sudo rabbitmqctl set_permissions -p / bioce ".*" ".*" ".*"
 ```
Change `config.py` to 

```
CELERY_BROKER_URL = 'amqp://bioce:*******@pbioce.andrelab.org:5672//'
```

Start the service with:
```
sudo rabbitmq-server
```
If you get an error saying it's already running, that's OK.
  
11. __Setup celery__

Celery would need to run as a daemon process in the background. For this we'll use
 the very powerful [supervisord package](http://supervisord.org/). It can do __much__
  more than this so definitely have a look at the docs.
 
 Once supervisor is installed from packages is it should be enough to copy config file: 
 ```
 sudo cp /home/wojtek/public_html/bioce_webserver/supervisor.conf /etc/supervisor/supervisord.conf
 ```
The remaining part about celery is deprecated but leaving it for the record in case one wants to run it from pip installable package
 
 [Here's](https://thomassileo.name/blog/2012/08/20/how-to-keep-celery-running-with-supervisor/) 
 a quick tutorial on how  to setup supervisor with Celery.
 
 Science Flask repo already has a `supervisord.conf file` that should work out of the
  box if you've followed everything till this point. 
  
  Let's start supervisord by typing `supervisord` in `science_flask` folder. 

When you try to start supervisord and get an error like this:
 ```
 Error: Another program is already listening on a port that one of our HTTP servers is configured to use.
 ```
follow [this trick](http://stackoverflow.com/questions/25121838/supervisor-on-debian-wheezy-another-program-is-already-listening-on-a-port-that)

You can restart celeryd process via the supervisorctl like this:
```
supervisorctl restart celeryd
```

12. You can check __Apache's logs__  or from __Webmin__ interface:
```
less -S /var/log/apache2/error.log
less -S /var/log/apache2/access.log
```

Celery and Science Flask also logs. These are in ~/bioce_webserver/logs. These are
very useful to check on the status of the app. 


13. __Restart server and enjoy!__ 
```
sudo systemctl restart apache2
```

You should be able to log in with the admin credentials you specified in `frontend/config.py`.
Go to the Profile page and then to the Admin panel (botton right corner). 



