In order to import the SQL dump via phpMyAdmin / UploadDir, 
the dump has been split in several files.
The files 'zweig_part_*' contain the structural information for all
tables and data for all tables but 'zweig_texte'.
The files 'zt_*' contain the data in 'zweig_texte'.
Thus, you need to import the 'zweig_part*' files first and then 
the 'zt*' files, both in numerical order.

