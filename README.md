# mariacmdb
This repository contains Python and bash code that form a simple Configuration Management Database (CMDB). It uses the *mariadb* relational database to store the data.

# Overview
There are four source files:
- ``mariacmdb.py``&nbsp;&nbsp;&nbsp;&nbsp; Line command that maintains the database
- ``restapi.py``&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; RESTful API interfaced through Apache 
- ``finder.py``&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; GUI search script with a browser interface
- ``serverinfo``&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Bash script that returns data from managed servers

Key-based authentication, or *Passwordless* SSH access is needed for one user from the mariacmdb server to all systems that will be managed. 
``mariacmdb.py`` commands must be run by that user.

Using mariadb, one database named ``cmdb`` is created, and one table named ``servers`` is created in that database.

Following is a block diagram.
![](mariacmdb.jpg) 

mariacmdb block diagram

# Installation
These steps set up a virtual environment under ``/srv/venv``. This is crucial to the code functioning.

To install mariacmdb, perform the following steps.

- Login as a non-root user with sudo privileges. Add the group which will be running apache to that user.  

```
sudo usermod -aG apache mikemac
su - mikemac
id
uid=1000(mikemac) gid=1000(mikemac) groups=1000(mikemac),48(apache)
```

- Update your system.

  - For Debian based:
    ```
    sudo apt update 
    ```

  - For RHEL based:
    ```
    sudo dnf update 
    ```

- Install co-requisite packages.

  - For Debian based:
    ```
    sudo apt install cifs-utils curl gcc git  make mlocate net-tools pandoc python3 python3-dev python3-pip 
    ```

  - For RHEL based:
    ```
    sudo dnf install bzip2-devel cifs-utils curl gcc git libffi-devel make mlocate net-tools openssl-devel pandoc python3 python3-devel python3-pip vim wget zlib-devel
    ```

- Install Apache.

  - For Debian based:
    ```
    sudo apt install apache2
    ```

  - For RHEL based:
    ```
    sudo dnf install httpd
    ```

- Set Apache to start at boot time: 

  - For Debian based:
    ```
    sudo systemctl enable apache2
    ```

  - For RHEL based:

    ```
    sudo systemctl enable httpd
    ```

- Install Mariadb, Apache and some co-requisite packages:

  - For Debian based:

    ```
    sudo apt install mariadb-server libmariadb3 libmariadb-dev 
    ```

  - For RHEL based:

    ```
    sudo dnf install MariaDB-server
    ```

- Start mariadb.

```
sudo systemctl start mariadb
```

- Set the mariadb root password. Enter the MariaDB command-line tool:

```
sudo mariadb
```

- From there, change the root password: 

```
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
```

- Change to the ``/srv`` directory:

```
cd /srv
```

- Create a virtual environment under ``/srv``:

```
sudo python3 -m venv venv
```

- Change the group to that which will be running Apache, and add group write permission to ``/`` and ``/srv``

```
sudo chgrp apache / 
sudo chmod g+w / 
sudo chgrp apache /srv
sudo chmod g+w /srv
```

- Recursively change the group of the new virtual environment:

```
sudo chgrp -R apache venv
sudo chmod -R g+w venv
```

- Activate the environment:

```
. venv/bin/activate  
```

- Upgrade pip:

```
sudo /srv/venv/bin/python3 -m pip install --upgrade pip
```

- Install wheel:

```
sudo pip install wheel
```

- Install the Mariadb Python connector:

```
pip3 install mysql-connector-python
```

- Issue the following command and answer the many security questions:
```
sudo mysql_secure_installation
```

- Clone this repo to your home directory:

```
git clone https://github.com/mike99mac/mariacmdb
```

- Copy the line command to ``/usr/local/sbin``


```
sudo cp $HOME/mariacmdb/usr/local/sbin/mariacmdb.py /usr/local/sbin
```

- Copy the CGI files to a new directory ``/srv/www/maraicmdb/``. 

```
sudo cp -a ~/mariacmdb/srv/www/mariacmdb /srv/www
```

- Copy the ``serverinfo`` script to your home directory.  When the ``-C`` flag is included on ``mariacmdb.py add`` command, it will first copy the script to the managed server before running it remotely.

```
cp ~/mariacmdb/usr/local/sbin/serverinfo $HOME 
```

- Following is the Apache configuration file used in this document:

```
# cat /etc/apache2/sites-available/mariacmdb.conf
```

```
#
# Mariacmdb configuration file
#
User pi
Group pi
<VirtualHost *:80>
  ServerAdmin mmacisaac@example.com 
  DocumentRoot /srv/www/mariacmdb
  ServerName model1500
  LogLevel error
  LoadModule cgi_module /usr/lib/apache2/modules/mod_cgi.so

  <Directory "/srv/www/html">
    Options Indexes FollowSymLinks
    AllowOverride all
    Require all granted
  </Directory>

  <Directory /srv/www/mariacmdb>
    Options +ExecCGI
    DirectoryIndex restapi.py
    Require all granted
  </Directory>
  AddHandler cgi-script .py

  ErrorLog ${APACHE_LOG_DIR}/error.log
  CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```

- Enable the site

```
sudo a2ensite mariacmdb.conf
```

- Following is the systemd ``service`` file. 

```
cat /etc/systemd/system/apache2.service
```

```
[Unit]
Description=The Apache HTTP Server
After=network.target remote-fs.target nss-lookup.target
Documentation=https://httpd.apache.org/docs/2.4/

[Service]
Type=forking
Environment=APACHE_STARTED_BY_SYSTEMD=true
ExecStartPre=/usr/local/sbin/mklogdir
ExecStart=/usr/sbin/apachectl start
ExecStop=/usr/sbin/apachectl graceful-stop
ExecReload=/usr/sbin/apachectl graceful
KillMode=mixed
PrivateTmp=true
Restart=on-abort

[Install]
WantedBy=multi-user.target
```

- Set Apache to start at boot time:

```
sudo systemctl enable apache2
```

- Start Apache now:

```
sudo systemctl start apache2
```

# Usage
This mariacmdb solution was designed to be very easy to use.

The following sections describe the line command and the RESTful API.

## The mariacmdb.py line command
One of the following *subcommands* must be supplied to the line command:

- ``add       `` Add a server to be managed - if it already exists, it will be updated.  
- ``describe  `` Show the metadata of the ``servers`` table.
- ``init      `` Create the ``servers`` table. 
- ``query     `` Show the specified rows of the ``servers`` table.
- ``remove    `` Remove a managed server.
- ``update    `` Update all rows in table.

Following is the help output for ``mariacmdb.py``:

```
mariacmdb.py -h
usage: mariacmdb.py [-h] [-v] [-C] [-c COLUMN] [-p PATTERN] [-s SERVER] subcommand

mariacmdb - A simple Configuration Management Database

positional arguments:
  subcommand            Can be 'add', 'describe', 'init', 'query', 'remove' or 'update'

options:
  -h, --help            show this help message and exit
  -v, --verbose         increase output verbosity
  -C, --copyscript      copy script 'serverinfo' to target server before add
  -c COLUMN, --column COLUMN
                        column name to search
  -p PATTERN, --pattern PATTERN
                        pattern to search for
  -s SERVER, --server SERVER
                        server to add or remove
```

- Use the ``init`` subcommand to create the ``servers`` table:

``` 
$ mariacmdb.py init
Created database 'servers'
```

- Use the ``describe`` subcommand to list the attributes of the ``servers`` table: 

```
mariacmdb.py describe 
Table servers:
Field,Type,Null,Key,Default,Extra
---------------------------------
host_name,varchar(255),NO,PRI,None,
ip_addr,varchar(20),YES,,None,
cpus,int(11),YES,,None,
mem_gb,int(11),YES,,None,
arch,varchar(50),YES,,None,
arch_com,varchar(50),YES,,None,
os,varchar(100),YES,,None,
os_ver,varchar(50),YES,,None,
kernel,varchar(100),YES,,None,
rootfs,int(11),YES,,None,
app,varchar(50),YES,,None,
grp,varchar(50),YES,,None,
owner,varchar(50),YES,,None,
last_ping,timestamp,NO,,current_timestamp(),
created_at,timestamp,NO,,current_timestamp(),
```

- Use the ``add`` subcommand to insert rows into the database.  

The mariacmdb server must be able to **``ssh``** to all servers using key-based authentication.  Following is an example of adding four severs to be managed:
 
```
mariacmdb.py add --server model800
Added or updated server model800

mariacmdb.py add --server model1000
Added or updated server model1000

mariacmdb.py add --server model1500
Added or updated server model1500

mariacmdb.py add --server model2000
Added or updated server model12000
```

- Use the ``query`` subcommand to show all rows in the table:

```
mariacmdb.py query 
model1000,192.168.12.233,4,4,aarch64,Linux,Debian GNU/Linux 12 (bookworm),6.6.28+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.6.28-1+rpt1 (2024-04-22),29,2024-05-06 14:01:22
TODO: get output with new data structure
```

- Use the ``update`` subcommand to update all rows in the ``servers`` table.  There must be the ability to use key-based authentication to ``ssh`` to all managed servers. 

```
mariacmdb.py update 
__main__    : INFO     replace_row(): replaced row for server model1000
__main__    : INFO     replace_row(): replaced row for server model1500
__main__    : INFO     replace_row(): replaced row for server model2000
__main__    : INFO     replace_row(): replaced row for server model800
__main__    : INFO     update_cmdb() successfully updated table 'servers'
```
 
## RESTful API

Following is an example of using the RESTful API to search for servers that have 4 CPUs and 4GB of memory.  Three of the four servers do.

```
curl "http://model1500/restapi.py?cpus=4&mem_gb=4"
<html><head>
</head><body>
<h1>This is the mariacmdb RESTful API!</h1>
<pre>
model1000,192.168.12.233,4,4,aarch64,Linux,Debian GNU/Linux 12 (bookworm),6.6.28+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.6.28-1+rpt1 (2024-04-22),29,2024-05-06 14:01:22
model1500,192.168.12.239,4,4,aarch64,Linux,Ubuntu 22.04.4 LTS,5.15.0-1053-raspi #56-Ubuntu SMP PREEMPT Mon Apr 15 18:50:10 UTC 2024,24,2024-05-06 14:02:01
model800,192.168.12.176,4,4,aarch64,Linux,Ubuntu 22.04.4 LTS,5.15.0-1053-raspi #56-Ubuntu SMP PREEMPT Mon Apr 15 18:50:10 UTC 2024,23,2024-05-06 14:01:04
</pre>
</body></html>
```

