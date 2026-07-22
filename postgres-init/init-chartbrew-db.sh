#!/bin/bash
# 创建 Chartbrew 数据库
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE chartbrew_db;
    GRANT ALL PRIVILEGES ON DATABASE chartbrew_db TO $POSTGRES_USER;
EOSQL

echo "Chartbrew database created successfully"
