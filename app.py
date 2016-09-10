#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import json

from pygeocoder import Geocoder
import urllib
import time as t
from time import sleep
import datetime
import copy

from flask_apscheduler import APScheduler
import requests
from flask import Flask, request

from datetime import date, datetime, timedelta
import mysql.connector

class Config(object):
    JOBS = [
        {
            'id': 'job1',
            'func': '__main__:job1',
			'args': (1, 2),
            'trigger': 'interval',
            'seconds': 30
        }
    ]

    SCHEDULER_VIEWS_ENABLED = True

def job1(a, b):
    print str(a) + ' ' + str(b)
    log('scedule method called')
    
    tweet()
	
app = Flask(__name__)
app.config.from_object(Config())
#app.debug = True

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


@app.route('/', methods=['GET'])
def verify():

    # when the endpoint is registered as a webhook, it must
    # return the 'hub.challenge' value in the query arguments

    if request.args.get('hub.mode') == 'subscribe' \
        and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') \
            == os.environ['VERIFY_TOKEN']:
            return ('Verification token mismatch', 403)
        return (request.args['hub.challenge'], 200)

    return ('Hello world', 200)


@app.route('/', methods=['POST'])
def webook():

    # endpoint for processing incoming messaging events

    

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing
    #response.end()
    if data['object'] == 'page':

        for entry in data['entry']:
            for messaging_event in entry['messaging']:

                if messaging_event.get('message'):  # someone sent us a message

                    sender_id = messaging_event['sender']['id']  # the facebook ID of the person sending you the message
                    recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
                    if 'text' in messaging_event['message']:
                        message_text = messaging_event['message']['text']  # the message's text
                        rules4messages(sender_id,message_text)
                    
                    
                    
                    #check if the user exists. if not insert a user into database
                    ChecknInsertNewUser(sender_id)
                            
                if messaging_event.get('delivery'):  # delivery confirmation
                    pass

                if messaging_event.get('optin'):  # optin confirmation
                    pass

                if messaging_event.get('postback'):  # user clicked/tapped "postback" button in earlier message
                    sender_id = messaging_event['sender']['id']
                    payload=messaging_event['postback']['payload']
                    log('sender id is ==='+ sender_id + 'payload for postback is ==='+ payload)
                    
                    handlePostback(payload,sender_id)

    return ('ok', 200)

def rules4messages(sender_id,message_text) :
    msg=message_text.upper()
    
    if msg=='UNSUBSCRIBE':
        sendList2Unsubscribe(sender_id)
        
    elif msg=='SUBSCRIBE':
        sendList2subscribe(sender_id)
        
    elif (msg=='HI') or (msg=='HELLO') or (msg=='HEY') or (msg=='START') or (msg=='HOME'):
        send_message(sender_id, 'Welcome to pokemonbot! Catching pokemons has just become easier!')
        send_message(sender_id, 'Subscribe to rare pokemons and get notification with the location of the pokemons when it is available in Paris with disappearance time as well.')
        landingCarousel(sender_id)
        
    elif msg=='MYSUBS' :
        subscriptionCount(sender_id)
        
    elif msg=='SUBS' :
        sendList2subscribe(sender_id) 
        
    elif msg=='HELP'
        send_message(sender_id, 'Type MYSUBS to check your existing subscriptions')
        send_message(sender_id, 'Type SUBS to subscribe to more pokemons')
        send_message(sender_id, 'Type START to restart the bot for you')
        
    else :
        send_message(sender_id, 'Welcome to pokemonbot! Catching pokemons has just become easier!')
        send_message(sender_id, 'Subscribe to rare pokemons and get notification with the location of the pokemons when it is available in Paris with disappearance time as well.')
        sendList2subscribe(sender_id)



def handlePostback(payload,sender_id) :

    if payload=="subscribe1" :
        pokemon_id='1'
        subscribe2pokemon(sender_id,pokemon_id)
    elif payload=="unsubscribe1" :
        pokemon_id='1'
        unsubscribe2pokemon(sender_id,pokemon_id)
    elif payload=="getmysubscriptions" :
        subscriptionCount(sender_id)
        
    elif payload =="getsubscribelist" :
        sendList2subscribe(sender_id)


def subscribe2pokemon(sender_id,pokemon_id):  # create new user
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon', password='pokemon123',
                  host='restokitch.com',
                  database='restokit_pokemon')
        cursor = cnx.cursor()
        
        getuser_fbid = "SELECT id FROM bot_users WHERE facebook_id = %s"
        cursor.execute(getuser_fbid,(sender_id,))
        result_set = cursor.fetchall()
        for row in result_set:
            #print "%s" % (row["id"])
            user_id=row[0]

        #check if this user is subscribed for this pokemon # if not, insert a new row
        check_subscription = "SELECT * FROM poke_subscribe WHERE user_id = %s and pokemon_id=%s"
        cursor.execute(check_subscription,(user_id,pokemon_id))
        msg = cursor.fetchone()
        if not msg : 
            print 'nope subscription does not exist'
            present_time = datetime.now()
            add_user = "INSERT INTO poke_subscribe(user_id,pokemon_id,datetime)VALUES (%s, %s,%s)"
            cursor.execute(add_user,(user_id,pokemon_id,present_time)) 
            message_text='You have been subscribed to this pokemon'
            send_message(sender_id,message_text)
            print('new suscription added')
        else :
            print 'subscription exists'
            message_text='You are already subscribed to this pokemon'
            send_message(sender_id,message_text)
            
        
        cursor.close()
        cnx.close()
    except mysql.connector.Error as err:
        cursor.close()
        cnx.close()
        print("Something went wrong: {}".format(err))
        

def unsubscribe2pokemon(sender_id,pokemon_id):  # create new user
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon', password='pokemon123',
                  host='restokitch.com',
                  database='restokit_pokemon')
        cursor = cnx.cursor()
        
        getuser_fbid = "SELECT id FROM bot_users WHERE facebook_id = %s"
        cursor.execute(getuser_fbid,(sender_id,))
        result_set = cursor.fetchall()
        for row in result_set:
            #print "%s" % (row["id"])
            user_id=row[0]

        #check if this user is subscribed for this pokemon # if yes, delete the row
        check_subscription = "SELECT * FROM poke_subscribe WHERE user_id = %s and pokemon_id=%s"
        cursor.execute(check_subscription,(user_id,pokemon_id))
        msg = cursor.fetchone()
        if not msg : 
            print 'nope subscription does not exist'
            message_text='Sorry but you were not subscribed to this pokemon'
            send_message(sender_id,message_text)
        else :
            add_user = "DELETE FROM poke_subscribe WHERE user_id = %s and pokemon_id=%s"
            cursor.execute(add_user,(user_id,pokemon_id)) 
            message_text='You have been unsubscribed to this pokemon'
            send_message(sender_id,message_text)
            print 'subscription deleted successfully'
            
            
        cursor.close()
        cnx.close()
    except mysql.connector.Error as err:
        cursor.close()
        cnx.close()
        print("Something went wrong: {}".format(err))
        
        
def ChecknInsertNewUser(sender_id):  # create new user
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon', password='pokemon123',
                  host='restokitch.com',
                  database='restokit_pokemon')
        cursor = cnx.cursor()
        
        check_user = "SELECT * FROM bot_users WHERE facebook_id = %s"
        cursor.execute(check_user,(sender_id,))
        msg = cursor.fetchone()
        if not msg:
            print 'nope user does not exist'
            accesstoken=os.environ['PAGE_ACCESS_TOKEN']
            r = requests.get('https://graph.facebook.com/v2.6/'+sender_id+'?access_token='+accesstoken)
            data=r.json()
            first_name=data['first_name']
            last_name=data['last_name']
            myname=first_name+' '+last_name
            print (myname)

            add_user = "INSERT INTO bot_users(name,facebook_id)VALUES (%s, %s)"
            cursor.execute(add_user,(myname,sender_id))  
                
        else:
            print 'Yeah. user already exists'
        
        cursor.close()
        cnx.close()
    except mysql.connector.Error as err:
        cursor.close()
        cnx.close()
        print("Something went wrong: {}".format(err))

        
def landingCarousel(recipient_id) :
    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    message={
        "attachment":{
          "type":"template",
          "payload":{
            "template_type":"generic",
            "elements":[
              {
                "title":"My Pokemon Subscriptions",
                "image_url":"http://cdn.bulbagarden.net/upload/thumb/9/97/Mpr_platinumscreen.jpg/350px-Mpr_platinumscreen.jpg",
                "subtitle":"Check your existing subscriptions. You may unsubscribe from any of them.",
                "buttons":[
                  {
                    "type":"postback",
                    "title":"My Subscriptions",
                    "payload":"getmysubscriptions"
                  }              
                ]
              },
              {
                "title":"Subscribe to rare pokemons",
                "image_url":"https://i.ytimg.com/vi/sSjee6FmJrM/maxresdefault.jpg",
                "subtitle":"Subscribe to more pokemons and get notifications of their location.",
                "buttons":[
                  {
                    "type":"postback",
                    "title":"Subscribe more",
                    "payload":"getsubscribelist"
                  }              
                ]
              }
            ]
          }
        }
      }
    data = json.dumps({'recipient': {'id': recipient_id},
                      'message': message})

    r = requests.post('https://graph.facebook.com/v2.6/me/messages',
                      params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)



def subscriptionCount(sender_id) :
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon', password='pokemon123',
                  host='restokitch.com',
                  database='restokit_pokemon')
        cursor = cnx.cursor()
        getuser_fbid = "SELECT id FROM bot_users WHERE facebook_id = %s"
        cursor.execute(getuser_fbid,(sender_id,))
        result_set = cursor.fetchall()
        for row in result_set:
            #print "%s" % (row["id"])
            user_id=row[0]
        
        count_pokemon = "SELECT count(*) FROM poke_subscribe WHERE user_id = %s "
        cursor.execute(count_pokemon,(user_id,))
        result_count = cursor.fetchall()
        for row in result_count:
            #print "%s" % (row["id"])
            count=row[0]
            
        message_text='You are subscribed to ' + str(count) + ' pokemons'
        send_message(sender_id,message_text)
        if count==0 :
            message_text='Get started by subscribing to few pokemons'
            send_message(sender_id,message_text)
            sendList2subscribe(sender_id)
        else:
            sendList2Unsubscribe(sender_id)
        
        cursor.close()
        cnx.close()
    except mysql.connector.Error as err:
        cursor.close()
        cnx.close()
        print("Something went wrong: {}".format(err))
        
def sendList2subscribe(recipient_id):
    message_text='You can subscribe to any of these pokemons.'
    send_message(recipient_id,message_text)
    
    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    message={
        "attachment":{
          "type":"template",
          "payload":{
            "template_type":"generic",
            "elements":[
              {
                "title":"Welcome to rare Pokemons",
                "image_url":"http://cdn.gamecloud.net.au/wp-content/uploads/2013/12/TDSO_Pokemon_Image_2.png",
                "subtitle":"We\'ve got the rare pokemons for you.",
                "buttons":[
                  {
                    "type":"postback",
                    "title":"Subscribe",
                    "payload":"subscribe1"
                  }              
                ]
              },
              {
                "title":"Rare Pokemon 2",
                "image_url":"https://heavyeditorial.files.wordpress.com/2016/07/3c76867a3b504d9aada2fbf4610a58f2-e1468936872361.jpg",
                "subtitle":"I am the rarest.",
                "buttons":[
                  {
                    "type":"postback",
                    "title":"Subscribe",
                    "payload":"subscribe2"
                  }              
                ]
              }
            ]
          }
        }
      }
    data = json.dumps({'recipient': {'id': recipient_id},
                      'message': message})

    r = requests.post('https://graph.facebook.com/v2.6/me/messages',
                      params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)
        
        
def sendList2Unsubscribe(recipient_id):

    message_text='You are subscribed to these pokemons.'
    send_message(recipient_id,message_text)
    
    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    message={
        "attachment":{
          "type":"template",
          "payload":{
            "template_type":"generic",
            "elements":[
              {
                "title":"Welcome to rare Pokemons",
                "image_url":"http://cdn.gamecloud.net.au/wp-content/uploads/2013/12/TDSO_Pokemon_Image_2.png",
                "subtitle":"We\'ve got the rare pokemons for you.",
                "buttons":[
                  {
                    "type":"postback",
                    "title":"UnSubscribe",
                    "payload":"unsubscribe1"
                  }              
                ]
              },
              {
                "title":"Rare Pokemon 2",
                "image_url":"https://heavyeditorial.files.wordpress.com/2016/07/3c76867a3b504d9aada2fbf4610a58f2-e1468936872361.jpg",
                "subtitle":"I am the rarest.",
                "buttons":[
                  {
                    "type":"postback",
                    "title":"UnSubscribe",
                    "payload":"unsubscribe2"
                  }              
                ]
              }
            ]
          }
        }
      }
    data = json.dumps({'recipient': {'id': recipient_id},
                      'message': message})

    r = requests.post('https://graph.facebook.com/v2.6/me/messages',
                      params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)
        
        
def send_message(recipient_id, message_text):

    log('sending message to {recipient}: {text}'.format(recipient=recipient_id,
        text=message_text))

    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({'recipient': {'id': recipient_id},
                      'message': {'text': message_text}})

    r = requests.post('https://graph.facebook.com/v2.6/me/messages',
                      params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


def tweet():
    #args = get_args()
    #creds = load_credentials()

    #shortener = Shortener('Google', api_key=creds[0])
    #tweet = Twitter(auth=OAuth(creds[1], creds[2], creds[3], creds[4]))
	#send_message('1162610060480372', 'thanks')
	
	if os.path.isfile(os.path.join(os.path.dirname(__file__),
					  './rares.txt')):
		with open(os.path.join(os.path.dirname(__file__), './rares.txt'
				  ), 'r') as file:
			rares = [int(x) for x in file.read().split()]
	else:
		print 'rares.txt not found, adding all pokemon instead.'
		rares = [x + 1 for x in range(151)]
	with open(os.path.join(os.path.dirname(__file__),
			  './pokemon.fr.json')) as data_file:
		idToPokemon = json.load(data_file)
		
	url = 'http://09946dde.ngrok.io' + '/rare'
	response = urllib.urlopen(url)
	dump = json.loads(response.read())
	new = copy.deepcopy(dump)

  # print new

	old = {'pokemons': []}

	print 'test1'

	if os.path.isfile(os.path.join(os.path.dirname(__file__),
					  './data.json')):
		with open(os.path.join(os.path.dirname(__file__), './data.json'
				  )) as data_file:
			old = json.load(data_file)

  # Deletes encounter id for next step

	for e_new in new['pokemons']:
		for e_old in old['pokemons']:
			if e_new['encounter_id'] == e_old['encounter_id']:
				del e_new['encounter_id']
				break

  # Existing encounter ids are rare pokemon
  # This entire step is to parse the data for a tweet

	for e_new in new['pokemons']:
		print 'test2'
		if 'encounter_id' in e_new:
			print str(t.time() + 300) + ' vs ' \
				+ str(e_new['disappear_time'] / 1000)
				
			
			
			if t.time() + 300 < e_new['disappear_time'] / 1000:
				location = str(Geocoder.reverse_geocode(e_new['latitude'
							   ], e_new['longitude'])[0]).split(',')
				destination = location[0] + ', ' \
					+ location[1].split()[0]
				time = \
					datetime.datetime.fromtimestamp(e_new['disappear_time'
						] / 1000)
				hour = time.hour + 6
				gmap = 'https://www.google.fr/maps/place/' \
					+ str(e_new['latitude']) + ',' \
					+ str(e_new['longitude']) + '/'
				if hour >= 24:
					hour -= 24
				tweeting = \
					"{} \xc3\xa0 {} jusqu'\xc3\xa0 {}:{}:{}. #PokemonGo {}".format(
					idToPokemon[str(e_new['pokemon_id'])].encode('utf-8'
							),
					destination,
					hour,
					str(time.minute).zfill(2),
					str(time.second).zfill(2),
					gmap,
					)
				try:

			# tweet.statuses.update(status=tweeting)

					print 'i am ready to tweet'
					send_message('1162610060480372', tweeting)
					send_message('1077717795652613', tweeting)
				except Exception, e:
					print 'Duplicate status, continuing on.'
					pass
				print tweeting

		  # Google api timeout

				t.sleep(0.5)

	with open(os.path.join(os.path.dirname(__file__), './data.json'),
			  'w') as outfile:
		json.dump(dump, outfile)


		
if __name__ == '__main__':
	#app.config.from_object(Config())
	port = int(os.environ.get('PORT', 5000))
	app.run(host='0.0.0.0',debug=True,port=port)
