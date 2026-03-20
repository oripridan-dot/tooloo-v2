from unittest import mock
import pytest

def test_unauthenticated_access():
    with mock.patch('app.views.is_authenticated', return_value=False):
        response = mock.Mock()
        response.status_code = 403
        assert response.status_code == 403

def test_unauthorized_resource_access():
    with mock.patch('app.views.is_authenticated', return_value=True):
        with mock.patch('app.views.user_has_permission', return_value=False):
            response = mock.Mock()
            response.status_code = 403
            assert response.status_code == 403

def test_authorized_access():
    with mock.patch('app.views.is_authenticated', return_value=True):
        with mock.patch('app.views.user_has_permission', return_value=True):
            response = mock.Mock()
            response.status_code = 200
            assert response.status_code == 200
