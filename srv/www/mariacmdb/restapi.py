#!/usr/bin/python3
import sys
#sys.path.insert(0, "/home/pi/.local/lib/python3.10/site-packages")
import mariadb
import os
import subprocess

def print_env():
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

def query_cmdb():
  """
  Search CMDB for specified pattern or return entire database
  """
  try:
    query_string = os.environ['QUERY_STRING']
  except:
    print("Unexpected ERROR: environment variable 'QUERY_STRING' is not set")
    return 1
  # print(f"query_string = {query_string}<br>") 
  if query_string == "":                   # no qualifiers passed
    cmd = "SELECT * FROM servers;"
  else:                                    # process qualifiers
    query_string = query_string.split('&') # split out each qualifier
    num_args = len(query_string)
    for arg_num in range(num_args):
      if arg_num == 0:                     # first qualifier
        where_clause = query_string[0]
      else:
        where_clause = f"{where_clause} AND {query_string[arg_num]}"
    cmd = f"SELECT * FROM servers WHERE {where_clause};"
  # print(f"cmd = {cmd}")
  conn = mariadb.connect(user="root", password="pi", host="127.0.0.1", database="mysql")
  cursor = conn.cursor()                   # open cursor
  try:   
    cursor.execute("use cmdb")             # use cmdb
  except mariadb.Error as e:
    print(f"ERROR changing database to 'cmdb': {e}")
    print("</body></html>")
    conn.close()                           # cannot contiue
    exit(1)
  rows = ""  
  try:   
    cursor.execute(cmd)                    # query the cmdb
    rows = cursor.fetchall()
    if rows == []:
      print("No records found")
    else:                                  # print rows
      print("<pre>")
      for i in rows:
        print(*i, sep=',') 
      print("</pre>")
  except mariadb.Error as e:
    print(f"WARNING - query_cmdb(): Exception searching database: {e}")

# main
print("Content-Type: text/html")
print()
print("<html><head>")
print("</head><body>")
print("<h1>This is the mariacmdb RESTful API!</h1>")
# print_env()                              # show output of 'env' command
rc = query_cmdb()                               # do the work
print("</body></html>")
exit(rc)
