from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# HEALTH
######################################################################


@app.route('/health', methods=['GET'])
def health():
    return jsonify(dict(Status='OK')), 200


######################################################################
# COUNT
######################################################################


@app.route('/count', methods=['GET'])
def count():
    count = db.songs.count_documents({})

    return jsonify({'Count': count}), 200


######################################################################
# SONGS
######################################################################


@app.route('/song')
def songs():
    songs = list(db.songs.find({}))

    return jsonify({'Songs': parse_json(songs)}), 200


######################################################################
# GET SONG/ID
######################################################################


@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    song = db.songs.find_one({'id': id})
    if not song:
        return jsonify({'Message': f'Song with ID {id} not found'}), 404
    
    return parse_json(song), 200


######################################################################
# POST SONG
######################################################################


@app.route('/song', methods=['POST'])
def create_song():
    posted_song = request.json

    song = db.songs.find_one({'id': posted_song['id']})
    if song:
        return jsonify({
            'Message': f"Song with ID {posted_song['id']} already present"
        }), 302

    insert_id: InsertOneResult = db.songs.insert_one(posted_song)

    return jsonify({'Inserted ID': parse_json(insert_id.inserted_id)}), 201


######################################################################
# UPDATE SONG/ID
######################################################################


@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    inserted_song = request.json

    song = db.songs.find_one({'id': id})

    if song == None:
        return jsonify({'Message': 'Song not found'}), 400

    updated_data = {'$set': inserted_song}
    result = db.songs.update_one({'id': id}, updated_data)

    if result.modified_count == 0:
        return jsonify({'Message': 'Song found, but nothing updated'})
    else:
        return parse_json(db.songs.find_one({'id': id})), 201


######################################################################
# DELETE SONG/ID
######################################################################


@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    songs_left = db.songs.delete_one({'id': id})
    
    if songs_left.deleted_count == 0:
        return jsonify({'Message': 'Song not found'}), 404
    else:
        return jsonify({}), 204
    