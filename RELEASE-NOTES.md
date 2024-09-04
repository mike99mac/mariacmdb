# Release notes
Following are the release notes of this ``mariacmdb`` repository.

The version numbers are simply *yy.mm.dd*.

### Version 24.09.??
- Changed name of ``mariacmdb.py`` to ``mariacmdb``
- Added script ``vif`` - a reanimation of the IBM product from 2000 
-

### Version 24.08.21
- Added inline editing of 3 metadata columns in ``finder.py``
- Added an **Update all servers** button in finder
- Added update operation to ``restapi.py``
- In ``mariacmdb.py`` add function uses ``INSERT`` and update uses ``UPDATE`` rather than both using ``REPLACE``

### Version 24.07.02
- Add columns ``arch_com, app, grp, owner, last_ping`` to table ``servers``
- Update ``serverinfo`` to return values for new columns
- Add ``/srv/www/mariacmdb/finder.py`` to create a search GUI 
- The code is still *beta* (but somewhat beta than the last version :)) 

### Version 24.06.17
- Many updates to get code in sync VM Workshop presentation 6/22/24 

### Version 24.06.09
- Incremental release - consider the code *beta*
- Added ``update`` subcommand to ``mariacmdb.py`` line command
- Updated README to describe all line subcommands

### Version 24.05.06
- Initial release - consider the code *alpha*

