"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User

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

    def test_loggedout_visit_homepage(self):
        """We should get the anon homepage when logged out"""

        with self.client as c:

            resp = c.get("/")
            data = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("New to Warbler?", data)

    def test_loggedout_see_followers(self):
        """We should not be able to see followers when logged out"""

        with self.client as c:

            resp = c.get("/users/1/followers", follow_redirects=True)
            data = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", data)

    def test_loggedout_see_following(self):
        """We should not be able to see followers when logged out"""

        with self.client as c:

            resp = c.get("/users/1/following", follow_redirects=True)
            data = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", data)

    def test_see_followers(self):
        """We should be able to see followers when logged in"""

        with self.client as c:
            with c.session_transaction() as sess:
                with app.app_context():
                    testuser = User.query.first()
                    print(testuser.id)
                    print(testuser.username)
                    sess[CURR_USER_KEY] = testuser.id

            resp = c.get("/users/1/following")
            data = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("testfollowing", data)


    def test_see_following(self):
        """We should be able to see following when logged in"""

        with self.client as c:
            with c.session_transaction() as sess:
                with app.app_context():
                    testuser = User.query.first()
                    print(testuser.id)
                    print(testuser.username)
                    sess[CURR_USER_KEY] = testuser.id

            resp = c.get("/users/1/followers")
            data = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("testfollower", data)