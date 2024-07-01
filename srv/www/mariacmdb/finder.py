#!/usr/bin/python3
import subprocess
import sys
from tabulate import tabulate

class Finder:
  def __init__(self):
    """
    Initialize globals, create page header
    """
    self.pattern = ""                      # search pattern
    self.rows = []                         # resulting rows
    print('Content-Type: text/html')
    print()
    print('<!DOCTYPE html>')  
    print('<html><head>')
    print('  <link rel="stylesheet" href="/finder.css">')
    print('</head>')

    # add subtle background of Ukrainian flag to page body
    print('<body style="background-image: url(/ukr_flag_bg.png); background-repeat: no-repeat; background-size: cover; background-position: center; height: 100vh;">')

  def print_env(self):
    """
    Show all environment variables with the 'env' command
    """
    proc = subprocess.run("env", shell=True, capture_output=True, text=True)
    rc = proc.returncode
    env_vars = []
    env_vars = proc.stdout
    print('<pre>')
    for line in env_vars.split("\n"):
      print(str(line))
    print('</pre>')
    print()

  def search_cmdb(self):
    """
    Search mariacmdb for the specified pattern
    """
    cmd = "/usr/local/sbin/mariacmdb.py query"
    if self.pattern != "":                 # search pattern specified
      cmd = f"{cmd} -p {self.pattern}"     # add -p flag
    print(f"running cmd: {cmd}<br>")
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    rc = proc.returncode
    if rc == 2:                            # no hits
      self.rows = []
    else:  
      self.rows = proc.stdout
    print(f"Finder.search_cmdb() rc: {rc} rows: {self.rows}<br>")

  def process_query(self):
    """
    Perform operation specified in env var QUERY_STRING
    """
    print('<h1>Finder search</h1>')
    proc = subprocess.run("echo $QUERY_STRING", shell=True, capture_output=True, text=True)
    rc = proc.returncode
    if rc != 0:
      print(f"Finder.process_query(): subprocess.run('echo $REQUEST_URI' returned {rc}")
      return 1
    ptrn = []
    ptrn = proc.stdout                     # get value
    ptrn = ptrn.split("=")
    ptrn_len = len(ptrn)
    if ptrn_len < 2:                       # no search pattern supplied
      self.pattern = ""                    # search for all
    else: 
      self.pattern = str(ptrn[1])
    self.rows = list(self.search_cmdb())
    rows_type = type(self.rows)
    print("rocess_query(): type(self.rows)")
    print('<form action="/finder.py" method="get" enctype="multipart/form-data">')
    print('  Search pattern: <input maxlength="60" size="60" value="" name="pattern">')
    print('  <input value="Submit" type="submit">')
    print('</form>')
    print('<br>') 
    table = [['one','two','three'],['four','five','six'],['seven','eight','nine']]
    print(tabulate(table, tablefmt='html'))
    print("<br>")
    # print(tabulate(self.rows, tablefmt='html'))
    print('</body></html>')                # end page

# main()
finder = Finder()                          # create a singleton
# finder.print_env() 
finder.process_query()                     # process the request
