"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError


from models import db, Message, User, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"    # - Even with the refactor this still works and changes the database accordingly


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

# Will need to refactor some base code to use Flask 3

# Creating new app instance with test database URI
# app = create_app("postgressql:///warbler-test")

# Configuring app in a similar way to how it would be in production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")

# Disable some of Flasks error behavior and disabling debugtoolbar. Disabling CSRF token.
# Don't have WTForms use CSRF at all, since it's a pain to test
app.config['TESTING'] = True
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']
app.config['WTF_CSRF_ENABLED'] = False

# with app.app_context():
#     db.create_all()



class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        # Moving table creation here so we can have similar keys when testing
        with app.app_context():
            db.create_all()
            User.query.delete()
            Message.query.delete()
            Follows.query.delete()

            self.client = app.test_client()

            self.testuser = User.signup(username="testuser",
                                        email="test@test.com",
                                        password="testuser",
                                        image_url=None)

            self.testfollowing = User.signup(username="testfollowing",
                                        email="following@test.com",
                                        password="testuser",
                                        image_url=None)
            
            self.testfollower = User.signup(username="testfollower",
                                        email="follower@test.com",
                                        password="testuser",
                                        image_url=None)

            # Setting up messages for test follower and test following
            testmessage1 = Message(text="test message 1")
            testmessage2 = Message(text="test message 2")
            self.testfollowing.messages.append(testmessage1)
            self.testfollower.messages.append(testmessage2)

            # Setting up diifferent followers and following for test user
            self.testuser.following.append(self.testfollowing)
            self.testuser.followers.append(self.testfollower)

            db.session.commit()
    
    def tearDown(self):

        """
        Rolling back database, dropping all tables
        """
        # Will drop tables here and recreate them in setUp()
        with app.app_context():
            db.drop_all()
            db.session.rollback()


    def test_user_model(self):
        """Does basic model work?"""

        with self.client as c:
            with app.app_context():
                u = User(
                    email="anothertest@test.com",
                    username="anothertestuser",
                    password="HASHED_PASSWORD"
                )
                db.session.add(u)
                db.session.commit()

                # User should have no messages & no followers
                self.assertEqual(len(u.messages), 0)
                self.assertEqual(len(u.followers), 0)

    def test_not_unique_user_model(self):
        """Do we get an error when we try and add an already existing user?"""

        with self.client as c:
            with app.app_context():
                u = User(
                    email="test@test.com",
                    username="testuser",
                    password="HASHED_PASSWORD"
                )

                db.session.add(u)

                # We should get an integrity error
                with self.assertRaises(IntegrityError):
                    db.session.commit()

    def test_testuser_follows(self):
        """
        Does testuser have followers and follows?
        """
        with self.client as c:
            with app.app_context():

                # This should be the testuser we made earlier.
                user = User.query.get(1)

                self.assertEqual(len(user.followers), 1)
                self.assertEqual(len(user.following), 1)

    def test_testuser_isfollowing_testfollows(self):
        """
        Does testuser.is_following() work with testfollows user?
        """

        with self.client as c:
            with app.app_context():
                testuser = User.query.get(1)
                testfollowing = User.query.get(2)
                self.assertEqual(testuser.is_following(testfollowing), True)

    def test_testuser_isfollowedby_testfollower(self):

        """
        Does testuser.is_followed_by() work with testfollower user?
        """

        with self.client as c:
            with app.app_context():
                testuser = User.query.get(1)
                testfollower = User.query.get(3)
                self.assertEqual(testuser.is_followed_by(testfollower), True)


    def test_testuser_not_following_testfollows(self):
        """
        Does testuser.is_following() return False when testfollows unfollows?
        """

        with self.client as c:
            with app.app_context():
                testuser = User.query.get(1)
                testfollowing = User.query.get(2)

                testuser.following.remove(testfollowing)
                self.assertEqual(testuser.is_following(testfollowing), False)

    def test_testuser_not_followedby_testfollower(self):

        """
        Does testuser.is_followed_by() work with testfollower user?
        """

        with self.client as c:
            with app.app_context():
                testuser = User.query.get(1)
                testfollower = User.query.get(3)

                testuser.followers.remove(testfollower)

                self.assertEqual(testuser.is_followed_by(testfollower), False)

    def test_user_signup(self):
        """Does user signup work?"""

        with self.client as c:
            with app.app_context():
                u = User.signup(username="signuptestuser",
                                email="signup@test.com",
                                password="signupuser",
                                image_url=None)
                db.session.commit()

                # We should be able to query and find this user

                user = User.query.get(u.id)
                self.assertEqual(user.username, "signuptestuser")

    def test_user_authentication(self):
        """Does user authentication work?"""

        with self.client as c:
            with app.app_context():
                u = User.authenticate(username="testuser",
                                password="testuser")
                
                # That should have returned an authenticated user
                self.assertEqual(u.username, "testuser")

    def test_user_authentication_fail_username(self):
        """Does user authentication fail when we use wrong username?"""

        with self.client as c:
            with app.app_context():
                u = User.authenticate(username="wrongusername",
                                password="testuser")
                
                # That should have returned None
                self.assertEqual(u, False)


    def test_user_authentication_fail_password(self):
        """Does user authentication fail when we use wrong password?"""

        with self.client as c:
            with app.app_context():
                u = User.authenticate(username="testuser",
                                password="wrongpassword")
                
                # That should have returned None
                self.assertEqual(u, False)


