from flask import Flask
from .routes.ai_routes import ai_bp
from .routes.system_routes import system_bp

app = Flask(__name__)

app.register_blueprint(ai_bp)
app.register_blueprint(system_bp)

@app.route('/')
def hello_world():
    return 'Hello, Sentinel!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)