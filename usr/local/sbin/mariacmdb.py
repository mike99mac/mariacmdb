#!/usr/bin/python3
"""
mariacmdb is a simple Configuration Management Database (CMDB) based on the mariadb relational database.
It consists:
- A database: 'cmdb'
- A table:    'servers

The table has these columns:
- host_name  Short host name
- ip_addr    Primary IP address
- cpus       Number of CPUs
- mem_gb     GB of memeory
- arch       Architecture
- os         Operating system
- os_ver     OS version
- kernel     Kernel version
- rootfs     Root file system % full

It supports the following commands:
- initialize        Creates the table 'servers' in database 'cmdb'
- add <SERVER>      If SERVER already exists, record is updated
- query <PATTERN>   If no PATTERN is supllied, return all rows
- remove <SERVER>

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
import mariadb
import os
import subprocess
import sys

class Mariacmdb:
  def __init__(self):
    self.script_dir = "/home/pi/"          # directory where script 'serverinfo' resides
    self.parser = argparse.ArgumentParser(description = "mariacmdb - A simple Configuration Management Database")
    self.parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    self.parser.add_argument("-c", "--copyscript", help="copy script 'serverinfo' to target server before add", action="store_true")
    self.parser.add_argument("--column", help="column name to search", action="append")
    self.parser.add_argument("--value", help="value to search for in previous column", action="append")
    self.parser.add_argument("command", help="Can be 'add', 'describe', 'initialize', 'query', or 'remove'")
    self.parser.add_argument("--pattern", help="pattern for query all columns", action="append")
    self.parser.add_argument("--server", help="server to add or remove", action="append")
    self.args = self.parser.parse_args()
    self.verbose_msg(f"__init__(): self.args = {str(self.args)}")
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
    self.use_cmd = "USE cmdb" 

  def verbose_msg(self, msg):
    """
    Print message when in verbose mode
    """
    if self.args.verbose:
      print(msg)

  def connect_db(self):   
    """
    Connect to mariadb running on this server
    """   
    return mariadb.connect(user="root", password="pi", host="127.0.0.1", database="mysql")   
    
  def query_cmdb(self):
    """
    Search CMDB for specified pattern 
    """
    pattern = self.args.pattern
    self.verbose_msg(f"query_cmdb(): self.args.pattern = {self.args.pattern}")
    cmd = ""
    if self.args.column:
      self.verbose_msg(f"query_cmdb(): self.args.column = {self.args.column} self.args.value = {self.args.value}")
      print("TODO: search by column")
    if self.args.pattern == None and self.args.value == None:  # no search pattern
      self.verbose_msg("query_cmdb(): No search PATTERN - returning all records")
      cmd = self.select_all_cmd            # return all rows
    else:  
      cmd = self.select_cmd.replace("ptrn", "'%"+pattern+"%'") # put search pattern in query
    self.verbose_msg(f"query_cmdb(): searching for '{pattern}' with command: {cmd}")
    conn = self.connect_db()               # open connection
    cursor = conn.cursor()                 # open cursor
    try:   
      cursor.execute(self.use_cmd)         # use cmdb 
      self.verbose_msg("query_cmdb(): changed database to 'cmdb'")
    except mariadb.Error as e:
      print(f"ERROR changing database to 'cmdb': {e}")
      conn.close()                         # cannot contiue
      return 1
    rows = ""  
    try:   
      cursor.execute(cmd)                  # query the cmdb
      rows = cursor.fetchall()
      if rows == []:
        self.verbose_msg("query_cmdb(): No records found")
        return 2                           # no records found
      else:                                # print rows
        for i in rows:
          print(*i, sep=',') 
    except mariadb.Error as e:
      print(f"WARNING - query_cmdb(): Exception searching database: {e}")
      return 1
        
  def initialize(self):  
    """
    Create the Configuration Management Database with one table
    - CREATE DATABASE 'cmdb'
    - USE cmdb
    - CREATE TABLE 'servers'
    """
    conn = self.connect_db()               # open connection
    cursor = conn.cursor()                 # open cursor
    try:   
      cursor.execute(self.create_db_cmd)   # create database "cmdb"
      conn.commit()                        # commit changes
    except mariadb.Error as e:
      print(f"WARNING - Exception creating database: {e}")
    try:   
      cursor.execute(self.use_cmd)         # use cmdb
      self.verbose_msg("initialize(): changed to database 'cmdb'")
    except mariadb.Error as e:
      print(f"ERROR changing database to 'cmdb': {e}")
      conn.close()                         # cannot continue
      exit(1)
    try:   
      cursor.execute(self.create_table_cmd) # create database "cmdb"
      self.verbose_msg(f"initialize(): Created table 'servers'")
      print("Created table 'servers'")
    except mariadb.Error as e:
      print(f"ERROR creating table 'servers': {e}")
      exit(1)
    conn.commit()                          # commit changes
    cursor.close()                         # close cursor
    conn.close()                           # close connection
  
  def ping_server(self):
    """
    Ping the server passed in with the --server option
    """
    if self.args.server == None:           # no server name specified
      print(f"ERROR: Option '--server SERVER' must be specified with command '{self.args.command}'")
      return 1
    server = str(self.args.server[0])  
    self.verbose_msg(f"ping_server(): server = {server}")
    ping_cmd = f"ping -c1 -W 0.5 {server}" # send 1 packet, timeout after 500ms
    proc = subprocess.run(ping_cmd, shell=True, capture_output=True, text=True)
    rc = proc.returncode
    self.verbose_msg(f"ping_server(): command {ping_cmd} returned {rc}")
    if rc != 0:                          # just give warning
      print(f"ERROR: cannot ping server: {server}")
      return 1
    else:
      return 0 

  def find_server(self):
    """
    Get data from a server
    - if requested, copy the script 'serverinfo' to the target server's script directory
    - run it on the target node
    - sample output:
    model800,192.168.12.176,4,4,aarch64,Linux,Ubuntu 22.04.4 LTS,5.15.0-1053-raspi #56-Ubuntu SMP PREEMPT Mon Apr 15 18:50:10 UTC 2024
    """
    server = str(self.args.server[0]) 
    if self.args.copyscript:               # copy script first
      scp_cmd = f"scp {self.script_dir}/serverinfo {server}:{self.script_dir}" 
      proc = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
      rc = proc.returncode
      self.verbose_msg(f"find_server(): command {scp_cmd} returned {rc}")
      if rc != 0:                          # just give warning
        print(f"WARNING: command {scp_cmd} returned {rc}")

    # run script 'serverinfo' and get output
    ssh_cmd = f"ssh {server} {self.script_dir}/serverinfo"
    proc = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
    rc = proc.returncode
    server_data = []
    server_data = proc.stdout.split(",")
    self.verbose_msg(f"find_server(): command {ssh_cmd} rc: {rc} stdout: {server_data}")
    return server_data

  def replace_row(self, server_data = []): 
    """
    USE cmdb
    INSERT a row into table 'servers' or REPLACE it if host_name is a duplicate
    """
    server = str(self.args.server[0]) 
    self.verbose_msg(f"replace_row(): self.args.server = {self.args.server}")
    conn = self.connect_db()               # open connection
    cursor = conn.cursor()                 # open cursor
    try:   
      cursor.execute(self.use_cmd)         # use cmdb
      self.verbose_msg("replace_row(): changed to database 'cmdb'")
    except mariadb.Error as e:
      print(f"Error changing database to 'cmdb': {e}")
      conn.close()                         # cannot contiue
      return 1
    try: 
      cursor.execute(self.replace_row_cmd, server_data)  
      self.verbose_msg(f"replace_row(): replacing row with: {self.replace_row_cmd}")
      print(f"Added or updated server {server}")
    except mariadb.Error as e:
      print(f"Error inserting row into table 'servers': {e}")
      conn.close()                         # close connection
      return        
    conn.commit()                          # commit changes
    cursor.close()                         # close cursor
    conn.close()                           # close connection

  def delete_row(self):
    """
    Delete a row with a "host_name" of the specified server 
    """
    self.verbose_msg(f"delete_row(): self.args.server = {self.args.server}")
    if self.args.server == None:           # no server name specified
      print("ERROR: --server SERVER must be specified with delete")
      return 1
    conn = self.connect_db()               # open connection
    cursor = conn.cursor()                 # open cursor
    try:   
      cursor.execute(self.use_cmd)         # use cmdb
      self.verbose_msg("delete_row(): changed to database 'cmdb'")
    except mariadb.Error as e:
      print(f"Error changing database to 'cmdb': {e}")
      conn.close()                         # cannot contiue
      return 1
    server = str(self.args.server[0])  
    cmd = self.delete_cmd.replace("pattern", "'"+server+"'") # add target server in single quotes
    self.verbose_msg(f"delete_row(): cmd = {cmd}")  
    try: 
      cursor.execute(cmd)  
      if cursor.rowcount == 0:             # no matching server
        self.verbose_msg(f"delete_row(): cursor.rowcount = {cursor.rowcount}")  
        print(f"ERROR: did not find server {server} in CMDB")
        return 2 
      else:   
        self.verbose_msg(f"delete_row(): deleted server = {server} cursor.rowcount = {cursor.rowcount}")  
        print(f"Removed server {server}")
    except mariadb.Error as e:
      print(f"Error deleting row in table 'servers': {e}")
      conn.close()                         # close connection
      return 1       
    conn.commit()                          # commit changes
    cursor.close()                         # close cursor
    conn.close()                           # close connection
  
  def describe_table(self):
    """
    Describe the 'server' table
    """
    conn = self.connect_db()               # open connection
    cursor = conn.cursor()                 # open cursor
    try:   
      cursor.execute(self.use_cmd)         # use cmdb
      self.verbose_msg("describe_table(): changed database to 'cmdb'")
    except mariadb.Error as e:
      print(f"ERROR changing database to 'cmdb': {e}")
      conn.close()                         # cannot contiue
      return 1
    try:   
      cursor.execute(self.describe_cmd)    # describe the table
      rows = cursor.fetchall()
      print("Table servers:")
      print("Field,Type,Null,Key,Default,Extra")
      print("---------------------------------")
      for i in rows:
        print(*i, sep=',') 
    except mariadb.Error as e:
      print(f"WARNING - describe_table(): Exception searching database: {e}")
      conn.close()                         # cannot contiue
      return 1
    conn.close()                           # close connection  

  def run_command(self):
    """
    Run the command passed in
    """
    rc = 0                                 # assume success
    self.verbose_msg(f"run_command(): command = {self.args.command}")
    match self.args.command:
      case 'initialize':
        rc = self.initialize()             # ignore 2nd word if any
      case 'add':  
        rc = self.ping_server()
        if rc == 0:                        # server pings
          self.verbose_msg(f"run_command(): server pings, calling find_server")
          server_data = self.find_server()
          rc = self.replace_row(server_data)
      case 'remove':
        if self.args.server == None:       # no server name specified
          print("ERROR: Option '--server SERVER' must be specified with command 'remove'")
          return 1
        rc = self.delete_row()  
      case "query":
        rc = self.query_cmdb()
      case "describe":
        rc = self.describe_table()
      case _:
        print(f"ERROR: unrecognized command {self.args.command}")  
        rc = 1
    exit(rc)    

# main()
mariacmdb = Mariacmdb()                    # create a singleton
mariacmdb.run_command()                    # do the work
