"""
Alerts App Tests
Tests for alerts, notifications, and alert rules
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from alerts.models import Alert, NotificationLog, AlertRule
from vehicle_tracking.models import Vehicle

User = get_user_model()


class AlertModelTest(TestCase):
    """Test Alert model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='alertuser',
            password='pass123'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='ALERT 001',
            make='Test',
            model='Vehicle',
            year=2020,
            device_id='RPI_ALERT'
        )
    
    def test_alert_creation(self):
        """Test alert can be created"""
        alert = Alert.objects.create(
            vehicle=self.vehicle,
            alert_type='unauthorized_access',
            severity='critical',
            title='Unauthorized Access Detected',
            message='Someone tried to start the vehicle without authorization',
            status='pending'
        )
        
        self.assertEqual(alert.vehicle, self.vehicle)
        self.assertEqual(alert.alert_type, 'unauthorized_access')
        self.assertEqual(alert.severity, 'critical')
        self.assertEqual(alert.status, 'pending')
        self.assertIsNotNone(alert.created_at)
    
    def test_alert_severities(self):
        """Test different alert severities"""
        severities = ['low', 'medium', 'high', 'critical']
        
        for severity in severities:
            alert = Alert.objects.create(
                vehicle=self.vehicle,
                alert_type='test',
                severity=severity,
                title=f'Test {severity}',
                message='Test message'
            )
            self.assertEqual(alert.severity, severity)
    
    def test_alert_statuses(self):
        """Test different alert statuses"""
        statuses = ['pending', 'sent', 'acknowledged', 'resolved']
        
        for status in statuses:
            alert = Alert.objects.create(
                vehicle=self.vehicle,
                alert_type='test',
                severity='medium',
                title='Test',
                message='Test',
                status=status
            )
            self.assertEqual(alert.status, status)
    
    def test_str_representation(self):
        """Test alert string representation"""
        alert = Alert.objects.create(
            vehicle=self.vehicle,
            alert_type='speed_alert',
            severity='medium',
            title='Speed Limit Exceeded',
            message='Vehicle exceeded 100 km/h'
        )
        
        self.assertIn('Speed Limit Exceeded', str(alert))
        self.assertIn('ALERT 001', str(alert))


class NotificationLogTest(TestCase):
    """Test NotificationLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='notifuser',
            password='pass123',
            phone_number='+254712345678',
            email='notif@example.com'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='NOTIF 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_NOTIF'
        )
        self.alert = Alert.objects.create(
            vehicle=self.vehicle,
            alert_type='unauthorized_access',
            severity='critical',
            title='Test Alert',
            message='Test message'
        )
    
    def test_sms_notification_log(self):
        """Test SMS notification log creation"""
        log = NotificationLog.objects.create(
            alert=self.alert,
            recipient=self.user,
            notification_type='sms',
            recipient_address='+254712345678',
            message_content='ALERT: Unauthorized access detected',
            is_successful=True
        )
        
        self.assertEqual(log.notification_type, 'sms')
        self.assertEqual(log.recipient_address, '+254712345678')
        self.assertTrue(log.is_successful)
        self.assertIsNotNone(log.sent_at)
    
    def test_email_notification_log(self):
        """Test email notification log creation"""
        log = NotificationLog.objects.create(
            alert=self.alert,
            recipient=self.user,
            notification_type='email',
            recipient_address='notif@example.com',
            message_content='Alert notification email body',
            is_successful=True
        )
        
        self.assertEqual(log.notification_type, 'email')
        self.assertEqual(log.recipient_address, 'notif@example.com')
    
    def test_failed_notification_log(self):
        """Test failed notification logging"""
        log = NotificationLog.objects.create(
            alert=self.alert,
            recipient=self.user,
            notification_type='sms',
            recipient_address='+254700000000',
            message_content='Test',
            is_successful=False,
            error_message='Network timeout'
        )
        
        self.assertFalse(log.is_successful)
        self.assertEqual(log.error_message, 'Network timeout')


class AlertRuleTest(TestCase):
    """Test AlertRule model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='ruleuser',
            password='pass123'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='RULE 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_RULE'
        )
    
    def test_alert_rule_creation(self):
        """Test alert rule can be created"""
        rule = AlertRule.objects.create(
            vehicle=self.vehicle,
            name='Critical Security Alert',
            description='Send alerts for unauthorized access',
            trigger_on_unauthorized_access=True,
            trigger_on_failed_auth=True,
            send_sms=True,
            send_email=True,
            notify_owner=True,
            is_active=True
        )
        
        self.assertEqual(rule.vehicle, self.vehicle)
        self.assertTrue(rule.trigger_on_unauthorized_access)
        self.assertTrue(rule.send_sms)
        self.assertTrue(rule.is_active)
    
    def test_speed_alert_rule(self):
        """Test speed monitoring rule"""
        rule = AlertRule.objects.create(
            vehicle=self.vehicle,
            name='Speed Monitor',
            trigger_on_speed_limit=True,
            speed_limit_threshold=100,
            send_sms=True,
            notify_owner=True,
            is_active=True
        )
        
        self.assertTrue(rule.trigger_on_speed_limit)
        self.assertEqual(rule.speed_limit_threshold, 100)
    
    def test_geofence_alert_rule(self):
        """Test geofence breach rule"""
        rule = AlertRule.objects.create(
            vehicle=self.vehicle,
            name='Geofence Monitor',
            trigger_on_geofence_breach=True,
            send_email=True,
            notify_owner=True,
            is_active=True
        )
        
        self.assertTrue(rule.trigger_on_geofence_breach)


class AlertListViewTest(TestCase):
    """Test alert list view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='listuser',
            password='listpass123'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='LIST 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_LIST'
        )
        self.alerts_url = reverse('alerts:alert_list')
        
        # Create test alerts
        for i in range(5):
            Alert.objects.create(
                vehicle=self.vehicle,
                alert_type='test',
                severity='medium',
                title=f'Test Alert {i}',
                message=f'Test message {i}'
            )
    
    def test_alerts_page_requires_login(self):
        """Test alerts page requires authentication"""
        response = self.client.get(self.alerts_url)
        self.assertEqual(response.status_code, 302)
    
    def test_alerts_page_loads(self):
        """Test alerts page loads for authenticated user"""
        self.client.login(username='listuser', password='listpass123')
        response = self.client.get(self.alerts_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/alert_list.html')
    
    def test_alerts_page_shows_all_alerts(self):
        """Test all alerts are displayed"""
        self.client.login(username='listuser', password='listpass123')
        response = self.client.get(self.alerts_url)
        
        # Should have 5 alerts
        self.assertEqual(len(response.context['alerts']), 5)
    
    def test_filter_by_severity(self):
        """Test filtering alerts by severity"""
        # Create critical alert
        Alert.objects.create(
            vehicle=self.vehicle,
            alert_type='unauthorized_access',
            severity='critical',
            title='Critical Alert',
            message='Critical message'
        )
        
        self.client.login(username='listuser', password='listpass123')
        response = self.client.get(self.alerts_url + '?severity=critical')
        
        # Should only show critical alerts
        alerts = response.context['alerts']
        self.assertTrue(all(a.severity == 'critical' for a in alerts))


class AlertDetailViewTest(TestCase):
    """Test alert detail view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='detailuser',
            password='detailpass123'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='DETAIL 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_DETAIL'
        )
        self.alert = Alert.objects.create(
            vehicle=self.vehicle,
            alert_type='unauthorized_access',
            severity='critical',
            title='Unauthorized Access',
            message='Someone tried to start the vehicle',
            location_latitude=-1.0927,
            location_longitude=37.0143
        )
        self.detail_url = reverse('alerts:alert_detail', args=[self.alert.id])
    
    def test_alert_detail_loads(self):
        """Test alert detail page loads"""
        self.client.login(username='detailuser', password='detailpass123')
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/alert_detail.html')
    
    def test_alert_detail_shows_info(self):
        """Test alert detail shows all information"""
        self.client.login(username='detailuser', password='detailpass123')
        response = self.client.get(self.detail_url)
        
        self.assertContains(response, 'Unauthorized Access')
        self.assertContains(response, 'critical')
        self.assertContains(response, 'DETAIL 001')
    
    def test_alert_detail_shows_location(self):
        """Test alert detail shows GPS location"""
        self.client.login(username='detailuser', password='detailpass123')
        response = self.client.get(self.detail_url)
        
        self.assertContains(response, '-1.0927')
        self.assertContains(response, '37.0143')


class AlertAcknowledgeTest(TestCase):
    """Test alert acknowledgment"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='ackuser',
            password='ackpass123'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='ACK 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_ACK'
        )
        self.alert = Alert.objects.create(
            vehicle=self.vehicle,
            alert_type='test',
            severity='medium',
            title='Test',
            message='Test',
            status='pending'
        )
        self.ack_url = reverse('alerts:acknowledge_alert', args=[self.alert.id])
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert"""
        self.client.login(username='ackuser', password='ackpass123')
        response = self.client.post(self.ack_url)
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Alert status should be updated
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, 'acknowledged')


class NotificationLogsViewTest(TestCase):
    """Test notification logs view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='loguser',
            password='logpass123',
            phone_number='+254712345678'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='LOG 001',
            make='Test',
            model='Car',
            year=2020,
            device_id='RPI_LOG'
        )
        self.alert = Alert.objects.create(
            vehicle=self.vehicle,
            alert_type='test',
            severity='medium',
            title='Test',
            message='Test'
        )
        self.logs_url = reverse('alerts:notification_logs')
        
        # Create notification logs
        for i in range(3):
            NotificationLog.objects.create(
                alert=self.alert,
                recipient=self.user,
                notification_type='sms',
                recipient_address='+254712345678',
                message_content=f'Test message {i}',
                is_successful=True
            )
    
    def test_notification_logs_page_loads(self):
        """Test notification logs page loads"""
        self.client.login(username='loguser', password='logpass123')
        response = self.client.get(self.logs_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/notification_logs.html')
    
    def test_notification_logs_shows_all(self):
        """Test all notification logs are displayed"""
        self.client.login(username='loguser', password='logpass123')
        response = self.client.get(self.logs_url)
        
        # Should have 3 logs
        self.assertEqual(len(response.context['logs']), 3)


# Run tests with:
# python manage.py test alerts