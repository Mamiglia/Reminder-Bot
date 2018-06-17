import botogram
import sqlite3
import time
import redis
dat = sqlite3.connect("dat.db")
d = dat.cursor()
d.execute('CREATE TABLE IF NOT EXISTS user (userid INTEGER PRIMARY KEY, timezone INTEGER)')
d.execute("CREATE TABLE IF NOT EXISTS remind (userid INTEGER, mesid INTEGER, tim INTEGER)")
dat.commit()
bot = botogram.create('')
bot.about = "I AM THE GREAT REMINDERMASTER, with my 512Kb of memory I can Remember ANYTHING you desire, I am at your service, just push /remind"
bot.owner = "@Mamiglia @ferraririccardo"

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)


def final_question(cht, t):
    r.hset(cht.id, 'time', t)
    r.hincrby(cht.id, 'stage')
    bt = botogram.Buttons()
    bt[0].callback('Confirm', 'confirm')
    bt[0].callback('Cancel', 'cancel')
    cht.send('Do you really want me to remind you this?', attach=bt)


@bot.command('start')
def start(chat, message):
    chat.send('welcome message')
    d.execute('INSERT INTO users (userid) VALUES (?)', (message.sender.id, ))
    dat.commit()
    # TODO ask timezone, check if user already in db


@bot.command("remind")
def reminder_start(chat, args, message):
    """ This command allow you to remind something new """
    if chat.type == 'private':
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
        if stage == 1:
            r.hset(chat.id, 'mesid', message.id)
            bt = botogram.Buttons()
            bt[0].callback('Cancel', 'cancel')
            bt[1].callback('1 Day', 'timeadd', str(86400))
            bt[1].callback('1 Hour', 'timeadd', str(3600))
            bt[1].callback('10 min', 'timeadd', str(600))
            chat.send("When are you interested in remembering this?\nYou can send me date in this format DD/MM/YY or just the minuetes", attach=bt)
            r.hincrby(chat.id, 'stage')
        elif stage == 2:
            text = message.text
            try:
                if '/' in text and ':' in text:
                    t = time.mktime(time.strptime(text, "%d/%m/%y %H:%M"))
                elif ':' in text:
                    temp = time.strftime('%d/%m/%y ') + text
                    t = time.mktime(time.strptime(temp, "%d/%m/%y %H:%M"))
                elif '/' in text:
                    t = time.mktime(time.strptime(text, "%d/%m/%y"))
                else:
                    t = time.time() + (60 * int(text))
                # FIX support to timezone is missing
            except ValueError:
                chat.send('Incorrect format, retry')
            else:
                if t - time.time() > 0:
                    final_question(chat, t)
                else:
                    chat.send('I can\'t send messages in the past, I\'m not enough powerful\nChoose another date')


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
    t = time.time() + int(data)
    final_question(chat, t)


@bot.timer(60)
def check_rem():
    d.execute('SELECT * FROM remind')
    reminds = d.fetchall()
    for z in reminds:
        if z[2] <= time.time():
            bot.api.call("forwardMessage", {"chat_id": z[0], "message_id": z[1], "from_chat_id": z[0]})
            d.execute('DELETE FROM remind WHERE userid=? AND mesid=?', (z[0], z[1]))
            dat.commit()


if __name__ == "__main__":
    bot.run()
