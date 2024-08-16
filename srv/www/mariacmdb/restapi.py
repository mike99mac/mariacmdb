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
import logging
import mariadb
import os
import re
import subprocess
import sys
from urllib.parse import urlparse, parse_qs

class MariacmdbAPI():
  def __init__(self):
    logging.basicConfig(filename='/home/pi/restapi.log',
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.DEBUG)
    self.log = logging.getLogger(__name__)
    self.log.setLevel(logging.DEBUG)
    print("Content-Type: text/html")       # print MIME type
    print()                                # required empty line

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

  def run_sql_cmd(self, cmd: str) -> str:
    """
    run the SQL command passed in
    """
    self.log.info(f"MariacmdbAPI.run_sql_cmd(): cmd = {cmd}")
    conn = mariadb.connect(user="root", password="pi", host="127.0.0.1", database="mysql")
    cursor = conn.cursor()                 # open cursor
    try:   
      cursor.execute("use cmdb")
    except mariadb.Error as e:
      print(f"ERROR changing database to 'cmdb': {e}")
      print("</body></html>")
      conn.close()                         # cannot contiue
      exit(1)
    rows = "" 
    output = ""
    self.log.info(f"MariacmdbAPI.run_sql_cmd(): running cmd: {cmd}") 
    try:   
      cursor.execute(cmd)                  # query the cmdb
      rows = cursor.fetchall()
      rows = str(rows)                     # convert to string
      rows = rows.replace("(", "").replace(",)", "").replace("'", '"') # clean up SQL fluff
      rows = rows.replace("[", "").replace("]", "")
      self.log.info(f"MariacmdbAPI.run_sql_cmd(): rows = {rows} type(rows) = {type(rows)}") 
      if rows == []:                       # no match
        self.log.info(f"MariacmdbAPI.run_sql_cmd(): no matching rows") 
      else:  
        output = rows
    except mariadb.Error as e:
      self.log.error(f"MariacmdbAPI.run_sql_cmd(): output = {output}")  
    return output  

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
    operation = query_parms[0]            # get operation
    query_parms = query_parms[1:]        # chop off operation
    return operation, query_parms

  def ping_servers(self, where_clause: str) -> str:
    """
    ping specified servers and return how many servers ping out of how many found 
    """
    sql_cmd = f"SELECT host_name FROM servers {where_clause}"
    sql_out = self.run_sql_cmd(sql_cmd)    # list of server host names
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
    sql_out = self.run_sql_cmd(sql_cmd)
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
    return self.run_sql_cmd(sql_cmd) 
    print(str(sql_out))    

  def get_records(self, where_clause: str) -> str:
    """
    Send SQL command to return hostnames of specified search
    Return: JSON output
    """
    # TO DO: this is not emitting valid JSON... but is it needed at all?
    sql_cmd = f"SELECT * FROM servers {where_clause}"
    self.log.debug(f"MariacmdbAPI.get_records(): query sql_cmd = {sql_cmd}")
    sql_out = self.run_sql_cmd(sql_cmd) 
    return '{"servers": '+'"'+str(sql_out)+'"}'  
   
  def process_uri(self):
    """
    Perform operation specified in env var QUERY_STRING 
    """
    operation, query_parms = self.parse_query_string()
    self.log.debug(f"MariacmdbAPI.process_uri() operation: {operation} query_parms: {query_parms}")
    for i in range(len(query_parms)):      # uu-decode each element
      query_parms[i] = self.uu_decode(query_parms[i]) 
    where_clause=""
    if operation == "update":              # params are hostname&newApp&newGroup&newOwner
      self.update_record(query_parms)
    elif query_parms != "":                # there are query parameters 
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
        pass                               # already complete 
      case _:  
        print(f"unexpected: operation = {operation}")
        exit(1)    

# main()
mariacmdbRestAPI = MariacmdbAPI()          # create a singleton
# mariacmdbRestAPI.print_env()             # show env vars when debugging
mariacmdbRestAPI.process_uri()             # process the request
