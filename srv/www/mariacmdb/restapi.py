#!/usr/bin/python3
"""
This is the mariacmdb RESTful API
Ex: http://model1500/restapi.py/ping/mem_gb=4
"""
import sys
sys.path.insert(0, "/home/pi/.local/lib/python3.10/site-packages") # Python libs
import logging
import mariadb
import os
import subprocess

class MariacmdbRestAPI():
  def __init__(self):
    logging.basicConfig(filename='/var/log/apache2/restapi.log',
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.DEBUG)
    self.log = logging.getLogger(__name__)
    self.log.setLevel(logging.DEBUG)
    print("Content-Type: text/html")       # print MIME type
    print()                                # required empty line

  # def print_env(self):
  #   """
  #   Show all environment variables with the 'env' command
  #   """
  #   proc = subprocess.run("env", shell=True, capture_output=True, text=True)
  #   rc = proc.returncode
  #   env_vars = []
  #   env_vars = proc.stdout
  #   print("<pre>")
  #   for line in env_vars.split("\n"):
  #     print(str(line))
  #   print("</pre>")
  #   print("")

  def run_sql_cmd(self, cmd: str) -> str:
    """
    run the SQL command passed in
    """
    self.log.info(f"run_sql_cmd(): cmd = {cmd}")
    conn = mariadb.connect(user="root", password="pi", host="127.0.0.1", database="mysql")
    cursor = conn.cursor()                 # open cursor
    try:   
      cursor.execute("use cmdb")           # use cmdb
    except mariadb.Error as e:
      print(f"ERROR changing database to 'cmdb': {e}")
      print("</body></html>")
      conn.close()                         # cannot contiue
      exit(1)
    rows = "" 
    output = ""
    try:   
      cursor.execute(cmd)                  # query the cmdb
      rows = cursor.fetchall()
      if rows != []:                       # records found
        for i in rows:
          if output == "":
            output = f"{i[0]}"
          else:  
            output = f"{output} {i[0]}"
    except mariadb.Error as e:
      print(f"WARNING - show_cmdb(): Exception searching database: {e}")  
      self.log.error(f"run_sql_cmd(): output = {output}")  
    return output  

  def ping_servers(self, search_criteria: str) -> str:
    """
    ping specified servers and return how many servers ping out of how many found 
    """
    if len(search_criteria.strip()) != 0:  # there is a search criteria
      self.log.debug(f"ping_servers(): len(search_criteria.strip()) = '{len(search_criteria.strip())}'")
      sql_cmd = f"SELECT host_name FROM servers WHERE {search_criteria}"
    else:  
      sql_cmd = "SELECT host_name FROM servers"
    sql_out = self.run_sql_cmd(sql_cmd).split(" ") # list of server host names
    self.log.info(f"ping_servers(): sql_out = {sql_out}")
    num_servers = 0
    pinged_servers = 0
    if sql_out == "":                      # no records found
      pinged_servers = 0
      num_servers = 0
    else:
      for next_server in sql_out:
        self.log.debug(f"ping_servers(): next_server = {next_server}")
        num_servers += 1 
        proc = subprocess.run(f"ping -c1 -w1 {next_server}", shell=True, capture_output=True, text=True)     
        if proc.returncode == 0:                            # server pings
          pinged_servers += 1
    return f"{pinged_servers} {num_servers}"

  def process_request_uri(self):
    """
    Perform operation based on REQUEST_URI
    """
    proc = subprocess.run("echo $REQUEST_URI", shell=True, capture_output=True, text=True)
    rc = proc.returncode
    request_uri = []
    request_uri = proc.stdout
    self.log.debug(f"process_request_uri(): request_uri = '{request_uri}'")
    request_uri = request_uri.rstrip('\n').lstrip("/").rstrip('/') # strip trailing newline, leading and trailing '/'s
    request_words = request_uri.split("/")
    num_words = len(request_words)
    self.log.debug(f"process_request_uri(): num_words = {num_words}")
    if num_words == 1:                       # no operation   
      print("<html><head>")
      print("</head><body>")
      print("<h1>Contents of mariacmdb</h1>")
      sql_cmd = "SELECT * FROM servers"
    else: 
      operation = request_words[1].strip()
      self.log.debug(f"process_request_uri() opearation = '{operation}'")
      if operation == "ping":                # ping servers
        search_criteria = ""
        if num_words == 3:
          search_criteria = request_words[2]
        ret_str = self.ping_servers(search_criteria)
        print(ret_str)
      else:                                  # SQL command
        match operation:
          case "count":
            if num_words == 3:               # search criteria included
              sql_cmd = f"SELECT COUNT(host_name) FROM servers WHERE {request_words[2]}"
            else:
              sql_cmd = f"SELECT COUNT(host_name) FROM servers" 
          case "hostname":
            if num_words == 3:               # search criteria included
              sql_cmd = f"SELECT host_name FROM servers WHERE {request_words[2]}"
            else:
              sql_cmd = f"SELECT host_name FROM servers"
          case "query":
            if num_words == 3:               # search criteria included
              sql_cmd = f"SELECT * FROM servers WHERE {request_words[2]}"
            else:
              sql_cmd = f"SELECT * FROM servers"
          case _:  
            print(f"unexpected: operation = {operation}")
            exit(1)
        sql_out = self.run_sql_cmd(sql_cmd)       # return output of SQL command
        print(sql_out)

# main
mariacmdbRestAPI = MariacmdbRestAPI()      # create a singleton
# mariacmdbRestAPI.print_env() 
mariacmdbRestAPI.process_request_uri()     # process the request