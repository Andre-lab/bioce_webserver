
# Depoyment on murcof

1. Now __clone the BioCE webserver repo__ and register the app with apache and make a few folders:
```
git clone github.com/Andre-lab/bioce_webserver.git
mkdir logs
mkdir failedAnalyses
mkdir userData
```

2. __Install all Python packages__ that we need for Science Flask:
```
cd bioce_webserver
conda env create -n bioce_web -f requirments.yml
```

3. We want to serve our users through a __secure HTTPS connection__. This can be done from Webmin interface

4. __Edit config file for Apache__:
 
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
 
10. __Customize `frontend/config_example.py`__ and rename it to `frontend/config.py`
    1. Generate a secret key for your app like [this](https://pythonadventures.wordpress.com/2015/01/01/flask-generate-a-secret-key/)
    2. Setup the username, email, password for the admin. You can then log in with
     these credentials and go to the Admin profile from the Profile page. Then you
     can edit all the tables of the database from online.
    3. Setup mail sending. You can use [AWS's SES service](http://docs.aws.amazon.com/ses/latest/DeveloperGuide/quick-start.html) if you have a domain name,
     (that's what I did for CorrMapper and for this demo). Alternatively you can use [Gmail](http://stackoverflow.com/questions/37058567/configure-flask-mail-to-use-gmail) also.
     You'll need to [allow](https://support.google.com/accounts/answer/6010255?hl=en) 
     less secure apps to use your account for this to work which might not be a great idea. You can also
     [create an app-key](http://www.wpbeginner.com/plugins/how-to-send-email-in-wordpress-using-the-gmail-smtp-server/).
      
11. If you'd like to use Alembic to migrate your database if you update it's schema, 
then read [this blog post](https://blog.miguelgrinberg.com/post/flask-migrate-alembic-database-migration-wrapper-for-flask) 
and the docs [here](https://blog.miguelgrinberg.com/post/flask-migrate-alembic-database-migration-wrapper-for-flask) and do:

```
./manage.py db init
./manage.py db migrate
./manage.py db upgrade
```

12. We are getting close. Let's __install SQLite__ and create the database for the app.
```
sudo apt-get install sqlite
sudo apt-get install python-tk
python db_create.py
```

13. __Install RabbitMQ__ and setup a user with it, add it to config.py
 
 ```
sudo apt-get install rabbitmq-server
sudo rabbitmqctl add_user <username> <password>
sudo rabbitmqctl set_permissions -p / <username> ".*" ".*" ".*"
 ```
Change `config.py` to 

```
CELERY_BROKER_URL = 'amqp://<username>:<password>@public_IPv4_address_for_your_EC2:5672//'
```

Start the service with:
```
sudo rabbitmq-server
```
If you get an error saying it's already running, that's OK.
  
14. __Update security group of your EC2 instance__ to add inbound traffic for HTTP, HTTPS and RabbitMQ:
    - go to `Security Groups` and edit the `Inbound rules` of the security group
    of your instance.
    - add the following:
        - SSH TCP 22 0.0.0.0/0
        - HTTP TCP 80 0.0.0.0/0
        - HTTPS TCP 443 0.0.0.0/0
        - Custom TCP Rule TCP 5672 0.0.0.0/0
        - Custom UDP Rule UDP 5672 0.0.0.0/0

15. __Setup celery__

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

16. You can check __Apache's logs__ like this:
```
less -S /var/log/apache2/error.log
less -S /var/log/apache2/access.log
```

Celery and Science Flask also logs. These are in ~/science_flask/logs. These are
very useful to check on the status of the app. 


17. __Restart server and enjoy!__ 
```
sudo systemctl restart apache2
```

You should be able to log in with the admin credentials you specified in `frontend/config.py`.
Go to the Profile page and then to the Admin panel (botton right corner). 





