# coding: utf-8
"""
    MySQL

    Date:
        24/01/2018

    Author:
        slave110

    Version:
        Alpha

    Notes:


"""

import numpy as np
import os
from pandas import DataFrame, notnull
import re
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.exc import DatabaseError


class MySQL:

    engine = None
    # TODO: check this conversion map
    conversion_map = {
        'object': 'VARCHAR(255)',
        'int64': 'INT',
        'float32': 'DECIMAL(20,6)',
        'float64': 'DECIMAL(20,6)'
    }

    @classmethod
    def _connect(cls, user, password, host, port, database):
        cls.conn_string = "mysql+mysqlconnector://{0}:{1}@{2}:{3}/{4}".format(
            user,
            password,
            host,
            port,
            database)
        cls.engine = create_engine(cls.conn_string)

    @classmethod
    def execute_sql(cls, sql, user, password, host, port, database):
        """
        Executes a DDL or DML SQL statement
        :param sql: SQL statement
        :param user: database user
        :param password: database password
        :param host: host name or IP address
        :param port: database connection port
        :param database: database name
        :return: status (True | False); result (str or data frame)
        """
        cls._connect(user, password, host, port, database)
        connection = cls.engine.connect()
        try:
            result = connection.execute(sql)
            status = True
            if re.match('^[ ]*SELECT .*', sql, re.IGNORECASE):
                rows = result.fetchall()
                result = DataFrame(rows, columns=result.keys())
        except DatabaseError as e:
            result = e
            status = False
        finally:
            connection.close()
        return status, result

    @classmethod
    def create(cls, table, user, password, host, port, database):
        """
        Create a new table in database from DataFrame format.

        :param table: DataFrame which name and column's label match with database
        table's name and columns that you wish to create.
        :param user: database user
        :param password: database password
        :param host: host name or IP address
        :param port: database connection port
        :param database: database name
        """
        cls._connect(user, password, host, port, database)
        connection = cls.engine.connect()

        if not cls.check_for_table(table.name, user, password, host, port, database):
            sql = "CREATE TABLE"

            if isinstance(table, DataFrame):
                sql += " `{0}` (".format(table.name)

                for label in table:
                    sql += "`{0}` {1}, ".format(label, cls.conversion_map[str(table[label].dtype)])
                sql = sql[:-2] + ')'

                rts = connection.execute(sql)
                rts.close()
                connection.close()

                # meta = MetaData()

                # messages = Table(table.name, meta, autoload=True, autoload_with=cls.engine)
                # rts_columns = [c.name for c in messages.columns]
                #
                # if len(set(list(table.columns.values)) & set(rts_columns)) == len(table.columns):
                #     return True
                #
                # #print(rts.keys())
                # if rts.returns_rows:
                #     print(rts.rowcount)

        return False

    @classmethod
    def select(cls, table, user, password, host, port, database, conditions=''):
        """
        Select data from table.

        :param table: (:obj:`str` or :obj:`DataFrame`): Table's name in database if
                    you want read all fields in database table or a DataFrame
                    which name and column's label match with table's name and
                    columns table that you want read from database.
        :param user: database user
        :param password: database password
        :param host: host name or IP address
        :param port: database connection port
        :param database: database name
        :param conditions: (:obj:`str` or :obj:`list` of :obj:`str`, optional):
                    A select condition or list of select conditions with sql
                    syntax.
        Returns:
            :obj:`DataFrame`: A DataFrame with data from database.

        """
        cls._connect(user, password, host, port, database)
        connection = cls.engine.connect()

        df = None
        sql = "SELECT"
        if isinstance(table, str):
            sql += " {0} FROM `{1}`".format('*', table)
        elif isinstance(table, DataFrame):
            for label in list(table):
                sql += " {0},".format(label)

            sql = sql[:-1]
            sql += " FROM `{0}`".format(table.name)
        else:
            raise TypeError("table must be a string or DataFrame.")

        if isinstance(conditions, str) and conditions is not '':
            sql += " WHERE {0}".format(conditions)
        elif isinstance(conditions, list) and len(conditions) > 0:
            sql += " WHERE"
            for condition in conditions:
                sql += " {0},".format(condition)
            sql = sql[:-1]

        rts = connection.execute(sql)   # ResultProxy

        if rts.rowcount > 0:
            df = DataFrame(rts.fetchall())
            df.columns = rts.keys()

        rts.close()
        connection.close()

        return df

    @classmethod
    def insert(cls, table, user, password, host, port, database, rows=None):
        """
        Insert DataFrame's rows in a database table.

        :param table: (:obj:`DataFrame`): DataFrame which name and column's label
                    match with table's name and column's name in database. It
                    must filled with data rows.
        :param user: database user
        :param password: database password
        :param host: host name or IP address
        :param port: database connection port
        :param database: database name
        :param rows: (:obj:`list` of int, optional): A list of row's indexes that you
                    want insert to database.
        Returns:
            int: number of rows matched.
        """
        rows_matched = 0

        cls._connect(user, password, host, port, database)
        connection = cls.engine.connect()

        if isinstance(table, DataFrame):
            if not cls.check_for_table(table.name):
                cls.create(table)

            sql = "INSERT INTO"
            sql += " `{0}`".format(table.name)
            sql += ' ('
            for label in list(table):
                sql += "{0}, ".format(label)
            sql = sql[:-2]
            sql += ')'

            for index, row in table.iterrows():

                if rows is None or index in rows:
                    sql_insert = sql
                    sql_insert += " VALUES ("
                    for value in row:
                        if isinstance(value, str):
                            sql_insert += "'{0}', ".format(value)
                        else:
                            if np.isnan(value):
                                sql_insert += "{0}, ".format('NULL')
                            else:
                                sql_insert += "{0}, ".format(value)
                    sql_insert = sql_insert[:-2] + ')'

                    rts = connection.execute(sql_insert)  # ResultProxy

                    rows_matched += rts.rowcount

                    rts.close()
                    connection.close()
        else:
            raise TypeError("table must be a DataFrame.")

        return rows_matched

    @classmethod
    def update(cls, table, user, password, host, port, database, index=None):
        """
        Update rows in a database table.

        :param table: (:obj:`DataFrame`): DataFrame which name and column's label
                    match with table's name and columns name in database. It must
                    filled with data rows.
        :param user: database user
        :param password: database password
        :param host: host name or IP address
        :param port: database connection port
        :param database: database name
        :param index: (:obj:`list` of name columns): list of DataFrame's columns names
                    use as index in the update search. Other columns will be
                    updated in database.
        Returns:
            int: number of rows matched.
        """
        rows_matched = 0

        cls._connect(user, password, host, port, database)
        connection = cls.engine.connect()

        if isinstance(table, DataFrame):
            if isinstance(index, list):
                for row in table.values:
                    sql = "UPDATE `{0}` SET".format(table.name)
                    sql_conditions = ''
                    sql_updates = ''
                    for id, label in enumerate(table):
                        if label not in index:
                            if isinstance(row[id], str):
                                sql_updates += " {0}={1},".format(label, row[id])
                            else:
                                sql_updates += " {0}={1},".format(label, row[id])
                        else:
                            if isinstance(row[id], str):
                                sql_conditions += " {0}={1} and".format(label, row[id])
                            else:
                                sql_conditions += " {0}={1} and".format(label, row[id])
                    sql += sql_updates[:-1]

                    if len(sql_conditions) > 1:
                        sql += ' WHERE' + sql_conditions[:-4]
                    rts = connection.execute(sql)  # ResultProxy

                    rows_matched += rts.rowcount

                    rts.close()
                    connection.close()
        else:
            raise TypeError("table must be a DataFrame.")

        return rows_matched

    @classmethod
    def bulk_insert(cls, table, user, password, host, port, database):
        """
        Make a bulk insert in database.

        :param table: (:obj:`DataFrame`): DataFrame which name and column's label
                    match with table's name and columns in database. It must
                    filled with data rows.
        :param user: database user
        :param password: database password
        :param host: host name or IP address
        :param port: database connection port
        :param database: database name
        Returns:
            int: number of rows matched.
        """
        rows_matched = 0
        csv_path = 'temp.csv'

        cls._connect(user, password, host, port, database)
        connection = cls.engine.connect()

        if not cls.check_for_table(table.name):
            cls.create(table)

        if isinstance(table, DataFrame):
            aux = table.replace(np.NaN, "\\N")
            aux.to_csv(csv_path, sep=';', header=False, index=False)
        else:
            raise TypeError("table must be a DataFrame.")

        sql = """LOAD DATA LOCAL INFILE '{0}' INTO TABLE `{1}` FIELDS TERMINATED BY ';' ENCLOSED BY '"' """\
              .format(csv_path, table.name)

        rts = connection.execute(sql)

        rows_matched = rts.rowcount
        rts.close()
        connection.close()

        os.remove(csv_path)

        return rows_matched

    @classmethod
    def delete(cls, table, user, password, host, port, database, conditions=''):
        """
        Delete data from table.

        Args:
        :param table: (:obj:`str`): Database table name that you wish delete rows.
        :param user: database user
        :param password: database password
        :param host: host name or IP address
        :param port: database connection port
        :param database: database name
        :param conditions: (:obj:`str`, optional): A string of select conditions
            with sql syntax.
        Returns:
            int: number of rows matched.
        """
        cls._connect(user, password, host, port, database)
        connection = cls.engine.connect()

        sql = "DELETE FROM `{0}`".format(table)

        if isinstance(conditions, str) and conditions is not '':
            sql += ' WHERE ' + conditions

        rts = connection.execute(sql)

        rows_matched = rts.rowcount

        rts.close()
        connection.close()

        return rows_matched

    @classmethod
    def check_for_table(cls, table, user, password, host, port, database):
        """
        Check if table exists in database.

        :param table: (:obj:`str`): Database table's name.
        :param user: database user
        :param password: database password
        :param host: host name or IP address
        :param port: database connection port
        :param database: database name
        Returns:
            bool: True if table exists, False in otherwise.
        """
        cls._connect(user, password, host, port, database)

        return cls.engine.dialect.has_table(cls.engine, table)
