import os

import flask
from redis import Redis

from bytebin import models


PROJECT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bytebin')


def create_app():
    import bytebin.view.paste

    app = flask.Flask(__name__)
    app.debug = bool(os.getenv('DEBUG', False))
    app.template_folder = os.path.join(PROJECT_DIR, 'templates')

    redis = Redis(db=int(os.getenv('REDIS_DATABSE', 3)))
    models.Paste.set_connection(redis)

    app.register_blueprint(bytebin.view.paste.app)

    return app


app = create_app()


@app.errorhandler(404)
@app.errorhandler(models.NotFound)
def page_not_found(e):
    return "Page not found", 404


if __name__ == "__main__":
    app.run()
