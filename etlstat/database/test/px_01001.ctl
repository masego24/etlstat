LOAD DATA
CHARACTERSET UTF8
INFILE './px_01001.dat'
TRUNCATE
INTO TABLE test.px_01001
FIELDS TERMINATED BY ';' OPTIONALLY ENCLOSED BY '"'
TRAILING NULLCOLS
(id,tipo_indicador,nivel_educativo,valor)