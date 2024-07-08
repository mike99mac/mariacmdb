#!/usr/bin/python3
import subprocess
import sys
from tabulate import tabulate

class Finder:
  def __init__(self):
    """
    Initialize globals, create page header, set background
    """
    self.pattern = ""                      # search pattern
    self.rows = []                         # resulting rows
    self.headers = ['Host name', 'IP address', 'CPUs', 'Memory', 'Architecture', 'Common arch', 'OS', 'OS version', 'Kernel ver', 'Kernel rel', 'Root fs full', 'App', 'Group', 'Owner', 'Last ping', 'Created']

    # start the HTML page
    print('Content-Type: text/html')
    print()
    print('<!DOCTYPE html>')  
    print('<html><head>')
    print('  <link rel="stylesheet" href="/finder.css">')  # Cascading style sheets
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
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    rc = proc.returncode
    self.rows = []
    if rc != 2:                            # data found
      for next_row in proc.stdout.split("\n"):
        list_row = next_row.split(",")
        self.rows.append(list_row)         # add list to list of rows

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
    self.search_cmdb()                     # do search

    # show the search pattern text box and submit button
    print('<form action="/finder.py" method="get" enctype="multipart/form-data">')
    print('  Search pattern: <input maxlength="60" size="60" value="" name="pattern">')
    print('  <input value="Submit" type="submit">')
    print('</form><br>')

    # show the current search pattern if one exists
    if self.pattern != "":                 # there is a current search pattern
      print(f"Current search pattern: {self.pattern}<br><br>") 
    print(tabulate(self.rows, self.headers, tablefmt='html'))
    print('</body></html>')                # end page

# main()
finder = Finder()                          # create a singleton
# finder.print_env() 
finder.process_query()                     # process the request
