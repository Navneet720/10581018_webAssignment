
import datetime
from multiprocessing.sharedctypes import Value
import google.oauth2.id_token
import random
from google.cloud import datastore, storage
from flask import Flask, render_template, request, redirect, session, url_for
from google.auth.transport import requests

app = Flask(__name__)
datastore_client = datastore.Client()
firebase_request_adapter = requests.Request()

######################### Create and Retrieve UserInfo #########################
def createUserInfo(claims, username):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore.Entity(key = entity_key)
    if "name" in claims.keys():
        ssName = claims["name"]
    else:
        ssName = claims["email"]
    entity.update({
        'email': claims['email'],
        'name': ssName,
        'bio': "",
        'username': username,
        'follower_list': [],
        'following_list': [],
        'tweet_list': []
    })
    datastore_client.put(entity)

def retrieveUserInfo(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore_client.get(entity_key)
    return entity

####################### Create and Retrieve Tweets ###########################
#Create Tweet Objects
def createTweet(claims, tweet, username, url):
    # 63 bit random number that will serve as the key for this board object.
    id = random.getrandbits(63)
    entity_key = datastore_client.key('Tweet', id)
    entity = datastore.Entity(key = entity_key)
    entity.update({
        'tweet': tweet,
        'time': datetime.datetime.now(),
        'username': username,
        'media': url
    })
    datastore_client.put(entity)
    return id

def addTweetToUser(user_info, tweet_id):
    tweet_keys = user_info['tweet_list']
    tweet_keys.append(tweet_id)
    user_info.update({
        'tweet_list': tweet_keys
    })
    datastore_client.put(user_info)
    
#Retrieve Tweets Objects
def retrieveTweets(user_info):
    #make key objects out of all the keys and retrieve them
    tweet_id = user_info['tweet_list']
    tweet_keys = []
    for i in range(len(tweet_id)):
        tweet_keys.append(datastore_client.key('Tweet', tweet_id[i]))
    tweet_list = datastore_client.get_multi(tweet_keys)
    return tweet_list

def retrieveFeed(user_info):
    #make key objects out of all the keys and retrieve them
    following_id = user_info['following_list']
    following_keys = []
    for i in range(len(following_id)):
        following_keys.append(datastore_client.key('UserInfo', following_id[i]))
    following_list = datastore_client.get_multi(following_keys)
    feed = []
    for user in following_list:
        tweets = retrieveTweets(user)
        for tweet in tweets:
            feed.append(tweet)
    tweets = retrieveTweets(user_info)
    for tweet in tweets:
        feed.append(tweet)
    feed.sort(key=lambda x: x['time'], reverse=True)
    feed = feed[0:50]
    return feed

def userFollowed(user_following, user_followed):
    following_keys = user_following['following_list']
    following_keys.append(user_followed['email'])
    user_following.update({
        'following_list': following_keys
    })
    datastore_client.put(user_following)
    
    followed_keys = user_followed['follower_list']
    followed_keys.append(user_following['email'])
    user_followed.update({
        'follower_list': followed_keys
    })
    datastore_client.put(user_followed)

def userUnFollowed(user_following, user_followed):
    following_keys = user_following['following_list']
    following_keys.remove(user_followed['email'])
    user_following.update({
        'following_list': following_keys
    })
    datastore_client.put(user_following)
    
    followed_keys = user_followed['follower_list']
    followed_keys.remove(user_following['email'])
    user_followed.update({
        'follower_list': followed_keys
    })
    datastore_client.put(user_followed)

######################### Delete Tweet ########################
def deleteTweet(tweet_id, user_info):
    tweet_key = datastore_client.key('Tweet', tweet_id)
    datastore_client.delete(tweet_key)
    
    tweet_list = user_info['tweet_list']
    tweet_list.remove(tweet_id)
    user_info.update({
        'tweet_list' : tweet_list
    })
    datastore_client.put(user_info)

def addFile(file):
    storage_client = storage.Client(project='My First Project')
    bucket = storage_client.bucket('divine-tempo-341205.appspot.com')
    blob = bucket.blob(file.filename)
    #blob.upload_from_file(file)
    blob.upload_from_string( file.read(), content_type= "image/jpeg")
    blob.make_public()
    url = blob.public_url
    return url
   
################################################################################
################################## App Routes ##################################
################################################################################

@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit_tweet(id):
    id_token = request.cookies.get("token")
    error_message=None
    claims=None
    tweet = None
    if request.method == 'GET':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                        id_token, firebase_request_adapter)
                user_info = retrieveUserInfo(claims)
                entity_key = datastore_client.key("Tweet", id)
                tweet = datastore_client.get(entity_key)
            except ValueError as exc:
                error_message = str(exc)
        return render_template('edit.html', user_data=claims, error_message=error_message, user_info=user_info, tweet=tweet)
    else:
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                        id_token, firebase_request_adapter)
                entity_key = datastore_client.key('Tweet', id)
                entity = datastore_client.get(entity_key)
                
                file = request.files['file_name']
                if file.filename == '':
                    url = None
                elif file.filename.split(".")[1:] == ['jpg'] or file.filename.split(".")[1:] == ['jpeg'] or file.filename.split(".")[1:] == ['png']:
                    url = addFile(file)
                else:
                    url = None
                entity.update({
                    'tweet': request.form['tweet'],
                    'time': datetime.datetime.now(),
                    'media': url
                })
                datastore_client.put(entity)
            except ValueError as exc:
                error_message = str(exc)
        return redirect('/')

@app.route('/delete/<int:id>', methods=['GET','POST'])
def delete_tweet(id):
    id_token = request.cookies.get("token")
    error_message=None
    claims=None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            deleteTweet(id, user_info)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')
    
@app.route('/unfollow/<email>', methods=['POST'])
def unfollow(email):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    current_user = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
                
            entity_key = datastore_client.key('UserInfo', email)
            current_user = datastore_client.get(entity_key)
                
            userUnFollowed(user_info, current_user)
        except ValueError as exc:
            error_message = str(exc)
    return redirect(url_for('user_info', email=email))

@app.route('/follow/<email>', methods=['POST'])
def follow(email):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    current_user = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
                
            entity_key = datastore_client.key('UserInfo', email)
            current_user = datastore_client.get(entity_key)
                
            userFollowed(user_info, current_user)
        except ValueError as exc:
            error_message = str(exc)
    return redirect(url_for('user_info', email=email))

@app.route('/user/<email>', methods=['GET','POST'])
def user_info(email):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    current_user = None
    tweets = None
    if request.method == 'GET':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
                user_info = retrieveUserInfo(claims)
            
                entity_key = datastore_client.key('UserInfo', email)
                current_user = datastore_client.get(entity_key)
            
                tweets = retrieveTweets(retrieveUserInfo(current_user))
                tweets.sort(key=lambda x: x['time'], reverse=True)
                tweets = tweets[0:50]
            except ValueError as exc:
                error_message = str(exc)
        return render_template('user_info.html', user_data=claims, error_message=error_message, user_info=user_info,
                            current_user=current_user, tweets=tweets)
       

@app.route('/search', methods=['POST'])
def search():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    users = []
    tweets = []
    search = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            
            query = datastore_client.query(kind= "UserInfo")
            results = list(query.fetch())
            for user in results:
                if request.form['search'].lower() in user['username'].lower():
                    users.append(user)
            users = list(users)
            
            query1 = datastore_client.query(kind= "Tweet")
            results1 = list(query1.fetch())
            for tweet in results1:
                if request.form['search'].lower() in tweet['tweet'].lower():
                    tweets.append(tweet)
            tweets = list(tweets)
            
        except ValueError as exc:
            error_message = str(exc)
    return render_template('search.html', user_data=claims, error_message=error_message, user_info=user_info, users=users, 
                           tweets=tweets, search=request.form['search'])
    
@app.route('/profile', methods=['GET','POST'])
def profile():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    tweets = None
    if request.method == 'POST':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
                entity_key = datastore_client.key('UserInfo', claims['email'])
                entity = datastore_client.get(entity_key)
                entity.update({
                    'name': request.form['name'],
                    'bio': request.form['bio']
                })
                datastore_client.put(entity) 
            except ValueError as exc:
                error_message = str(exc)
        return redirect(url_for('profile'))
    else:
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
                user_info = retrieveUserInfo(claims)
                tweets = retrieveTweets(user_info)
                
            except ValueError as exc:
                error_message = str(exc)
        return render_template('profile.html', user_data=claims, error_message=error_message, user_info=user_info, tweets=tweets)
    
@app.route('/username', methods=['GET','POST'])
def username():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    if request.method == 'POST':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
                createUserInfo(claims, request.form['username'])
                user_info = retrieveUserInfo(claims)
            except ValueError as exc:
                error_message = str(exc)
        return redirect(url_for('root'))
    else:
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
            except ValueError as exc:
                error_message = str(exc)
        return render_template('username.html')

@app.route('/', methods=['GET', 'POST'])
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    tweets = None
    if request.method == 'GET':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
                user_info = retrieveUserInfo(claims)
                if user_info == None:
                    return redirect(url_for("username"))
                tweets = retrieveFeed(user_info)
                
            except ValueError as exc:
                error_message = str(exc)
        return render_template('main.html', user_data=claims, error_message=error_message, user_info=user_info, tweets=tweets)
    else:
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
                user_info = retrieveUserInfo(claims)
                
                file = request.files['file_name']
                if file.filename == '':
                    url = None
                elif file.filename.split(".")[1:] == ['jpg'] or file.filename.split(".")[1:] == ['jpeg'] or file.filename.split(".")[1:] == ['png']:
                    url = addFile(file)
                else:
                    url = None
                tweet_id = createTweet(claims, request.form['tweet'], user_info['username'], url)
                addTweetToUser(user_info, tweet_id)
            except ValueError as exc:
                error_message = str(exc)
        return redirect(url_for('root'))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
