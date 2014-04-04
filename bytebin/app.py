import uuid

import flask
import redis


app = flask.Flask(__name__)
app.redis = redis.Redis()


@app.route("/", methods=["GET"])
def index():
    return flask.render_template('index.html')


@app.route("/", methods=["POST"])
def create_page():
    data = flask.request.form.get('data', None)
    if not data:
        flask.abort(400)

    try:
        timeout = int(flask.request.form.get('timeout', 60 * 60))
    except (ValueError, TypeError):
        return 'invalid "timeout" value', 400
    if timeout < 1:
        return 'timeout has to be greater than 0', 400

    while True:
        key = str(uuid.uuid4())
        if app.redis.set(key, data, nx=True, ex=timeout):
            break

    return flask.render_template('set_success.html', key=key)


@app.route("/<key>", methods=["GET"])
def fetch_page(key):
    data = app.redis.get(key)
    if data is None:
        flask.abort(404)
    return data


@app.route("/<key>", methods=["PUT"])
def change_page(key):
    data = flask.request.form.get('data', None)
    if not data:
        flask.abort(400)
    if not app.redis.set(key, data, xx=True):
        flask.abort(404)
    return flask.render_template('set_success.html', key=key)



if __name__ == "__main__":
    app.run(debug=True)
