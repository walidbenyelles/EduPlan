from flask import Flask, render_template
from extensions import db, csrf


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'etuplan-secret-key-2024'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    csrf.init_app(app)

    from routes.admin import admin_bp
    from routes.views import views_bp

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(views_bp, url_prefix='/view')

    @app.route('/')
    def portal():
        return render_template('portal.html')

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
