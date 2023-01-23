from .clients_views import (ClientFeesSetup, ClientFeesUpdate, Clients,
                            CustomClientFeesProfilesUpdateView,
                            SuperAdminCancelsRootSetupView,
                            SuperAdminFeesProfileTemplateView,
                            OnboardingNewMerchant,
                            SuperAdminRootSetup, toggle_client)
from .disbursement_setups_views import (AddCheckerView, AddMakerView,
                                        BaseFormsetView, CategoryFormView,
                                        CheckerFormView, LevelsFormView,
                                        LevelsView, MakerFormView, PinFormView,
                                        change_pin_view,
                                        vodafone_change_pin_view)
from .instant_views import (APICheckerCreateView, OAuth2ApplicationDetailView,
                            ViewerCreateView)
from .main_views import (ExpiringAuthToken, LevelUpdateView, OTPLoginView,
                         ProfileUpdateView, ProfileView, RedirectPageView,
                         login_view, ourlogout)
from .onboard_user_view import (OnboardUsersListView, OnbooardUserHomeView,
                                SuperAdminOnboardSetupCreateView)
from .password_handling_views import (ForgotPasswordView, PasswordResetView,
                                      change_password)
from .sessions_views import (SessionDeleteOtherView, SessionDeleteView,
                             SessionListView)
from .super_and_root_views import EntityBranding, Members, UserDeleteView
from .supervisor_views import (SuperAdminSupervisorSetupCreateView,
                               SupervisorReactivateSupportView,
                               SupervisorUserHomeView, SupervisorUsersListView)
from .support_views import (ClientCredentialsDetails,
                            ClientsForSupportListView,
                            DocumentForSupportDetailView,
                            DocumentsForSupportListView,
                            OnboardingNewInstantAdmin,
                            SuperAdminSupportSetupCreateView, SupportHomeView,
                            SupportUsersListView)
