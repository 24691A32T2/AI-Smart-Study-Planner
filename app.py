import os, sys
from flask import Flask, render_template
import database
from routes import auth, main

def create_app(db_path=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-change-me'),
                      DATABASE=db_path or os.path.join(app.instance_path, 'planner.db'))
    database.init_db(app)
    app.teardown_appcontext(database.close_db)
    app.register_blueprint(auth.bp); app.register_blueprint(main.bp)
    @app.errorhandler(404)
    def nf(e): return render_template('error.html', msg='Page not found'), 404
    @app.errorhandler(500)
    def err(e): return render_template('error.html', msg='Something went wrong'), 500
    return app

if __name__ == '__main__':
    app = create_app()
    if '--seed' in sys.argv: database.seed_demo(app)
    else: app.run(debug=True)
