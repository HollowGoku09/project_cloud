import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.server import WebBIHandler

class handler(WebBIHandler):
    """
    Vercel Serverless Function Handler.
    Inherits from WebBIHandler to handle all /api/* endpoints in serverless context.
    """
    pass
