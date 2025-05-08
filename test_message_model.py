"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase

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

    def test_existing_messages(self):
        """Does the message exist in the database?"""

        with self.client as c:
            with app.app_context():
                message = Message.query.get(1)
                testfollowing = User.query.get(2)
                self.assertIsNotNone(message)
                self.assertEqual(message.text, "test message 1")
                self.assertEqual(message.user_id, testfollowing.id)

    def test_add_message(self):
        """ Can we add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with app.app_context():

                newmessage = Message(text="Hello")
                testuser = User.query.first() # That should get us testuser
                testuser.messages.append(newmessage)

                db.session.commit()

                messages = Message.query.all()

                self.assertEqual(len(messages), 3)
                self.assertEqual(messages[2].text, "Hello")
                self.assertEqual(messages[2].user_id, testuser.id)
                self.assertEqual(testuser.messages[0].text, "Hello")

    def test_delete_message(self):
        """Can we delete a message?"""

        with self.client as c:
            with app.app_context():
                message = Message.query.get(1)
                db.session.delete(message)
                db.session.commit()

                messages = Message.query.all()

                self.assertEqual(len(messages), 1)
                self.assertEqual(messages[0].text, "test message 2")
