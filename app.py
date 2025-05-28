
from flask import Flask
from routes.webhook_routes import webhook_bp
from routes.view_routes import view_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp)
app.register_blueprint(view_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
