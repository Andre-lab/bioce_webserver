
# Depoyment on murcof

1. Apache should be installed from webmin, one still needs to install mod_wsgi module:
```
sudo apt-get install libapache2-mod-wsgi-py3
```

2. Now __clone the BioCE webserver repo__ and register the app with apache and make a few folders:
```
git clone github.com/Andre-lab/bioce_webserver.git
mkdir logs
mkdir failedAnalyses
mkdir userData
```

3. __Install all Python packages__ to native python (It didn't work with Anaconda!):
```
pip install flask flask-mail flask-sqlalchemy flask-login flask-security flask-admin flask-migrate requests email_validator seaborn pystan pandas
```

4. __Compile vbi module__
```
(Make sure swig is installed) sudo apt-get install swig 
swig -python -c++ -o vbw_sc_wrap.cpp vbw_sc.i
g++ -c VBW_sc.cpp vbw_sc_wrap.cpp -shared -fpic -I/usr/include/python3.6 -fopenmp -O3 -lgsl -lgslcblas -lm -std=c++11
g++ -shared VBW_sc.o vbw_sc_wrap.o -o _vbwSC.so -fopenmp -lgsl -lgslcblas -lm -std=c++11
```

5. We want to serve our users through a __secure HTTPS connection__. This can be done from Webmin interface

6. __Edit config file for Apache__:
 
 ```
 vi /etc/apache2/sites-enabled/bioce.andrelab.org.conf 
 ```
 
 Copy and paste the following:
 
 ```

<VirtualHost *:443>

        <Directory /home/bioce/public_html/frontend>
            WSGIProcessGroup frontend
            WSGIApplicationGroup %{GLOBAL}
            Order deny,allow
            Allow from all
        </Directory>

        <Directory /home/bioce/public_html>
            WSGIProcessGroup frontend
            WSGIApplicationGroup %{GLOBAL}
            Order deny,allow
            Allow from all
        </Directory>

        # Static Directories
        Alias /static /home/bioce/public_html/frontend/static/
        <Location "/static">
                SetHandler None
        </Location>

</VirtualHost>
 ```
Make sure you actually go through this file and make sure everything makes sense
for __your__ app.
 
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





