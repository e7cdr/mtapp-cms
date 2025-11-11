import os
# import sys

# Activate virtual environment
# activate_this = '/home/MILANOTRAVEL/.virtualenvs/mtapp-cms-env/bin/activate_this.py'
# with open(activate_this) as file_:
#     exec(file_.read(), dict(__file__=activate_this))


# # Project path
# path = '/home/MILANOTRAVEL/mtapp-cms/mtapp-cms'
# if path not in sys.path:
#     sys.path.append(path)

# Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'mtapp.settings.dev'

# Import and create WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()