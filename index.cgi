#!/home/mizy/www/insta-dl/venv/bin/python3
import os
import sys

# Set execution path
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
sys.path.insert(0, current_dir)

# Add bin to path
os.environ["PATH"] = os.path.join(current_dir, "bin") + os.pathsep + os.environ["PATH"]

try:
    from a2wsgi import ASGIMiddleware
    from wsgiref.handlers import CGIHandler
    from main import app

    # Manually sanitize environment for subdirectory deployment
    script_name = os.environ.get('SCRIPT_NAME', '')
    path_info = os.environ.get('PATH_INFO', '')

    # Strip index.cgi from script name for clean routing
    if 'index.cgi' in script_name:
        os.environ['SCRIPT_NAME'] = script_name.split('index.cgi')[0].rstrip('/')
    
    # Ensure PATH_INFO starts with / and reflects the actual sub-path
    if not path_info or path_info == '':
        os.environ['PATH_INFO'] = '/'

    # Wrap and run
    wsgi_app = ASGIMiddleware(app)
    CGIHandler().run(wsgi_app)

except Exception as e:
    print("Content-Type: text/plain; charset=utf-8\n")
    import traceback
    print("CGI Execution Error:")
    print(traceback.format_exc())
