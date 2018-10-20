from flask import Blueprint

Api = Blueprint('TPages', __name__, static_folder='./static', subdomain='api', template_folder='./templates')
