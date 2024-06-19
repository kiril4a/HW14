import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session
from src.repository.users import (
    get_user_by_email,
    get_user_by_username,
    create_user,
    update_token,
    confirmed_email,
    update_avatar
)
from src.database.models import User

class TestUserRepository(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.db = MagicMock(spec=Session)
        self.user = User(id=1, email="test@example.com", username="testuser", refresh_token=None, confirmed=False, avatar=None)

    @patch("src.repository.users.User")
    async def test_get_user_by_email(self, MockUser):
        mock_query = self.db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = self.user

        result = await get_user_by_email("test@example.com", self.db)
        
        self.assertEqual(result, self.user)
        mock_query.filter.assert_called_once_with(MockUser.email == "test@example.com")
        mock_filter.first.assert_called_once()

    @patch("src.repository.users.User")
    async def test_get_user_by_username(self, MockUser):
        mock_query = self.db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = self.user

        result = await get_user_by_username("testuser", self.db)
        
        self.assertEqual(result, self.user)
        mock_query.filter.assert_called_once_with(MockUser.username == "testuser")
        mock_filter.first.assert_called_once()

    @patch("src.repository.users.Gravatar")
    @patch("src.repository.users.User", autospec=True)
    async def test_create_user(self, MockUser, MockGravatar):
        body = MagicMock()
        body.email = "test@example.com"
        body.dict.return_value = {"email": "test@example.com", "username": "testuser"}
        MockGravatar.return_value.get_image.return_value = "avatar_url"

        new_user_instance = MockUser.return_value
        result = await create_user(body, self.db)
        
        self.assertEqual(result, new_user_instance)
        MockGravatar.assert_called_once_with("test@example.com")
        self.db.add.assert_called_once_with(new_user_instance)
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(new_user_instance)

    async def test_update_token(self):
        token = "new_refresh_token"
        await update_token(self.user, token, self.db)
        self.assertEqual(self.user.refresh_token, token)
        self.db.commit.assert_called_once()

    @patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_confirmed_email(self, mock_get_user_by_email):
        mock_get_user_by_email.return_value = self.user
        await confirmed_email("test@example.com", self.db)
        self.assertTrue(self.user.confirmed)
        self.db.commit.assert_called_once()
        mock_get_user_by_email.assert_awaited_once_with("test@example.com", self.db)

    @patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_update_avatar(self, mock_get_user_by_email):
        mock_get_user_by_email.return_value = self.user
        url = "new_avatar_url"
        result = await update_avatar("test@example.com", url, self.db)
        self.assertEqual(result.avatar, url)
        self.db.commit.assert_called_once()
        mock_get_user_by_email.assert_awaited_once_with("test@example.com", self.db)

if __name__ == '__main__':
    unittest.main()
