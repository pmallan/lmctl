import unittest
import unittest.mock as mock
from pydantic import ValidationError
from lmctl.environment import TNCOEnvironment, LmSessionConfig, LmSession
from lmctl.client import TNCOClient, LegacyUserPassAuth, UserPassAuth, ClientCredentialsAuth, JwtTokenAuth

class TestTNCOEnvironment(unittest.TestCase):
    maxDiff = None

    def test_minimum_init(self):
        config = TNCOEnvironment(address='testing')
        self.assertEqual(config.address, 'testing')
        self.assertEqual(config.secure, False)
        # Defaults
        self.assertEqual(config.brent_name, 'brent')
        self.assertEqual(config.protocol, 'https')
        self.assertEqual(config.auth_protocol, 'https')
        self.assertEqual(config.kami_port, '31289')
        self.assertEqual(config.kami_protocol, 'http')
        
    def test_init_fails_when_address_and_host_are_none(self):
        with self.assertRaises(ValidationError) as context:
            config = TNCOEnvironment()
        self.assertEqual(str(context.exception), '1 validation error for TNCOEnvironment\n__root__\n  TNCO environment cannot be configured without "address" property or "host" property (type=value_error)')

    def test_init_fails_when_secure_and_credentials_not_set(self):
        with self.assertRaises(ValidationError) as context:
            config = TNCOEnvironment(host='test', port=80, secure=True)
        self.assertEqual(str(context.exception), '1 validation error for TNCOEnvironment\n__root__\n  Secure TNCO environment must be configured with either "client_id" or "username" property when using "auth_mode=oauth". If the TNCO environment is not secure then set "secure" to False (type=value_error)')

    def test_init_defaults_port_and_protocol_and_path(self):
        config = TNCOEnvironment(host='test')
        self.assertEqual(config.address, 'https://test')

    def test_init_auth_defaults_auth_address(self):
        config = TNCOEnvironment(host='test', port=80, secure=True, username='test')
        self.assertEqual(config.auth_address, 'https://test:80')

    def test_init_auth_defaults_auth_mode(self):
        config = TNCOEnvironment(host='test', port=80, secure=True, username='test')
        self.assertEqual(config.auth_mode, 'oauth')

    def test_init_with_password(self):
        config = TNCOEnvironment(host='test', port=80, secure=True, username='test', password='secret')
        self.assertEqual(config.username, 'test')
        self.assertEqual(config.password, 'secret')

    def test_init_with_all_as_parts(self):
        config = TNCOEnvironment(host='test', port=80, protocol='http', path='gateway', secure=True, username='user', password='secret', auth_host='auth', auth_port=81, auth_protocol='https', brent_name='alt_brent')
        
        self.assertEqual(config.address, 'http://test:80/gateway')
        self.assertEqual(config.auth_address, 'https://auth:81')
        self.assertEqual(config.secure, True)
        self.assertEqual(config.username, 'user')
        self.assertEqual(config.brent_name, 'alt_brent')

    def test_init_with_address(self):
        config = TNCOEnvironment(address='https://test:8080/api')
        self.assertEqual(config.address, 'https://test:8080/api')
        self.assertEqual(config.auth_address, 'https://test:8080/api')
        self.assertEqual(config.kami_address, 'http://test:31289')

    def test_is_secure(self):
        insecure_env = TNCOEnvironment(host='test', port=80)
        self.assertFalse(insecure_env.secure)
        secure_env = TNCOEnvironment(host='test', port=80, secure=True, username='user')
        self.assertTrue(secure_env.secure)

    def test_address_from_parts(self):
        env = TNCOEnvironment(host='test')
        self.assertEqual(env.address, 'https://test')
        env = TNCOEnvironment(host='test', port=32455)
        self.assertEqual(env.address, 'https://test:32455')
        env = TNCOEnvironment(host='test', port=32455, protocol='http')
        self.assertEqual(env.address, 'http://test:32455')
        env = TNCOEnvironment(host='test', port=None, protocol='http')
        self.assertEqual(env.address, 'http://test')
        env = TNCOEnvironment(host='test', port=None, protocol='http', path='gateway')
        self.assertEqual(env.address, 'http://test/gateway')
        env = TNCOEnvironment(host='test', port=32455, protocol='http', path='gateway')
        self.assertEqual(env.address, 'http://test:32455/gateway')

    def test_auth_address_from_parts(self):
        env = TNCOEnvironment(host='test', port=80, protocol='http', secure=True, username='user', auth_host='auth', auth_port=82, auth_protocol='https')
        self.assertEqual(env.auth_address, 'https://auth:82')

    def test_kami_address_from_parts(self):
        env = TNCOEnvironment(host='test', port=80, protocol='http', secure=True, username='user', auth_host='auth', auth_port=82, auth_protocol='https')
        self.assertEqual(env.kami_address, 'http://test:31289')

    def test_kami_address_override_port(self):
        env = TNCOEnvironment(address='http://test:8080', kami_port=5678)
        self.assertEqual(env.kami_address, 'http://test:5678')

    def test_kami_address_override_protocol(self):
        env = TNCOEnvironment(address='http://test:8080', kami_protocol='https')
        self.assertEqual(env.kami_address, 'https://test:31289')

    def test_token_auth_mode(self):
        env = TNCOEnvironment(address='http://test:8080', secure=True, auth_mode='token', token='123')
        self.assertEqual(env.auth_mode, 'token')
        self.assertEqual(env.token, '123')

    def test_create_session_config(self):
        env = TNCOEnvironment(address='http://test')
        session_config = env.create_session_config()
        self.assertIsInstance(session_config, LmSessionConfig)
        self.assertEqual(session_config.env, env)
        self.assertEqual(session_config.username, None)
        self.assertEqual(session_config.password, None)

    def test_create_session_config_with_username_password(self):
        env = TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user')
        session_config = env.create_session_config()
        self.assertEqual(session_config.username, 'user')
        self.assertEqual(session_config.password, None)
        env = TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', password='secret')
        session_config = env.create_session_config()
        self.assertEqual(session_config.username, 'user')
        self.assertEqual(session_config.password, 'secret')
        self.assertEqual(session_config.auth_mode, 'oauth')

    def test_create_session_config_with_client_credentials(self):
        env = TNCOEnvironment(host='test', port=80, protocol='https', secure=True, client_id='client', client_secret='secret')
        session_config = env.create_session_config()
        self.assertEqual(session_config.client_id, 'client')
        self.assertEqual(session_config.client_secret, 'secret')
        self.assertEqual(session_config.auth_mode, 'oauth')

    def test_create_session_config_with_token_auth(self):
        env = TNCOEnvironment(host='test', port=80, protocol='https', secure=True, auth_mode='token', token='123')
        session_config = env.create_session_config()
        self.assertEqual(session_config.token, '123')
        self.assertEqual(session_config.auth_mode, 'token')

    def test_build_client_sets_address(self):
        config = TNCOEnvironment(
                         host='test', 
                         port=80, 
                         protocol='http', 
                         path='gateway', 
                         secure=True, 
                         username='user', 
                         password='secret', 
                         auth_host='auth', 
                         auth_port=81, 
                         auth_protocol='https'
                         )
        client = config.build_client()
        self.assertIsInstance(client, TNCOClient)
        self.assertEqual(client.address, 'http://test:80/gateway')
        self.assertEqual(client.kami_address, 'http://test:31289')

    def test_build_client_legacy_auth(self):
        config = TNCOEnvironment(
                         address='https://testing',
                         secure=True, 
                         username='user', 
                         password='secret', 
                         auth_host='auth', 
                         auth_port=81, 
                         auth_protocol='https'
                         )
        client = config.build_client()
        self.assertIsInstance(client, TNCOClient)
        self.assertIsInstance(client.auth_type, LegacyUserPassAuth)
        self.assertEqual(client.auth_type.username, 'user')
        self.assertEqual(client.auth_type.password, 'secret')
        self.assertEqual(client.auth_type.legacy_auth_address, 'https://auth:81')

    def test_build_client_user_pass_auth(self):
        config = TNCOEnvironment(
                         address='https://testing',
                         secure=True, 
                         client_id='TNCOClient',
                         client_secret='sosecret',
                         username='user', 
                         password='secret'
                         )
        client = config.build_client()
        self.assertIsInstance(client, TNCOClient)
        self.assertIsInstance(client.auth_type, UserPassAuth)
        self.assertEqual(client.auth_type.username, 'user')
        self.assertEqual(client.auth_type.password, 'secret')
        self.assertEqual(client.auth_type.client_id, 'TNCOClient')
        self.assertEqual(client.auth_type.client_secret, 'sosecret')
    
    def test_build_client_credentials_auth(self):
        config = TNCOEnvironment(
                         address='https://testing',
                         secure=True, 
                         client_id='TNCOClient',
                         client_secret='sosecret'
                         )
        client = config.build_client()
        self.assertIsInstance(client, TNCOClient)
        self.assertIsInstance(client.auth_type, ClientCredentialsAuth)
        self.assertEqual(client.auth_type.client_id, 'TNCOClient')
        self.assertEqual(client.auth_type.client_secret, 'sosecret')

    def test_build_client_token_auth(self):
        config = TNCOEnvironment(
                         address='https://testing',
                         secure=True, 
                         auth_mode='token',
                         token='123'
                         )
        client = config.build_client()
        self.assertIsInstance(client, TNCOClient)
        self.assertIsInstance(client.auth_type, JwtTokenAuth)
        self.assertEqual(client.auth_type.token, '123')


class TestLmSessionConfig(unittest.TestCase):

    def test_create(self):
        env = TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', password='secret')
        session_config = env.create_session_config()
        session = session_config.create()
        self.assertIsInstance(session, LmSession)
        self.assertEqual(session.env, env)
        self.assertEqual(session.username, 'user')
        self.assertEqual(session.password, 'secret')

class TestLmSession(unittest.TestCase):

    def test_init(self):
        env = TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', password='secret')
        session_config = env.create_session_config()
        session = LmSession(session_config)
        self.assertEqual(session.env, env)
        self.assertEqual(session.username, 'user')
        self.assertEqual(session.password, 'secret')

    def test_init_fails_without_config(self):
        with self.assertRaises(ValueError) as context:
            LmSession(None)
        self.assertEqual(str(context.exception), 'config not provided to session')

    @mock.patch('lmctl.environment.lmenv.lm_drivers.security.TNCOClientBuilder')
    def test_security_ctrl_builds_client_with_legacy_auth(self, mock_client_builder_init):
        env = TNCOEnvironment(address='http://api:80', secure=True, username='user', password='secret', auth_address='http://auth:81')
        session_config = env.create_session_config()
        session = LmSession(session_config)
        driver = session.descriptor_driver #Force LmSecurityCtrl to be created
        mock_client_builder = mock_client_builder_init.return_value 
        mock_client_builder.legacy_user_pass_auth.assert_called_once_with(username='user', password='secret', legacy_auth_address='http://auth:81')
        mock_client_builder.user_pass_auth.assert_not_called()
        mock_client_builder.client_credentials_auth.assert_not_called()
        mock_client_builder.zen_api_key_auth.assert_not_called()
    
    @mock.patch('lmctl.environment.lmenv.lm_drivers.security.TNCOClientBuilder')
    def test_security_ctrl_builds_client_with_legacy_auth_on_default_address(self, mock_client_builder_init):
        env = TNCOEnvironment(address='http://api:80', secure=True, username='user', password='secret')
        session_config = env.create_session_config()
        session = LmSession(session_config)
        driver = session.descriptor_driver #Force LmSecurityCtrl to be created
        mock_client_builder = mock_client_builder_init.return_value 
        mock_client_builder.legacy_user_pass_auth.assert_called_once_with(username='user', password='secret', legacy_auth_address='http://api:80')
        mock_client_builder.user_pass_auth.assert_not_called()
        mock_client_builder.client_credentials_auth.assert_not_called()
        mock_client_builder.zen_api_key_auth.assert_not_called()
    
    @mock.patch('lmctl.environment.lmenv.lm_drivers.security.TNCOClientBuilder')
    def test_security_ctrl_builds_client_with_user_pass_auth(self, mock_client_builder_init):
        env = TNCOEnvironment(address='http://api:80', secure=True, username='user', password='secret', client_id='UserClient', client_secret='c_secret', auth_address='http://auth:81')
        session_config = env.create_session_config()
        session = LmSession(session_config)
        driver = session.descriptor_driver #Force LmSecurityCtrl to be created
        mock_client_builder = mock_client_builder_init.return_value 
        mock_client_builder.address.assert_called_once_with('http://auth:81')
        mock_client_builder.legacy_user_pass_auth.assert_not_called()
        mock_client_builder.user_pass_auth.assert_called_once_with(username='user', password='secret', client_id='UserClient', client_secret='c_secret')
        mock_client_builder.client_credentials_auth.assert_not_called()
        mock_client_builder.zen_api_key_auth.assert_not_called()

    @mock.patch('lmctl.environment.lmenv.lm_drivers.security.TNCOClientBuilder')
    def test_security_ctrl_builds_client_with_user_pass_auth_on_default_address(self, mock_client_builder_init):
        env = TNCOEnvironment(address='http://api:80', secure=True, username='user', password='secret', client_id='UserClient', client_secret='c_secret')
        session_config = env.create_session_config()
        session = LmSession(session_config)
        driver = session.descriptor_driver #Force LmSecurityCtrl to be created
        mock_client_builder = mock_client_builder_init.return_value 
        mock_client_builder.address.assert_called_once_with('http://api:80')
        mock_client_builder.legacy_user_pass_auth.assert_not_called()
        mock_client_builder.user_pass_auth.assert_called_once_with(username='user', password='secret', client_id='UserClient', client_secret='c_secret')
        mock_client_builder.client_credentials_auth.assert_not_called()
        mock_client_builder.zen_api_key_auth.assert_not_called()
    
    @mock.patch('lmctl.environment.lmenv.lm_drivers.security.TNCOClientBuilder')
    def test_security_ctrl_builds_client_with_client_auth(self, mock_client_builder_init):
        env = TNCOEnvironment(address='http://api:80', secure=True, client_id='UserClient', client_secret='c_secret', auth_address='http://auth:81')
        session_config = env.create_session_config()
        session = LmSession(session_config)
        driver = session.descriptor_driver #Force LmSecurityCtrl to be created
        mock_client_builder = mock_client_builder_init.return_value 
        mock_client_builder.address.assert_called_once_with('http://auth:81')
        mock_client_builder.legacy_user_pass_auth.assert_not_called()
        mock_client_builder.user_pass_auth.assert_not_called()
        mock_client_builder.client_credentials_auth.assert_called_once_with(client_id='UserClient', client_secret='c_secret')
        mock_client_builder.zen_api_key_auth.assert_not_called()

    @mock.patch('lmctl.environment.lmenv.lm_drivers.security.TNCOClientBuilder')
    def test_security_ctrl_builds_client_with_client_auth_on_default_address(self, mock_client_builder_init):
        env = TNCOEnvironment(address='http://api:80', secure=True, client_id='UserClient', client_secret='c_secret')
        session_config = env.create_session_config()
        session = LmSession(session_config)
        driver = session.descriptor_driver #Force LmSecurityCtrl to be created
        mock_client_builder = mock_client_builder_init.return_value 
        mock_client_builder.address.assert_called_once_with('http://api:80')
        mock_client_builder.legacy_user_pass_auth.assert_not_called()
        mock_client_builder.user_pass_auth.assert_not_called()
        mock_client_builder.client_credentials_auth.assert_called_once_with(client_id='UserClient', client_secret='c_secret')
        mock_client_builder.zen_api_key_auth.assert_not_called()

    @mock.patch('lmctl.environment.lmenv.lm_drivers.security.TNCOClientBuilder')
    def test_security_ctrl_builds_client_with_token_auth(self, mock_client_builder_init):
        env = TNCOEnvironment(address='http://api:80', secure=True, auth_mode='token', token='123')
        session_config = env.create_session_config()
        session = LmSession(session_config)
        driver = session.descriptor_driver #Force LmSecurityCtrl to be created
        mock_client_builder = mock_client_builder_init.return_value 
        mock_client_builder.address.assert_called_once_with('http://api:80')
        mock_client_builder.legacy_user_pass_auth.assert_not_called()
        mock_client_builder.user_pass_auth.assert_not_called()
        mock_client_builder.client_credentials_auth.assert_not_called()
        mock_client_builder.token_auth.assert_called_once_with(token='123')

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmDescriptorDriver')
    def test_descriptor_driver(self, descriptor_driver_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https'), None, auth_mode='oauth'))
        driver = session.descriptor_driver
        descriptor_driver_init.assert_called_once_with('https://test:80', None)
        self.assertEqual(driver, descriptor_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmSecurityCtrl')
    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmDescriptorDriver')
    def test_descriptor_driver_with_security(self, descriptor_driver_init, mock_security_ctrl_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', auth_host='auth', auth_port=81, auth_protocol='http'), 'user', 'secret', auth_mode='oauth'))
        driver = session.descriptor_driver
        mock_security_ctrl_init.assert_called_once_with('http://auth:81', username='user', password='secret', client_id=None, client_secret=None, token=None, auth_mode='oauth')
        descriptor_driver_init.assert_called_once_with('https://test:80', mock_security_ctrl_init.return_value)
        self.assertEqual(driver, descriptor_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmOnboardRmDriver')
    def test_onboard_rm_driver(self, onboard_rm_driver_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https'), None))
        driver = session.onboard_rm_driver
        onboard_rm_driver_init.assert_called_once_with('https://test:80', None)
        self.assertEqual(driver, onboard_rm_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmSecurityCtrl')
    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmOnboardRmDriver')
    def test_onboard_rm_driver_with_security(self, onboard_rm_driver_init, mock_security_ctrl_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', auth_host='auth', auth_port=81, auth_protocol='http'), 'user', 'secret', auth_mode='oauth'))
        driver = session.onboard_rm_driver
        mock_security_ctrl_init.assert_called_once_with('http://auth:81', username='user', password='secret', client_id=None, client_secret=None, token=None, auth_mode='oauth')
        onboard_rm_driver_init.assert_called_once_with('https://test:80', mock_security_ctrl_init.return_value)
        self.assertEqual(driver, onboard_rm_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmTopologyDriver')
    def test_topology_driver(self, topology_driver_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https'), None))
        driver = session.topology_driver
        topology_driver_init.assert_called_once_with('https://test:80', None)
        self.assertEqual(driver, topology_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmSecurityCtrl')
    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmTopologyDriver')
    def test_topology_driver_with_security(self, topology_driver_init, mock_security_ctrl_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', auth_host='auth', auth_port=81, auth_protocol='http'), 'user', 'secret', auth_mode='oauth'))
        driver = session.topology_driver
        mock_security_ctrl_init.assert_called_once_with('http://auth:81', username='user', password='secret', client_id=None, client_secret=None, token=None, auth_mode='oauth')
        topology_driver_init.assert_called_once_with('https://test:80', mock_security_ctrl_init.return_value)
        self.assertEqual(driver, topology_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmBehaviourDriver')
    def test_behaviour_driver(self, behaviour_driver_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https'), None))
        driver = session.behaviour_driver
        behaviour_driver_init.assert_called_once_with('https://test:80', None)
        self.assertEqual(driver, behaviour_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmSecurityCtrl')
    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmBehaviourDriver')
    def test_behaviour_driver_with_security(self, behaviour_driver_init, mock_security_ctrl_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', auth_host='auth', auth_port=81, auth_protocol='http'), 'user', 'secret', auth_mode='oauth'))
        driver = session.behaviour_driver
        mock_security_ctrl_init.assert_called_once_with('http://auth:81', username='user', password='secret', client_id=None, client_secret=None, token=None, auth_mode='oauth')
        behaviour_driver_init.assert_called_once_with('https://test:80', mock_security_ctrl_init.return_value)
        self.assertEqual(driver, behaviour_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmDeploymentLocationDriver')
    def test_deployment_location_driver(self, deployment_location_driver_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https'), None))
        driver = session.deployment_location_driver
        deployment_location_driver_init.assert_called_once_with('https://test:80', None)
        self.assertEqual(driver, deployment_location_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmSecurityCtrl')
    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmDeploymentLocationDriver')
    def test_deployment_location_driver_with_security(self, deployment_location_driver_init, mock_security_ctrl_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', auth_host='auth', auth_port=81, auth_protocol='http'), 'user', 'secret', auth_mode='oauth'))
        driver = session.deployment_location_driver
        mock_security_ctrl_init.assert_called_once_with('http://auth:81', username='user', password='secret', client_id=None, client_secret=None, token=None, auth_mode='oauth')
        deployment_location_driver_init.assert_called_once_with('https://test:80', mock_security_ctrl_init.return_value)
        self.assertEqual(driver, deployment_location_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmInfrastructureKeysDriver')
    def test_infrastructure_keys_driver(self, infrastructure_keys_driver_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https'), None))
        driver = session.infrastructure_keys_driver
        infrastructure_keys_driver_init.assert_called_once_with('https://test:80', None)
        self.assertEqual(driver, infrastructure_keys_driver_init.return_value)

    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmSecurityCtrl')
    @mock.patch('lmctl.environment.lmenv.lm_drivers.LmInfrastructureKeysDriver')
    def test_infrastructure_keys_driver_with_security(self, infrastructure_keys_driver_init, mock_security_ctrl_init):
        session = LmSession(LmSessionConfig(TNCOEnvironment(host='test', port=80, protocol='https', secure=True, username='user', auth_host='auth', auth_port=81, auth_protocol='http'), 'user', 'secret', auth_mode='oauth'))
        driver = session.infrastructure_keys_driver
        mock_security_ctrl_init.assert_called_once_with('http://auth:81', username='user', password='secret', client_id=None, client_secret=None, token=None, auth_mode='oauth')
        infrastructure_keys_driver_init.assert_called_once_with('https://test:80', mock_security_ctrl_init.return_value)
        self.assertEqual(driver, infrastructure_keys_driver_init.return_value)
