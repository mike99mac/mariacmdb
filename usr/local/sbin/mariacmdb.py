#!/usr/bin/python3
"""
mariacmdb is a simple Configuration Management Database (CMDB) based on the mariadb relational database.
It consists of a database named 'cmdb' with a table named 'servers' with these columns:
- host_name  Short host name
- ip_addr    Primary IP address
- cpus       Number of CPUs
- mem_gb     GB of memeory
- arch       Architecture
- os         Operating system
- os_ver     OS version
- kernel     Kernel version
- rootfs     Root file system % full
- created_at Timestamp

It supports the following commands:
- initialize        Creates the table 'servers' in database 'cmdb'
- add <SERVER>      If SERVER already exists, record is updated
- describe          Show the format of the 'servers' database
- query <PATTERN>   If no PATTERN is supllied, return all rows
- remove <SERVER>   Remove row for specified server
- update            Refresh entire database

Return codes:
0 - Success
1 - Error
2 - No records found 

Examples:
- mariacmdb.py -v initialize
- mariacmdb.py describe
- mariacmdb.py -v add --server johnsbox
- mariacmdb.py -v query
"""
import argparse
import logging
import mariadb
import os
import subprocess
import sys

class Mariacmdb:
  def __init__(self):
    # create a logger that writes both to a file and stdout
    logging.basicConfig(filename='/home/pi/mariacmdb.log',
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.INFO)
    self.console = logging.StreamHandler()          # set up logging to console
    self.console.setLevel(logging.INFO)
    self.formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')  # set a format which is simpler for console use
    self.console.setFormatter(self.formatter)
    logging.getLogger('').addHandler(self.console) # add the handler to the root logger
    self.log = logging.getLogger(__name__)

    self.script_dir = "/home/pi"           # directory where script 'serverinfo' resides
    self.parser = argparse.ArgumentParser(description = "mariacmdb - A simple Configuration Management Database")
    self.parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    self.parser.add_argument("-C", "--copyscript", help="copy script 'serverinfo' to target server before add", action="store_true")
    self.parser.add_argument("-c", "--column", help="column name to search", action="append")
    self.parser.add_argument("subcommand", help="Can be 'add', 'describe', 'initialize', 'query', 'remove' or 'update'")
    self.parser.add_argument("-p", "--pattern", help="pattern to search for", action="append")
    self.parser.add_argument("-s", "--server", help="server to add or remove", action="append")
    self.args = self.parser.parse_args()
    self.conn = None                       # mariadb connection
    self.cursor = None                     # mariadb cursor
    self.log.debug(f"__init__(): self.args = {str(self.args)}")
    self.create_db_cmd = "CREATE DATABASE cmdb;"
    self.describe_cmd = "DESC servers;"
    self.delete_cmd = "DELETE FROM servers WHERE host_name = pattern;"
    self.create_table_cmd = """
      CREATE TABLE IF NOT EXISTS servers (
        host_name VARCHAR(255) NOT NULL UNIQUE,
        ip_addr VARCHAR(20),
        cpus INT,
        mem_gb INT,
        arch VARCHAR(50),
        os VARCHAR(100),
        os_ver VARCHAR(50), 
        kernel VARCHAR(100),
        rootfs INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
      """
    self.replace_row_cmd = """
      REPLACE INTO servers (
        host_name, ip_addr, cpus, mem_gb, arch, os, os_ver, kernel, rootfs) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      """
    self.select_cmd = """
      SELECT * FROM servers WHERE host_name LIKE ptrn 
        OR ip_addr LIKE ptrn 
        OR cpus LIKE ptrn 
        OR mem_gb LIKE ptrn 
        OR arch LIKE ptrn 
        OR os LIKE ptrn 
        OR os_ver LIKE ptrn 
        OR kernel LIKE ptrn
        OR rootfs LIKE ptrn;
        """
    self.select_all_cmd = "SELECT * FROM servers"
    self.select_host_names_cmd = "SELECT host_name FROM servers"
    self.use_cmd = "USE cmdb" 

  def connect_db(self):   
    """
    Connect to mariadb running on this server
    """   
    return mariadb.connect(user="root", password="pi", host="127.0.0.1", database="mysql")   

  def connect_to_cmdb(self):   
    """
    Connect to mariadb and use datase cmdb 
    """  
    self.conn = self.connect_db()          # open connection
    self.cursor = self.conn.cursor()       # open cursor
    try:   
      self.cursor.execute(self.use_cmd)    # use cmdb 
      self.log.debug("connect_to_cmdb(): changed database to 'cmdb'")
    except mariadb.Error as e:
      self.log.error(f"connect_to_cmdb(): ERROR changing database to 'cmdb': {e}")
      self.conn.close()                    # cannot contiue
      return -1 
    
  def query_cmdb(self):
    """
    Search CMDB for specified pattern 
    """
    pattern = str(self.args.pattern).replace("'", "").replace("[", "").replace("]", "")
    self.log.debug(f"query_cmdb(): self.args.pattern = {self.args.pattern}")
    cmd = ""
    if self.args.column:                   # search is based on one column
      if self.args.pattern == None:        # no pattern to search on
        self.log.error("query_cmdb(): if COLUMN is specified there must be a search PATTERN")
        return 1
      self.log.debug(f"query_cmdb(): TODO: search on args.column = {self.args.column} args.pattern = {self.args.pattern}")
      return 2 # for now
    if self.args.pattern == None:          # no search pattern
      self.log.debug("query_cmdb(): No search PATTERN - returning all records")
      cmd = self.select_all_cmd            # return all rows
    else:  
      cmd = self.select_cmd.replace("ptrn", "'%"+pattern+"%'") # put search pattern in query
    self.log.debug(f"query_cmdb(): searching for '{pattern}' with command: {cmd}")
    if self.connect_to_cmdb() == -1: 
      self.log.error("query_cmdb(): connect_to_cmdb() failed")
      return -1
    rows = ""  
    try:   
      self.cursor.execute(cmd)             # query the cmdb
      rows = self.cursor.fetchall()
      if rows == []:
        self.log.debug("query_cmdb(): No records found")
        return 2                           # no records found
      else:                                # print rows
        for i in rows:
          print(*i, sep=',') 
    except mariadb.Error as e:
      self.log.warning(f"WARNING - query_cmdb(): Exception searching database: {e}")
      return 1

  def commit_changes(self):   
    """
    Commit all SQL changes then close cursor and connection
    """ 
    self.conn.commit()                     # commit changes
    self.cursor.close()                    # close cursor
    self.conn.close()                      # close connection

  def initialize(self):  
    """
    Create the Configuration Management Database with one table
    - CREATE DATABASE 'cmdb'
    - USE cmdb
      CREATE TABLE 'servers'
    """
    self.conn = self.connect_db()          # open connection
    self.cursor = self.conn.cursor()       # open cursor
    try:   
      self.cursor.execute(self.create_db_cmd) # create database "cmdb"
      self.conn.commit()                   # commit changes
    except mariadb.Error as e:
      self.log.warning(f"initialize(): Exception creating database: {e}")
    try:   
      self.cursor.execute(self.use_cmd)    # use cmdb
      self.log.debug("initialize(): changed to database 'cmdb'")
    except mariadb.Error as e:
      self.log.error(f"initialize(): changing database to 'cmdb': {e}")
      self.conn.close()                    # cannot continue
      exit(1)
    try:   
      self.cursor.execute(self.create_table_cmd) # create database "cmdb"
      self.log.debug(f"initialize(): Created table 'servers'")
    except mariadb.Error as e:
      self.log.error(f"initialize(): ERROR creating table 'servers': {e}")
      exit(1)
    self.commit_changes()  
  
  def ping_server(self):
    """
    Ping the server passed in with the --server option
    """
    if self.args.server == None:           # no server name specified
      self.log.error(f"ping_server(): Option '--server SERVER' must be specified with command '{self.args.command}'")
      return 1
    server = str(self.args.server[0])  
    self.log.debug(f"ping_server(): server = {server}")
    ping_cmd = f"ping -c1 -W 0.5 {server}" # send 1 packet, timeout after 500ms
    proc = subprocess.run(ping_cmd, shell=True, capture_output=True, text=True)
    rc = proc.returncode
    self.log.debug(f"ping_server(): command {ping_cmd} returned {rc}")
    if rc != 0:                          # just give warning
      self.log.error(f"ping_server(): cannot ping server: {server}")
      return 1
    else:
      return 0 

  def find_server(self, server):
    """
    Get data from a server
    - if requested, copy the script 'serverinfo' to the target server's script directory
    - run it on the target node
    - sample output:
    model800,192.168.12.176,4,4,aarch64,Linux,Ubuntu 22.04.4 LTS,5.15.0-1053-raspi #56-Ubuntu SMP PREEMPT Mon Apr 15 18:50:10 UTC 2024
    """
    self.log.debug(f"find_server(): server = {server}")
    if self.args.copyscript:               # copy script first
      scp_cmd = f"scp {self.script_dir}/serverinfo {server}:{self.script_dir}" 
      proc = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True) 
      if proc.returncode != 0:             # just give warning
        self.log.warning(f"find_server(): command {scp_cmd} returned {proc.returncode}")
      else:
        self.log.debug(f"find_server(): command {scp_cmd} returned {proc.returncode}")
    ssh_cmd = f"ssh {server} {self.script_dir}/serverinfo"  # run script 'serverinfo' and get output
    proc = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
    server_data = []
    server_data = proc.stdout.split(",")
    self.log.debug(f"find_server(): command {ssh_cmd} returncode: {proc.returncode} stdout: {server_data}")
    return server_data

  def replace_row(self, server_data = []): 
    """
    USE cmdb
    INSERT a row into table 'servers' or REPLACE it if host_name is a duplicate
    """
    server = server_data[0] 
    self.log.debug(f"replace_row(): server_data = {server_data} server = {server}")
    self.connect_to_cmdb()
    try: 
      self.log.debug(f"replace_row(): replacing row with: {self.replace_row_cmd}")
      self.cursor.execute(self.replace_row_cmd, server_data)  
    except mariadb.Error as e:
      self.log.error(f"replace_row() inserting row into table 'servers': {e}")
      self.conn.close()                         # close connection
      return 
    self.commit_changes() 
    self.log.info(f"replace_row(): replaced row for server {server}")

  def delete_row(self):
    """
    Delete a row with a "host_name" of the specified server 
    """
    self.log.debug(f"delete_row(): self.args.server = {self.args.server}")
    if self.args.server == None:           # no server name specified
      self.log.error("delete_row(): --server SERVER must be specified with delete")
      return 1
    if self.connect_to_cmdb() == -1:  
      self.log.debug("delete_row(): connect_to_cmdb() failed")
      return -1
    server = str(self.args.server[0])  
    cmd = self.delete_cmd.replace("pattern", "'"+server+"'") # add target server in single quotes
    self.log.debug(f"delete_row(): cmd = {cmd}")  
    try: 
      self.cursor.execute(cmd)  
      if self.cursor.rowcount == 0:        # no matching server
        self.log.debug(f"delete_row(): cursor.rowcount = {cursor.rowcount}")  
        self.log.error(f"delete_row(): did not find server {server} in CMDB")
        return 2 
      else:   
        self.log.debug(f"delete_row(): deleted server = {server} cursor.rowcount = {cursor.rowcount}")  
    except mariadb.Error as e:
      self.log.error(f"delete_row(): ERROR deleting row in table 'servers': {e}")
      self.conn.close()                         # close connection
      return 1    
    self.commit_changes()           
  
  def describe_table(self):
    """
    Describe the 'server' table
    """
    if self.connect_to_cmdb() == -1:
      self.log.error("describe_table(): connect_to_cmdb() failed")
      return -1
    try:   
      self.cursor.execute(self.describe_cmd)    # describe the table
      rows = cursor.fetchall()
      print("Table servers:")
      print("Field,Type,Null,Key,Default,Extra")
      print("---------------------------------")
      for i in rows:
        print(*i, sep=',') 
    except mariadb.Error as e:
      self.log.warning(f"describe_table(): Exception searching database: {e}")
      self.conn.close()                    # cannot contiue
      return 1
    self.conn.close()                      # close connection  

  def update_cmdb(self):
    """
    Update all rows in 'server' table
    """
    if self.connect_to_cmdb() == -1:
      self.log.debug("update_cmdb(): connect_to_cmdb() failed")
      return -1
    try:   
      self.cursor.execute(self.select_host_names_cmd) # get all hostnames in table
      servers = self.cursor.fetchall()
      self.log.debug(f"update_cmdb(): servers = {servers}")
      for next_server in servers:
        next_server = str(next_server).strip("'").strip("(").strip(")").strip(",").strip("'")
        self.log.debug(f"update_cmdb(): next_server = {next_server}")
        server_data = self.find_server(next_server)
        self.log.debug(f"update_cmdb(): server_data = {server_data}")
        if server_data == ['']:            # did not get server data
          self.log.warning(f"update_cmdb(): did not get server_data for {next_server} - skipping")
          continue                         # iterate loop
        self.replace_row(server_data)
      self.log.info("update_cmdb() successfully updated table 'servers'")  
    except mariadb.Error as e:
      self.log.warning(f"update_cmdb(): Exception updating database: {e}")
      self.conn.close()                    # cannot contiue
      return 1

  def run_command(self):
    """
    Run the command passed in
    """
    rc = 0                                 # assume success
    if self.args.verbose:                  # set log level to DEBUG for log file and stdout
      self.log.setLevel(logging.DEBUG)
      self.console.setLevel(logging.DEBUG)
    self.log.debug(f"run_command(): subcommand = {self.args.subcommand}")
    match self.args.subcommand:
      case 'initialize':
        rc = self.initialize()             # ignore 2nd word if any
      case 'add':  
        if self.args.server == None:       # no server name specified
          self.log.error("run_command(): Option '--server SERVER' must be specified with subcommand 'add'")
          return 1
        rc = self.ping_server()
        if rc == 0:                        # server pings
          self.log.debug(f"run_command(): server pings, calling find_server")
          server_data = self.find_server(self.args.server[0])
          rc = self.replace_row(server_data)
      case "describe":
        rc = self.describe_table() 
      case 'remove':
        if self.args.server == None:       # no server name specified
          self.log.error("run_command(): Option '--server SERVER' must be specified with subcommand 'remove'")
          return 1
        rc = self.delete_row()  
      case "query":
        rc = self.query_cmdb()
      case "update":
        rc = self.update_cmdb()
      case _:
        self.log.error(f"run_command(): unrecognized subcommand {self.args.subcommand}")  
        rc = 1
    exit(rc)    

# main()
mariacmdb = Mariacmdb()                    # create a singleton
mariacmdb.run_command()                    # do the work
