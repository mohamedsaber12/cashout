# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase,Client, RequestFactory
from disbursement.api import permission_classes
from django.contrib.auth.models import Permission
from disbursement.factories import VariousAgentFactory
from users.models.instant_api_checker import InstantAPICheckerUser
from users.models.instant_api_viewer import InstantAPIViewerUser
from users.models.root import RootUser

from users.tests.factories import VariousOnboardingSuperAdminUserFactory
from users.models import SuperAdminUser
from users.tests.factories import (
    SuperAdminUserFactory, VMTDataFactory, AdminUserFactory
)
from users.models import (
    SuperAdminUser, Client as ClientModel)
from django.core.exceptions import ValidationError

from users.tests.factories import (
    SuperAdminUserFactory, AdminUserFactory, VMTDataFactory
)
from users.models import (
    Setup, Client as ClientModel, Brand, EntitySetup, CheckerUser, Levels,
    MakerUser,OnboardUser,OnboardUserSetup,SupervisorUser,SupervisorSetup,SupportUser,SupportSetup,UploaderUser,UpmakerUser
)
from data.models import Doc, DocReview, FileCategory
from utilities.models import Budget, FeeSetup
from disbursement.models import Agent, DisbursementDocData
from django.urls import reverse, reverse_lazy
from rest_framework_expiring_authtoken.models import ExpiringToken




class ModelTests(TestCase):
    """
    Tests for the users application models
    """

    def test_successful_creating_default_vodafone_superadmin(self):
        """Test successfully creating superadmin user with default vodafone onboarding permissions"""
        superadmin = VariousOnboardingSuperAdminUserFactory.default_vodafone()
        self.assertEqual(superadmin.username, str(superadmin))
        self.assertTrue(superadmin.is_superadmin)
        self.assertEqual(superadmin, superadmin.vmt.vmt)
        self.assertTrue(superadmin.has_perm("users.vodafone_default_onboarding"))
        self.assertEqual(superadmin.agents.all().count(), 0)        
        self.assertRaises(ValueError, superadmin.first_non_super_agent, 'etisalat')

        


    def test_successful_creating_accept_vodafone_superadmin(self):
        """Test successfully creating superadmin user with accept vodafone onboarding permissions"""
        superadmin = VariousOnboardingSuperAdminUserFactory.accept_vodafone()
        self.assertEqual(superadmin.username, str(superadmin))
        self.assertTrue(superadmin.is_superadmin)
        self.assertEqual(superadmin, superadmin.vmt.vmt)
        self.assertTrue(superadmin.has_perm("users.accept_vodafone_onboarding"))
        self.assertIn(superadmin.wallet_fees_profile, ["Full", "Half", "No fees"])
        self.assertGreaterEqual(superadmin.agents.all().count(), 3)
        

    def test_successful_creating_instant_superadmin(self):
        """Test successfully creating superadmin user with instant onboarding permissions"""
        superadmin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        self.assertEqual(superadmin.username, str(superadmin))
        self.assertTrue(superadmin.is_superadmin)
        self.assertEqual(superadmin, superadmin.vmt.vmt)
        self.assertTrue(superadmin.has_perm("users.instant_model_onboarding"))
        self.assertGreaterEqual(superadmin.agents.all().count(), 3)
        msisdn=superadmin.first_non_super_agent(wallet_issuer="etisalat")
        self.assertEqual('01100926774',msisdn)
        
    
    def test_creating_superadmin(self):

        superadmin = SuperAdminUser.objects.create_user(username="test_user")
        self.assertEqual(superadmin.is_staff,True)
        self.assertEqual(superadmin.user_type,0)
        self.assertEqual(superadmin.is_superuser,False)
    


    def test_get_all_hierarchy_tree(self):
        all=SuperAdminUser.objects.get_all_hierarchy_tree(0)
        self.assertGreaterEqual(all.count(), 0)
        all_makers=SuperAdminUser.objects.get_all_makers(0)
        self.assertEqual(all_makers.count(),0)
        all_checkers=SuperAdminUser.objects.get_all_checkers(0)
        self.assertEqual(all_checkers.count(),0)
    
    def test_set_pin(self):
        superadmin = SuperAdminUser.objects.create_user(username="test_user")
        superadmin.set_pin("123456")

    def test_check_pin(self):
        superadmin = SuperAdminUser.objects.create_user(username="test_user")
        superadmin.check_pin("123456")

    def test_children_for_superadmin(self):
        self.superadmin = SuperAdminUser.objects.create_user(username="test_user")
        self.vmt_data_obj = VMTDataFactory(vmt=self.superadmin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.root.save()
        self.client_user = ClientModel(client=self.root, creator=self.superadmin)
        self.client_user.save()
        children= self.superadmin.children()
        self.assertEqual(len(children),1)

    def test_children_for_root(self):
        self.root = AdminUserFactory(user_type=3)
        children= self.root.children()
        self.assertEqual(len(children),0)

    def test_children_for_other(self):
        self.root = AdminUserFactory(user_type=2)
        with self.assertRaises(ValidationError) as exception_text:
            self.root.children()
        self.assertTrue(
            "This user has no children'"
            in str(exception_text.exception))

    def test_can_view_docs(self):
        superadmin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        self.assertTrue(superadmin.can_view_docs)

    def test_can_not_view_docs(self):
        self.root = AdminUserFactory(user_type=3)
        self.assertFalse(self.root.can_view_docs)

    def test_can_disburse(self):
        self.root = AdminUserFactory(user_type=3)
        superadmin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        self.assertFalse(superadmin.can_disburse)
        self.root.user_permissions.add(
            Permission.objects.get(content_type__app_label="data", codename="can_disburse")
        )
        self.assertTrue(self.root.can_disburse)

    def test_super_admin_property(self):
        self.superadmin = SuperAdminUser.objects.create(username="test_user")
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.root.save()
        self.client_user = ClientModel(client=self.root, creator=self.superadmin)
        self.client_user.save()
        self.assertEqual(self.superadmin.super_admin,self.superadmin)
        self.assertEqual(self.root.super_admin,self.superadmin)

    def test_can_pass_disbursement_and_can_pass_collection(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.access_top_up_balance=True
        self.root.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
            uploaders_setup=True,
            format_collection_setup=True,
            collection_setup=True,
        )

        self.assertTrue(self.root.can_pass_disbursement)
        self.assertTrue(self.root.can_pass_collection)
        self.assertTrue(self.root.has_access_to_topUp_balance)

        self.root2 = AdminUserFactory(user_type=3)
        self.assertFalse(self.root2.can_pass_disbursement)
        self.assertFalse(self.root2.can_pass_collection)

        superadmin_user = VariousOnboardingSuperAdminUserFactory.create_new_superadmin()
        VariousAgentFactory.mandatory_agents(agent_provider=superadmin_user)
        superadmin_user.user_permissions.add(
            Permission.objects.get(content_type__app_label="users", codename="instant_model_onboarding")
        )
        superadmin_user.save()
        self.assertTrue(superadmin_user.is_instant_member)

    def test_is_vodafone_monthly_report_and_is_system_admin(self):
        self.vodafone_monthly_report_user = AdminUserFactory(user_type=13)
        self.system_admin_user = AdminUserFactory(user_type=14)
        self.assertTrue(self.vodafone_monthly_report_user.is_vodafone_monthly_report)
        self.assertTrue(self.system_admin_user.is_system_admin)


    def test_has_vmt_setup(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.access_top_up_balance=True
        self.root.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
            uploaders_setup=True,
            format_collection_setup=True,
            collection_setup=True,
        )
        # self.root2 = AdminUserFactory(user_type=3)
        # self.super_admin2 = SuperAdminUserFactory()
        # self.client_user = ClientModel(client=self.root2, creator=self.super_admin2)
        # self.client_user.save()

        self.assertTrue(self.super_admin.has_vmt_setup)
        self.assertTrue(self.root.has_vmt_setup)

    def test_with_except(self):
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.super_admin = SuperAdminUserFactory()
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.assertFalse(self.root.has_vmt_setup)
        self.checker_user = CheckerUser.objects.create(
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.assertFalse(self.checker_user.has_vmt_setup)

    def test_has_custom_budget(self):
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.root.save()
        self.budget = Budget.objects.create(disburser=self.root, current_balance=150)
        self.assertTrue(self.root.has_custom_budget)
    
    def test_has_custom_budget_with_except(self):
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.root.save()
        self.assertFalse(self.root.has_custom_budget)
    
    def test_superadmin_has_uncomplete_entity_creation(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin,
            entity=self.root,
            agents_setup=True,
            fees_setup=False)
        
        self.assertEqual(self.super_admin.uncomplete_entity_creation(),self.entity_setup)

        self.assertTrue(self.super_admin.has_uncomplete_entity_creation())
        
    def test_get_absolute_url(self):
        self.client = Client()
        self.super_admin = SuperAdminUserFactory()
        # response = self.client.get(reverse('users:profile',kwargs={'username': self.username}))
        self.assertEqual(self.super_admin.get_absolute_url(),reverse('users:profile',kwargs={'username': self.super_admin.username}))

    def test_data_type(self):
        self.root1 = AdminUserFactory(user_type=3)
        self.root1.root=self.root1
        self.root1.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root1.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_collection')
        )
        self.root1.save()
        self.root2 = AdminUserFactory(user_type=3)
        self.root2.root =self.root2
        self.root2.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_collection')
        )
        self.root2.save()

        self.assertEqual(self.root1.data_type(),3)
        self.assertEqual(self.root2.data_type(),2)

    def test_get_status(self):
        self.request = RequestFactory()
        self.root1 = AdminUserFactory(user_type=3)
        self.root1.root=self.root1
        
        self.root1.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_collection')
        )
        self.root1.save()
        self.assertEqual(self.root1.get_status(self.request),"collection")
    """end test for base_user"""

    def test_checker_maker_creation(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
                user=self.root,
                levels_setup=True,
                maker_setup=True,
                checker_setup=True,
                category_setup=True,
                pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
                user=self.super_admin,
                entity=self.root,
                agents_setup=True,
                fees_setup=True
        )
        self.checker_user = CheckerUser.objects.create_user(
                hierarchy=1,
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.level = Levels.objects.create(
                max_amount_can_be_disbursed=1200,
                created=self.root
        )
        self.checker_user.level = self.level
        self.checker_user.save()
        self.maker_user = MakerUser.objects.create_user(
                hierarchy=1,
                id=14,
                username='test_maker_user',
                email='t@mk.com',
                root=self.root,
                user_type=1
        )

        with self.assertRaises(ValueError) as exception_text:
             CheckerUser.objects.create_user(
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.assertTrue(
            "The given hierarchy must be set"
            in str(exception_text.exception))
        with self.assertRaises(ValueError) as exception_text:
             MakerUser.objects.create_user(
               id=15,
                username='test_maker_user',
                root=self.root,
                user_type=1
        )
        self.assertTrue(
            "The given hierarchy must be set"
            in str(exception_text.exception))
        self.assertEqual(self.checker_user.username,"test_checker_user")
        self.assertEqual(self.maker_user.username,"test_maker_user")

    '''test client model'''

    def test_client_function(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin,fees_percentage=100, custom_profile="test_client")
        self.client_user.save()

        # self.assertTrue(self.client_user.toggle_activation())
        # self.assertFalse(self.client_user.toggle_activation())
        self.assertEqual(self.client_user.__str__(),f'The client: {self.client_user.client.username} owned by superadmin: {self.super_admin}')
        self.assertEqual(self.client_user.get_absolute_url(),reverse('users:update_fees',kwargs={'username': self.client_user.client.username}))
        self.assertEqual(self.client_user.get_fees(),'test_client')
        self.client_user.custom_profile=''
        self.client_user.save()
        self.assertEqual(self.client_user.get_fees(),'Full')
        self.client_user.toggle_activation()
        self.client_user.toggle_activation()
        self.client_user.fees_percentage=50
        self.client_user.save()
        self.assertEqual(self.client_user.get_fees(),'Half')
        self.client_user.fees_percentage=0
        self.client_user.save()
        self.assertEqual(self.client_user.get_fees(),'No fees')
        self.client_user.delete_client()
        client= ClientModel.objects.toggle()

        '''test entity setups model'''

    def test_entity_setups_model(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin,
            entity=self.root,
            agents_setup=True,
            fees_setup=True
        )

        self.assertEqual(self.entity_setup.__str__(),f'{self.super_admin} setup for {self.root} entity')
        self.assertTrue(self.entity_setup.can_pass())   
        self.assertEqual(self.entity_setup.percentage,100)
        self.entity_setup.agents_setup=False
        self.entity_setup.save()
        token, created = ExpiringToken.objects.get_or_create(user=self.entity_setup.entity)
        self.assertEqual(self.entity_setup.get_reverse(),reverse_lazy('disbursement:add_agents', kwargs={'token': token.key}))
        self.entity_setup.agents_setup=True
        self.entity_setup.fees_setup=False
        self.entity_setup.save()
        self.assertEqual(self.entity_setup.get_reverse(),reverse_lazy('users:add_fees', kwargs={'token': token.key}))

    def test_instant_api_checker_and_viewer(self):
        self.super_admin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        # self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root, super=True)
        self.agent.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
            uploaders_setup=True,
            format_collection_setup=True,
            collection_setup=True
        )
        self.checker_user = InstantAPICheckerUser.objects.create_user(
                hierarchy=1,
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.level = Levels.objects.create(
                max_amount_can_be_disbursed=1200,
                created=self.root
        )
        self.checker_user.level = self.level
        self.checker_user.save()
        self.maker_user = InstantAPIViewerUser.objects.create_user(
                hierarchy=1,
                id=14,
                username='test_maker_user',
                email='t@mk.com',
                root=self.root,
                user_type=1
        )

        with self.assertRaises(ValueError) as exception_text:
             InstantAPICheckerUser.objects.create_user(
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.assertTrue(
            "The given hierarchy must be set"
            in str(exception_text.exception))
        with self.assertRaises(ValueError) as exception_text:
             InstantAPIViewerUser.objects.create_user(
               id=15,
                username='test_maker_user',
                root=self.root,
                user_type=1
        )
        self.assertTrue(
            "The given hierarchy must be set"
            in str(exception_text.exception))
        self.assertNotEqual(InstantAPIViewerUser.objects.get_queryset().count(),1)
        self.assertNotEqual(InstantAPICheckerUser.objects.get_queryset().count(),1)

        '''test setups'''
        self.assertEqual(self.setup.__str__(),'{0}_setup'.format(str(self.root)))
        self.assertTrue(self.setup.can_add_users())
        self.setup.levels_setup=False
        self.setup.save()
        self.assertFalse(self.setup.can_add_users())
        self.assertEqual(self.setup.collection_percentage,100)
        self.assertEqual(len(self.setup.collection_enabled_steps()),3)




    '''test onboard user'''
    def test_onboard_user_and_supervisor(self):
        self.super_admin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        Onboard_User= OnboardUser.objects.create_user(username="test_onboard_user")
        self.assertEqual(OnboardUser.objects.get_queryset().count(),1)
        Onboard_User_Setup= OnboardUserSetup(onboard_user=Onboard_User,user_created=self.super_admin)
        self.assertEqual(Onboard_User_Setup.__str__(),f'{self.super_admin} setup for {Onboard_User}')
        '''test supervisor'''
        Supervisor_User=SupervisorUser.objects.create_user(username="supervisor_user",email="supervisor@gmail.com")
        Supervisor_User_setup=SupervisorSetup.objects.create(supervisor_user=Supervisor_User, user_created=self.super_admin)
        self.assertEqual(Supervisor_User_setup.__str__(),f'{self.super_admin} setup for {Supervisor_User}')
        self.assertEqual(SupervisorUser.objects.get_queryset().count(),1)

    
    def test_root(self):
        root=RootUser.objects.create_user(username="root_user")


    def test_support_user(self):
        support_user=SupportUser.objects.create_user(username="support_user",email="support_user@gmail.com")
        self.super_admin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        support_user_setup=SupportSetup.objects.create(support_user=support_user, user_created=self.super_admin)
        self.assertEqual(SupportUser.objects.get_queryset().count(),1)
        self.assertEqual(support_user_setup.__str__(),f'{self.super_admin} setup for {support_user}')

    def test_uploader_and_upmaker(self):
        self.super_admin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        # self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root, super=True)
        self.agent.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()

        uploader=UploaderUser.objects.create_user(
            hierarchy=1,
            username='test_uploader_user',
            email='test_uploader_user@gmail.com',
            root=self.root,

        )
        upmaker=UpmakerUser.objects.create_user(
            hierarchy=1,
            username='test_upmaker_user',
            root=self.root,
            email='test_upmaker_user@gmail.com'

        )
        self.assertEqual(UpmakerUser.objects.get_queryset().count(),1)
        with self.assertRaises(ValueError) as exception_text:
             UploaderUser.objects.create_user(
                username='test_uploader_user',
        )
        self.assertTrue(
            "The given hierarchy must be set"
            in str(exception_text.exception))

        with self.assertRaises(ValueError) as exception_text:
             UpmakerUser.objects.create_user(
                username='test_upmaker_user',
        )
        self.assertTrue(
            "The given hierarchy must be set"
            in str(exception_text.exception))









        
        





















































