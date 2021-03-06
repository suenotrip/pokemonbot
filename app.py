#!/usr/bin/python
# -*- coding: utf-8 -*-
#http://pokemondb.net/pokedex/national for list of pokemons

import os
import sys
import json
reload(sys)
sys.setdefaultencoding('utf-8')
from pygeocoder import Geocoder
import urllib
import time as t
from time import sleep
import datetime
import copy
import re

from flask_apscheduler import APScheduler
import requests
from flask import Flask, request

from datetime import date, datetime, timedelta
import mysql.connector


class Config(object):

    JOBS = [{
        'id': 'job1',
        'func': '__main__:job1',
        'args': (1, 2),
        'trigger': 'interval',
        'seconds': 30,
        }]

    SCHEDULER_VIEWS_ENABLED = True


def job1(a, b):
    print str(a) + ' ' + str(b)
    log('scedule method called')

    tweet()


app = Flask(__name__)
app.config.from_object(Config())

# app.debug = True

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

    # if post is from facebook page

    if data['object'] == 'page':

        for entry in data['entry']:
            for messaging_event in entry['messaging']:

                if messaging_event.get('message'):  # someone sent us a message

                    sender_id = messaging_event['sender']['id']  # the facebook ID of the person sending you the message

                    # recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID

                    if 'text' in messaging_event['message']:
                        message_text = messaging_event['message']['text'
                                ]  # the message's text
                        rules4messages(sender_id, message_text)

                    # check if the user exists. if not insert a user into database

                    ChecknInsertNewUser(sender_id)

                if messaging_event.get('delivery'):  # delivery confirmation
                    pass

                if messaging_event.get('optin'):  # optin confirmation
                    pass

                if messaging_event.get('postback'):  # user clicked/tapped "postback" button in earlier message
                    sender_id = messaging_event['sender']['id']
                    payload = messaging_event['postback']['payload']
                    log('sender id is ===' + sender_id
                        + 'payload for postback is ===' + payload)

                    handlePostback(payload, sender_id)
    elif data['object'] == 'stripe':
        
        facebook_id = data['user_id']
        sub_id=data['sub_id']
        send_message(facebook_id, 'Congratulations!')
        if sub_id=='1' :
            #update subscription count of this user
            updateSubscriptionCount(facebook_id)
            send_message(facebook_id,
                     'Great, Your payment has been processed successfully! Now you can subscribe to more pokemons.'
                     )
        else :
            updateUnsubscriptionCount(facebook_id)
            send_message(facebook_id,
                     'Great, Your payment has been processed successfully! Now you can unsubscribe and then subscribe to more pokemons.'
                     )

    return ('ok', 200)


def rules4messages(sender_id, message_text):
    msg = message_text.upper()
    if sender_id == '1661666914149514':
        log('trying to send message to the page itself.')
    else:

        if msg == 'UNSUBSCRIBE':
            sendList2Unsubscribe(sender_id,1)
        elif msg == 'SUBSCRIBE':

            sendList2subscribe(sender_id,1)
        elif msg == 'HI' or msg == 'HELLO' or msg == 'HEY' or msg \
            == 'START' or msg == 'HOME':

            send_message(sender_id,
                         'Welcome to pokemonbot! Catching pokemons has just become easier!'
                         )
            send_message(sender_id,
                         'Subscribe to rare pokemons and get notification with the location of the pokemons when it is available in Paris with disappearance time as well.'
                         )
            landingCarousel(sender_id)
        elif msg == 'MYSUBS':

            subscriptionCount(sender_id)
        elif msg == 'SUBS':

            sendList2subscribe(sender_id,1)
        elif msg == 'HELP':

            send_message(sender_id,
                         'Type MYSUBS to check your existing subscriptions'
                         )
            send_message(sender_id,
                         'Type SUBS to subscribe to more pokemons')
            send_message(sender_id,
                         'Type START to restart the bot for you')
        else:

            send_message(sender_id,
                         'Welcome to pokemonbot! Catching pokemons has just become easier!'
                         )
            send_message(sender_id,
                         'Subscribe to rare pokemons and get notification with the location of the pokemons when it is available in Paris with disappearance time as well.'
                         )
            sendList2subscribe(sender_id,1)


def handlePostback(payload, sender_id):

    if re.search('(subscribepokemon.*)', payload):
        pokemon_id = int(payload[16:])
        if pokemon_id==1000 :
            sendList2subscribe(sender_id,2)
        elif pokemon_id==2000 :
            sendList2subscribe(sender_id,3)
        elif pokemon_id==3000 :
            sendList2subscribe(sender_id,4)
        else :
            subscribe2pokemon(sender_id, pokemon_id)
    elif re.search('(unsubspokemon.*)', payload):
        pokemon_id = int(payload[13:])
        if pokemon_id==1000 :
            sendList2Unsubscribe(sender_id,2)
        elif pokemon_id==2000 :
            sendList2Unsubscribe(sender_id,3)
        elif pokemon_id==3000 :
            sendList2Unsubscribe(sender_id,4)
        else :
            unsubscribe2pokemon(sender_id, pokemon_id)
    elif payload == 'getmysubscriptions':
        subscriptionCount(sender_id)
    elif payload == 'getsubscribelist':
        sendList2subscribe(sender_id,1)


def subscribe2pokemon(sender_id, pokemon_id):  # create new user
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()

        getuser_fbid = 'SELECT id FROM bot_users WHERE facebook_id = %s'
        cursor.execute(getuser_fbid, (sender_id, ))
        result_set = cursor.fetchall()
        for row in result_set:
            user_id = row[0]

        # check if this user is subscribed for this pokemon # if not, insert a new row

        check_subscription = \
            'SELECT * FROM poke_subscribe WHERE user_id = %s and pokemon_id=%s'
        cursor.execute(check_subscription, (user_id, pokemon_id))
        msg = cursor.fetchone()
        if not msg:
            print 'nope subscription does not exist'
            #get count of subscription and subscribe only if its less than purchased count
            count_pokemon ='SELECT count(*) FROM poke_subscribe WHERE user_id = %s '
            cursor.execute(count_pokemon, (user_id, ))
            result_count = cursor.fetchall()
            for row in result_count:
                count_subscribed = row[0]
            
            limit_pokemon ='SELECT count(*) FROM upgrade_subscription WHERE user_id = %s '
            cursor.execute(limit_pokemon, (user_id, ))
            limit_count = cursor.fetchall()
            for row in limit_count:
                limit_subscribed = row[0]*5
            
            if limit_subscribed==0 and (pokemon_id==1 or pokemon_id==6 or pokemon_id==4) :
                message_text = 'This pokemon is not available for free subscription. Please pay now and get 5 subscriptions.'
                send_message(sender_id, message_text)
                carousel_payment(sender_id,1)
                
            elif count_subscribed <(2+limit_subscribed) :            
                present_time = datetime.now()
                add_user = \
                    'INSERT INTO poke_subscribe(user_id,pokemon_id,datetime)VALUES (%s, %s,%s)'
                cursor.execute(add_user, (user_id, pokemon_id,
                               present_time))
                message_text = 'You have been subscribed to this pokemon'
                send_message(sender_id, message_text)
                print 'new suscription added'
            else:
                #send a message with payment button
                message_text='Sorry. You have already reached the full quota of subscription. Pay 5 USD to get 5 more subscriptions.'
                send_message(sender_id,message_text)
                carousel_payment(sender_id,1)
        else:
            print 'subscription exists'
            message_text = 'You are already subscribed to this pokemon'
            send_message(sender_id, message_text)

        cursor.close()
        cnx.close()
    except mysql.connector.Error, err:
        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)


def unsubscribe2pokemon(sender_id, pokemon_id):  # create new user
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()

        getuser_fbid = 'SELECT id FROM bot_users WHERE facebook_id = %s'
        cursor.execute(getuser_fbid, (sender_id, ))
        result_set = cursor.fetchall()
        for row in result_set:
            user_id = row[0]

        # check if this user is subscribed for this pokemon # if yes, delete the row

        check_subscription = \
            'SELECT * FROM poke_subscribe WHERE user_id = %s and pokemon_id=%s'
        cursor.execute(check_subscription, (user_id, pokemon_id))
        msg = cursor.fetchone()
        if not msg:
            print 'nope subscription does not exist'
            message_text = \
                'Sorry but you were not subscribed to this pokemon'
            send_message(sender_id, message_text)
        else:
            #check if the user has paid to unsubscribe
            #get count of subscription and subscribe only if its less than purchased count
            count_pokemon_unsub ='SELECT count(*) FROM poke_unsubscribe WHERE user_id = %s '
            cursor.execute(count_pokemon_unsub, (user_id, ))
            result_count = cursor.fetchall()
            for row in result_count:
                count_unsubscribed = row[0]
            
            limit_pokemon_unsub ='SELECT count(*) FROM edit_subscription WHERE user_id = %s '
            cursor.execute(limit_pokemon_unsub, (user_id, ))
            limit_count = cursor.fetchall()
            for row in limit_count:
                limit_unsubscribed = row[0]*5
            
            if count_unsubscribed < (2+limit_unsubscribed) :                
                delete_subscription = \
                    'DELETE FROM poke_subscribe WHERE user_id = %s and pokemon_id=%s'
                cursor.execute(delete_subscription, (user_id, pokemon_id))
                
                #update the unsubscribe table by making an entry
                present_time = datetime.now()
                update_unsubscribe='INSERT INTO poke_unsubscribe(user_id,pokemon_id,datetime)VALUES (%s, %s,%s)'
                cursor.execute(update_unsubscribe, (user_id, pokemon_id, present_time))
                
                message_text = 'You have been unsubscribed to this pokemon'
                send_message(sender_id, message_text)
                print 'subscription deleted successfully'
                
            else:
                #send a message with payment button
                message_text='Sorry. You have already reached the full quota of Unsubscribing. Pay 5 USD to get 5 more Unsubscriptions.'
                send_message(sender_id,message_text)
                carousel_payment(sender_id,0)

        cursor.close()
        cnx.close()
    except mysql.connector.Error, err:
        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)


def ChecknInsertNewUser(sender_id):  # create new user
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()

        check_user = 'SELECT * FROM bot_users WHERE facebook_id = %s'
        cursor.execute(check_user, (sender_id, ))
        msg = cursor.fetchone()
        if not msg:
            print 'nope user does not exist'
            accesstoken = os.environ['PAGE_ACCESS_TOKEN']
            r = requests.get('https://graph.facebook.com/v2.6/'
                             + sender_id + '?access_token='
                             + accesstoken)
            data = r.json()
            first_name = data['first_name']
            last_name = data['last_name']

            # first_name='Felipé Rach'
            # last_name='Azria'

            myname = first_name + ' ' + last_name
            print myname

            add_user = \
                'INSERT INTO bot_users(name,facebook_id)VALUES (%s, %s)'
            cursor.execute(add_user, (myname, sender_id))
        else:

            print 'Yeah. user already exists'

        cursor.close()
        cnx.close()
    except mysql.connector.Error, err:
        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)


def landingCarousel(recipient_id):
    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    url = 'http://stripe.restokitch.com/stripe.php?user_id=' + recipient_id +'&sub_id=1'
    message = {'attachment': {'type': 'template',
               'payload': {'template_type': 'generic', 'elements': [{
        'title': 'My Pokemon Subscriptions',
        'image_url': 'http://cdn.bulbagarden.net/upload/thumb/9/97/Mpr_platinumscreen.jpg/350px-Mpr_platinumscreen.jpg'
            ,
        'subtitle': 'Check your existing subscriptions. You may unsubscribe from any of them.'
            ,
        'buttons': [{'type': 'postback', 'title': 'My Subscriptions',
                    'payload': 'getmysubscriptions'}],
        }, {
        'title': 'Subscribe to rare pokemons',
        'image_url': 'https://i.ytimg.com/vi/sSjee6FmJrM/maxresdefault.jpg'
            ,
        'subtitle': 'Subscribe to more pokemons and get notifications of their location.'
            ,
        'buttons': [{'type': 'postback', 'title': 'Subscribe more',
                    'payload': 'getsubscribelist'}],
        }, {
        'title': 'Pay to subscribe',
        'image_url': 'https://ruter.no/contentassets/711a33afa4144b97b2f7d9772a49418a/reisekort_767x250.jpg'
            ,
        'subtitle': 'Pay to subscribe to more pokemons',
        'buttons': [{'type': 'web_url', 'url': url, 'title': 'Pay 5 USD'
                    }],
        }]}}}

    data = json.dumps({'recipient': {'id': recipient_id},
                      'message': message})

    r = requests.post('https://graph.facebook.com/v2.6/me/messages',
                      params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def subscriptionCount(sender_id):
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()
        getuser_fbid = 'SELECT id FROM bot_users WHERE facebook_id = %s'
        cursor.execute(getuser_fbid, (sender_id, ))
        result_set = cursor.fetchall()
        for row in result_set:

            # print "%s" % (row["id"])

            user_id = row[0]

        count_pokemon = \
            'SELECT count(*) FROM poke_subscribe WHERE user_id = %s '
        cursor.execute(count_pokemon, (user_id, ))
        result_count = cursor.fetchall()
        for row in result_count:
            count = row[0]

        message_text = 'You are subscribed to ' + str(count) \
            + ' pokemons'
        send_message(sender_id, message_text)
        if count == 0:
            message_text = 'Get started by subscribing to few pokemons'
            send_message(sender_id, message_text)
            sendList2subscribe(sender_id,1)
        else:
            sendList2Unsubscribe(sender_id,1)

        cursor.close()
        cnx.close()
    except mysql.connector.Error, err:
        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)


def sendList2subscribe(recipient_id,sequence_id):
    message_text = 'You can subscribe to any of these pokemons.'
    send_message(recipient_id, message_text)

    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}

    # get list of pokemons from db

    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()

        if sequence_id==2 :
            fetch_pokemon ='SELECT id,pokemon_id,pokemon_name,rarity FROM rare_pokemons where id>9 and id<19 '
        elif sequence_id==3 :
            fetch_pokemon ='SELECT id,pokemon_id,pokemon_name,rarity FROM rare_pokemons where id>18 and id<28 '
        elif sequence_id==4 :
            fetch_pokemon ='SELECT id,pokemon_id,pokemon_name,rarity FROM rare_pokemons where id>27 and id<37 '
        else :
            fetch_pokemon ='SELECT id,pokemon_id,pokemon_name,rarity FROM rare_pokemons where id<9 '
            
        cursor.execute(fetch_pokemon)
        result_count = cursor.fetchall()
        elements = []
        for row in result_count:
            id = row[0]
            pokemon_id = row[1]
            pokemon_name = row[2]
            rarity = row[3]
            element = createFBelement(id, pokemon_id, pokemon_name,
                    rarity)
            elements.append(element)
        if sequence_id==1 :
            element = createMoreElement(1000)
            elements.append(element)
        elif sequence_id ==2 :
            element = createMoreElement(2000)
            elements.append(element)
        elif sequence_id ==3 :
            element = createMoreElement(3000)
            elements.append(element)
        
        cursor.close()
        cnx.close()

        message = {'attachment': {'type': 'template',
                   'payload': {'template_type': 'generic',
                   'elements': elements}}}

        data = json.dumps({'recipient': {'id': recipient_id},
                          'message': message})

        r = requests.post('https://graph.facebook.com/v2.6/me/messages'
                          , params=params, headers=headers, data=data)
        if r.status_code != 200:
            log(r.status_code)
            log(r.text)
    except mysql.connector.Error, err:

        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)


def sendList2Unsubscribe(recipient_id,sequence_id):

    message_text = 'You are subscribed to these pokemons.'
    send_message(recipient_id, message_text)

    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}

    # get list of my pokemons from db

    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()

        # get user id from fb id

        getuser_fbid = 'SELECT id FROM bot_users WHERE facebook_id = %s'
        cursor.execute(getuser_fbid, (recipient_id, ))
        result_set = cursor.fetchall()
        for row in result_set:
            user_id = row[0]

        # get pokemon_ids subscribed for this user
        if sequence_id==2 :
            my_subscribed_pokemons ='SELECT pokemon_id FROM poke_subscribe where user_id=%s ORDER BY DATETIME DESC LIMIT 9,19'
        elif sequence_id==3 :
            my_subscribed_pokemons ='SELECT pokemon_id FROM poke_subscribe where user_id=%s ORDER BY DATETIME DESC LIMIT 19,29 '
        elif sequence_id==4 :
            my_subscribed_pokemons ='SELECT pokemon_id FROM poke_subscribe where user_id=%s ORDER BY DATETIME DESC LIMIT 29,39 '
        else :
            my_subscribed_pokemons ='SELECT pokemon_id FROM poke_subscribe where user_id=%s ORDER BY DATETIME DESC LIMIT 0,9'
            
        
        log('sql_query' + my_subscribed_pokemons)
        cursor.execute(my_subscribed_pokemons, (user_id, ))
        result_my_pokemons = cursor.fetchall()
        pokemon_ids = []
        for row in result_my_pokemons:
            pokemon_id = row[0]
            pokemon_ids.append(pokemon_id)
            print pokemon_ids

        # get pokemons details for subscribed ones

        myTuple = tuple(pokemon_ids)
        pokemon_count = len(pokemon_ids)
        if pokemon_count == 1:
            myTuple = myTuple[0]
            fetch_pokemon = \
                'SELECT id,pokemon_id,pokemon_name,rarity FROM rare_pokemons where id in (' \
                + str(myTuple) + ')'
        else:
            fetch_pokemon = \
                'SELECT id,pokemon_id,pokemon_name,rarity FROM rare_pokemons where id in' \
                + str(myTuple)

        # log ('sql_pokemon'+fetch_pokemon)

        cursor.execute(fetch_pokemon)
        result_count = cursor.fetchall()
        elements = []
        for row in result_count:
            id = row[0]
            pokemon_id = row[1]
            pokemon_name = row[2]
            rarity = row[3]
            element = createFBelement4Unsubscribe(id, pokemon_id,
                    pokemon_name, rarity)
            elements.append(element)
        if pokemon_count==9 :   
            if sequence_id==1 :
                element = createMoreUnsubElement(1000)
                elements.append(element)
            elif sequence_id ==2 :
                element = createMoreUnsubElement(2000)
                elements.append(element)
            elif sequence_id ==3 :
                element = createMoreUnsubElement(3000)
                elements.append(element)

        cursor.close()
        cnx.close()

        message = {'attachment': {'type': 'template',
                   'payload': {'template_type': 'generic',
                   'elements': elements}}}

        data = json.dumps({'recipient': {'id': recipient_id},
                          'message': message})

        r = requests.post('https://graph.facebook.com/v2.6/me/messages'
                          , params=params, headers=headers, data=data)
        if r.status_code != 200:
            log(r.status_code)
            log(r.text)
    except mysql.connector.Error, err:

        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)

        
def updateSubscriptionCount(facebook_id) :
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()

        getuser_fbid = 'SELECT id FROM bot_users WHERE facebook_id = %s'
        cursor.execute(getuser_fbid, (facebook_id, ))
        result_set = cursor.fetchall()
        for row in result_set:
            user_id = row[0]

        # check if this user is subscribed for this pokemon # if not, insert a new row
        increment=5
        
        count_upgrade = \
            'INSERT INTO upgrade_subscription (user_id,upgrade_count) values (%s,%s)'
        cursor.execute(count_upgrade, (user_id,increment))
        
        cursor.close()
        cnx.close()
    except mysql.connector.Error, err:
        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)
    
def updateUnsubscriptionCount(facebook_id) :
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()

        getuser_fbid = 'SELECT id FROM bot_users WHERE facebook_id = %s'
        cursor.execute(getuser_fbid, (facebook_id, ))
        result_set = cursor.fetchall()
        for row in result_set:
            user_id = row[0]

        increment=5
        
        count_upgrade = \
            'INSERT INTO edit_subscription (user_id,edit_count) values (%s,%s)'
        cursor.execute(count_upgrade, (user_id,increment))
        
        cursor.close()
        cnx.close()
    except mysql.connector.Error, err:
        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)
        
    
    
def createMoreElement(id):
    payload_text = 'subscribepokemon' + str(id)
    subtitle = 'Click the button below to check more pokemons & subscribe'
    img_url = 'http://www.siriusxm.ca/wp-content/uploads/2014/08/EN-More.png'
    return {
        'title': 'More pokemons',
        'image_url': img_url,
        'subtitle': subtitle,
        'buttons': [{'type': 'postback', 'title': 'More Pokemons',
                    'payload': payload_text}],
        }
        
        
def createMoreUnsubElement(id):
    payload_text = 'unsubspokemon' + str(id)
    subtitle = 'Click the button below to check more of the pokemons you are subscribed to'
    img_url = 'http://www.siriusxm.ca/wp-content/uploads/2014/08/EN-More.png'
    return {
        'title': 'More pokemons',
        'image_url': img_url,
        'subtitle': subtitle,
        'buttons': [{'type': 'postback', 'title': 'More Pokemons',
                    'payload': payload_text}],
        }        
def createFBelement(
    id,
    pokemon_id,
    pokemon_name,
    rarity,
    ):
    payload_text = 'subscribepokemon' + str(id)
    subtitle = 'I am ' + rarity + ' pokemon'
    img_url = 'https://img.pokemondb.net/artwork/' \
        + pokemon_name.lower() + '.jpg'
    return {
        'title': pokemon_name,
        'image_url': img_url,
        'subtitle': subtitle,
        'buttons': [{'type': 'postback', 'title': 'Subscribe',
                    'payload': payload_text}],
        }

def carousel_payment(recipient_id,sub_id) :
    #sub_id=1==subscribe; sub_id=0==unsubscribe
    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    url = 'http://stripe.restokitch.com/stripe.php?user_id='+ recipient_id +'&sub_id='+str(sub_id)
    message = {'attachment': {'type': 'template',
               'payload': {'template_type': 'generic', 'elements': [ {
        'title': 'Pay to subscribe',
        'image_url': 'https://ruter.no/contentassets/711a33afa4144b97b2f7d9772a49418a/reisekort_767x250.jpg'
            ,
        'subtitle': 'Pay to subscribe to more pokemons',
        'buttons': [{'type': 'web_url', 'url': url, 'title': 'Pay 5 USD'
                    }],
        }]}}}

    data = json.dumps({'recipient': {'id': recipient_id},
                      'message': message})

    r = requests.post('https://graph.facebook.com/v2.6/me/messages',
                      params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)
        
def createFBelement4Unsubscribe(
    id,
    pokemon_id,
    pokemon_name,
    rarity,
    ):
    payload_text = 'unsubspokemon' + str(id)
    subtitle = 'I am ' + rarity + ' pokemon'
    img_url = 'https://img.pokemondb.net/artwork/' \
        + pokemon_name.lower() + '.jpg'
    return {
        'title': pokemon_name,
        'image_url': img_url,
        'subtitle': subtitle,
        'buttons': [{'type': 'postback', 'title': 'UnSubscribe',
                    'payload': payload_text}],
        }


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


def sendNotificationToSubscribedUsers(pokemon_id, message):

    # check who all are subscribed to this pokemon
    #log('notification method called')
    log('pokemon id for this notification===== ' + str(pokemon_id))
    try:
        cnx = mysql.connector.connect(user='restokit_pokemon',
                password='pokemon123', host='restokitch.com',
                database='restokit_pokemon')
        cursor = cnx.cursor()

        getusers_subscribed = \
            'SELECT DISTINCT (b.facebook_id) FROM poke_subscribe p join bot_users b  on p.user_id= b.id JOIN rare_pokemons r WHERE r.pokemon_id =%s'
        cursor.execute(getusers_subscribed, (pokemon_id, ))
        result_set = cursor.fetchall()
        fb_ids = []
        for row in result_set:
            fb_id = row[0]
            send_message(fb_id, message)
            fb_ids.append(fb_id)
            
        myTuple_fbid = tuple(fb_ids)
        log('fb id to send the message ' +str(myTuple_fbid))

        cursor.close()
        cnx.close()
    except mysql.connector.Error, err:
        cursor.close()
        cnx.close()
        print 'Something went wrong: {}'.format(err)


def tweet():

    # args = get_args()
    # creds = load_credentials()

    # shortener = Shortener('Google', api_key=creds[0])
    # tweet = Twitter(auth=OAuth(creds[1], creds[2], creds[3], creds[4]))
    # send_message('1162610060480372', 'thanks')

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

    url = 'http://23914fed.ngrok.io' + '/rare'
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
                print 'test13'
                # location = str(Geocoder.reverse_geocode(e_new['latitude'
                               # ], e_new['longitude'])[0]).split(',')
                latitude=e_new['latitude']
                longitude=e_new['longitude']
                location=str(Geocoder.reverse_geocode(latitude, longitude)[0])
                               
                #log('location is '+location)
                #time =datetime.fromtimestamp(e_new['disappear_time'] / 1000)
                time=datetime.fromtimestamp(e_new['disappear_time']/ 1e3)
                #log('time is '+str(time.hour))
                
                #log ('location'+location)
                #latitude=str(e_new['latitude'])
                #longitude=str(e_new['longitude'])
                gmap = 'https://www.google.fr/maps/place/' \
                    + str(e_new['latitude']) + ',' \
                    + str(e_new['longitude']) + '/'
                
                id_pokemon=e_new['pokemon_id']
                pokemon_name=idToPokemon[str(e_new['pokemon_id'])]
                #log('pokemon generated is == '+ pokemon_name)
                hour=time.hour+6
                if hour >= 24:
                    hour -= 24
                message=pokemon_name +' found at '+ location +' till '+str(hour)+':'+str(time.minute).zfill(2)+':'+str(time.second).zfill(2)
                # message = \
                     # "{} \xc3\xa0 {} jusqu'\xc3\xa0 {}:{}:{}. #PokemonGo {}".format(
                     # pokemon_name,
                     # location,
                     # hour,
                     # str(time.minute).zfill(2),
                     # str(time.second).zfill(2),
                     # gmap,
                     # )
                    
                log ('message is == ' + message)
                try:

                    print 'i am ready to tweet'
                    with open(os.path.join(os.path.dirname(__file__),'./lastpokemon.json')) as data_file:
                         last_encounter = json.load(data_file)
                    last_encounter_id=last_encounter['pokemon'][0]['encounter_id']
                    log('last encounter id is == '+str(last_encounter_id))
                    if last_encounter_id==e_new['encounter_id'] :
                        log('same encounter id. no action taken.')
                    else :
                        sendNotificationToSubscribedUsers(id_pokemon, message)
                        new_encounter_id=e_new['encounter_id']
                        last_encounter_json={"pokemon": [{"encounter_id":new_encounter_id}]}
                        with open(os.path.join(os.path.dirname(__file__), './lastpokemon.json'),'w') as outfile:
                            json.dump(last_encounter_json,outfile)
                        
                except Exception, e:
                    print e.value
                    print 'A problem occurred while sending message to fb user.'
                    pass
                #print tweeting

          # Google api timeout

                #t.sleep(0.5)

    with open(os.path.join(os.path.dirname(__file__), './data.json'),
              'w') as outfile:
        json.dump(dump, outfile)


if __name__ == '__main__':

    # app.config.from_object(Config())

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=True, port=port)
