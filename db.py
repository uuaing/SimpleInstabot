import sqlite3
import time

class instabot_db:
     
    conn = sqlite3.connect('instabot.db')
    cursor = conn.cursor()

    def __init__(self):
        self.cursor.execute("create table if not exists users(userid int, username varchar(200) , isfollowed chr(1) default '1', insert_time timestamp)")

    def get_next_unfollower(self,ufollow_interval):
        unfollow_time = time.time() - ufollow_interval
        user = self.cursor.execute("select  userid, username, insert_time from users where isfollowed = '1' and insert_time < %f order by insert_time limit 1" % unfollow_time)
        u = user.fetchone()
        if u is not None and len(u) > 0:
            return u[0]
        else:
            return 0

    def is_followed(self, user_id):
        users = self.cursor.execute("select userid from users where userid = %s" % user_id)
        return len(users.fetchall()) > 0

    def unfollow(self, user_id):
        self.cursor.execute("update users set isfollowed='0' where userid = %s" % user_id)
        self.conn.commit()

    def follow(self, user_id, user_name):
        self.cursor.execute("insert into users (userid, username, isfollowed, insert_time) values (%s, '%s', '1', %f)" %(str(user_id), user_name, time.time())) 
        self.conn.commit()

    def close(self):
        self.conn.close()