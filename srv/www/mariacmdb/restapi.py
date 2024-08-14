#!/srv/venv/bin/python3
"""
restapi.py - the mariacmdb RESTful API.
It accesses the table 'servers' in the mariadb database 'cmdb'.
Examples: 
http://model1500/restapi.py/ping                        ping all servers
http://model1500/restapi.py/count/cpus=4/mem_gb=4")     number of servers with 4 CPUs and 4 GB of memory
http://model1500/restapi.py/hostname/cpus<4")           host names of servers with less than 4 CPUs

http://model1500/restapi.py/count ...
{ "num_servers": 4 }

http://model1500/restapi.py/ping ...
{ "up_servers": 3, "num_servers": 4 }

http://model1500/restapi.py/hostname ...
[ "model1000", "model1500", "model2000", "model800" ]
"""
import sys
sys.path.insert(0, "/home/pi/.local/lib/python3.10/site-packages") # Python libs
import logging
import mariadb
import os
import subprocess

class MariacmdbRestAPI():
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
    self.log.info(f"MariacmdbRestAPI.run_sql_cmd(): cmd = {cmd}")
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
    self.log.info(f"MariacmdbRestAPI.run_sql_cmd(): running cmd: {cmd}") 
    try:   
      cursor.execute(cmd)                  # query the cmdb
      rows = cursor.fetchall()
      rows = str(rows)                     # convert to string
      rows = rows.replace("(", "").replace(",)", "").replace("'", '"') # clean up SQL fluff
      rows = rows.replace("[", "").replace("]", "")
      self.log.info(f"MariacmdbRestAPI.run_sql_cmd(): rows = {rows} type(rows) = {type(rows)}") 
      if rows == []:                       # no match
        self.log.info(f"MariacmdbRestAPI.run_sql_cmd(): no matching rows") 
      else:  
        output = rows
    except mariadb.Error as e:
      self.log.error(f"MariacmdbRestAPI.run_sql_cmd(): output = {output}")  
    return output  

  def ping_servers(self, where_clause: str) -> str:
    """
    ping specified servers and return how many servers ping out of how many found 
    """
    sql_cmd = f"SELECT host_name FROM servers {where_clause}"
    sql_out = self.run_sql_cmd(sql_cmd)    # list of server host names
    self.log.info(f"MariacmdbRestAPI.ping_servers(): sql_out = {sql_out} type(sql_out) = {type(sql_out)}")
    up_servers = 0
    num_servers = 0
    if sql_out == "":                      # no records found
      self.log.debug(f"MariacmdbRestAPI.ping_servers(): no records found")
    else:                                  # ping servers
      sql_out = sql_out.replace('"', "").replace("[", "").replace("]", "").replace(",", "") # remove SQL fluff
      sql_list = sql_out.split()           # convert to list
      self.log.debug(f"MariacmdbRestAPI.ping_servers(): sql_list = {sql_list} type(sql_list) = {type(sql_list)}")
      for next_server in sql_list:
        self.log.debug(f"MariacmdbRestAPI.ping_servers(): next_server = {next_server}")
        num_servers += 1 
        proc = subprocess.run(f"ping -c1 -w1 {next_server}", shell=True, capture_output=True, text=True)     
        if proc.returncode == 0:                            # server pings
          up_servers += 1
    self.log.debug(f"MariacmdbRestAPI.ping_servers(): up_servers: {up_servers} num_servers: {num_servers}")
    print('{"up_servers": '+str(up_servers)+', "num_servers": '+str(num_servers)+'}') # return JSON

  def process_request_uri(self):
    """
    Perform operation specified in env var REQUEST_URI
    """
    # get value of env variable REQUEST_URI
    proc = subprocess.run("echo $REQUEST_URI", shell=True, capture_output=True, text=True)
    rc = proc.returncode
    if rc != 0:
      self.log.error(f"MariacmdbRestAPI.ping_servers(): subprocess.run('echo $REQUEST_URI' returned {rc}")
      return 1
    resp = []
    resp = proc.stdout                     # get value
    resp = resp.rstrip('\n').lstrip("/").rstrip('/') # strip trailing newline, leading and trailing '/'s
    words = resp.split("/")
    num_words = len(words)
    self.log.debug(f"MariacmdbRestAPI.process_request_uri(): resp = '{resp} words = {words} num_words = {num_words}")
    operation = words[1]
    self.log.debug(f"MariacmdbRestAPI.process_request_uri() operation = '{operation}'")
    where_clause = ""
    if num_words > 2:                      # there is a search criteria
      other_words = words[2:]
      for next_word in other_words:        # add search criteria to the WHERE clause
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
    match operation:
      case "ping":
        self.ping_servers(where_clause)
      case "count":                        # number of servers in table
        sql_cmd = f"SELECT COUNT(host_name) FROM servers {where_clause}"
        self.log.debug(f"MariacmdbRestAPI.process_request_uri(): count sql_cmd = {sql_cmd}")
        sql_out = self.run_sql_cmd(sql_cmd)
        sql_out = str(sql_out).replace("[", "").replace("]", "")
        if not sql_out:                    # no hits
          sql_out = "0"
        print('{"num_servers": '+sql_out+'}')  
      case "hostname":                     # all host names in table
        sql_cmd = f"SELECT host_name FROM servers {where_clause}"
        self.log.debug(f"MariacmdbRestAPI.process_request_uri(): hostname sql_cmd = {sql_cmd}")
        sql_out = self.run_sql_cmd(sql_cmd) 
        print(str(sql_out))    
      case "query":                        # all rows in table
        # TODO: this is not emitting valid JSON... but is it needed at all?
        sql_cmd = f"SELECT * FROM servers {where_clause}"
        self.log.debug(f"MariacmdbRestAPI.process_request_uri(): query sql_cmd = {sql_cmd}")
        sql_out = self.run_sql_cmd(sql_cmd) 
        print('{"servers": '+'"'+str(sql_out)+'"}')  
        self.log.debug(f"process_request_uri(): sql_out = {sql_out}") 
      case _:  
        print(f"unexpected: operation = {operation}")
        exit(1)    

# main()
mariacmdbRestAPI = MariacmdbRestAPI()      # create a singleton
mariacmdbRestAPI.process_request_uri()     # process the request
