from flask import Flask
from flask_session import Session
import os, logging, pdb

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.logger.setLevel(logging.INFO)

app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)

from app.errors import blueprint as errors_bp

app.register_blueprint(errors_bp)

from app import routes

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

