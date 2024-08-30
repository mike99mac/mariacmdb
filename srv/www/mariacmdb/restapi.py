#!/srv/venv/bin/python3
"""
restapi.py - the mariacmdb RESTful API - accesses the table 'servers' in the mariadb database 'cmdb'.
Format: http://<hostname>/restapi.py?<operation>&param1&param2 ...

Note the above "shebang" - expects to be run from virtual environment /srv/venv/

Operation   Return                            Parameters
---------   ------                            ----------
- count     Number of servers                 <col>=<value>&...
- hostname  Host names of servers             <col>=<value>&...
- ping      Servers pinged out of total       <col>=<value>&...
- query     All server data                   <col>=<value>&...
- update    Update a server's app/grp/owner   hostname&app&grp&owner

Examples: 
http://model1500/restapi.py?ping                  ping all servers
http://model1500/restapi.py?count&cpus=4&mem_gb=4 number of servers with 4 CPUs and 4 GB of memory
http://model1500/restapi.py?hostname&cpus<4       host names of servers with less than 4 CPUs
http://model1500/restapi.py?update&model1000&myApp&myGroup&myOwner
http://model1500/restapi.py?count 
{ "num_servers": 4 }

http://model1500/restapi.py?ping ...
{ "up_servers": 3, "num_servers": 4 }

http://model1500/restapi.py?hostname ...
[ "model1000", "model1500", "model2000", "model800" ]
"""
import base64
import json
import logging
import mariadb
import os
import re
import subprocess
from urllib.parse import urlparse, parse_qs

class MariacmdbAPI():
  def __init__(self):
    self.conn = None 
    self.cursor = None 
    self.DBuser = "root"                   # default database user
    self.DBpw = "pi"                       # default database password
    self.DBhost = "127.0.0.1"              # default database host
    self.DBname = "cmdb"        
    self.script_dir = "/home/pi"
    self.log_level = "debug"
    self.load_config_file()
    logging.basicConfig(filename='/home/pi/restapi.log',
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=self.log_level)
    self.log = logging.getLogger(__name__)
    # self.log.setLevel(logging.DEBUG)
    print("Content-Type: text/html")       # print MIME type
    print()                                # required empty line

  def load_config_file(self):
    """
    read the JSON config file /etc/mariacmdb.conf
    """
    try:
      conf_file = open("/etc/mariacmdb.conf", 'r')
    except Exception as e:
      self.log.error("load_config_file(): could not open configuration file /etc/mariacmdb.conf - using defaults")
      return
    confJSON = json.loads(conf_file.read())
    self.DBuser = confJSON['DBuser']
    self.DBpw = confJSON['DBpw']
    self.DBhost = confJSON['DBhost']
    self.DBname = confJSON['DBname']
    self.script_dir = confJSON['homeDir']  
    self.log_level = confJSON['logLevel']  

  def print_env(self):
    """
    Show all environment variables with the 'env' command
    """
    proc = subprocess.run("env", shell=True, capture_output=True, text=True)
    rc = proc.returncode
    env_vars = []
    env_vars = proc.stdout
    print("<pre>")
    for line in env_vars.split("\n"):
      print(str(line))
    print("</pre>")
    print("")

  def connect_to_cmdb(self):
    """
    Connect to mariadb, use datase cmdb and establish a cursor
    """
    try:
      self.conn = mariadb.connect(user=self.DBuser, password=self.DBpw, host=self.DBhost, database=self.DBname)
      self.cursor = self.conn.cursor()       # open cursor
    except mariadb.Error as e:
      self.log.error(f"initialize(): Exception creating database: {e}")
      self.log.info("Run 'mariacmdb.py init'?")
      exit(3)


  def run_sql_query(self, cmd: str) -> str:
    """
    run the SQL command passed in
    """
    self.log.info(f"MariacmdbAPI.run_sql_query(): cmd = {cmd}")
    self.connect_to_cmdb()                 # connect to DB
    try:   
      self.cursor.execute(f"use {self.DBname}")
    except mariadb.Error as e:
      print(f"ERROR changing database to {self.DBname}: {e}")
      print("</body></html>")
      self.conn.close()                    # cannot contiue
      exit(1)
    rows = "" 
    output = ""
    self.log.info(f"MariacmdbAPI.run_sql_query(): running cmd: {cmd}") 
    try:   
      self.cursor.execute(cmd)             # query the cmdb
      rows = self.cursor.fetchall()
      rows = str(rows)                     # convert to string
      rows = rows.replace("(", "").replace(",)", "").replace("'", '"') # clean up SQL fluff
      rows = rows.replace("[", "").replace("]", "")
      self.log.info(f"MariacmdbAPI.run_sql_query(): rows = {rows} type(rows) = {type(rows)}") 
      if rows == []:                       # no match
        self.log.info(f"MariacmdbAPI.run_sql_query(): no matching rows") 
      else:  
        output = rows
    except mariadb.Error as e:
      self.log.error(f"MariacmdbAPI.run_sql_query(): ERROR! e: {e}")  
    return output  

  def close_conn(self):
    """
    Close the SQL cursor, then the connection 
    """
    self.cursor.close()
    self.conn.close()

  def parse_query_string(self) -> tuple[str, str]:
    """
    Get the env var QUERY_STRING and return operation and remaining parameters 
    """
    proc = subprocess.run("echo $QUERY_STRING", shell=True, capture_output=True, text=True)
    rc = proc.returncode
    if rc != 0:
      self.log.error(f"MariacmdbAPI.parse_query_string(): subprocess.run('echo $QUERY_STRING' returned {rc}")
      return 1
    query_str = proc.stdout.strip('\n')    # get value removing newline
    self.log.debug(f"MariacmdbAPI.parse_query_string(): query_str: {query_str}")
    query_parms = query_str.split('&')
    operation = query_parms[0]             # get operation
    query_parms = query_parms[1:]          # chop off operation
    return operation, query_parms

  def ping_servers(self, where_clause: str) -> str:
    """
    ping specified servers and return how many servers ping out of how many found 
    """
    sql_cmd = f"SELECT host_name FROM servers {where_clause}"
    sql_out = self.run_sql_query(sql_cmd)    # list of server host names
    self.close_conn()
    self.log.info(f"MariacmdbAPI.ping_servers(): sql_out = {sql_out} type(sql_out) = {type(sql_out)}")
    up_servers = 0
    num_servers = 0
    if sql_out == "":                      # no records found
      self.log.debug(f"MariacmdbAPI.ping_servers(): no records found")
    else:                                  # ping servers
      sql_out = sql_out.replace('"', "").replace("[", "").replace("]", "").replace(",", "") # remove SQL fluff
      sql_list = sql_out.split()           # convert to list
      self.log.debug(f"MariacmdbAPI.ping_servers(): sql_list = {sql_list} type(sql_list) = {type(sql_list)}")
      for next_server in sql_list:
        self.log.debug(f"MariacmdbAPI.ping_servers(): next_server = {next_server}")
        num_servers += 1 
        proc = subprocess.run(f"ping -c1 -w1 {next_server}", shell=True, capture_output=True, text=True)     
        if proc.returncode == 0:                            # server pings
          up_servers += 1
    self.log.debug(f"MariacmdbAPI.ping_servers(): up_servers: {up_servers} num_servers: {num_servers}")
    return ('{"up_servers": '+str(up_servers)+', "num_servers": '+str(num_servers)+'}') # return JSON

  def uu_decode(self, url):
    """ 
    Decode a uu-encoded URL (have absolutely no idea how this works, but it does :))
    """
    return re.compile('%([0-9a-fA-F]{2})',re.M).sub(lambda m: chr(int(m.group(1),16)), url)

  def mk_where_clause(self, query_parms: list) -> str:
    """ 
    Construct an SQL WHERE clause from search parameters passed in 
    Return: constructed WHERE clause
    """
    where_clause = ""
    for next_word in query_parms:       # add search criteria to the WHERE clause
      self.log.debug(f"MariacmdbAPI.mk_where_clause() next_word: {next_word}")
      next_list = next_word.split("=")
      if len(next_list) == 2:            # '=' found
        attr = next_list[0]
        if attr == "os" or attr == "arch": # column is a string - escape the value
          value = next_list[1]
          next_word = f"{attr}=\"{value}\""
      if where_clause == "":             # start the clause
        where_clause = f"WHERE {next_word}"
      else:                              # append to the clause
        where_clause = f"{where_clause} AND {next_word}"
    self.log.debug(f"MariacmdbAPI.mk_where_clause(): where_clause: {where_clause}")
    return where_clause

  def count_servers(self, where_clause: str) -> str:
    """ 
    Send SQL command to count servers  
    Return: JSON output
    """
    sql_cmd = f"SELECT COUNT(host_name) FROM servers {where_clause}"
    self.log.debug(f"MariacmdbAPI.count_servers(): sql_cmd: {sql_cmd}")
    sql_out = self.run_sql_query(sql_cmd)
    self.close_conn()
    sql_out = str(sql_out).replace("[", "").replace("]", "")
    if not sql_out:                    # no hits
      sql_out = "0"
    return '{"num_servers": '+sql_out+'}'

  def get_host_names(self, where_clause: str) -> str:
    """
    Send SQL command to return hostnames of specified search 
    Return: JSON output
    """
    sql_cmd = f"SELECT host_name FROM servers {where_clause}"
    self.log.debug(f"MariacmdbAPI.get_host_names(): hostname sql_cmd = {sql_cmd}")
    return self.run_sql_query(sql_cmd) 
    self.close_conn()
    print(str(sql_out))    

  def get_records(self, where_clause: str) -> str:
    """
    Send SQL command to return hostnames of specified search
    Return: JSON output
    """
    sql_cmd = f"SELECT * FROM servers {where_clause}"
    self.log.debug(f"MariacmdbAPI.get_records(): query sql_cmd = {sql_cmd}")
    sql_out = self.run_sql_query(sql_cmd) 
    self.close_conn()
    return '{"servers": '+'"'+str(sql_out)+'"}'  

  def update_record(self, query_str: str):
    """
    query_str contains the host name to be updated and three pieces of metadata
    Send SQL command to update a record's metadata:
    - App
    - Group
    - Owner
    """
    list_len = len(query_str)
    if list_len != 4:                       # error
      self.log.error(f"MariacmdbAPI.update_record(): len(query_str): {list_len}, expected 4") 
      return
    cmd = f"UPDATE servers SET app = '{query_str[1]}', grp = '{query_str[2]}', owner = '{query_str[3]}' WHERE host_name = '{query_str[0]}'"
    self.connect_to_cmdb()                 # connect to DB
    try:   
      self.cursor.execute(cmd)             # run SQL command 
    except mariadb.Error as e:
      self.log.error(f"MariacmdbAPI.run_sql_query(): e: {e}")  
    self.conn.commit()                     # commit changes
    self.close_conn()                      # close connection
   
  def process_uri(self):
    """
    Perform operation specified in env var QUERY_STRING 
    """
    operation, query_parms = self.parse_query_string()
    self.log.debug(f"MariacmdbAPI.process_uri() operation: {operation} query_parms: {query_parms}")
    for i in range(len(query_parms)):      # uu-decode each element
      query_parms[i] = self.uu_decode(query_parms[i]) 
    where_clause=""
    if operation != "update" and query_parms != "": # query parameters => WHERE clause 
      where_clause = self.mk_where_clause(query_parms)
      self.log.debug(f"MariacmdbAPI.process_uri() where_clause: {where_clause}")
    match operation:
      case "count":                        # number of servers in table
        JSONout = self.count_servers(where_clause)
        print(JSONout)
      case "hostname":                     # all host names in table
        JSONout = self.get_host_names(where_clause)
        print(JSONout)
      case "ping":
        JSONout = self.ping_servers(where_clause)
        print(JSONout)
      case "query":                        # all rows in table
        JSONout = self.get_records(where_clause)
        print(JSONout)
      case "update":
        self.update_record(query_parms)    # params are hostname&newApp&newGroup&newOwner
      case _:  
        print(f"unexpected: operation = {operation}")
        exit(1)    

# main()
mariacmdbRestAPI = MariacmdbAPI()          # create a singleton
# mariacmdbRestAPI.print_env()             # show env vars when debugging
mariacmdbRestAPI.process_uri()             # process the request
