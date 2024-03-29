from .clients_views import (
    ClientFeesSetup, Clients, CustomClientFeesProfilesUpdateView,
    SuperAdminFeesProfileTemplateView, SuperAdminCancelsRootSetupView, SuperAdminRootSetup,
    toggle_client, ClientFeesUpdate
)
from .disbursement_setups_views import (AddCheckerView, AddMakerView, CategoryFormView, CheckerFormView,
                                  LevelsFormView, LevelsView, MakerFormView, PinFormView, BaseFormsetView, change_pin_view)
from .instant_views import APICheckerCreateView, ViewerCreateView, OAuth2ApplicationDetailView
from .main_views import (ExpiringAuthToken, OTPLoginView, ProfileUpdateView,
                         ProfileView, RedirectPageView, login_view, ourlogout)
from .password_handling_views import ForgotPasswordView, PasswordResetView, change_password
from .sessions_views import SessionDeleteView, SessionDeleteOtherView, SessionListView
from .super_and_root_views import EntityBranding, Members, UserDeleteView
from .support_views import (
    ClientsForSupportListView, DocumentForSupportDetailView, DocumentsForSupportListView,
    SuperAdminSupportSetupCreateView, SupportHomeView, SupportUsersListView,
    OnboardingNewInstantAdmin, ClientCredentialsDetails
)
from .onboard_user_view import (
    OnboardUsersListView, OnbooardUserHomeView, SuperAdminOnboardSetupCreateView
)
from .supervisor_views import (
    SupervisorUsersListView, SuperAdminSupervisorSetupCreateView, SupervisorUserHomeView,
    SupervisorReactivateSupportView
)
