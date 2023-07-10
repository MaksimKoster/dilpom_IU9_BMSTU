import clickhouse_connect

create_database_sql = """
CREATE DATABASE IF NOT EXISTS security_db COMMENT 'diplom';

CREATE TABLE security_db.detection
(
    `camera_id` String,
    `people`  String,
    `photo_url` String,
    `time_detect` DateTime
)
ENGINE = MergeTree
PRIMARY KEY (camera_id, time_detect);
"""


def bd_commands():
    client = clickhouse_connect.get_client(host='92.53.105.143', port='18123', user='default', password= '')
    #client.command('DROP TABLE IF EXISTS pandas_example')

    #client.command('CREATE USER maks IDENTIFIED WITH plaintext_password BY \'maks\'')

    '''res = client.command('CREATE USER IF NOT EXISTS maksim IDENTIFIED WITH sha256_password BY \'maksim\';')
    print(res)

    res = client.command('GRANT ALL ON *.* TO maksim WITH GRANT OPTION;')
    print(res)'''

    #client.command('CREATE USER IF NOT EXISTS maks IDENTIFIED WITH PLAINTEXT_PASSWORD BY \'maks\'')
    client.command(create_database_sql)


if __name__ == '__main__':
    bd_commands()
