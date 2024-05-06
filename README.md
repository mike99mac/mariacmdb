# mariacmdb
A simple Configuration Management Database (CMDB) that uses mariadb to store the data

# Overview
It has the following files:
- mariacmdb.py   Line command that maintains the database
- restapi.py     RESTful API that works through a Web server
- serverinfo     A small bash script that returns data from managed servers

Key-based authentication, or *Passwordless* access is needed from the mariacmdb server to all systems that will be managed.

Using mariadb, one database (``cmdb``) is created, and one table (``servers``) in that database.

Following is a block diagram.
![](mariacmdb.jpg)

# Installation
TODO - finish

To install MariaDB:
```
sudo apt update
sudo apt install mariadb-server libmariadb3 libmariadb-dev
pip3 install mariadb
pip install mysqlx-connector-python
```
Answer many security questions:
```
sudo mysql_secure_installation
... answer many questions ...
  MariaDB root password: pi
```

# Usage
Using mariacmdb was designed to be very easy to use.

## Line command
Following is the help output for the line command:

```
$ mariacmdb.py -h
usage: mariacmdb.py [-h] [-v] [-c] [--column COLUMN] [--value VALUE] [--pattern PATTERN] [--server SERVER] command

mariacmdb - A simple Configuration Management Database

positional arguments:
  command            Can be 'add', 'describe', 'initialize', 'query', or 'remove'

options:
  -h, --help         show this help message and exit
  -v, --verbose      increase output verbosity
  -c, --copyscript   copy script 'serverinfo' to target server before add
  --column COLUMN    column name to search
  --value VALUE      value to search for in previous column
  --pattern PATTERN  pattern for query all columns
  --server SERVER    server to add or remove
```

The command ``mariacmdb.py add --server <host-name>`` will add a record
## RESTful API

```
curl "http://model1500/restapi.py?cpus=4&mem_gb=4"

Here is a description of the table:
```
$ mariacmdb.py describe
Table servers:
Field,Type,Null,Key,Default,Extra
---------------------------------
host_name,varchar(255),NO,PRI,None,
ip_addr,varchar(20),YES,,None,
cpus,int(11),YES,,None,
mem_gb,int(11),YES,,None,
arch,varchar(50),YES,,None,
os,varchar(100),YES,,None,
os_ver,varchar(50),YES,,None,
kernel,varchar(100),YES,,None,
rootfs,int(11),YES,,None,
created_at,timestamp,NO,,current_timestamp(),
```
