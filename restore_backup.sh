
# 备份恢复脚本
 

#!/bin/bash

set -e

# 参数校验
if [ $# -ne 1 ]; then
    echo "用法: ./restore_backup.sh YYYYMMDD"
    exit 1
fi

DATE=$1
BACKUP_FILE="./backups/db_backup_${DATE}.dump.gz"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "找不到备份文件: $BACKUP_FILE"
    exit 1
fi

echo "解压并恢复备份文件: $BACKUP_FILE"

docker exec -i $(docker ps -qf "name=db") sh -c "
    gunzip -c /backups/db_backup_${DATE}.dump.gz | pg_restore -U \$POSTGRES_USER -d \$POSTGRES_DB
"

echo "恢复完成。"


# 使用前请运行 `chmod +x restore_backup.sh` 赋予脚本执行权限。

