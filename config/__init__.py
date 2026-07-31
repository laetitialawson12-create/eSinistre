import pymysql
pymysql.install_as_MySQLdb()

from django.db.backends.mysql.base import DatabaseWrapper

# Désactive la vérification de version MariaDB
DatabaseWrapper.check_database_version_supported = lambda self: None

# Modification ciblée de la classe des fonctionnalités MySQL/MariaDB
from django.db.backends.mysql.features import DatabaseFeatures
DatabaseFeatures.can_return_columns_from_insert = False
DatabaseFeatures.can_return_rows_from_bulk_insert = False