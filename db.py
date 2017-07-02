import sqlite3
import time

class instabot_db:
     
    conn = sqlite3.connect('instabot.db')
    cursor = conn.cursor()

    def __init__(self):
        self.cursor.execute("create table if not exists users(userid int, username varchar(200) , isfollowed chr(1) default '1', isfollowsme chr(1) default '', isdisable chr(1) default '0', insert_time timestamp)")

    def get_next_unfollower(self, dayUnfollowMe, dayFollowMe):
        unfollow_me_max_time = time.time() - dayUnfollowMe * 24 * 60 * 60
        follow_me_max_time = time.time() - dayFollowMe * 24 * 60 * 60
        user = self.cursor.execute("select userid, username, isfollowed, isfollowsme, insert_time from users where isdisable = '0' and isfollowed = '1' \
                                    and ((isfollowsme = '0' and insert_time < %f ) or  (isfollowsme = '1' and insert_time < %f)) \
                                    order by insert_time limit 1" % (unfollow_me_max_time, follow_me_max_time))
        u = user.fetchone()
        if u is not None and len(u) > 0:
            return u[0], u[1], u[2], u[3], u[4]
        else:
            return 0, '', '', '', '',0

    def is_followed(self, user_id):
        users = self.cursor.execute("select userid from users where userid = %s" % user_id)
        return len(users.fetchall()) > 0

    def unfollow(self, user_id):
        self.cursor.execute("update users set isfollowed='0' where userid = %s" % user_id)
        self.conn.commit()

    def follow(self, user_id, user_name):
        self.cursor.execute("insert into users (userid, username, isfollowed, insert_time) values (%s, '%s', '1', %f)" %(str(user_id), user_name, time.time())) 
        self.conn.commit()

    # to update table that indicates an user followed you
    def set_follows(self, user_id):
        self.cursor.execute("update users set isfollowsme = '1' where userid = %s" % str(user_id))
        self.conn.commit()

    def set_disable(self, user_id):
        self.cursor.execute("update users set isdisable = '1' where userid = %s" % str(user_id))
        self.conn.commit()

    def close(self):
        self.conn.close()