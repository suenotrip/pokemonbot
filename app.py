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

class Config(object):
    JOBS = [
        {
            'id': 'job1',
            'func': '__main__:job1',
            'args': (1, 2),
            'trigger': 'interval',
            'seconds': 10
        }
    ]

    SCHEDULER_VIEWS_ENABLED = True

def job1(a, b):
    print(str(a) + ' ' + str(b))
	log('scedule method called'))
	
app = Flask(__name__)
#app.config.from_object(Config())
#app.debug = True

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

#app.run()

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

    if data['object'] == 'page':

        for entry in data['entry']:
            for messaging_event in entry['messaging']:

                if messaging_event.get('message'):  # someone sent us a message

                    sender_id = messaging_event['sender']['id']  # the facebook ID of the person sending you the message
                    recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event['message']['text']  # the message's text

                    send_message(sender_id, 'got it, thanks!')

                if messaging_event.get('delivery'):  # delivery confirmation
                    pass

                if messaging_event.get('optin'):  # optin confirmation
                    pass

                if messaging_event.get('postback'):  # user clicked/tapped "postback" button in earlier message
                    pass

    return ('ok', 200)


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
				
			send_message('1661666914149514', 'thanks')
			
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
	app.config.from_object(Config())
	app.run(debug=True)
