from .clients_views import (ClientFeesSetup, Clients, CustomClientFeesProfilesUpdateView,
                      SuperAdminCancelsRootSetupView, SuperAdminRootSetup, toggle_client)
from .collection_setups_views import BaseFormsetView, CollectionFormView, FormatFormView, UploaderFormView
from .disbursement_setups_views import (AddCheckerView, AddMakerView, CategoryFormView, CheckerFormView,
                                  LevelsFormView, LevelsView, MakerFormView, PinFormView)
from .instant_views import ViewerCreateView
from .main_views import (ExpiringAuthToken, OTPLoginView, ProfileUpdateView,
                         ProfileView, RedirectPageView, login_view, ourlogout)
from .password_handling_views import ForgotPasswordView, PasswordResetView, change_password
from .sessions_views import SessionDeleteView, SessionDeleteOtherView, SessionListView
from .super_and_root_views import EntityBranding, Members, UserDeleteView
from .support_views import (ClientsForSupportListView, DocumentForSupportDetailView, DocumentsForSupportListView,
                            SuperAdminSupportSetupCreateView, SupportHomeView, SupportUsersListView)
