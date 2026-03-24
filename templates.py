# templates.py

# Импортируем все переменные из новых файлов
from tpl_admin_base import *
from tpl_admin_panels import *
from tpl_client_qr import *
from tpl_client_web import *

# Этот файл (templates.py) теперь служит точкой входа (агрегатором),
# чтобы не менять импорты в main.py и других файлах.