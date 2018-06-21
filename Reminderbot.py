import botogram
import sqlite3
from datetime import datetime, timedelta
import redis
import json
from dateutil import parser
dat = sqlite3.connect("dat.db")
d = dat.cursor()
# to delete in final version
# d.execute('DROP TABLE IF EXISTS users')
# d.execute('DROP TABLE IF EXISTS remind')
d.execute('CREATE TABLE IF NOT EXISTS users (userid INTEGER PRIMARY KEY, timezone INTEGER, DST INTEGER DEFAULT 0)')
d.execute("CREATE TABLE IF NOT EXISTS remind (userid INTEGER, mesid INTEGER, tim DATE)")
dat.commit()
bot = botogram.create('')
bot.about = "I AM THE GREAT REMINDERUS, with my 512Kb of memory I can Remember ANYTHING you desire, I am at your service, just push /remind"
bot.owner = "@Mamiglia @ferraririccardo"

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)


def final_question(cht, t, pretty):
    r.hset(cht.id, 'time', t)
    r.hincrby(cht.id, 'stage')
    bt = botogram.Buttons()
    bt[0].callback('Confirm', 'confirm')
    bt[0].callback('Cancel', 'cancel')
    cht.send('Do you really want me to remind you this %s?' % (pretty), attach=bt)


@bot.command('start')
def start(chat, message):
    if chat.type == 'private':
        chat.send('Welcome in Reminderus, this powerful bot allows you to register reminds that I will send you in the future, as first thing set up your timezone')
        d.execute("SELECT userid FROM users")
        x = d.fetchone()
        if x is None or message.sender.id not in x:
            choose_continent(chat)


@bot.command('list')
def list(chat, message):
    if chat.type == 'private':
        d.execute('SELECT * FROM remind WHERE userid=?', (chat.id, ))
        # TODO list and options


@bot.command('settings')
def settings(chat, message):
    pass
    # TODO setting command


@bot.command('cancel')
def cancel_remind(chat, message):
    if chat.type == 'private':
        if r.delete(chat.id) == 1:
            chat.send('Remind Canceled')
        else:
            chat.send('No remind to cancel :c')


@bot.command("remind")
def reminder_start(chat, args, message):
    """ This command allow you to remind something new """
    if chat.type == 'private':
        d.execute('SELECT timezone FROM users WHERE userid=?', (chat.id, ))
        if d.fetchone() is None:
            chat.send('You still haven\'t set timezone and DST, press /start!')
            return
        # check if timezone is set
        bt = botogram.Buttons()
        bt[0].callback('Cancel the Remind', 'cancel')
        if r.hsetnx(chat.id, 'stage', 1) == 1:
            chat.send("Now, Send me the task that you need to remember", attach=bt)
            r.hset(chat.id, 'userid', message.sender.id)
        else:
            chat.send("Complete your request before asking for another", attach=bt)


@bot.process_message
def stager(chat, message):
    if chat.type == 'private':
        try:
            stage = int(r.hget(chat.id, 'stage'))
        except TypeError:
            chat.send('Press /remind to start the magiccc')
            return
        except ValueError:
            timezone_set(chat, message)
            return
        if stage == 1:
            bot.edit_message(message.message_id - 1, "Now, Send me the task that you need to remember")
            r.hset(chat.id, 'mesid', message.id)
            bt = botogram.Buttons()
            bt[1].callback('1 Day', 'timeadd', str(1440))
            bt[1].callback('1 Hour', 'timeadd', str(60))
            bt[1].callback('10 min', 'timeadd', str(10))
            bt[1].callback('5 min', 'timeadd', str(5))
            chat.send("When are you interested in remembering this?\nYou can send me in how many minutes or the date in any format", attach=bt)
            r.hincrby(chat.id, 'stage')
            # TODO delete old buttons here and below
        elif stage == 2:
            text = message.text
            if len(text) < 4:
                t = datetime.utcnow() + timedelta(minutes=(int(text)))
                pretty = "in %s minutes" % (text)
            else:
                try:
                    t = parser.parse(text)
                except ValueError:
                    chat.send('Retry')
                    bot.edit_message(message.message_id - 1, "Invalid Input, retry")
                    return
                pretty = t.strftime("on %A %d/%m/%y at %H:%M")
                d.execute('SELECT DST, timezone FROM users WHERE userid=?', (chat.id, ))
                tz = d.fetchone()
                t = t - timedelta(minutes=(tz[0]+tz[1]))
            if t > datetime.utcnow():
                final_question(chat, t, pretty)
                bot.edit_message(message.message_id - 1, "Ok, you selected %s" % (pretty))
            else:
                chat.send('I can\'t send messages in the past, I\'m not enough powerful\nChoose another date')
                bot.edit_message(message.message_id - 1, "Invalid Input, retry")


@bot.callback('cancel')
def cancel(chat, message):
    message.edit('Remind Canceled')
    r.delete(chat.id)


@bot.callback('confirm')
def confirm(chat, message):
    message.edit('Your wish is granted')
    rem = r.hgetall(chat.id)
    d.execute('INSERT INTO remind (userid, mesid, tim) VALUES (?,?,?)', (rem['userid'], rem['mesid'], rem['time']))
    dat.commit()
    r.delete(chat.id)


@bot.callback('timeadd')
def timeadd(chat, message, data):
    message.edit(message.text)
    t = datetime.now() + timedelta(minutes=int(data))
    pretty = "in %s minutes" % (data)
    final_question(chat, t, pretty)


@bot.callback('choose_continent')
def choose_continent(chat):
    bt = botogram.Buttons()
    bt[0].callback('Europe', 'continents', 'europe')
    bt[1].callback('America', 'continents', 'america')
    bt[2].callback('Asia', 'continents', 'asia')
    bt[3].callback('Africa', 'continents', 'africa')
    bt[4].callback('Oceania', 'continents', 'oceania')
    chat.send('Select Your continent (no polar bears accepted)', attach=bt)


@bot.callback('continents')
def continent_set(message, chat, data):
    message.edit(message.text)
    if data == 'europe':
        button = [["+0", "+1"], ["+2", "+3", "+4"]]
    elif data == 'asia':
        button = [["+2", '+3', '+3:30'], ['+4', '+4:30', '+5'], ['+5:30', '+6', '+7'], ['+8', '+9', '+10', '+11', '+12']]
    elif data == 'oceania':
        button = [['+8', '+9', '+10', '+11'], ['+12', '+13', '-11', '-10']]
    elif data == 'africa':
        button = [['+0', '+1'], ['+2', '+3']]
    elif data == 'america':
        button = [['-9', '-8', '-7'], ['-6', '-5', '-4', '-3']]
    r.hset(chat.id, 'stage', 'tz')
    bot.api.call('sendMessage', {
        'chat_id': chat.id,
        'text': 'Select your Timezone',
        "disable_web_page_preview": True,
        'parse_mode': 'Markdown',
        'reply_markup': json.dumps({"keyboard": button})
        })


@bot.callback('timezone')
def timezone_set(chat, message):
    try:
        d.execute('INSERT INTO users (userid, timezone) VALUES (?,?)', (chat.id, int(message.text) * 60))
        dat.commit()
    except ValueError:
        dat.rollback()
        x = float(message.text[1]) + (float(message.text[3:5]) / 60)
        d.execute('INSERT INTO users (userid, timezone) VALUES (?,?)', (chat.id, int(x * 60)))
        dat.commit()
    r.delete(chat.id)
    bot.api.call('sendMessage', {
        'chat_id': chat.id,
        'text': 'Timezone correctly set',
        'parse_mode': 'HTML',
        'reply_markup': json.dumps({"remove_keyboard": True})
        })
    bt = botogram.Buttons()
    bt[0].callback('Yes', 'DST', '1')
    bt[0].callback('No', 'DST', '0')
    chat.send('Is DST active where you live?', attach=bt)


@bot.callback('DST')
def DST_set(chat, message, data):
    message.edit(message.text)
    d.execute('UPDATE users SET DST=? WHERE userid=?', (int(data) * 60, chat.id))
    dat.commit()
    chat.send('Everything is correctly set!\nYou can now start using the bot by pressing /remind')


@bot.timer(60)
def check_rem():
    d.execute('SELECT * FROM remind')
    reminds = d.fetchall()
    for z in reminds:
        if datetime.strptime(z[2], "%Y-%m-%d %H:%M:%S.%f") <= datetime.utcnow():
            bot.api.call("forwardMessage", {"chat_id": z[0], "message_id": z[1], "from_chat_id": z[0]})
            d.execute('DELETE FROM remind WHERE userid=? AND mesid=?', (z[0], z[1]))
            dat.commit()


if __name__ == "__main__":
    bot.run()
